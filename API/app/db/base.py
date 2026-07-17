"""
Base class cho tất cả SQLAlchemy models.
Import file này để truy cập Base.metadata (dùng cho create_all, Alembic, ...).
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
