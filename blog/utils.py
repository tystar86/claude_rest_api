from django.utils.text import slugify


def build_unique_slug(model_cls, source_text, instance_id=None, max_length=None):
    if max_length is None:
        max_length = model_cls._meta.get_field("slug").max_length
    base = slugify(source_text or "").strip("-")[:max_length] or "item"
    candidate = base
    n = 2
    while True:
        qs = model_cls.objects.filter(slug=candidate)
        if instance_id is not None:
            qs = qs.exclude(id=instance_id)
        if not qs.exists():
            return candidate
        suffix = f"-{n}"
        candidate = f"{base[: max_length - len(suffix)]}{suffix}"
        n += 1
