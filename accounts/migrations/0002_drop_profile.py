from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [  # noqa: RUF012
        ("accounts", "0001_squashed_0005_customuser_cutover"),
    ]

    operations = [  # noqa: RUF012
        migrations.RunSQL(
            "DROP TABLE IF EXISTS accounts_profile",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
