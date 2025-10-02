import redis
import os
import config
import logging

app_name = config.APP_NAME
logger = logging.getLogger(app_name)

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
    method_name = 'set_hash_key'
    logger.info("processing begins.", extra = {'path': method_name})
    try:
        r = get_redis_connection()
        r.hset(hash_name, field, value)
        logger.info("processing ends.", extra = {'path': method_name})
    except Exception as ex:
        logger.exception("processing ends with an exception: %s", ex, extra = {'path': method_name} )
        #print(ex)

def get_hash_key(hash_name, field):
    method_name = 'get_hash_key'
    logger.info("processing begins.", extra = {'path': method_name})
    try:
        r = get_redis_connection()
        value = r.hget(hash_name, field)
        logger.info("processing ends.", extra = {'path': method_name})
        return value
    except Exception as ex:
        logger.exception("processing ends with an exception: %s", ex, extra={"path": method_name})
        #print(ex)

def set_set_key(set_name, value, ttl=3600):
    method_name = 'set_set_key'
    logger.info("processing begins.", extra = {'path': method_name})
    try:
        r = get_redis_connection()
        pipeline = r.pipeline()
        pipeline.sadd(set_name, value)

        if not r.exists(set_name):
            pipeline.expire(set_name, ttl)

        results = pipeline.execute()
        was_added = results[0]
        logger.info("processing ends.", extra = {'path': method_name})
        return was_added
    except Exception as ex:
        logger.exception("processing ends with an exception: %s", ex, extra={"path": method_name})
        #print(ex)
        return -1