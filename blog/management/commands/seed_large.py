"""
Management command to seed 1000 users, 50 posts each, 20 IT tags, 8 votes per user.
Run: python manage.py seed_large
Add --clear to wipe previously seeded data first.
"""

import random
from datetime import datetime, timedelta, timezone

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Profile
from blog.models import Comment, CommentVote, Post, Tag

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
    "Alex",
    "Jordan",
    "Taylor",
    "Morgan",
    "Casey",
    "Riley",
    "Jamie",
    "Avery",
    "Quinn",
    "Skyler",
    "Drew",
    "Reese",
    "Blake",
    "Cameron",
    "Dakota",
    "Emerson",
    "Finley",
    "Harley",
    "Hayden",
    "Jesse",
    "Kai",
    "Lane",
    "Logan",
    "Mackenzie",
    "Max",
    "Nico",
    "Parker",
    "Payton",
    "Peyton",
    "Phoenix",
    "Reagan",
    "Remy",
    "River",
    "Robin",
    "Rowan",
    "Ryan",
    "Sage",
    "Sam",
    "Sidney",
    "Spencer",
    "Stevie",
    "Storm",
    "Sydney",
    "Tatum",
    "Terry",
    "Toby",
    "Tracy",
    "Val",
    "Winter",
    "Wyatt",
]

LAST_NAMES = [
    "Anderson",
    "Bailey",
    "Baker",
    "Brooks",
    "Brown",
    "Campbell",
    "Carter",
    "Chen",
    "Clark",
    "Collins",
    "Cooper",
    "Davis",
    "Evans",
    "Fisher",
    "Foster",
    "Garcia",
    "Gonzalez",
    "Green",
    "Hall",
    "Harris",
    "Hernandez",
    "Hill",
    "Jackson",
    "Johnson",
    "Jones",
    "Kim",
    "King",
    "Lee",
    "Lewis",
    "Lopez",
    "Martin",
    "Martinez",
    "Miller",
    "Mitchell",
    "Moore",
    "Morgan",
    "Nelson",
    "Parker",
    "Patel",
    "Perez",
    "Phillips",
    "Price",
    "Rivera",
    "Roberts",
    "Robinson",
    "Rodriguez",
    "Scott",
    "Smith",
    "Taylor",
    "Thomas",
    "Thompson",
    "Torres",
    "Turner",
    "Walker",
    "White",
    "Williams",
    "Wilson",
    "Wood",
    "Wright",
    "Young",
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
        "is crucial — allkeys-lru works well for caches, while noeviction suits use cases where "
        "data loss is unacceptable."
    ),
    (
        "Python's asyncio event loop enables writing highly concurrent I/O-bound code using "
        "cooperative multitasking. Async generators, context managers, and structured concurrency "
        "via TaskGroups (introduced in Python 3.11) make it significantly easier to reason about "
        "cancellation and error propagation in complex async workflows."
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
        "CI/CD pipelines should be treated as production code — versioned, reviewed, and tested. "
        "Separating build, test, and deploy stages enables parallelism. Caching dependencies and "
        "Docker layer builds between runs can cut pipeline times by 60-80%, accelerating "
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
        "blocking from HTTP/1.1 pipelining. Server push, header compression via HPACK, and "
        "stream prioritisation improve page load performance for APIs and web assets, particularly "
        "on high-latency connections where connection establishment dominates."
    ),
    (
        "Rate limiting protects backend services from both abusive clients and accidental traffic "
        "spikes. Token bucket and sliding window algorithms offer different trade-offs in burst "
        "tolerance. Storing rate limit state in Redis with atomic Lua scripts enables consistent "
        "enforcement across multiple application server instances."
    ),
    (
        "Dependency injection decouples component construction from usage, making code easier to "
        "test and extend. Frameworks automate wiring, but understanding the underlying patterns — "
        "constructor injection, interface segregation, and the dependency inversion principle — "
        "lets developers build testable systems even without framework support."
    ),
    (
        "WebAssembly brings near-native execution speed to browser environments, enabling "
        "compute-intensive workloads like video encoding, cryptography, and simulation to run "
        "client-side. WASI extends this to server-side sandboxed execution, with projects like "
        "Wasmtime exploring Wasm as a lightweight container alternative."
    ),
    (
        "Chaos engineering involves deliberately injecting failures into production or staging "
        "systems to uncover weaknesses before incidents do. Starting with a steady-state hypothesis, "
        "running controlled experiments, and automating regular game days builds organisational "
        "confidence in system resilience and incident response procedures."
    ),
    (
        "Protocol Buffers provide a language-neutral binary serialisation format that is both "
        "smaller and faster to parse than JSON. Combined with gRPC's HTTP/2 transport and "
        "streaming support, they are well-suited for high-throughput internal service communication "
        "where schema evolution must be handled without breaking existing clients."
    ),
]


def _make_body(rng: random.Random, min_len: int = 1000, max_len: int = 10000) -> str:
    target = rng.randint(min_len, max_len)
    paragraphs = rng.sample(IT_PARAGRAPHS, len(IT_PARAGRAPHS))
    body_parts = []
    length = 0
    idx = 0
    while length < target:
        p = paragraphs[idx % len(paragraphs)]
        body_parts.append(p)
        length += len(p) + 2  # account for "\n\n"
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


BASE_DATE = datetime(2023, 1, 1, tzinfo=timezone.utc)


def _rand_date(rng: random.Random, span_days: int = 730) -> datetime:
    return BASE_DATE + timedelta(
        days=rng.randint(0, span_days),
        hours=rng.randint(0, 23),
        minutes=rng.randint(0, 59),
    )


