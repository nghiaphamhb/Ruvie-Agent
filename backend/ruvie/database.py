from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

def create_database_engine(database_url: str) -> Engine:
    """Create the connection pool and check stale connections before reuse."""
    return create_engine(database_url, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return a factory so each request/job owns and closes its DB session."""
    return sessionmaker(bind=engine)
