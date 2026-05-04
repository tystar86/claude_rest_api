"""
Management command to seed a large, production-like demo dataset.
Run: python manage.py seed_large
Add --clear to wipe previously seeded data first.
"""

import random
import re
from bisect import bisect_left
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from blog.models import Comment, CommentVote, Post, Tag

User = get_user_model()

SEED_USER_COUNT = 1000
SEED_POST_TARGET = 50000
SEED_EMAIL_DOMAIN = "seed.blogit.example.dev"

# ---------------------------------------------------------------------------
# Static data pools
# ---------------------------------------------------------------------------

TAGS = [
    ("Python", "python"),
    ("JavaScript", "javascript"),
    ("Rust", "rust"),
    ("Go", "go"),
    ("Docker", "docker"),
    ("Kubernetes", "kubernetes"),
    ("PostgreSQL", "postgresql"),
    ("Redis", "redis"),
    ("REST API", "rest-api"),
    ("GraphQL", "graphql"),
    ("Machine Learning", "machine-learning"),
    ("DevOps", "devops"),
    ("Security", "security"),
    ("Microservices", "microservices"),
    ("CI/CD", "ci-cd"),
    ("AWS", "aws"),
    ("Linux", "linux"),
    ("Git", "git"),
    ("TypeScript", "typescript"),
    ("System Design", "system-design"),
]

FIRST_NAMES = [
    "Olivia",
    "Liam",
    "Emma",
    "Noah",
    "Ava",
    "Mateo",
    "Sofia",
    "Ethan",
    "Mia",
    "Lucas",
    "Amelia",
    "Leo",
    "Isabella",
    "Mason",
    "Harper",
    "Elijah",
    "Evelyn",
    "Logan",
    "Charlotte",
    "James",
    "Aria",
    "Benjamin",
    "Nora",
    "Alexander",
    "Luna",
    "Samuel",
    "Ella",
    "Daniel",
    "Chloe",
    "Jack",
    "Grace",
    "Henry",
    "Zoe",
    "David",
    "Hannah",
    "Michael",
    "Layla",
    "Sebastian",
    "Scarlett",
    "Julian",
    "Avery",
    "Wyatt",
    "Penelope",
    "Owen",
    "Mila",
    "Theodore",
    "Riley",
    "Gabriel",
    "Stella",
    "Levi",
    "Aurora",
    "Isaac",
    "Paisley",
    "Nathan",
    "Aaliyah",
    "Adrian",
    "Elena",
    "Caleb",
    "Naomi",
    "Dylan",
    "Alice",
    "Roman",
    "Hazel",
    "Elias",
    "Lucy",
    "Jasper",
    "Ivy",
    "Connor",
    "Maya",
]

LAST_NAMES = [
    "Martin",
    "Smith",
    "Nguyen",
    "Johnson",
    "Garcia",
    "Kim",
    "Brown",
    "Patel",
    "Taylor",
    "Lopez",
    "Anderson",
    "Clark",
    "Walker",
    "Wright",
    "Hill",
    "Allen",
    "Young",
    "Scott",
    "Adams",
    "Baker",
    "Nelson",
    "Carter",
    "Mitchell",
    "Perez",
    "Roberts",
    "Turner",
    "Phillips",
    "Campbell",
    "Parker",
    "Evans",
    "Edwards",
    "Collins",
    "Stewart",
    "Sanchez",
    "Morris",
    "Rogers",
    "Reed",
    "Cook",
    "Morgan",
    "Bell",
    "Murphy",
    "Bailey",
    "Rivera",
    "Cooper",
    "Richardson",
    "Cox",
    "Howard",
    "Ward",
    "Torres",
    "Peterson",
    "Gray",
    "Ramirez",
    "James",
    "Watson",
    "Brooks",
    "Kelly",
    "Sanders",
    "Price",
    "Bennett",
    "Wood",
    "Barnes",
    "Ross",
    "Henderson",
    "Coleman",
    "Jenkins",
    "Perry",
    "Powell",
    "Long",
    "Flores",
    "Russell",
]

