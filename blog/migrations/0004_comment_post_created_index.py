from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0003_performance_indexes"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="comment",
            index=models.Index(
                fields=["post", "created_at"],
                name="blog_comment_post_created_idx",
            ),
        ),
    ]
