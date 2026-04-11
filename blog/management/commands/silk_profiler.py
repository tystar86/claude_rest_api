"""
Management command to profile all API endpoints via django-silk.

Hits every endpoint using Django's test Client (goes through middleware,
so SilkyMiddleware captures real SQL queries, timings, etc.), then queries
Silk's database tables and prints a formatted report.

Run:
    python manage.py silk_profiler
    python manage.py silk_profiler --keep       # don't wipe previous Silk data
    python manage.py silk_profiler --repeat 5   # hit each endpoint 5 times
    python manage.py silk_profiler --verbose     # show per-query SQL breakdown
"""

from __future__ import annotations

import json

from django.apps import apps
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.test import Client
from django.utils import timezone

from blog.models import Comment, CommentVote, Post, Tag


# ---------------------------------------------------------------------------
# Endpoint definitions
# ---------------------------------------------------------------------------


def _build_endpoints(post_slug, tag_slug, username, comment_id):
    """Return a list of (method, path, payload | None, description) tuples."""
    return [
        # ── Public reads ──────────────────────────────────────────────
        ("GET", "/api/dashboard/", None, "Dashboard (aggregated stats)"),
        ("GET", "/api/posts/", None, "Post list (page 1)"),
        ("GET", "/api/posts/?page=2", None, "Post list (page 2)"),
        ("GET", f"/api/posts/{post_slug}/", None, "Post detail + comments"),
        ("GET", "/api/tags/", None, "Tag list"),
        ("GET", f"/api/tags/{tag_slug}/", None, "Tag detail + posts"),
        ("GET", "/api/comments/", None, "Comment list"),
        ("GET", "/api/users/", None, "User list"),
        ("GET", f"/api/users/{username}/", None, "User profile"),
        ("GET", f"/api/users/{username}/comments/", None, "User comments"),
        # ── Auth endpoints ────────────────────────────────────────────
        ("GET", "/api/auth/csrf/", None, "CSRF token"),
        ("GET", "/api/auth/user/", None, "Current user (auth'd)"),
        # ── Writes (auth'd) ──────────────────────────────────────────
        (
            "POST",
            "/api/posts/",
            {"title": "Silk profiler test post", "body": "Profiling body."},
            "Create post",
        ),
        (
            "POST",
            f"/api/posts/{post_slug}/comments/",
            {"body": "Silk profiler test comment."},
            "Create comment",
        ),
        (
            "POST",
            f"/api/comments/{comment_id}/vote/",
            {"vote": "like"},
            "Vote on comment",
        ),
    ]


def _split_endpoints(endpoints):
    read_endpoints = [endpoint for endpoint in endpoints if endpoint[0] == "GET"]
    write_endpoints = [endpoint for endpoint in endpoints if endpoint[0] != "GET"]
    return read_endpoints, write_endpoints


def _request(client, method, path, payload, host):
    if method == "GET":
        return client.get(path, **host)
    if method == "POST":
        return client.post(
            path,
            data=json.dumps(payload),
            content_type="application/json",
            **host,
        )
    if method == "PATCH":
        return client.patch(
            path,
            data=json.dumps(payload),
            content_type="application/json",
            **host,
        )
    if method == "DELETE":
        return client.delete(path, **host)
    return None


def _run_endpoints(client, endpoints, repeat, host):
    responses = []
    for _ in range(repeat):
        for method, path, payload, desc in endpoints:
            resp = _request(client, method, path, payload, host)
            if resp is None:
                continue
            responses.append((method, path, resp.status_code, desc))
    return responses


def _cleanup_write_side_effects(user_id, vote_comment_id):
    CommentVote.objects.filter(user_id=user_id, comment_id=vote_comment_id).delete()
    Comment.objects.filter(
        author_id=user_id, body="Silk profiler test comment."
    ).delete()
    Post.objects.filter(author_id=user_id, title="Silk profiler test post").delete()


def _run_write_endpoints(client, endpoints, repeat, host, user_id, vote_comment_id):
    responses = []
    for _ in range(repeat):
        responses.extend(_run_endpoints(client, endpoints, 1, host))
        _cleanup_write_side_effects(user_id, vote_comment_id)
    return responses


# ---------------------------------------------------------------------------
# Report helpers
# ---------------------------------------------------------------------------

_HEADER = (
    f"{'#':>3}  {'Method':<6}  {'Path':<42}  {'Status':>6}  "
    f"{'Time ms':>8}  {'Queries':>7}  {'SQL ms':>8}  {'Description'}"
)
_SEP = "-" * 140