BIO_TEMPLATES = [
    "Senior {role} with {n}+ years experience. Passionate about {tech1} and {tech2}.",
    "{role} focused on {tech1}, {tech2}, and distributed systems. Open source contributor.",
    "Full-stack {role} specialising in {tech1} and cloud-native {tech2} architectures.",
    "Backend {role} with deep expertise in {tech1}. Currently exploring {tech2}.",
    "{role} at a fintech startup. Loves {tech1}, hates flaky tests. {tech2} advocate.",
    "Platform {role} obsessed with {tech1} reliability and {tech2} automation.",
    "Software {role} building high-throughput systems with {tech1} and {tech2}.",
]

ROLES = ["engineer", "developer", "architect", "consultant", "lead"]
TECH_WORDS = [
    "Python",
    "Go",
    "Rust",
    "TypeScript",
    "Kubernetes",
    "PostgreSQL",
    "Redis",
    "Docker",
    "gRPC",
    "GraphQL",
    "Kafka",
    "Terraform",
]

POST_TITLE_TEMPLATES = [
    "Deep Dive into {} Performance Tuning",
    "Building a Production-Ready {} Service",
    "Why {} Changed My Development Workflow",
    "Common {} Pitfalls and How to Avoid Them",
    "{} Best Practices for 2025",
    "Scaling {} to Millions of Users",
    "From Zero to {} in Production",
    "Understanding {} Internals",
    "A Practical Guide to {} in {}",
    "How We Migrated to {} at Scale",
    "Debugging {} in Production",
    "Optimising {} Query Performance",
    "Securing Your {} Deployment",
    "Monitoring {} with Observability Tools",
    "{} vs {}: A Real-World Comparison",
    "Automating {} with {}: Lessons Learned",
    "The Architecture Behind Our {} Pipeline",
    "Implementing {} Patterns with {}",
    "Unit Testing {} Applications Effectively",
    "CI/CD for {} Projects: A Complete Guide",
]

