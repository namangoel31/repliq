import base64
from bs4 import BeautifulSoup
import re
import config
import logging

app_name = config.APP_NAME
logger = logging.getLogger(app_name)
#logger.info("Valid Repliq token present in request. Redirecting to dashboard.", extra={"path": method_name})

def parse_message(msg):
    method_name = 'parse_message'
    logger.info("processing begins.", extra={"path": method_name})

    headers = msg.get("payload", {}).get("headers", [])
    header_dict = {h["name"]: h["value"] for h in headers}

    sender = header_dict.get("From", "")
    subject = header_dict.get("Subject", "")

    body = ""
    payload = msg.get("payload", {})

    def decode_part(part):
        method_name = 'parse_message -> decode_part'
        data = part.get("body", {}).get("data", "")
        if data:
            logger.info("processing ends.", extra={"path": method_name})
            return base64.urlsafe_b64decode(data.encode()).decode()
        logger.info("processing ends with nothing to extract from message part.", extra={"path": method_name})
        return ""

    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain":
                body = decode_part(part)
                break
        else:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/html":
                    html_content = decode_part(part)
                    body = BeautifulSoup(html_content, "html.parser").get_text()
                    break
    else:
        mime_type = payload.get("mimeType", "")
        if mime_type == "text/plain":
            body = decode_part(payload)
        elif mime_type == "text/html":
            html_content = decode_part(payload)
            body = BeautifulSoup(html_content, "html.parser").get_text()

    body = " ".join(body.split())

    logger.info("processing ends.", extra={"path": method_name})
    return {
        "sender": sender,
        "subject": subject,
        "body": body
    }

def get_plain_text(payload):
    method_name = "get_plain_text"
    logger.info("processing begins.", extra = {'path': method_name})
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                logger.info("processing ends.", extra = {'path': method_name})
                return part['body'].get('data', '')
            elif 'parts' in part:
                text = get_plain_text(part)
                if text:
                    logger.info("processing ends.", extra = {'path': method_name})
                    return text
    elif payload['mimeType'] == 'text/plain':
        logger.info("processing ends.", extra = {'path': method_name})
        return payload['body'].get('data', '')
    
    logger.info("processing ends with nothing to convert to plain text.", extra = {'path': method_name})
    return ""

def extract_text_from_message(message):
    method_name = "extract_text_from_message"
    logger.info("processing begins.", extra = {'path': method_name})
    payload = message['payload']
    raw_text = get_plain_text(payload)
    logger.info("processing ends.", extra = {'path': method_name})
    return base64.urlsafe_b64decode(raw_text.encode('ASCII')).decode('utf-8')

def strip_quoted_text(text):
    method_name = "strip_quoted_text"
    logger.info("processing begins.", extra = {'path': method_name})
    text = re.sub(r'(^>.*$\n?)', '', text, flags=re.MULTILINE)
    text = re.sub(r'On .* wrote:', '', text)
    logger.info("processing ends.", extra = {'path': method_name})
    return text.strip()

def clean_message_body(message):
    method_name = "clean_message_body"
    logger.info("processing begins.", extra = {'path': method_name})
    body = extract_text_from_message(message)
    sender=''
    receiver=''
    DateTime = ''
    for i in message['payload']['headers']:
        if i['name'] == 'To':
            receiver = i['value']
        if i['name'] == 'From':
            sender = i['value']
        if i['name'] == 'Date':
            DateTime = i['value']
    result = {"id":message['id'], 
            "threadId": message["threadId"], 
            "date": DateTime, 
            "from": sender, 
            "to": receiver, 
            "message": strip_quoted_text(body)}
    
    logger.info("processing ends.", extra = {'path': method_name})
    return result

def create_threads_preserve_breaks(messages, email):
    method_name = "create_threads_preserve_breaks"
    logger.info("processing begins.", extra = {'path': method_name})
    #print(messages)
    threads = []
    thread = {}
    for message in messages:
        if thread.get('id') and thread.get('id') == message['threadId']:
            if email in message['from']:
                thread['messageSent'] = message['message']
            else:
                thread['messageReceived'] = message['message']
        else:
            if thread:
                threads.append(thread)
            thread= {}
            thread['id'] = message['threadId']
            if email in message['from']:
                thread['messageSent'] = message['message']
            else:
                thread['messageReceived'] = message['message']
    if thread:
        threads.append(thread)
    logger.info("processing ends.", extra = {'path': method_name})
    return threads

def create_threads(messages, email):
    method_name = "create_threads"
    logger.info("processing begins.", extra = {'path': method_name})
    threads = []
    thread = {}
    for message in messages:
        if thread.get('id') and thread.get('id') == message['threadId']:
            if email in message['from']:
                message_data = message['message'].replace('\r', '').replace('\n', ' ')
                thread['messages'].append(f"Sent: {message_data}")
            else:
                message_data = message['message'].replace('\r', '').replace('\n', ' ')
                thread['messages'].append(f"Received: {message_data}")
        else:
            if thread:
                threads.append(thread)
            thread= {}
            thread['id'] = message['threadId']
            if email in message['from']:
                message_data = message['message'].replace('\r', '').replace('\n', ' ')
                thread['messages'] = [f"Sent: {message_data}"]
            else:
                message_data = message['message'].replace('\r', '').replace('\n', ' ')
                thread['messages'] = [f"Received: {message_data}"]
    if thread:
        threads.append(thread)

    logger.info("processing ends.", extra = {'path': method_name})
    return threads