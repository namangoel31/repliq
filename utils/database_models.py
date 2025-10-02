from .database import Base
from sqlalchemy import Column, Integer, String, Boolean, text, ForeignKey
from sqlalchemy.sql.sqltypes import TIMESTAMP

class user(Base):
    __tablename__ = "repliq_users"

    id = Column(Integer, primary_key = True, nullable = False)
    email = Column(String, unique= True, nullable = False)
    name = Column(String, nullable = False)
    google_refresh_token = Column(String, nullable = False)
    token_issued_at = Column(Integer, nullable = False)
    token_expires_in = Column(Integer, nullable = False, server_default = text('604799'))
    watch_status = Column(Boolean, nullable = False, server_default = text('False'))

    created_at = Column (TIMESTAMP(timezone = True),
                         nullable = False,
                         server_default = text('now()'))
    

class writing_style(Base):
    __tablename__ = "repliq_writing_style"

    id = Column(Integer, primary_key = True, nullable = False,)
    user_id = Column(Integer, ForeignKey("repliq_users.id"), nullable = False)
    style = Column(String, nullable = False)

    created_at = Column (TIMESTAMP(timezone = True),
                         nullable = False,
                         server_default = text('now()'))