# ~250-350 chars each — combine until target length
IT_PARAGRAPHS = [
    (
        "When designing distributed systems, the CAP theorem forces a fundamental trade-off between "
        "consistency, availability, and partition tolerance. Most modern cloud-native applications "
        "choose eventual consistency, accepting brief windows of stale reads in exchange for higher "
        "availability and horizontal scalability."
    ),
    (
        "Container orchestration with Kubernetes has become the de-facto standard for deploying "
        "microservices at scale. Understanding pod scheduling, resource requests and limits, and "
        "horizontal pod autoscaling is essential for operating reliable production workloads without "
        "manual intervention during traffic spikes."
    ),
    (
        "PostgreSQL's MVCC implementation allows concurrent readers and writers to proceed without "
        "blocking each other in most scenarios. Vacuuming dead tuples is critical for preventing "
        "table bloat and transaction ID wraparound, both of which can cause severe performance "
        "degradation if ignored over time."
    ),
    (
        "Redis operates as an in-memory data structure store, offering sub-millisecond latency for "
        "caching, pub/sub messaging, and distributed locking. Choosing the right eviction policy "
        "is crucial - allkeys-lru works well for caches, while noeviction suits use cases where "
        "data loss is unacceptable."
    ),
    (
        "Python's asyncio event loop enables writing highly concurrent I/O-bound code using "
        "cooperative multitasking. Async generators, context managers, and structured concurrency "
        "via TaskGroups make it significantly easier to reason about cancellation and error "
        "propagation in complex async workflows."
    ),
    (
        "Rust's ownership model eliminates entire classes of memory safety bugs at compile time, "
        "with zero runtime overhead. The borrow checker enforces that at any point, either one "
        "mutable reference or any number of immutable references to data exist, preventing data "
        "races without garbage collection."
    ),
    (
        "GraphQL shifts the API contract from server-defined resource shapes to client-specified "
        "queries. This reduces over-fetching on mobile clients and eliminates the need for multiple "
        "round-trips. However, naive resolvers can produce N+1 query problems that DataLoader "
        "patterns or persisted queries help address."
    ),
    (
        "Docker multi-stage builds allow separating build-time dependencies from the final runtime "
        "image, dramatically reducing image sizes. Combining this with distroless base images and "
        "non-root user execution is a strong baseline for hardening containerised applications "
        "before they reach a production Kubernetes cluster."
    ),
    (
        "Git's object model stores every version as a content-addressed snapshot rather than a "
        "delta chain, making checkout and branching extremely cheap. Interactive rebasing, the "
        "reflog, and partial staging via git add -p give developers powerful tools for crafting "
        "clean, bisectable commit histories."
    ),
    (
        "TypeScript's structural type system enables gradual adoption in existing JavaScript "
        "codebases. Discriminated unions, template literal types, and the infer keyword in "
        "conditional types unlock expressive type-level programming that catches entire categories "
        "of runtime bugs during compilation."
    ),
    (
        "CI/CD pipelines should be treated as production code - versioned, reviewed, and tested. "
        "Separating build, test, and deploy stages enables parallelism. Caching dependencies and "
        "Docker layer builds between runs can cut pipeline times dramatically, accelerating "
        "developer feedback loops substantially."
    ),
    (
        "Service meshes like Istio and Linkerd provide mutual TLS, traffic shaping, and "
        "observability at the infrastructure level, decoupling cross-cutting concerns from "
        "application code. The added operational complexity is justified primarily in environments "
        "with many heterogeneous services requiring fine-grained traffic control."
    ),
    (
        "AWS Lambda functions excel at event-driven workloads with sporadic traffic patterns, "
        "eliminating the cost of idle compute. Cold start latency, driven by runtime initialisation "
        "and VPC attachment, can be mitigated using provisioned concurrency for latency-sensitive "
        "paths, at the cost of higher steady-state billing."
    ),
    (
        "SQL query optimisation begins with EXPLAIN ANALYZE output. Understanding seq scans versus "
        "index scans, hash joins versus nested loop joins, and the planner's cost estimates reveals "
        "why a query is slow. Partial indexes, covering indexes, and expression indexes can "
        "eliminate expensive full-table scans in targeted workloads."
    ),
    (
        "The twelve-factor app methodology defines a set of principles for building portable, "
        "resilient SaaS applications. Storing config in the environment, treating backing services "
        "as attached resources, and enabling stateless horizontal scaling are particularly relevant "
        "to teams migrating legacy monoliths to containerised deployments."
    ),
    (
        "Observability in production systems rests on three pillars: metrics, logs, and traces. "
        "Structured JSON logs enable efficient querying in platforms like Loki or Elasticsearch. "
        "Distributed traces via OpenTelemetry correlate requests across service boundaries, "
        "making root cause analysis in complex systems tractable."
    ),
    (
        "Go's goroutines and channels implement CSP-style concurrency, making it straightforward "
        "to write programs that efficiently utilise all CPU cores. The runtime multiplexes "
        "thousands of goroutines onto a small pool of OS threads, and the garbage collector "
        "has evolved to deliver sub-millisecond pause times suitable for latency-sensitive services."
    ),
    (
        "Zero-trust security models assume no implicit trust based on network location, requiring "
        "every request to be authenticated and authorised regardless of origin. Implementing "
        "short-lived credentials, just-in-time access, and continuous verification reduces the "
        "blast radius of compromised credentials or misconfigured firewall rules."
    ),
    (
        "Event sourcing stores state as an immutable log of domain events rather than current "
        "snapshots. Replaying the event log to derive read models enables temporal queries and "
        "easy audit trails. Combined with CQRS, it supports independently scalable read and write "
        "paths tuned to their respective access patterns."
    ),
    (
        "Linux cgroups and namespaces form the foundation of container isolation. Understanding "
        "PID, network, mount, and user namespaces helps diagnose subtle issues when containers "
        "interact with the host kernel. Tools like nsenter and strace remain invaluable for "
        "low-level debugging that higher-level tooling abstracts away."
    ),
    (
        "Machine learning model deployment involves far more than exporting weights. Versioning "
        "datasets and models, monitoring for feature drift, and A/B testing new versions in shadow "
        "mode before full rollout are critical practices that distinguish research prototypes from "
        "production ML systems serving real user traffic."
    ),
    (
        "API versioning strategies range from URI path versioning to content negotiation via "
        "Accept headers. Regardless of approach, maintaining backwards compatibility, clearly "
        "communicating deprecation timelines, and providing migration guides reduces client "
        "breakage and builds trust with teams consuming your API surface area."
    ),
    (
        "Database connection pooling is essential when running many application replicas against "
        "a single PostgreSQL instance. PgBouncer in transaction-mode pooling allows thousands of "
        "application connections to share a much smaller pool of server connections, avoiding the "
        "memory and process overhead of unlimited direct connections."
    ),
    (
        "Terraform enables infrastructure as code for cloud resources, tracking desired versus "
        "actual state and applying only the minimal diff. Remote state stored in S3 with DynamoDB "
        "locking enables safe collaboration. Using modules for repeated patterns keeps "
        "configurations DRY and maintainable across multiple environments."
    ),
    (
        "HTTP/2 multiplexes multiple streams over a single TCP connection, eliminating head-of-line "
        "blocking from HTTP/1.1 pipelining. Header compression and stream prioritisation improve "
        "page load performance for APIs and web assets, particularly on high-latency connections "
        "where connection establishment dominates."
    ),
    (
        "Rate limiting protects backend services from both abusive clients and accidental traffic "
        "spikes. Token bucket and sliding window algorithms offer different trade-offs in burst "
        "tolerance. Storing rate limit state in Redis with atomic Lua scripts enables consistent "
        "enforcement across multiple application server instances."
    ),
]

