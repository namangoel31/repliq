import requests
import config
import time
from .cacheProvider import get_hash_key, set_hash_key
from . import database_models as models
from sqlalchemy.orm import Session
from fastapi import Depends
from utils.database import engine, get_db

def is_google_token_expired(email: str) -> bool:
    try:
        hashKey = "repliq:google:access_token:fetched_at"
        cacheKey = email
        fetched_at = get_hash_key(hashKey, cacheKey)
        if fetched_at is None:
            return True
        fetched_at = float(fetched_at)
        return time.time() > fetched_at + config.GOOGLE_ACCESS_TOKEN_EXPIRE_SECONDS
    except Exception as e:
        print(f"Error checking token expiry: {e}")
        return True

def refresh_google_access_token(email: str, refresh_token: str, db: Session):
    try:
        # user = db.query(models.user).filter(models.user.email == email).first()
        # refresh_token = user.google_refresh_token
        data = {
            "client_id": config.GOOGLE_CLIENT_ID,
            "client_secret": config.GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }

        token_fetched_at = time.time()

        response = requests.post(config.GOOGLE_TOKEN_URL, data=data)

        response.raise_for_status()
        token_data = response.json()
        access_token = token_data["access_token"]
        
        hashKey = "repliq:google:access_token"
        cacheKey = email
        set_hash_key(hashKey, cacheKey, access_token)

        hashKey = "repliq:google:access_token:fetched_at"
        cacheKey = email
        set_hash_key(hashKey, cacheKey, token_fetched_at)

        return access_token  # contains new access_token

    except Exception as e:
        print("Exception occured: ", e)
        return False