from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from .dashboard_query import invalidate_dashboard_cache
from .models import Comment, Post, Tag


@receiver(post_save, sender=Post)
@receiver(post_delete, sender=Post)
@receiver(post_save, sender=Comment)
@receiver(post_delete, sender=Comment)
@receiver(post_save, sender=Tag)
@receiver(post_delete, sender=Tag)
def invalidate_dashboard_snapshot_on_model_change(sender, **kwargs):
    invalidate_dashboard_cache()


@receiver(m2m_changed, sender=Post.tags.through)
def invalidate_dashboard_snapshot_on_tag_change(sender, action, **kwargs):
    if action in {"post_add", "post_remove", "post_clear"}:
        invalidate_dashboard_cache()