USERNAME_NUMERIC_SUFFIXES = [2, 7, 11, 19, 24, 42, 58, 73, 88, 96]


@dataclass(frozen=True)
class SeededUserPlan:
    user: User
    post_target: int
    publish_rate: float
    comment_weight: float
    vote_weight: float


def _make_body(rng: random.Random, min_len: int = 1000, max_len: int = 10000) -> str:
    target = rng.randint(min_len, max_len)
    paragraphs = rng.sample(IT_PARAGRAPHS, len(IT_PARAGRAPHS))
    body_parts = []
    length = 0
    idx = 0
    while length < target:
        paragraph = paragraphs[idx % len(paragraphs)]
        body_parts.append(paragraph)
        length += len(paragraph) + 2  # account for "\n\n"
        idx += 1
    return "\n\n".join(body_parts)[:max_len]


def _make_title(rng: random.Random, tag_names: list[str]) -> str:
    template = rng.choice(POST_TITLE_TEMPLATES)
    placeholders = template.count("{}")
    words = rng.sample(tag_names, min(placeholders, len(tag_names)))
    return template.format(*words)


def _make_bio(rng: random.Random) -> str:
    template = rng.choice(BIO_TEMPLATES)
    return template.format(
        role=rng.choice(ROLES),
        n=rng.randint(3, 15),
        tech1=rng.choice(TECH_WORDS),
        tech2=rng.choice(TECH_WORDS),
    )


def _normalise_name_token(value: str) -> str:
    token = slugify(value).replace("-", "")
    token = re.sub(r"[^a-z0-9]", "", token)
    return token or "user"


def _username_candidates(first: str, last: str, index: int) -> list[str]:
    first_token = _normalise_name_token(first)
    last_token = _normalise_name_token(last)
    year_suffix = 80 + (index % 20)
    two_digit = USERNAME_NUMERIC_SUFFIXES[index % len(USERNAME_NUMERIC_SUFFIXES)]

    return [
        f"{first_token}.{last_token}",
        f"{first_token}-{last_token}",
        f"{first_token}{last_token}",
        f"{first_token[0]}{last_token}",
        f"{first_token}.{last_token}{two_digit}",
        f"{first_token}{last_token}{two_digit}",
        f"{first_token}_{last_token[:1]}{year_suffix}",
        f"{first_token[:1]}{last_token}{year_suffix}",
    ]


def _build_username(existing: set[str], first: str, last: str, index: int) -> str:
    for candidate in _username_candidates(first, last, index):
        if candidate not in existing:
            existing.add(candidate)
            return candidate

    fallback_root = _username_candidates(first, last, index)[0]
    suffix = 2
    while True:
        candidate = f"{fallback_root}{suffix}"
        if candidate not in existing:
            existing.add(candidate)
            return candidate
        suffix += 1


