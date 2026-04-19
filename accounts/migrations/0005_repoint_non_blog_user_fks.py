from django.db import migrations


USER_FK_TARGETS = (
    ("accounts_profile", "user_id"),
    ("django_admin_log", "user_id"),
)


def _table_exists(schema_editor, table_name):
    return table_name in schema_editor.connection.introspection.table_names()


def _find_fk_constraint(schema_editor, table_name, column_name):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT c.conname, c.confrelid::regclass::text
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            JOIN pg_attribute a ON a.attrelid = t.oid
            WHERE c.contype = 'f'
              AND n.nspname = 'public'
              AND t.relname = %s
              AND a.attnum = ANY(c.conkey)
              AND a.attname = %s
            ORDER BY c.conname
            """,
            [table_name, column_name],
        )
        return cursor.fetchone()


def _fallback_constraint_name(table_name, column_name):
    suffix = "_fk_accounts_customuser_id"
    base = f"{table_name}_{column_name}"
    limit = 63 - len(suffix)
    return f"{base[:limit]}{suffix}"


def _repoint_foreign_keys(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    quote = schema_editor.quote_name
    for table_name, column_name in USER_FK_TARGETS:
        if not _table_exists(schema_editor, table_name):
            continue

        constraint = _find_fk_constraint(schema_editor, table_name, column_name)
        if constraint and constraint[1] == "accounts_customuser":
            continue

        constraint_name = (
            constraint[0] if constraint else _fallback_constraint_name(table_name, column_name)
        )

        if constraint:
            schema_editor.execute(
                f"ALTER TABLE {quote(table_name)} DROP CONSTRAINT {quote(constraint_name)}"
            )

        schema_editor.execute(
            f"""
            ALTER TABLE {quote(table_name)}
            ADD CONSTRAINT {quote(constraint_name)}
            FOREIGN KEY ({quote(column_name)})
            REFERENCES {quote("accounts_customuser")} ({quote("id")})
            DEFERRABLE INITIALLY DEFERRED
            """
        )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_repair_customuser_table"),
    ]

    operations = [
        migrations.RunPython(_repoint_foreign_keys, migrations.RunPython.noop),
    ]
