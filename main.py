from fastapi import FastAPI, Request, HTTPException, Depends, BackgroundTasks
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import requests
import jwt
from jwt import PyJWKClient
import time
from sqlalchemy.orm import Session
import secrets
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

import config
from utils.google_token import refresh_google_access_token, is_google_token_expired
from utils.google_messages import parse_message, create_threads, create_threads_preserve_breaks
from utils import database_models as models
from utils.database import engine, get_db
from utils.cacheProvider import get_hash_key, set_hash_key, set_set_key
from utils.repliq_token import get_current_user, create_custom_token
from utils.google_api import fetch_threads_in_batches, fetch_my_replies, save_draft
from utils.llmapi import get_writing_style
from utils.googlePubSub import create_watch_request, verify_incoming_request, decode_push_notification_data, handle_pubsub_notification

models.Base.metadata.create_all(bind = engine)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

GOOGLE_AUTH_URL = config.GOOGLE_AUTH_URL
GOOGLE_TOKEN_URL = config.GOOGLE_TOKEN_URL 
GOOGLE_USERINFO_URL = config.GOOGLE_USERINFO_URL
GOOGLE_JWKS_URL = config.GOOGLE_JWKS_URL

GOOGLE_CLIENT_ID = config.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = config.GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_URI = config.GOOGLE_REDIRECT_URI

GOOGLE_ACCESS_TOKEN_EXPIRE_SECONDS = config.GOOGLE_ACCESS_TOKEN_EXPIRE_SECONDS

SCOPE = config.SCOPE
SECRET_KEY = config.SECRET_KEY
ALGORITHM = config.ALGORITHM

results = []

@app.get("/", response_class=HTMLResponse)
def root(request: Request, db: Session = Depends(get_db)):
    repliq_token = request.cookies.get("repliq_token")
    if repliq_token:
        email = get_current_user(repliq_token).sub
        user = db.query(models.user).filter(models.user.email == email).first()
        if repliq_token and email and user:
            return RedirectResponse("/dashboard")

    state = secrets.token_urlsafe(16)
    login_url = (
        f"{GOOGLE_AUTH_URL}?response_type=code&state={state}&client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        f"&scope={SCOPE}&access_type=offline&prompt=consent"
    )

    response = templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "login_url": login_url
        }
    )
    response.set_cookie(
        key="oauth_state",
        value=state)
    return response

@app.get("/auth/google")
async def auth_google(request: Request, state:str, code: str, db: Session = Depends(get_db)):
    cookie_state = request.cookies.get("oauth_state")
    if not cookie_state or cookie_state != state:
        raise HTTPException(status_code=400, detail="Invalid or missing state")
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    token_response = requests.post(GOOGLE_TOKEN_URL, data=data).json()

    token_fetched_at = int(time.time())
    id_token = token_response.get("id_token")
    access_token = token_response.get("access_token")
    refresh_token = token_response.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=400,
            detail="No refresh token received. User must re-consent."
        )

    if not id_token:
        raise HTTPException(status_code=400, detail="No ID token returned")

    jwks_client = PyJWKClient(GOOGLE_JWKS_URL)
    signing_key = jwks_client.get_signing_key_from_jwt(id_token)

    claims = jwt.decode(
        id_token,
        signing_key.key,
        algorithms=["RS256"],
        audience=GOOGLE_CLIENT_ID,
    )


    userinfo = requests.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()
    
    user_obj_query = db.query(models.user).filter(models.user.email == userinfo.get("email"))
    user_obj = user_obj_query.first()
    email = userinfo.get("email")
    name = userinfo.get("name")
    if not user_obj:
        new_user = models.user(
            email = email,
            name = name,
            google_refresh_token = refresh_token,
            token_issued_at = token_fetched_at
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    else:
        user_dict = {"email": email,
                     "name": name,
                     "google_refresh_token": refresh_token}
        user_obj_query.update(user_dict, synchronize_session = False)

    hashKey = "repliq:google:access_token"
    cacheKey = email
    set_hash_key(hashKey, cacheKey, access_token)

    hashKey = "repliq:google:access_token:fetched_at"
    cacheKey = email
    set_hash_key(hashKey, cacheKey, token_fetched_at)

    repliq_token = create_custom_token(email)

    response = RedirectResponse("/dashboard")  # redirect to your dashboard
    response.set_cookie(
        key="repliq_token",
        value=repliq_token,
        max_age=60*60*24*7,  # 7 days
    )
    response.delete_cookie("oauth_state")

    return response

@app.get("/dashboard")
async def dashboard(request: Request, db: Session = Depends(get_db)):
    repliq_token = request.cookies.get("repliq_token")
    if not repliq_token:
        return RedirectResponse("/")
    user = get_current_user(repliq_token)
    email = user.sub

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "email": email,
            "get_email_url": f"http://localhost:8000/gmail/messages/batch"
        }
    )