BASE_DATE = datetime(2021, 1, 1, tzinfo=timezone.utc)


def _rand_date(rng: random.Random, span_days: int = 1460) -> datetime:
    return BASE_DATE + timedelta(
        days=rng.randint(0, span_days),
        hours=rng.randint(0, 23),
        minutes=rng.randint(0, 59),
    )


def _allocate_weighted_counts(weights: list[float], total: int) -> list[int]:
    if not weights or total <= 0:
        return [0 for _ in weights]

    total_weight = sum(weights)
    if total_weight <= 0:
        return [0 for _ in weights]

    raw_counts = [(weight / total_weight) * total for weight in weights]
    counts = [int(raw) for raw in raw_counts]
    remainder = total - sum(counts)

    if remainder > 0:
        order = sorted(
            range(len(raw_counts)),
            key=lambda idx: (raw_counts[idx] - counts[idx], weights[idx]),
            reverse=True,
        )
        for idx in order[:remainder]:
            counts[idx] += 1

    return counts


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _build_user_plans(users: list[User], rng: random.Random) -> list[SeededUserPlan]:
    activity_weights = []
    comment_weights = []
    vote_weights = []

    for _user in users:
        activity = rng.paretovariate(2.35)
        if rng.random() < 0.12:
            activity *= rng.uniform(0.02, 0.20)
        if rng.random() < 0.08:
            activity *= rng.uniform(1.5, 2.8)

        activity_weights.append(activity)
        comment_weights.append(activity * rng.uniform(0.7, 1.7) + rng.uniform(0.2, 1.4))
        vote_weights.append(activity * rng.uniform(0.5, 1.5) + rng.uniform(0.5, 1.8))

    post_targets = _allocate_weighted_counts(activity_weights, SEED_POST_TARGET)
    max_target = max(post_targets) if post_targets else 0

    plans = []
    for user, post_target, activity, comment_weight, vote_weight in zip(
        users,
        post_targets,
        activity_weights,
        comment_weights,
        vote_weights,
        strict=True,
    ):
        activity_ratio = (post_target / max_target) if max_target else 0
        publish_rate = _clamp(
            0.58 + (activity_ratio * 0.25) + rng.uniform(-0.05, 0.06),
            0.55,
            0.94,
        )
        plans.append(
            SeededUserPlan(
                user=user,
                post_target=post_target,
                publish_rate=publish_rate,
                comment_weight=comment_weight,
                vote_weight=vote_weight,
            )
        )

    return plans


def _make_post_slug(title: str, username: str, seq: int) -> str:
    title_slug = slugify(title)[:160] or "post"
    author_slug = slugify(username.replace(".", "-").replace("_", "-"))[:40] or "author"
    return f"{title_slug}-{author_slug}-{seq:04d}"[:255]


def _build_cumulative_weights(weights: list[float]) -> list[float]:
    cumulative = []
    running = 0.0
    for weight in weights:
        running += max(weight, 0.0001)
        cumulative.append(running)
    return cumulative


def _weighted_choice_index(rng: random.Random, cumulative_weights: list[float]) -> int:
    target = rng.random() * cumulative_weights[-1]
    return bisect_left(cumulative_weights, target)


def _pick_user(
    rng: random.Random,
    users: list[User],
    cumulative_weights: list[float],
    exclude_user_id: int | None = None,
) -> User:
    while True:
        candidate = users[_weighted_choice_index(rng, cumulative_weights)]
        if candidate.id != exclude_user_id:
            return candidate


def _comment_count_for_post(rng: random.Random, is_hot_author: bool) -> int:
    roll = rng.random()
    if is_hot_author:
        roll += 0.08

    if roll < 0.45:
        return 0
    if roll < 0.80:
        return rng.randint(1, 2)
    if roll < 0.95:
        return rng.randint(3, 5)
    if roll < 0.995:
        return rng.randint(6, 12)
    return rng.randint(15, 28)


