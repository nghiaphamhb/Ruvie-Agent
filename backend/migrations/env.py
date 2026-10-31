from alembic import context
from sqlalchemy import engine_from_config, pool

from ruvie.config import load_settings
from ruvie.models import Base


config = context.config
# Importing ruvie.models registers all active tables; applied version files stay unchanged.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generate migration SQL without opening a database connection."""
    context.configure(
        url=load_settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        config.attributes['fresh_database'] = context.get_starting_revision_argument() in (None, 'base')
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect using server DATABASE_URL and apply migrations in a transaction."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = load_settings().database_url
    connectable = engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            # Capture the starting revision before earlier migrations seed singleton rows.
            # A version-zero provider in an existing deployment is still a cutover, not a fresh install.
            config.attributes['fresh_database'] = context.get_context().get_current_revision() is None
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
