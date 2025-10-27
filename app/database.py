# the purpose of this module is to establish a database connection and a function
# to create new sessions from the database engine

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
from config import database_config

class Base(DeclarativeBase): pass

def create_connection_string() -> str:
    return f"mysql+pymysql://{database_config.get('user')}:{database_config.get('password')}@{database_config.get('host')}:{database_config.get('port')}/{database_config.get('database')}"

engine = create_engine(url=create_connection_string())
LocalSession = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False # keeps objects usable after commit
 )

def get_session() -> Session:
    return LocalSession()