def _vote_count_for_comment(rng: random.Random, is_approved: bool) -> int:
    if not is_approved and rng.random() < 0.85:
        return 0

    roll = rng.random()
    if roll < 0.70:
        return 0
    if roll < 0.90:
        return rng.randint(1, 2)
    if roll < 0.98:
        return rng.randint(3, 5)
    return rng.randint(6, 14)


class Command(BaseCommand):
    help = "Seed a large, production-like dataset with realistic identities and skewed activity."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete previously seeded data before inserting.",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Random seed for reproducibility (default: 42).",
        )

    def handle(self, *args, **options):
        rng = random.Random(options["seed"])

        if options["clear"]:
            self._clear()

        self.stdout.write("Creating tags...")
        tag_objs = self._ensure_tags()
        tag_names = [tag.name for tag in tag_objs]

        self.stdout.write("Creating realistic demo users...")
        users = self._create_users(rng)
        plans = _build_user_plans(users, rng)

        total_posts = sum(plan.post_target for plan in plans)
        self.stdout.write(f"Planning {len(users)} users and {total_posts} posts...")

        self.stdout.write("Creating skewed post activity...")
        published_posts = self._create_posts(rng, plans, tag_objs, tag_names)

        self.stdout.write("Creating production-like comments...")
        comments = self._create_comments(rng, plans, published_posts)

        self.stdout.write("Creating production-like votes...")
        self._create_votes(rng, plans, comments)

        self.stdout.write(self.style.SUCCESS("Done."))

    # ------------------------------------------------------------------

    def _clear(self):
        self.stdout.write("Clearing previously seeded demo users...")
        qs = User.objects.filter(email__iendswith=f"@{SEED_EMAIL_DOMAIN}")
        count, _ = qs.delete()
        self.stdout.write(f"  Deleted {count} objects.")

    def _ensure_tags(self) -> list[Tag]:
        tag_objs = []
        for name, slug in TAGS:
            obj, _ = Tag.objects.get_or_create(slug=slug, defaults={"name": name})
            tag_objs.append(obj)
        return tag_objs

    def _create_users(self, rng: random.Random) -> list[User]:
        existing = set(User.objects.values_list("username", flat=True))
        seeded_usernames = []
        to_create = []

        for index in range(1, SEED_USER_COUNT + 1):
            first = rng.choice(FIRST_NAMES)
            last = rng.choice(LAST_NAMES)
            username = _build_username(existing, first, last, index)
            seeded_usernames.append(username)

            to_create.append(
                User(
                    username=username,
                    email=f"{username}@{SEED_EMAIL_DOMAIN}",
                    first_name=first,
                    last_name=last,
                    password="!",
                    is_active=True,
                    date_joined=_rand_date(rng),
                    role="user",
                    bio=_make_bio(rng),
                )
            )

        User.objects.bulk_create(to_create, batch_size=500)
        return list(User.objects.filter(username__in=seeded_usernames).order_by("username"))

    def _create_posts(
        self,
        rng: random.Random,
        plans: list[SeededUserPlan],
        tag_objs: list[Tag],
        tag_names: list[str],
    ) -> list[Post]:
        existing_slugs = set(Post.objects.values_list("slug", flat=True))
        post_tag_through = Post.tags.through
        published_posts: list[Post] = []
        hot_author_ids = {
            plan.user.id
            for plan in sorted(plans, key=lambda item: item.post_target, reverse=True)[:50]
        }

        for plan in plans:
            if plan.post_target == 0:
                continue

            new_posts: list[Post] = []
            through_rows = []
            author = plan.user

            for seq in range(1, plan.post_target + 1):
                title = _make_title(rng, tag_names)
                slug = _make_post_slug(title, author.username, seq)
                if slug in existing_slugs:
                    continue
                existing_slugs.add(slug)

                created_at = _rand_date(rng)
                status = (
                    Post.Status.PUBLISHED if rng.random() < plan.publish_rate else Post.Status.DRAFT
                )
                published_at = created_at if status == Post.Status.PUBLISHED else None
                updated_at = created_at + timedelta(hours=rng.randint(0, 240))

                new_posts.append(
                    Post(
                        title=title,
                        slug=slug,
                        author=author,
                        body=_make_body(rng),
                        excerpt=_make_body(rng, 100, 300)[:300],
                        status=status,
                        created_at=created_at,
                        updated_at=updated_at,
                        published_at=published_at,
                    )
                )

            if not new_posts:
                continue

            with transaction.atomic():
                created_posts = Post.objects.bulk_create(new_posts, batch_size=500)
                for post in created_posts:
                    tag_count = rng.choices([1, 2, 3, 4, 5], weights=[20, 36, 24, 14, 6], k=1)[0]
                    chosen_tags = rng.sample(tag_objs, tag_count)
                    for tag in chosen_tags:
                        through_rows.append(post_tag_through(post_id=post.pk, tag_id=tag.pk))

                post_tag_through.objects.bulk_create(through_rows, batch_size=1000)
                published_posts.extend(
                    post for post in created_posts if post.status == Post.Status.PUBLISHED
                )

            if author.id in hot_author_ids:
                self.stdout.write(
                    f"  {author.username}: {len(new_posts)} posts (high-activity author)..."
                )

        return published_posts

    def _create_comments(
        self,
        rng: random.Random,
        plans: list[SeededUserPlan],
        published_posts: list[Post],
    ) -> list[Comment]:
        if not published_posts:
            return []

        existing_post_ids = set(Comment.objects.values_list("post_id", flat=True))
        users = [plan.user for plan in plans]
        cumulative_weights = _build_cumulative_weights([plan.comment_weight for plan in plans])
        hot_author_ids = {
            plan.user.id
            for plan in sorted(plans, key=lambda item: item.post_target, reverse=True)[:50]
        }

        comments_to_create: list[Comment] = []
        post_ids_with_new_comments = set()

        for post in published_posts:
            if post.id in existing_post_ids:
                continue

            quota = _comment_count_for_post(rng, post.author_id in hot_author_ids)
            for _ in range(quota):
                author = _pick_user(rng, users, cumulative_weights, exclude_user_id=post.author_id)
                created_at = post.published_at + timedelta(hours=rng.randint(1, 24 * 90))
                comments_to_create.append(
                    Comment(
                        post=post,
                        author=author,
                        body=_make_body(rng, 80, 450)[:450],
                        is_approved=rng.random() < 0.90,
                        created_at=created_at,
                        updated_at=created_at + timedelta(hours=rng.randint(0, 48)),
                    )
                )
                post_ids_with_new_comments.add(post.id)

        Comment.objects.bulk_create(comments_to_create, batch_size=1000)
        return list(
            Comment.objects.filter(post_id__in=post_ids_with_new_comments).select_related("author")
        )

    def _create_votes(
        self,
        rng: random.Random,
        plans: list[SeededUserPlan],
        comments: list[Comment],
    ) -> None:
        if not comments:
            return

        users = [plan.user for plan in plans]
        user_ids = [user.id for user in users]
        cumulative_weights = _build_cumulative_weights([plan.vote_weight for plan in plans])
        existing = set(CommentVote.objects.values_list("comment_id", "user_id"))
        to_create: list[CommentVote] = []

        for comment in comments:
            quota = _vote_count_for_comment(rng, comment.is_approved)
            if quota == 0:
                continue

            chosen_voters = set()
            attempts = 0
            while len(chosen_voters) < quota and attempts < quota * 8:
                voter_id = user_ids[_weighted_choice_index(rng, cumulative_weights)]
                attempts += 1
                if voter_id == comment.author_id:
                    continue
                if (comment.id, voter_id) in existing or voter_id in chosen_voters:
                    continue
                chosen_voters.add(voter_id)

            for voter_id in chosen_voters:
                existing.add((comment.id, voter_id))
                to_create.append(
                    CommentVote(
                        comment_id=comment.id,
                        user_id=voter_id,
                        vote=rng.choice([CommentVote.VoteType.LIKE, CommentVote.VoteType.DISLIKE]),
                    )
                )

        CommentVote.objects.bulk_create(to_create, batch_size=1000)
