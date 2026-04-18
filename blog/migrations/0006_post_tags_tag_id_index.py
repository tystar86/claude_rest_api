from django.db import migrations


class Migration(migrations.Migration):
    """Speed up Post × Tag filters (e.g. tag detail post lists) by indexing tag_id on the M2M table."""

    dependencies = [
        ("blog", "0005_add_comment_post_approved_idx"),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE INDEX IF NOT EXISTS blog_post_tags_tag_id_idx ON blog_post_tags (tag_id);",
            reverse_sql="DROP INDEX IF EXISTS blog_post_tags_tag_id_idx;",
        ),
    ]
