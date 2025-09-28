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

def create_watch_request(token, refresh_token, email):
    creds = Credentials(
        token=token,
        refresh_token= refresh_token,
        client_id= config.GOOGLE_CLIENT_ID,
        client_secret= config.GOOGLE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token"
    )

    service = build('gmail', 'v1', credentials=creds)

    topic_name = config.PUBSUB_TOPIC_NAME

    VERIFICATION_TOKEN = "my-secret-token-123"

    watch_request = {
        "labelIds": ["INBOX"],
        "topicName": topic_name,
        "labelFilterAction": "INCLUDE",
        "token": VERIFICATION_TOKEN
    }

    response = service.users().watch(userId="me", body=watch_request).execute()
    hashKey = "repliq:google:history_id"
    cacheKey = email
    set_hash_key(hashKey, cacheKey, response['historyId'])
    print("Watch started:", response)

google_certs = {}

def get_google_certs():
    global google_certs
    if not google_certs:
        response = requests.get(config.GOOGLE_CERTS_URL)
        response.raise_for_status()
        google_certs = response.json()
    return google_certs


def get_public_key(cert_pem: str):
    cert = x509.load_pem_x509_certificate(cert_pem.encode("utf-8"), default_backend())
    return cert.public_key()

def verify_incoming_request(token):
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
                print(f"Skipping cert {key_id}: {e}")
                continue

        if not decoded_token:
            raise Exception("Unable to verify token with any Google cert")

        print("JWT verified:", decoded_token)

    except Exception as e:
        print("JWT verification failed:", e)
        raise HTTPException(status_code=403, detail="JWT verification failed")


def decode_push_notification_data(pubsub_message):
    data = base64.urlsafe_b64decode(pubsub_message["message"]["data"]).decode("utf-8")
    decoded = json.loads(data)
    #print("Decoded Pub/Sub data:", decoded)

    email_address = decoded["emailAddress"]
    history_id = decoded["historyId"]

    return {"email_address" : email_address,
            "history_id" : history_id}

def handle_pubsub_notification(db: Session, result, service):
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
        print("from goolePubSub.py: No new messages.")
        # hashKey = "repliq:google:history_id"
        # cacheKey = email
        # value = history_id
        # set_hash_key(hashKey, cacheKey, value)
        print("returning from no history block")
        return None
    
    body_text = ''
    for record in history["history"]:
        if "messagesAdded" in record:
            for msg in record["messagesAdded"]:
                msg_id = msg["message"]["id"]
                print("messageId: ", msg_id)
                try:
                    message = service.users().messages().get(
                        userId=email,
                        id=msg_id,
                        format="full"
                    ).execute()
                except HTTPException as ex:
                    print(ex)
                    continue
                except HttpError as ex:
                    print(ex)
                    continue                    
                headers = {h['name']: h['value'] for h in message['payload']['headers']}
                print(headers)
                sender_email = parseaddr(headers.get('from'))[1]
                print("############################", sender_email)

                if sender_email == email:
                    print("Skipping my own message:", msg_id)
                    continue

                body_text = parse_message(message)['body']
                print("New message snippet:", message.get("snippet"))
                print("Full message ID:", message["id"])
                if check_duplicate(message["id"], email):
                    print("returning from handle_pubsub_notification, check duplicate block")
                    return
    # hashKey = "repliq:google:history_id"
    # cacheKey = email
    # value = history_id
    # set_hash_key(hashKey, cacheKey,value)
    if body_text:
        return {"original_msg": message, "body_text": body_text}
    return

def check_duplicate(message_id, email):
    set_name = f"repliq:google:message_id:{email}"
    duplicate = set_set_key(set_name, message_id)
    print(duplicate)
    if duplicate == 0:
        print(f"Skipping duplicate message: {message_id}")
        return True