@app.get("/gmail/messages")
async def get_messages(request: Request, db: Session = Depends(get_db), max_results: int = 10):
    repliq_token = request.cookies.get("repliq_token")
    if not repliq_token:
        return RedirectResponse("/")
    user = get_current_user(repliq_token)
    email = user.sub
    hashKey = "repliq:google:access_token"
    cacheKey = email
    access_code = get_hash_key(hashKey, cacheKey)
    if is_google_token_expired(email):
        access_code = refresh_google_access_token(email, db)
        if not access_code:
            return {"message": "An error occuered while trying to refresh token"}

    headers = {"Authorization": f"Bearer {access_code}"}
    
    list_resp = requests.get(
        f"https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults={max_results}",
        headers=headers
    )
    
    if list_resp.status_code != 200:
        raise HTTPException(status_code=list_resp.status_code, detail=list_resp.json())
    
    list_data = list_resp.json()
    messages = []

    for msg in list_data.get("messages", []):
        msg_id = msg["id"]
        msg_resp = requests.get(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}?format=full",
            headers=headers
        )
        if msg_resp.status_code == 200:
            messages.append(parse_message(msg_resp.json()))

    return {"messages": messages}

@app.get("/gmail/messages/batch")
async def get_messages(request: Request, db: Session = Depends(get_db), max_results: int = 10):
    print("inside batch")
    repliq_token = request.cookies.get("repliq_token")
    if not repliq_token:
        return RedirectResponse("/")
    
    user = get_current_user(repliq_token)
    email = user.sub

    user = db.query(models.user).filter(models.user.email == email).first()
    refresh_token = user.google_refresh_token

    hashKey = "repliq:google:access_token"
    cacheKey = email
    access_code = get_hash_key(hashKey, cacheKey)

    if is_google_token_expired(email):
        access_code = refresh_google_access_token(email, refresh_token, db)
        if not access_code:
            return {"message": "An error occuered while trying to refresh token"}
    
    style = db.query(models.writing_style).filter(models.writing_style.user_id == user.id).first()

    if not style:
        creds = Credentials.from_authorized_user_info(
            {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "token": access_code,
                "token_uri": "https://oauth2.googleapis.com/token",
                "scopes": ["https://www.googleapis.com/auth/gmail.readonly"]
            }
        )
        print("creds fetched. making batch call")

        service = build("gmail", "v1", credentials=creds)

        result = fetch_my_replies(service, email)
        final_res = create_threads_preserve_breaks(result,email)

        writing_style = get_writing_style(final_res)
        style = models.writing_style(
            user_id = user.id,
            style = writing_style,
        )
        db.add(style)
        db.commit()
        db.refresh(style)

    print(type("writing_style"))
    print(style)
    create_watch_request(access_code, refresh_token, email)


@app.post("/push")
async def push(request: Request,  background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=403, detail="Missing or invalid Authorization header")

    token = auth_header.split(" ")[1]
    verify_incoming_request(token)

    body = await request.json()
    print("📩 Pub/Sub notification received:", body)
    result = decode_push_notification_data(body)
    print(result)
    background_tasks.add_task(save_draft, db, result)

    return {"status": "ok"}

def handle_response(request_id, response, exception):
    if exception is None:
        results.append(response)