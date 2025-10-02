from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import config
import base64
import json
import requests
from cryptography import x509
from cryptography.hazmat.backends import default_backend
import jwt
from fastapi import HTTPException
from sqlalchemy.orm import Session
import utils.database_models as models
from utils.cacheProvider import get_hash_key, set_hash_key, set_set_key
from utils.google_messages import create_threads_preserve_breaks, parse_message
from email.utils import parseaddr
from googleapiclient.errors import HttpError
import logging

app_name = config.APP_NAME
logger = logging.getLogger(app_name)

def create_watch_request(token, refresh_token, email, db):
    method_name = "create_watch_request"
    logger.info("processing begins.", extra={"path": method_name})
    creds = Credentials(
        token=token,
        refresh_token= refresh_token,
        client_id= config.GOOGLE_CLIENT_ID,
        client_secret= config.GOOGLE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token"
    )

    service = build('gmail', 'v1', credentials=creds)

    topic_name = config.PUBSUB_TOPIC_NAME

    GMAIL_WATCH_VERIFICATION_TOKEN = config.GMAIL_WATCH_VERIFICATION_TOKEN

    watch_request = {
        "labelIds": ["INBOX"],
        "topicName": topic_name,
        "labelFilterAction": "INCLUDE",
        "token": GMAIL_WATCH_VERIFICATION_TOKEN
    }

    user_obj_query = db.query(models.user).filter(models.user.email == email)
    user_dict = {"watch_status": True}
    user_obj_query.update(user_dict, synchronize_session = False)
    db.commit()

    response = service.users().watch(userId="me", body=watch_request).execute()
    hashKey = "repliq:google:history_id"
    cacheKey = email
    set_hash_key(hashKey, cacheKey, response['historyId'])
    logger.info("processing ends.", extra={"path": method_name})

def stop_watch_request(token, refresh_token, email, db):
    method_name = "stop_watch_request"
    logger.info("processing begins.", extra={"path": method_name})

    creds = Credentials(
        token=token,
        refresh_token= refresh_token,
        client_id= config.GOOGLE_CLIENT_ID,
        client_secret= config.GOOGLE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token"
    )

    service = build('gmail', 'v1', credentials=creds)
    response = service.users().stop(userId="me").execute()

    user_obj_query = db.query(models.user).filter(models.user.email == email)
    user_dict = {"watch_status": False}
    user_obj_query.update(user_dict, synchronize_session = False)
    db.commit()
    logger.info("processing ends.", extra={"path": method_name})


google_certs = {}

def get_google_certs():
    method_name = "get_google_certs"
    logger.info("processing begins.", extra={"path": method_name})
    global google_certs
    if not google_certs:
        response = requests.get(config.GOOGLE_CERTS_URL)
        response.raise_for_status()
        google_certs = response.json()
    logger.info("processing ends.", extra={"path": method_name})
    return google_certs


def get_public_key(cert_pem: str):
    method_name = "get_public_key"
    logger.info("processing begins.", extra={"path": method_name})
    cert = x509.load_pem_x509_certificate(cert_pem.encode("utf-8"), default_backend())
    logger.info("processing ends.", extra={"path": method_name})
    return cert.public_key()

def verify_incoming_request(token):
    method_name = "verify_incoming_request"
    logger.info("processing begins.", extra={"path": method_name})
    try:
        certs = get_google_certs()
        decoded_token = None

        for key_id, cert_pem in certs.items():
            try:
                public_key = get_public_key(cert_pem)
                decoded_token = jwt.decode(
                    token,
                    public_key,
                    algorithms=["RS256"],
                    audience=f"{config.APP_DOMAIN}/push"
                )
                break
            except jwt.exceptions.InvalidSignatureError:
                continue
            except Exception as e:
                continue

        if not decoded_token:
            msg = "Unable to verify token with any Google cert"
            logger.error("processing ends with an exception: %s", msg, extra={"path": method_name})
            raise Exception(msg)
        
        logger.info("processing ends. JWT verified", extra={"path": method_name})

    except Exception as e:
        logger.exception("processing ends with an exception %s", e, extra = {"path": method_name})
        raise HTTPException(status_code=403, detail="JWT verification failed")


def decode_push_notification_data(pubsub_message):
    method_name = "decode_push_notification_data"
    logger.info("processing begins.", extra={"path": method_name})
    data = base64.urlsafe_b64decode(pubsub_message["message"]["data"]).decode("utf-8")
    decoded = json.loads(data)

    email_address = decoded["emailAddress"]
    history_id = decoded["historyId"]

    logger.info("processing ends.", extra={"path": method_name})
    return {"email_address" : email_address,
            "history_id" : history_id}

def handle_pubsub_notification(db: Session, result, service):
    method_name = "handle_pubsub_notification"
    logger.info("processing begins.", extra={"path": method_name})
    email = result['email_address']
    history_id = result['history_id']

    hashKey = "repliq:google:history_id"
    cacheKey = email
    start_history_id = get_hash_key(hashKey, cacheKey)

    if not start_history_id:
        start_history_id = history_id
    set_hash_key(hashKey, cacheKey, history_id)

    history = service.users().history().list(
        userId=email,
        startHistoryId=start_history_id,
        historyTypes=["messageAdded"]
    ).execute()

    if "history" not in history:
        logger.info("processing ends with no new message.", extra={"path": method_name})
        return None
    
    body_text = ''
    for record in history["history"]:
        if "messagesAdded" in record:
            for msg in record["messagesAdded"]:
                msg_id = msg["message"]["id"]
                try:
                    message = service.users().messages().get(
                        userId=email,
                        id=msg_id,
                        format="full"
                    ).execute()
                except HTTPException as ex:
                    logger.exception("An exception occured while going through message history: %s", str(ex), extra={"path": method_name})
                    continue
                except HttpError as ex:
                    logger.exception("An exception occured while going through message history: %s", str(ex), extra={"path": method_name})
                    continue                    
                headers = {h['name']: h['value'] for h in message['payload']['headers']}
                sender_email = parseaddr(headers.get('from'))[1]

                if sender_email == email:
                    continue
                body_text = parse_message(message)['body']
                logger.info("New message ID and snippet: %s: %s", message['id'], message.get("snippet"), extra={"path": method_name})
                if check_duplicate(message["id"], email):
                    logger.info("processing ends. Duplicate message.", extra={"path": method_name})
                    return
    if body_text:
        logger.info("processing ends.", extra={"path": method_name})
        return {"original_msg": message, "body_text": body_text}
    logger.info("processing ends with empty message.", extra={"path": method_name})
    return

def check_duplicate(message_id, email):
    method_name = "handle_pubsub_notification"
    logger.info("processing begins.", extra={"path": method_name})
    set_name = f"repliq:google:message_id:{email}"
    duplicate = set_set_key(set_name, message_id)
    if duplicate == 0:
        logger.info("processing ends. Duplicate message", extra={"path": method_name})
        return True