import redis
import os
import config

redis_connection = None

def get_redis_connection():
    global redis_connection
    
    if redis_connection is None:
        redis_host = config.CACHE_SERVER_ENDPOINT
        redis_port = config.CACHE_SERVER_PORT
        redis_password = config.CACHE_SERVER_PASSWORD
        redis_connection = redis.StrictRedis(host=redis_host, port=redis_port, password=redis_password, db=0, decode_responses=True)
    return redis_connection

def set_hash_key(hash_name, field, value):
    try:
        r = get_redis_connection()
        r.hset(hash_name, field, value)
    except Exception as ex:
        print(ex)

def get_hash_key(hash_name, field):
    try:
        r = get_redis_connection()
        value = r.hget(hash_name, field)
        return value
    except Exception as ex:
        print(ex)