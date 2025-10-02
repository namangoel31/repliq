from googleapiclient.http import BatchHttpRequest
from .google_messages import clean_message_body
import base64
from utils.googlePubSub import handle_pubsub_notification
from utils.llmapi import get_draft
import utils.database_models as models
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from email.utils import parseaddr
from utils.cacheProvider import get_hash_key, set_hash_key
from google.oauth2.credentials import Credentials
import config
import logging
import email

app_name = config.APP_NAME
logger = logging.getLogger(app_name)
#logger.info("Valid Repliq token present in request. Redirecting to dashboard.", extra={"path": method_name})

thread_pairs=[]

def fetch_threads_in_batches(service, thread_ids, batch_size=50):
    method_name = "fetch_threads_in_batches"
    logger.info("processing begins.", extra={"path": method_name})
    all_threads = {}

    def callback(request_id, response, exception):
        if exception:
            logger.exception("processign ends with en Exception: %s", str(exception), extra={"path": method_name})
            #print(f"Error for {request_id}: {exception}")
        else:
            all_threads[response['id']] = response

    for i in range(0, len(thread_ids), batch_size):
        batch = BatchHttpRequest(callback=callback)
        for tid in thread_ids[i:i + batch_size]:
            batch.add(service.users().threads().get(userId="me", id=tid))
        batch.execute()

    logger.info("processing ends", extra={"path": method_name})
    return all_threads


def filter_ids(lst):
    method_name = 'filter_ids'
    try:
        logger.info("processing beings.", extra={"path": method_name})
        seen = set()
        unique = []
        for item in lst:
            if item not in seen:
                seen.add(item)
                unique.append(item)
        return unique
    except Exception as ex:
        logger.exception("processing ends with an Exception: %s", str(ex), extra={"path": method_name})


def fetch_my_replies(service, user_email, batch_size=25):
    method_name = 'fetch_my_replies'
    logging.info("processing begins.", extra = {'path': method_name})
    sent_msgs = service.users().messages().list(userId="me", q="from:me in:sent", maxResults=batch_size).execute()
    sent_ids = [m["threadId"] for m in sent_msgs.get("messages", [])]
    results = []
    sent_ids = filter_ids(sent_ids)

    batch = service.new_batch_http_request()
    
    def callback(request_id, thread, exception):
        if exception:
            logger.exception("processing ends with en Exception: %s", str(exception), extra={"path": method_name})
            return

        messages = sorted(thread["messages"], key=lambda m: int(m["internalDate"]))
        last_outgoing = None

        for m in messages:
            results.append(clean_message_body(m))

    for thread_id in sent_ids:
        batch.add(service.users().threads().get(userId="me", id=thread_id, format="full"), callback=callback)
    batch.execute()

    logger.info("processing ends.", extra={'path': method_name})
    return results

def extract_text_from_message(msg):
    method_name = "extract_text_from_message"
    logger.info("processing begins.", extra={'path': method_name})

    if 'parts' in msg['payload']:
        for part in msg['payload']['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body']['data']
                text = base64.urlsafe_b64decode(data).decode()
                logger.info("processing ends.", extra={'path': method_name})
                return text

    if 'body' in msg['payload'] and 'data' in msg['payload']['body']:
        data = msg['payload']['body']['data']
        logger.info("processing ends.", extra={'path': method_name})
        return base64.urlsafe_b64decode(data).decode()
    
    logger.info("processing ends with nothing to extract from incoming message.", extra={'path': method_name})
    return ""

def extract_text_from_message2(msg):
    method_name = "extract_text_from_message2"
    logger.info("processing begins.", extra={'path': method_name})

    if 'parts' in msg['payload']:
        for part in msg['payload']['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body']['data']
                logger.info("processing ends.", extra={'path': method_name})
                return base64.urlsafe_b64decode(data).decode()
            
    if 'body' in msg['payload'] and 'data' in msg['payload']['body']:
        data = msg['payload']['body']['data']
        logger.info("processing ends.", extra={'path': method_name})
        return base64.urlsafe_b64decode(data).decode()
    
    logger.info("processing ends with nothing to extract from incoming message.", extra={'path': method_name})
    return ""


def save_draft(db,result):
    method_name = 'save_draft'
    logger.info("processing begins.", extra={'path': method_name})

    user = db.query(models.user).filter(models.user.email == result['email_address']).first()
    if config.DRAIN_NOTIFICATIONS and user.email == result['email_address']:
        logger.info("Discarding incoming notification. Toggle from config.py", extra={'path': method_name})
        return
    writingStyleObj = db.query(models.writing_style).filter(models.writing_style.user_id == user.id).first()
    writingStyle = writingStyleObj.style

    hashKey = "repliq:google:access_token"
    cacheKey = user.email
    access_code = get_hash_key(hashKey, cacheKey)

    creds = Credentials.from_authorized_user_info(
        {
            "client_id": config.GOOGLE_CLIENT_ID,
            "client_secret": config.GOOGLE_CLIENT_SECRET,
            "refresh_token": user.google_refresh_token,
            "token": access_code,
            "token_uri": "https://oauth2.googleapis.com/token",
            "scopes": ["https://www.googleapis.com/auth/gmail.readonly","https://www.googleapis.com/auth/gmail.compose"]
        }
    )
    service = build("gmail", "v1", credentials=creds)

    message_details = handle_pubsub_notification(db, result, service)
    if not message_details:
        logger.info("No new messages", extra={'path': method_name})
        #print("from saveDraft.py: No new messages")
        return
    original_message = message_details['original_msg']
    message_body_text = message_details['body_text']

    headers = {h['name']: h['value'] for h in original_message['payload']['headers']}
    sender_email = parseaddr(headers.get('from'))[1]


    if sender_email == user.email:
        logger.info("Skipping won messages.", extra={'path': method_name})
        #print("Skipping my own email.")
        return

    #print(message_body_text)
    draft = get_draft(writingStyle, message_body_text)
    #print(draft)


    original_subject = headers.get('Subject', '')
    original_from = headers.get('From')
    message_id = headers.get('Message-ID')
    thread_id = original_message['threadId']
    
    if not original_subject.lower().startswith('re:'):
        subject = f"Re: {original_subject}"
    else:
        subject = original_subject

    message = MIMEText(draft)
    message['to'] = original_from
    message['from'] = user.email
    message['subject'] = subject
    message['In-Reply-To'] = message_id
    message['References'] = message_id

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    #print(message, raw_message)
    # Create draft
    draft = service.users().drafts().create(
        userId="me",
        body={
            'message': {
                'raw': raw_message,
                'threadId': thread_id
            }
        }
    ).execute()

    logger.info("processing ends.", extra={'path': method_name})