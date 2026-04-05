# Generated manually for performance optimization
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0002_commentvote"),
    ]

    operations = [
        # Faster post_list: filter by status + order by created_at in one index scan
        migrations.AddIndex(
            model_name="post",
            index=models.Index(
                fields=["status", "-created_at"],
                name="blog_post_status_created_idx",
            ),
        ),
        # Faster comment_list: order by created_at DESC without seq scan
        migrations.AddIndex(
            model_name="comment",
            index=models.Index(
                fields=["-created_at"],
                name="blog_comment_created_idx",
            ),
        ),
        # Covering index for likes/dislikes count queries per comment
        migrations.AddIndex(
            model_name="commentvote",
            index=models.Index(
                fields=["comment", "vote"],
                name="blog_commentvote_comment_vote_idx",
            ),
        ),
    ]
