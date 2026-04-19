import django.contrib.auth.models
import django.contrib.auth.validators
import django.utils.timezone
from django.core.management.color import no_style
from django.db import migrations, models


COPYABLE_M2M_FIELDS = ("groups", "user_permissions")


def _table_exists(schema_editor, table_name):
    return table_name in schema_editor.connection.introspection.table_names()


def _ensure_customuser_schema(apps, schema_editor):
    CustomUser = apps.get_model("accounts", "CustomUser")
    customuser_table = CustomUser._meta.db_table
    if not _table_exists(schema_editor, customuser_table):
        schema_editor.create_model(CustomUser)
        return CustomUser

    for field_name in COPYABLE_M2M_FIELDS:
        through_model = getattr(CustomUser, field_name).through
        if not _table_exists(schema_editor, through_model._meta.db_table):
            schema_editor.create_model(through_model)
    return CustomUser


def _copy_missing_users(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    CustomUser = _ensure_customuser_schema(apps, schema_editor)
    existing_ids = set(CustomUser.objects.using(db_alias).values_list("id", flat=True))
    profile_by_user_id = _load_profile_rows(schema_editor)
    auth_user_rows = _load_auth_user_rows(schema_editor)
    existing_profile_ids = existing_ids & set(profile_by_user_id)

    missing_users = []
    for user_row in auth_user_rows:
        user_id = user_row["id"]
        if user_id in existing_ids:
            continue
        role, bio = profile_by_user_id.get(user_id, ("user", ""))
        missing_users.append(
            CustomUser(
                id=user_id,
                password=user_row["password"],
                last_login=user_row["last_login"],
                is_superuser=user_row["is_superuser"],
                username=user_row["username"],
                first_name=user_row["first_name"],
                last_name=user_row["last_name"],
                email=user_row["email"],
                is_staff=user_row["is_staff"],
                is_active=user_row["is_active"],
                date_joined=user_row["date_joined"],
                role=role,
                bio=bio,
            )
        )

    if existing_profile_ids:
        existing_users = CustomUser.objects.using(db_alias).in_bulk(existing_profile_ids)
        users_to_update = []
        for user_id, user in existing_users.items():
            role, bio = profile_by_user_id[user_id]
            if user.role == role and user.bio == bio:
                continue
            user.role = role
            user.bio = bio
            users_to_update.append(user)
        if users_to_update:
            CustomUser.objects.using(db_alias).bulk_update(users_to_update, ["role", "bio"])

    if missing_users:
        CustomUser.objects.using(db_alias).bulk_create(missing_users)

    _copy_m2m_memberships(schema_editor, CustomUser, db_alias)
    _reset_customuser_sequence(schema_editor, CustomUser)


def _load_profile_rows(schema_editor):
    if not _table_exists(schema_editor, "accounts_profile"):
        return {}

    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT user_id, role, bio FROM accounts_profile")
        return {user_id: (role, bio) for user_id, role, bio in cursor.fetchall()}


def _load_auth_user_rows(schema_editor):
    if not _table_exists(schema_editor, "auth_user"):
        return []

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                id,
                password,
                last_login,
                is_superuser,
                username,
                first_name,
                last_name,
                email,
                is_staff,
                is_active,
                date_joined
            FROM auth_user
            ORDER BY id
            """
        )
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def _copy_m2m_memberships(schema_editor, CustomUser, db_alias):
    for field_name in COPYABLE_M2M_FIELDS:
        target_through = getattr(CustomUser, field_name).through
        source_table = f"auth_user_{field_name}"
        if not _table_exists(schema_editor, source_table):
            continue

        target_field_names = [
            field.attname
            for field in target_through._meta.local_fields
            if not field.primary_key and not getattr(field, "auto_created", False)
        ]
        if not target_field_names:
            continue

        target_user_field = f"{CustomUser._meta.model_name}_id"
        other_field = next(
            field_name for field_name in target_field_names if field_name != target_user_field
        )
        with schema_editor.connection.cursor() as cursor:
            cursor.execute(f"SELECT user_id, {other_field} FROM {source_table}")
            source_rows = cursor.fetchall()

        rows = [
            target_through(**{target_user_field: user_id, other_field: related_id})
            for user_id, related_id in source_rows
        ]
        if rows:
            target_through.objects.using(db_alias).bulk_create(rows, ignore_conflicts=True)


def _reset_customuser_sequence(schema_editor, CustomUser):
    connection = schema_editor.connection
    if connection.vendor != "postgresql":
        return

    for sql in connection.ops.sequence_reset_sql(no_style(), [CustomUser]):
        schema_editor.execute(sql)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_enforce_sites_dependency"),
    ]

    # swappable_dependency(AUTH_USER_MODEL) resolves to ("accounts", "__first__"),
    # i.e. accounts.0001_initial — but CustomUser is not in migration state until
    # this migration's state_operations run. Without this, the planner can apply
    # admin.0001_initial / blog.0001_initial before 0004 and crash with
    # ValueError: ... lazy reference to 'accounts.customuser', but app 'accounts'
    # doesn't provide model 'customuser'.
    run_before = [
        ("admin", "0001_initial"),
        ("blog", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="CustomUser",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        ("password", models.CharField(max_length=128, verbose_name="password")),
                        (
                            "last_login",
                            models.DateTimeField(blank=True, null=True, verbose_name="last login"),
                        ),
                        (
                            "is_superuser",
                            models.BooleanField(
                                default=False,
                                help_text="Designates that this user has all permissions without explicitly assigning them.",
                                verbose_name="superuser status",
                            ),
                        ),
                        (
                            "username",
                            models.CharField(
                                error_messages={
                                    "unique": "A user with that username already exists."
                                },
                                help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.",
                                max_length=150,
                                unique=True,
                                validators=[
                                    django.contrib.auth.validators.UnicodeUsernameValidator()
                                ],
                                verbose_name="username",
                            ),
                        ),
                        (
                            "first_name",
                            models.CharField(blank=True, max_length=150, verbose_name="first name"),
                        ),
                        (
                            "last_name",
                            models.CharField(blank=True, max_length=150, verbose_name="last name"),
                        ),
                        (
                            "is_staff",
                            models.BooleanField(
                                default=False,
                                help_text="Designates whether the user can log into this admin site.",
                                verbose_name="staff status",
                            ),
                        ),
                        (
                            "is_active",
                            models.BooleanField(
                                default=True,
                                help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.",
                                verbose_name="active",
                            ),
                        ),
                        (
                            "date_joined",
                            models.DateTimeField(
                                default=django.utils.timezone.now, verbose_name="date joined"
                            ),
                        ),
                        ("email", models.EmailField(max_length=254, unique=True)),
                        (
                            "role",
                            models.CharField(
                                choices=[
                                    ("user", "Regular User"),
                                    ("moderator", "Moderator"),
                                    ("admin", "Admin"),
                                ],
                                default="user",
                                max_length=20,
                            ),
                        ),
                        ("bio", models.TextField(blank=True)),
                        (
                            "groups",
                            models.ManyToManyField(
                                blank=True,
                                help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                                related_name="user_set",
                                related_query_name="user",
                                to="auth.group",
                                verbose_name="groups",
                            ),
                        ),
                        (
                            "user_permissions",
                            models.ManyToManyField(
                                blank=True,
                                help_text="Specific permissions for this user.",
                                related_name="user_set",
                                related_query_name="user",
                                to="auth.permission",
                                verbose_name="user permissions",
                            ),
                        ),
                    ],
                    options={
                        "indexes": [
                            models.Index(
                                fields=["-date_joined"],
                                name="acc_user_date_joined_desc_idx",
                            ),
                        ],
                    },
                    managers=[
                        ("objects", django.contrib.auth.models.UserManager()),
                    ],
                ),
            ],
            database_operations=[],
        ),
        migrations.RunPython(_copy_missing_users, migrations.RunPython.noop),
    ]
