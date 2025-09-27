from googleapiclient.http import BatchHttpRequest
from .google_messages import clean_message_body
import base64

thread_pairs=[]

def fetch_threads_in_batches(service, thread_ids, batch_size=50):
    all_threads = {}

    def callback(request_id, response, exception):
        if exception:
            print(f"Error for {request_id}: {exception}")
        else:
            all_threads[response['id']] = response

    for i in range(0, len(thread_ids), batch_size):
        batch = BatchHttpRequest(callback=callback)
        for tid in thread_ids[i:i + batch_size]:
            batch.add(service.users().threads().get(userId="me", id=tid))
        batch.execute()

    return all_threads

def filter_ids(lst):
    seen = set()
    unique = []
    for item in lst:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def fetch_my_replies(service, user_email, batch_size=25):
    sent_msgs = service.users().messages().list(userId="me", q="from:me in:sent", maxResults=batch_size).execute()
    sent_ids = [m["threadId"] for m in sent_msgs.get("messages", [])]
    results = []
    sent_ids = filter_ids(sent_ids)

    batch = service.new_batch_http_request()
    
    def callback(request_id, thread, exception):
        if exception:
            return

        messages = sorted(thread["messages"], key=lambda m: int(m["internalDate"]))
        last_outgoing = None

        for m in messages:
            results.append(clean_message_body(m))

    for thread_id in sent_ids:
        batch.add(service.users().threads().get(userId="me", id=thread_id, format="full"), callback=callback)
    batch.execute()

    return results

def extract_text_from_message(msg):
    """Extract plain text from Gmail message payload"""
    import base64
    import email

    if 'parts' in msg['payload']:
        for part in msg['payload']['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body']['data']
                text = base64.urlsafe_b64decode(data).decode()
                return text

    if 'body' in msg['payload'] and 'data' in msg['payload']['body']:
        data = msg['payload']['body']['data']
        return base64.urlsafe_b64decode(data).decode()
    return ""

def extract_text_from_message2(msg):
    if 'parts' in msg['payload']:
        for part in msg['payload']['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body']['data']
                return base64.urlsafe_b64decode(data).decode()
    if 'body' in msg['payload'] and 'data' in msg['payload']['body']:
        data = msg['payload']['body']['data']
        return base64.urlsafe_b64decode(data).decode()
    return ""
