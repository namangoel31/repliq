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
from google.genai.errors import ServerError

import config
from utils.google_token import refresh_google_access_token, is_google_token_expired
from utils.google_messages import parse_message, create_threads, create_threads_preserve_breaks
from utils import database_models as models
from utils.database import engine, get_db
from utils.cacheProvider import get_hash_key, set_hash_key, set_set_key
from utils.repliq_token import get_current_user, create_custom_token
from utils.google_api import fetch_threads_in_batches, fetch_my_replies, save_draft
from utils.llmapi import get_writing_style
from utils.googlePubSub import create_watch_request, verify_incoming_request, decode_push_notification_data, handle_pubsub_notification, stop_watch_request
from utils.logger import get_console_logger, get_file_logger

models.Base.metadata.create_all(bind = engine)

app_name = config.APP_NAME

app = FastAPI()
templates = Jinja2Templates(directory="templates")
logger = get_file_logger(app_name)

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
    path = "/"
    repliq_token = request.cookies.get("repliq_token")
    if repliq_token:
        email = get_current_user(repliq_token).sub
        user = get_create_or_update_user_obj(db, email, action = 'get')
        if repliq_token and email and user:
            logger.info("Valid Repliq token present in request. Redirecting to dashboard.", extra={"path": path})
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
    path = "/auth/google"
    cookie_state = request.cookies.get("oauth_state")
    if not cookie_state or cookie_state != state:
        logger.exception("Exception occured: %s", str(HTTPException(status_code=400, detail="Invalid or missing state")), extra={"path": path})
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
        logger.exception("Exception occured: %s", str(HTTPException(status_code=400, detail="No refresh token received. User must re-consent.")), extra={"path": path})
        raise HTTPException(
            status_code=400,
            detail="No refresh token received. User must re-consent."
        )

    if not id_token:
        logger.exception("Exception occured: %s", str(HTTPException(status_code=400, detail="No ID token returned")), extra={"path": path})
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
    
    email = userinfo.get("email")
    name = userinfo.get("name")
    user = get_create_or_update_user_obj(db, email, name = name, refresh_token = refresh_token, token_fetched_at = token_fetched_at)

    hashKey = "repliq:google:access_token"
    cacheKey = email
    set_hash_key(hashKey, cacheKey, access_token)

    hashKey = "repliq:google:access_token:fetched_at"
    set_hash_key(hashKey, cacheKey, token_fetched_at)

    repliq_token = create_custom_token(email)

    response = RedirectResponse("/dashboard")
    response.set_cookie(
        key="repliq_token",
        value=repliq_token,
        max_age=60*60*24*7,
    )
    response.delete_cookie("oauth_state")
    logger.info("Login with Google successful.", extra={"path": path})
    return response

@app.get("/dashboard")
async def dashboard(request: Request, db: Session = Depends(get_db)):
    path = "/dashboard"
    repliq_token = request.cookies.get("repliq_token")
    if not repliq_token:
        logger.info("Token not found in request. Redirecting to login page.", extra={"path": path})
        return RedirectResponse("/")

    user = get_current_user(repliq_token)
    email = user.sub
    user_obj = get_create_or_update_user_obj(db, email, action = 'get')

    if not refresh_google_access_token(email, user_obj.google_refresh_token, db):
        logger.info("Unable to fetch refresh token. User must revalidate.", extra={"path": path})
        response = RedirectResponse("/")
        response.delete_cookie("repliq_token")
        return response

    style = get_create_or_update_writing_style(db, email, action = 'get')

    watch_status = user_obj.watch_status
    if not style:
        style = "Not Found"

    if not watch_status:
        watch_status = "Disabled"
    else:
        watch_status = "Enabled: Sit back and let Repliq do it's magic."

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "email": email,
            "writing_style": style,
            "watch_status": watch_status,
            "get_writing_style_url": f"http://localhost:8000/gmail/generate_writing_style",
            "get_watch_status_url": f"http://localhost:8000/gmail/toggle_watch",
            "logout_url": f"http://localhost:8000/gmail/logout"
        }
    )


