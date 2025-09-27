import base64
from bs4 import BeautifulSoup  # pip install beautifulsoup4

def parse_message(msg):
    """
    Extract sender, subject, and body from Gmail API message.
    Supports HTML emails by converting them to plain text.
    """
    headers = msg.get("payload", {}).get("headers", [])
    header_dict = {h["name"]: h["value"] for h in headers}

    sender = header_dict.get("From", "")
    subject = header_dict.get("Subject", "")

    body = ""
    payload = msg.get("payload", {})

    def decode_part(part):
        data = part.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data.encode()).decode()
        return ""

    # Try text/plain first
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain":
                body = decode_part(part)
                break
        else:
            # fallback to HTML
            for part in payload["parts"]:
                if part.get("mimeType") == "text/html":
                    html_content = decode_part(part)
                    body = BeautifulSoup(html_content, "html.parser").get_text()
                    break
    else:
        # single part message
        mime_type = payload.get("mimeType", "")
        if mime_type == "text/plain":
            body = decode_part(payload)
        elif mime_type == "text/html":
            html_content = decode_part(payload)
            body = BeautifulSoup(html_content, "html.parser").get_text()

    # Optional: clean up extra whitespace
    body = " ".join(body.split())

    return {
        "sender": sender,
        "subject": subject,
        "body": body
    }

def get_plain_text(payload):
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                return part['body'].get('data', '')
            elif 'parts' in part:
                text = get_plain_text(part)
                if text:
                    return text
    elif payload['mimeType'] == 'text/plain':
        return payload['body'].get('data', '')
    return ""


import base64

def extract_text_from_message(message):
    #print(message)
    payload = message['payload']
    raw_text = get_plain_text(payload)
    return base64.urlsafe_b64decode(raw_text.encode('ASCII')).decode('utf-8')

import re

def strip_quoted_text(text):
    # remove lines starting with '>'
    text = re.sub(r'(^>.*$\n?)', '', text, flags=re.MULTILINE)
    # remove lines like "On Tue, 3 Sep 2024, Naman Goel wrote:"
    text = re.sub(r'On .* wrote:', '', text)
    return text.strip()

def clean_message_body(message):
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

    return result

def create_threads_preserve_breaks(messages, email):
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
    return threads

def create_threads(messages, email):
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
    return threads