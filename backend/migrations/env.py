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
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect using server DATABASE_URL and apply migrations in a transaction."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = load_settings().database_url
    connectable = engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
