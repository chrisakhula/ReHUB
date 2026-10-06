import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from app.core.config import get_settings
from app.core.database import Base
from app.models import identity  # noqa: F401

fileConfig(context.config.config_file_name)
target_metadata = Base.metadata
domain = os.environ.get("ALEMBIC_DOMAIN")
domain_tables = (
    set(Base.metadata.tables)
    if domain is None
    else {
        table.name
        for mapper in Base.registry.mappers
        if domain is None or mapper.class_.__module__ == f"app.models.{domain}"
        for table in [mapper.local_table]
    }
)


def include_object(obj, name, object_type, reflected, compare_to):
    if object_type == "table":
        return name in domain_tables
    return True


def run():
    url = get_settings().database_url
    if context.is_offline_mode():
        context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
        with context.begin_transaction():
            context.run_migrations()
    else:
        with create_engine(url).connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                include_object=include_object,
            )
            with context.begin_transaction():
                context.run_migrations()


run()
