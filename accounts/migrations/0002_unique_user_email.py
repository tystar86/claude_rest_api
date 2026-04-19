from django.db import migrations


class Migration(migrations.Migration):
    """Previously added a unique index on ``auth_user.email``.

    ``AUTH_USER_MODEL`` is ``accounts.CustomUser``, which enforces a unique
    ``email`` column. The old SQL targeted ``auth_user`` and is not applicable
    on fresh installs.
    """

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = []
