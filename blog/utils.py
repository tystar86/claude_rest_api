from django.utils.text import slugify


def build_unique_slug(model_cls, source_text, instance_id=None):
    base = slugify(source_text or "").strip("-")[:50] or "item"
    candidate = base
    n = 2
    while True:
        qs = model_cls.objects.filter(slug=candidate)
        if instance_id is not None:
            qs = qs.exclude(id=instance_id)
        if not qs.exists():
            return candidate
        candidate = f"{base}-{n}"
        n += 1
