from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set sqlalchemy.url from our application settings
from symbology.utils.config import settings
config.set_main_option("sqlalchemy.url", settings.database.url)

# Import all models so Base.metadata is fully populated
from symbology.database.base import Base
import symbology.database.companies  # noqa: F401
import symbology.database.documents  # noqa: F401
import symbology.database.filings  # noqa: F401
import symbology.database.financial_concepts  # noqa: F401
import symbology.database.financial_values  # noqa: F401
import symbology.database.generated_content  # noqa: F401
import symbology.database.model_configs  # noqa: F401
import symbology.database.prompts  # noqa: F401
import symbology.database.ratings  # noqa: F401

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configures the context with just a URL so we don't need a live database.
    Emits SQL to stdout instead of executing it.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Creates an engine and runs migrations against the live database.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
