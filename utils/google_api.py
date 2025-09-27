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
    """
    Returns a new list containing only unique elements from the input list,
    preserving their original order.
    """
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
        # if exception is None:
        #     messages = thread.get("messages", [])
        #     my_msg = None
        #     original_msg = None
        #     for m in messages:
        #         headers = {h['name']: h['value'] for h in m['payload']['headers']}
        #         if user_email in headers.get("From", ""):
        #             my_msg = m
        #         else:
        #             original_msg = m
        #     if my_msg and original_msg:
        #         results.append({
        #             "original": {
        #                 "from": [h['value'] for h in original_msg['payload']['headers'] if h['name'] == "From"][0],
        #                 "subject": [h['value'] for h in original_msg['payload']['headers'] if h['name'] == "Subject"][0],
        #                 "body": extract_text_from_message(original_msg)
        #             },
        #             "reply": {
        #                 "body": extract_text_from_message(my_msg)
        #             }
        #         })
        # if exception is None:
        #     messages = sorted(thread["messages"], key=lambda x: int(x["internalDate"]))
        #     previous_outgoing = None

        #     for m in messages:
        #         headers = {h['name']: h['value'] for h in m['payload']['headers']}
        #         sender = headers.get("From", "")
        #         if user_email in sender:  # outgoing
        #             previous_outgoing = m
        #         elif previous_outgoing:    # incoming reply
        #             results.append({
        #                 "original": {
        #                     "from": previous_outgoing['payload']['headers'][0]['value'],  # Or better: clean headers
        #                     "subject": headers.get("Subject"),
        #                     "body": clean_message_body(previous_outgoing)
        #                 },
        #                 "reply": {
        #                     "body": clean_message_body(m)
        #                 }
        #             })
        #             previous_outgoing = None

        # if exception is None:
        #     # Sort messages chronologically
        #     messages = sorted(thread["messages"], key=lambda x: int(x["internalDate"]))
        #     outgoing_queue = []

        #     for m in messages:
        #         headers = {h['name']: h['value'] for h in m['payload']['headers']}
        #         sender = headers.get("From", "")
        #         if user_email in sender:  # outgoing
        #             outgoing_queue.append(m)
        #         else:  # incoming reply
        #             if outgoing_queue:
        #                 original_msg = outgoing_queue.pop(0)  # pair with oldest unpaired outgoing
        #                 results.append({
        #                     "original": {
        #                         "from": headers.get("From"),
        #                         "subject": headers.get("Subject"),
        #                         "body": clean_message_body(original_msg)
        #                     },
        #                     "reply": {
        #                         "body": clean_message_body(m)
        #                     }
        #                 })
        # if exception is not None:
        #     return

        # messages = sorted(thread["messages"], key=lambda m: int(m["internalDate"]))
        # outgoing_queue = []

        # for m in messages:
        #     headers = {h['name']: h['value'] for h in m['payload']['headers']}
        #     sender = headers.get("From", "")
        #     if user_email in sender:
        #         outgoing_queue.append(m)  # queue outgoing
        #     else:
        #         # incoming reply
        #         if outgoing_queue:
        #             original_msg = outgoing_queue.pop(0)  # pair with oldest unpaired outgoing
        #             results.append({
        #                 "original": {
        #                     "from": headers.get("From"),
        #                     "subject": headers.get("Subject"),
        #                     "body": clean_message_body(original_msg)
        #                 },
        #                 "reply": {
        #                     "body": clean_message_body(m)
        #                 }
        #             })
        if exception:
            return

        messages = sorted(thread["messages"], key=lambda m: int(m["internalDate"]))
        last_outgoing = None

        # for m in messages:
        #     headers = {h['name']: h['value'] for h in m['payload']['headers']}
        #     sender = headers.get("From", "")
            
        #     if user_email in sender:
        #         last_outgoing = m
        #     else:
        #         # incoming reply; pair with last outgoing message
        #         if last_outgoing:
        #             results.append({
        #                 "original": {
        #                     "from": headers.get("From"),
        #                     "subject": headers.get("Subject"),
        #                     "body": clean_message_body(last_outgoing)
        #                 },
        #                 "reply": {
        #                     "body": clean_message_body(m)
        #                 }
        #             })
        # seen_msg_ids = set()
        # for m in messages:
        #     if m['id'] in seen_msg_ids:
        #         continue
        #     seen_msg_ids.add(m['id'])

        #     headers = {h['name']: h['value'] for h in m['payload']['headers']}
        #     sender = headers.get("From", "")
            
        #     if user_email in sender:
        #         last_outgoing = m
        #     else:
        #         if last_outgoing:
        #             results.append({
        #                 "original": {
        #                     "from": headers.get("From"),
        #                     "subject": headers.get("Subject"),
        #                     "body": clean_message_body(last_outgoing)
        #                 },
        #                 "reply": {
        #                     "body": clean_message_body(m)
        #                 }
        #             })
        for m in messages:
            results.append(clean_message_body(m))


    for thread_id in sent_ids:
        batch.add(service.users().threads().get(userId="me", id=thread_id, format="full"), callback=callback)
    batch.execute()

    return results

# Assuming `service` is your Gmail API service object
# and `user_email` is your email address

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
    # fallback to top-level body
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

# def get_thread_pairs(service, user_email, thread_id):
#     thread = service.users().threads().get(userId='me', id=thread_id).execute()
#     messages = thread.get('messages', [])

#     seen_msg_ids = set()
#     results = []
#     last_outgoing = None

#     # Sort messages by internalDate to maintain chronological order
#     messages.sort(key=lambda m: int(m['internalDate']))

#     for m in messages:
#         msg_id = m['id']
#         if msg_id in seen_msg_ids:
#             continue
#         seen_msg_ids.add(msg_id)

#         headers = {h['name']: h['value'] for h in m['payload']['headers']}
#         sender = headers.get("From", "")

#         # Treat messages from self as outgoing
#         if user_email in sender:
#             last_outgoing = m
#         else:
#             # Message from someone else, pair with last outgoing
#             if last_outgoing:
#                 results.append({
#                     "original": {
#                         "from": sender,
#                         "subject": headers.get("Subject"),
#                         "body": extract_text_from_message(last_outgoing)
#                     },
#                     "reply": {
#                         "body": extract_text_from_message(m)
#                     }
#                 })
#     return results