class Command(BaseCommand):
    help = "Seed 1000 users × 50 IT posts, 20 tags, 8 votes per user."

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

        self.stdout.write("Creating tags…")
        tag_objs = self._ensure_tags()
        tag_names = [t.name for t in tag_objs]

        self.stdout.write("Creating 1000 users…")
        users = self._create_users(rng)

        self.stdout.write("Creating profiles…")
        self._create_profiles(rng, users)

        self.stdout.write("Creating 50 posts per user (50 000 total)…")
        posts = self._create_posts(rng, users, tag_objs, tag_names)

        self.stdout.write("Creating one comment per post…")
        comments = self._create_comments(rng, users, posts)

        self.stdout.write("Creating 8 votes per user…")
        self._create_votes(rng, users, comments)

        self.stdout.write(self.style.SUCCESS("Done."))

    # ------------------------------------------------------------------

    def _clear(self):
        self.stdout.write("Clearing seeded data…")
        usernames = [f"techuser_{i:04d}" for i in range(1, 1001)]
        qs = User.objects.filter(username__in=usernames)
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
        to_create = []
        for i in range(1, 1001):
            username = f"techuser_{i:04d}"
            if username in existing:
                continue
            first = rng.choice(FIRST_NAMES)
            last = rng.choice(LAST_NAMES)
            to_create.append(
                User(
                    username=username,
                    email=f"{username}@example.dev",
                    first_name=first,
                    last_name=last,
                    password="pbkdf2_sha256$870000$placeholder$placeholder=",
                    is_active=True,
                    date_joined=_rand_date(rng),
                )
            )
        User.objects.bulk_create(to_create, batch_size=500)
        return list(
            User.objects.filter(
                username__in=[f"techuser_{i:04d}" for i in range(1, 1001)]
            ).order_by("username")
        )

    def _create_profiles(self, rng: random.Random, users: list[User]) -> None:
        existing = set(Profile.objects.values_list("user_id", flat=True))
        to_create = [
            Profile(user=u, role="user", bio=_make_bio(rng))
            for u in users
            if u.pk not in existing
        ]
        Profile.objects.bulk_create(to_create, batch_size=500)

    def _create_posts(
        self,
        rng: random.Random,
        users: list[User],
        tag_objs: list[Tag],
        tag_names: list[str],
    ) -> list[Post]:
        existing_slugs = set(Post.objects.values_list("slug", flat=True))
        PostTag = Post.tags.through

        all_posts: list[Post] = []
        BATCH = 200  # users per transaction

        for batch_start in range(0, len(users), BATCH):
            batch_users = users[batch_start : batch_start + BATCH]
            new_posts: list[Post] = []

            for user in batch_users:
                for j in range(1, 51):
                    slug = f"{user.username}-post-{j:02d}"
                    if slug in existing_slugs:
                        continue
                    existing_slugs.add(slug)
                    title = _make_title(rng, tag_names)
                    pub_date = _rand_date(rng)
                    new_posts.append(
                        Post(
                            title=title,
                            slug=slug,
                            author=user,
                            body=_make_body(rng),
                            excerpt=_make_body(rng, 100, 300)[:300],
                            status="published",
                            created_at=pub_date,
                            updated_at=pub_date,
                            published_at=pub_date,
                        )
                    )

            with transaction.atomic():
                created = Post.objects.bulk_create(new_posts, batch_size=500)
                # M2M: assign 2-5 random tags per post
                through_rows = []
                for post in created:
                    chosen = rng.sample(tag_objs, rng.randint(2, 5))
                    for tag in chosen:
                        through_rows.append(PostTag(post_id=post.pk, tag_id=tag.pk))
                PostTag.objects.bulk_create(through_rows, batch_size=1000)
                all_posts.extend(created)

            done = min(batch_start + BATCH, len(users))
            self.stdout.write(f"  {done}/{len(users)} users processed…")

        return all_posts

    def _create_comments(
        self, rng: random.Random, users: list[User], posts: list[Post]
    ) -> list[Comment]:
        existing_post_ids = set(Comment.objects.values_list("post_id", flat=True))
        to_create = []
        for post in posts:
            if post.pk in existing_post_ids:
                continue
            author = rng.choice(users)
            to_create.append(
                Comment(
                    post=post,
                    author=author,
                    body=_make_body(rng, 80, 400)[:400],
                    is_approved=True,
                    created_at=post.published_at,
                    updated_at=post.published_at,
                )
            )
        Comment.objects.bulk_create(to_create, batch_size=1000)
        # Return all comments for these posts
        post_ids = [p.pk for p in posts]
        return list(Comment.objects.filter(post_id__in=post_ids))

    def _create_votes(
        self,
        rng: random.Random,
        users: list[User],
        comments: list[Comment],
    ) -> None:
        existing = set(CommentVote.objects.values_list("comment_id", "user_id"))
        to_create: list[CommentVote] = []
        vote_types = ["like", "dislike"]
        comment_pool = comments[:]

        for user in users:
            candidates = [c for c in comment_pool if c.author_id != user.pk]
            if len(candidates) < 8:
                continue
            chosen = rng.sample(candidates, 8)
            for comment in chosen:
                key = (comment.pk, user.pk)
                if key in existing:
                    continue
                existing.add(key)
                to_create.append(
                    CommentVote(
                        comment=comment,
                        user=user,
                        vote=rng.choice(vote_types),
                    )
                )

        CommentVote.objects.bulk_create(to_create, batch_size=1000)
