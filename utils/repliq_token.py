import jwt
from datetime import datetime, timedelta
import config
from . import pydantic_schema
from fastapi import status, HTTPException


SECRET_KEY = config.SECRET_KEY  # move to env var in production
ALGORITHM = config.ALGORITHM
REPLIQ_TOKEN_EXPIRE_MINUTES = config.REPLIQ_TOKEN_EXPIRE_MINUTES

def create_custom_token(email: str):
    expire = datetime.utcnow() + timedelta(minutes=REPLIQ_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": email, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_custom_token(token: str, credentials_exception):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub: str = payload.get("sub")
        if sub is None:
            raise credentials_exception
        token_data = pydantic_schema.TokenData(sub = sub)
    except jwt.PyJWTError:
        raise credentials_exception
    return token_data

def get_current_user(token: str):
    credentials_exception = HTTPException(status_code = status.HTTP_401_UNAUTHORIZED,
                                          detail = f"could not validate credentials",
                                          headers = {"WWW-Authenticate": "Bearer"})
    return decode_custom_token(token, credentials_exception)