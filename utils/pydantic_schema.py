from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class user(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str

class userResponse(user):
    created_at: datetime

    class Config:
        orm_model = True

class Token(BaseModel):
    sub: str

class TokenData(BaseModel):
    sub: Optional[str] = None