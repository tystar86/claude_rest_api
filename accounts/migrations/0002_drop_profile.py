from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_squashed_0005_customuser_cutover"),
    ]

    operations = [
        migrations.RunSQL(
            "DROP TABLE IF EXISTS accounts_profile",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
