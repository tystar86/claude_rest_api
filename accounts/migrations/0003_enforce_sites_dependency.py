"""
Empty migration whose sole purpose is to declare an explicit dependency on
django.contrib.sites so that fresh database installs always apply sites
migrations in a predictable order alongside accounts.

This prevents InconsistentMigrationHistory on new environments without
requiring any manual intervention.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_unique_user_email"),
        ("sites", "0002_alter_domain_unique"),
    ]

    operations = []
