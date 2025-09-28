from fastapi import FastAPI, Request
from google.oauth2 import service_account
import hmac
import hashlib
import base64

app = FastAPI()

# If you want to verify Pub/Sub messages using a secret token
PUBSUB_VERIFICATION_TOKEN = "YOUR_SECRET"  # optional

@app.post("/gmail/push")
async def gmail_push(request: Request):
    envelope = await request.json()
    
    # Pub/Sub message is base64-encoded
    msg_data = envelope.get("message", {}).get("data")
    if msg_data:
        import base64
        data_decoded = base64.b64decode(msg_data).decode("utf-8")
        print("Received Gmail push:", data_decoded)
    
    # Acknowledge Pub/Sub
    return {"status": "OK"}