@app.get("/gmail/generate_writing_style")
async def get_messages(request: Request, db: Session = Depends(get_db), max_results: int = 10):
    path = "/gmail/generate_writing_style"
    logger.info("Generating writing style for user.", extra={"path": path})
    repliq_token = request.cookies.get("repliq_token")
    if not repliq_token:
        logger.info("Token not found in request. Redirecting to login page.", extra={"path": path})
        return RedirectResponse("/")
    
    user = get_current_user(repliq_token)
    email = user.sub

    user = get_create_or_update_user_obj(db, email, action = 'get')
    refresh_token = user.google_refresh_token

    hashKey = "repliq:google:access_token"
    cacheKey = email
    access_code = get_hash_key(hashKey, cacheKey)

    if is_google_token_expired(email):
        access_code = refresh_google_access_token(email, refresh_token, db)
        if not access_code:
            logger.error("An error occuered while trying to refresh token", extra={"path": path})
            return {"message": "An error occuered while trying to refresh token"}
    
    style = get_create_or_update_writing_style(db, email, action = 'get')

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
    logger.info("Fetched user creds. Making bacth call for sent emails.", extra={"path": path})

    service = build("gmail", "v1", credentials=creds)

    result = fetch_my_replies(service, email)
    final_res = create_threads_preserve_breaks(result,email)
    writing_style = get_writing_style(final_res)
    get_create_or_update_writing_style(db, email, writing_style = writing_style)

    return RedirectResponse("/dashboard")

@app.get("/gmail/toggle_watch")
def toggle_watch(request: Request, db: Session = Depends(get_db)):
    path = "/gmail/toggle_watch"
    repliq_token = request.cookies.get("repliq_token")
    if not repliq_token:
        logger.info("Repliq token not found in request. Redirecting to login page.", extra={"path": path})
        return RedirectResponse("/")
    
    user = get_current_user(repliq_token)
    email = user.sub

    user = get_create_or_update_user_obj(db, email, action = 'get')
    refresh_token = user.google_refresh_token

    hashKey = "repliq:google:access_token"
    cacheKey = email
    access_code = get_hash_key(hashKey, cacheKey)

    if is_google_token_expired(email):
        access_code = refresh_google_access_token(email, refresh_token, db)
        if not access_code:
            logger.error("An error occuered while trying to refresh token", extra={"path": path})
            return {"message": "An error occuered while trying to refresh token"}
    if not user.watch_status:
        create_watch_request(access_code, refresh_token, email, db)
    else:
        stop_watch_request(access_code, refresh_token, email, db)

    return RedirectResponse("/dashboard")


@app.post("/push")
async def push(request: Request,  background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    path = "/push"
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=403, detail="Missing or invalid Authorization header")

    token = auth_header.split(" ")[1]
    verify_incoming_request(token)

    body = await request.json()
    if config.DRAIN_NOTIFICATIONS:
        logger.info("Discarding incoming notification!", extra={"path": path})
    result = decode_push_notification_data(body)
    logger.info("Decoded push notification: %s", result, extra={"path": path})
    background_tasks.add_task(save_draft, db, result)

    return {"status": "ok"}

