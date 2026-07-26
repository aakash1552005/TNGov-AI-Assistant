"""SQLAlchemy declarative base for all ORM models.

Import ``Base`` in every model module so that all tables are
registered on a single metadata instance. This allows
``Base.metadata.create_all`` in ``main.py`` to discover and create
every table.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass
