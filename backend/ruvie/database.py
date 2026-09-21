from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from ruvie.config import load_settings


def create_database_engine() -> Engine:
    return create_engine(load_settings().database_url, pool_pre_ping=True)