@app.get("/gmail/logout")
def logout_and_revoke_token(request: Request, db: Session = Depends(get_db)):
    path = "/gmail/logout"
    repliq_token = request.cookies.get("repliq_token")
    if not repliq_token:
        logger.info("Repliq token not found. Redirecting to dashboard", extra={"path": path})
        return RedirectResponse("/")
    
    user = get_current_user(repliq_token)
    email = user.sub

    user = get_create_or_update_user_obj(db, email, action = 'get')
    refresh_token = user.google_refresh_token

    hashKey = "repliq:google:access_token"
    cacheKey = email
    access_code = get_hash_key(hashKey, cacheKey)

    if is_google_token_expired(email):
        access_code = refresh_google_access_token(email, refresh_token, db)
        if not access_code:
            response = RedirectResponse("/dashboard")
            return response
    if not user.watch_status:
        pass
    else:
        stop_watch_request(access_code, refresh_token, email, db)

    try:
        response = requests.post(
            "https://oauth2.googleapis.com/revoke",
            params={"token": refresh_token},
            headers={"content-type": "application/x-www-form-urlencoded"}
        )
        if response.status_code == 200:
            logger.info("User's token revoked successfully.", extra={"path": path})
            response = RedirectResponse("/")
            response.delete_cookie("repliq_token")
            return response
        else:
            logger.info("User's token revoke unsuccessful.", extra={"path": path})
            response = RedirectResponse("/dashboard")
            return response
    except Exception as e:
        logger.exception("Exception occured while trying to revoke Gamil access token: %s", str(e), extra={"path": path})
        response = RedirectResponse("/dashboard")
        return response

def handle_response(request_id, response, exception):
    if exception is None:
        results.append(response)

def get_create_or_update_user_obj(db: Session, email: str, **kwargs):
    method_name = 'get_create_or_update_user_obj'
    logger.info("processing begins.", extra = {"path": method_name})
    user_obj_query = db.query(models.user).filter(models.user.email == email)
    user_obj = user_obj_query.first()
    if kwargs.get('action')=='get':
        logger.info("processing ends. User found.", extra = {"path": method_name})
        return user_obj
    name = kwargs.get("name")
    refresh_token = kwargs.get("refresh_token")
    if not user_obj:
        new_user = models.user(
            email = email,
            name = name,
            google_refresh_token = refresh_token,
            token_issued_at = kwargs.get('token_fetched_at')
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        logger.info("processing ends. User not found. Creating a new user", extra = {"path": method_name})
        return new_user
    else:
        user_dict = {"email": email,
                     "name": name,
                     "google_refresh_token": refresh_token}
        user_obj_query.update(user_dict, synchronize_session = False)
        db.commit()
        logger.info("updating and returning user with latest details", extra = {"path": method_name})
        return get_create_or_update_user_obj(db, email, action = 'get')

def get_create_or_update_writing_style(db: Session, email: str, **kwargs):
    method_name = 'get_create_or_update_writing_style'
    logger.info("updating and returning latest writing style", extra = {"path": method_name})

    user_obj = get_create_or_update_user_obj(db, email, action = 'get')
    writing_style_obj_query = db.query(models.writing_style).filter(models.writing_style.user_id == user_obj.id)
    writing_style_obj = writing_style_obj_query.first()
    if not writing_style_obj and kwargs.get('action') == 'get':
        logger.info("Writing style not generated for user", extra = {"path": method_name})
        return
    elif writing_style_obj and kwargs.get('action') == 'get':
        logger.info("Found user's writing style", extra = {"path": method_name})
        return writing_style_obj.style
    try:
        new_style = kwargs.get("writing_style")
        if not writing_style_obj:
            writing_style = get_writing_style(new_style)
            style = models.writing_style(
                user_id = user_obj.id,
                style = writing_style,
            )
            db.add(style)
            db.commit()
            db.refresh(style)
            logger.info("Writing style generated.", extra={"path": method_name})
            return style
        else:
            style_dict = {"user_id": user_obj.id,
                        "style": new_style}
            writing_style_obj_query.update(style_dict, synchronize_session = False)
            db.commit()
            logger.info("updating and returning latest writing style", extra = {"path": method_name})
            return get_create_or_update_writing_style(db, email, action = 'get')

    except ServerError as ex:
        logger.exception("Exception occured: %s", str(ex), extra={"path": method_name})

def get_google_access_code(db: Session, email: str):
    ...