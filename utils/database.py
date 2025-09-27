from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import config

SQL_ALCHEMY_DATABASE_URL = config.SQL_ALCHEMY_DATABASE_URL


engine = create_engine(SQL_ALCHEMY_DATABASE_URL)

sessionLocal = sessionmaker(autocommit = False,
                            autoflush = False,
                            bind = engine)

Base = declarative_base()
BaseMongo = declarative_base()

def get_db():
    db = sessionLocal()
    try:
        yield db
    finally:
        db.close()