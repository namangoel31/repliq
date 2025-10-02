import jwt
from datetime import datetime, timedelta
import config
from . import pydantic_schema
from fastapi import status, HTTPException, Request
import logging

app_name = config.APP_NAME
logger = logging.getLogger(app_name)
#logger.info("Valid Repliq token present in request. Redirecting to dashboard.", extra={"path": method_name})

SECRET_KEY = config.SECRET_KEY
ALGORITHM = config.ALGORITHM
REPLIQ_TOKEN_EXPIRE_MINUTES = config.REPLIQ_TOKEN_EXPIRE_MINUTES

def create_custom_token(email: str):
    method_name = "create_custom_token"
    logger.info("processing begins.", extra={"path": method_name})
    expire = datetime.utcnow() + timedelta(minutes=REPLIQ_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": email, "exp": expire}
    logger.info("processing ends.", extra={"path": method_name})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_custom_token(token: str, credentials_exception):
    method_name = "decode_custom_token"
    logger.info("processing begins.", extra={"path": method_name})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub: str = payload.get("sub")
        if sub is None:
            logger.error("processing ends with exception %s.", str(credentials_exception), extra={"path": method_name})
            raise credentials_exception
        token_data = pydantic_schema.TokenData(sub = sub)
    except jwt.PyJWTError as ex:
        logger.exception("processing ends with exception %s.", str(ex), extra={"path": method_name})
        raise credentials_exception
    return token_data

def get_current_user(token: str):
    method_name = "get_current_user"
    logger.info("processing begins.", extra={"path": method_name})
    credentials_exception = HTTPException(status_code = status.HTTP_401_UNAUTHORIZED,
                                          detail = f"could not validate credentials",
                                          headers = {"WWW-Authenticate": "Bearer"})
    logger.info("processing ends.", extra={"path": method_name})
    return decode_custom_token(token, credentials_exception)

def check_for_repliq_token(request: Request, db):
    method_name = "check_for_repliq_token"
    logger.info("processing begins.", extra = {"path": method_name})