def _fmt_row(idx, method, path, status_code, time_ms, num_queries, sql_ms, desc):
    return (
        f"{idx:>3}  {method:<6}  {path:<42}  {status_code:>6}  "
        f"{time_ms:>8.1f}  {num_queries:>7}  {sql_ms:>8.1f}  {desc}"
    )


def _print_sql_breakdown(silk_req, stdout):
    """Print individual SQL queries for a Silk request."""
    queries = silk_req.queries.order_by("start_time")
    if not queries.exists():
        return
    stdout.write(f"        {'#':>3}  {'Time ms':>8}  {'Query (first 120 chars)'}")
    for i, sq in enumerate(queries, 1):
        q_time = sq.time_taken or 0.0
        q_text = (sq.query or "")[:120].replace("\n", " ")
        stdout.write(f"        {i:>3}  {q_time:>8.2f}  {q_text}")


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


class Command(BaseCommand):
    help = "Profile all API endpoints with django-silk and print a report."

    def add_arguments(self, parser):
        parser.add_argument(
            "--keep",
            action="store_true",
            help="Keep previous Silk data (default: clear before run).",
        )
        parser.add_argument(
            "--repeat",
            type=int,
            default=1,
            help="Number of times to hit each endpoint (default: 1).",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show per-query SQL breakdown for each request.",
        )

    def handle(self, *args, **options):
        if not apps.is_installed("silk"):
            raise CommandError(
                "django-silk is not enabled. Add 'silk' to INSTALLED_APPS, "
                "enable SilkyMiddleware, and include the /silk/ URL before running "
                "this command."
            )
        try:
            from silk.models import Request as SilkRequest
        except ImportError as exc:
            raise CommandError(
                "django-silk is not installed in the active environment."
            ) from exc

        keep = options["keep"]
        repeat = options["repeat"]
        verbose = options["verbose"]

        # -- Resolve sample data from the local DB ---------------------------
        post = Post.objects.filter(status=Post.Status.PUBLISHED).first()
        tag = Tag.objects.first()
        user = User.objects.first()
        comment = Comment.objects.first()

        if not all([post, tag, user, comment]):
            self.stderr.write(
                self.style.ERROR(
                    "Local DB is missing seed data (need at least 1 post, tag, "
                    "user, comment).  Run:  python manage.py seed_large"
                )
            )
            return

        endpoints = _build_endpoints(post.slug, tag.slug, user.username, comment.id)
        read_endpoints, write_endpoints = _split_endpoints(endpoints)

        # -- Optionally clear previous Silk data -----------------------------
        if not keep:
            deleted, _ = SilkRequest.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f"Cleared {deleted} previous Silk records.")
            )

        # -- Mark the start so we only query our requests --------------------
        run_marker = timezone.now()

        # -- Set up authenticated Django test Client -------------------------
        client = Client(enforce_csrf_checks=False)
        client.force_login(user)

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"\nProfiling {len(read_endpoints)} read endpoints x{repeat} "
                f"plus {len(write_endpoints)} write endpoints x{repeat} "
                f"(user: {user.username}) ...\n"
            )
        )

        # -- Hit read endpoints first so write invalidations do not skew them --
        # SERVER_NAME='localhost' avoids DisallowedHost for 'testserver'.
        host = {"SERVER_NAME": "localhost"}
        responses = _run_endpoints(client, read_endpoints, repeat, host)
        responses.extend(
            _run_write_endpoints(
                client, write_endpoints, repeat, host, user.id, comment.id
            )
        )

        # -- Collect Silk data for this run ----------------------------------
        silk_requests = (
            SilkRequest.objects.filter(start_time__gte=run_marker)
            .order_by("start_time")
            .prefetch_related("queries")
        )

        # Match Silk requests to our responses by chronological order
        # (path-based matching breaks with query strings like ?page=2).
        silk_list = list(silk_requests)

        # -- Print detailed table --------------------------------------------
        self.stdout.write(_SEP)
        self.stdout.write(_HEADER)
        self.stdout.write(_SEP)

        total_time = 0.0
        total_queries = 0
        total_sql_time = 0.0
        slowest = (0, "", "", 0.0)  # (idx, method, path, time_ms)
        most_queries = (0, "", "", 0)  # (idx, method, path, count)

        for idx, (method, path, status_code, desc) in enumerate(responses, 1):
            sr = silk_list[idx - 1] if idx <= len(silk_list) else None

            if sr:
                time_ms = sr.time_taken or 0.0
                num_q = sr.num_sql_queries
                # meta_time_spent_queries is often null; sum from actual queries
                sql_ms = sr.meta_time_spent_queries or 0.0
                if not sql_ms:
                    sql_ms = sum(q.time_taken or 0.0 for q in sr.queries.all())
            else:
                time_ms = 0.0
                num_q = 0
                sql_ms = 0.0

            self.stdout.write(
                _fmt_row(idx, method, path, status_code, time_ms, num_q, sql_ms, desc)
            )
            if verbose and sr:
                _print_sql_breakdown(sr, self.stdout)

            total_time += time_ms
            total_queries += num_q
            total_sql_time += sql_ms

            if time_ms > slowest[3]:
                slowest = (idx, method, path, time_ms)
            if num_q > most_queries[3]:
                most_queries = (idx, method, path, num_q)

        self.stdout.write(_SEP)

        # -- Summary ---------------------------------------------------------
        n = len(responses)
        success = sum(1 for _, _, s, _ in responses if 200 <= s < 300)
        client_err = sum(1 for _, _, s, _ in responses if 400 <= s < 500)
        server_err = sum(1 for _, _, s, _ in responses if s >= 500)

        self.stdout.write(self.style.MIGRATE_HEADING("\n  Summary\n"))
        self.stdout.write(f"  Requests total:      {n}")
        self.stdout.write(
            f"  Status breakdown:    "
            f"{self.style.SUCCESS(f'{success} 2xx')}  "
            f"{self.style.WARNING(f'{client_err} 4xx')}  "
            f"{self.style.ERROR(f'{server_err} 5xx')}"
        )
        self.stdout.write(f"  Wall time (sum):     {total_time:,.1f} ms")
        self.stdout.write(
            f"  Avg per request:     {total_time / n:,.1f} ms" if n else ""
        )
        self.stdout.write(f"  SQL queries total:   {total_queries}")
        self.stdout.write(
            f"  Avg queries/request: {total_queries / n:,.1f}" if n else ""
        )
        self.stdout.write(f"  SQL time total:      {total_sql_time:,.1f} ms")
        self.stdout.write(
            f"  Avg SQL time/req:    {total_sql_time / n:,.1f} ms" if n else ""
        )

        self.stdout.write(self.style.MIGRATE_HEADING("\n  Hotspots\n"))
        self.stdout.write(
            f"  Slowest request:     #{slowest[0]}  {slowest[1]} {slowest[2]}  "
            f"({slowest[3]:,.1f} ms)"
        )
        self.stdout.write(
            f"  Most SQL queries:    #{most_queries[0]}  {most_queries[1]} "
            f"{most_queries[2]}  ({most_queries[3]} queries)"
        )

        # -- Per-endpoint averages (when repeat > 1) -------------------------
        if repeat > 1:
            self.stdout.write(self.style.MIGRATE_HEADING("\n  Per-endpoint averages\n"))
            self.stdout.write(
                f"  {'Method':<6}  {'Path':<42}  "
                f"{'Avg ms':>8}  {'Avg Q':>7}  {'Avg SQL ms':>10}  {'Hits':>5}"
            )
            self.stdout.write("  " + "-" * 90)

            # Compute from collected Silk requests (avoids null meta fields)
            from collections import defaultdict

            buckets: dict[tuple[str, str], list[tuple[float, int, float]]] = (
                defaultdict(list)
            )
            for sr in silk_requests:
                sql_t = sr.meta_time_spent_queries or 0.0
                if not sql_t:
                    sql_t = sum(q.time_taken or 0.0 for q in sr.queries.all())
                buckets[(sr.method, sr.path)].append(
                    (sr.time_taken or 0.0, sr.num_sql_queries, sql_t)
                )

            rows = []
            for (m, p), vals in buckets.items():
                hits = len(vals)
                avg_t = sum(v[0] for v in vals) / hits
                avg_q = sum(v[1] for v in vals) / hits
                avg_s = sum(v[2] for v in vals) / hits
                rows.append((avg_t, m, p, avg_q, avg_s, hits))
            rows.sort(reverse=True)  # slowest first

            for avg_t, m, p, avg_q, avg_s, hits in rows:
                self.stdout.write(
                    f"  {m:<6}  {p:<42}  "
                    f"{avg_t:>8.1f}  {avg_q:>7.1f}  {avg_s:>10.1f}  {hits:>5}"
                )

        self.stdout.write(self.style.SUCCESS("\nDone. Silk UI available at: /silk/\n"))
