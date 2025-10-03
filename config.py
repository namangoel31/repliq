#CONSTANTS
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v1/certs"
SCOPE = "openid email profile https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.compose"
GOOGLE_ACCESS_TOKEN_EXPIRE_SECONDS = 3599
REPLIQ_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
ALGORITHM = "HS256"

#VARIABLES
GOOGLE_CLIENT_ID = ""
GOOGLE_CLIENT_SECRET = ""

GOOGLE_REDIRECT_URI = "http://localhost:8000/auth/google"

APP_NAME = 'repliq'

GEMINI_API_KEY = ""

VERIFICATION_TOKEN = "some_verification_token"

SECRET_KEY = "supersecretkey"

SQL_ALCHEMY_DATABASE_URL = ""
SQL_ALCHEMY_MONGO_URL = ""

CACHE_SERVER_ENDPOINT = ""
CACHE_SERVER_PORT = ""
CACHE_SERVER_PASSWORD = ""

APP_DOMAIN = "https://ngrok-free.dev"

PUBSUB_TOPIC_NAME = "/topics/gmail-notifications"

DRAIN_NOTIFICATIONS = False

GMAIL_WATCH_VERIFICATION_TOKEN = "my-secret-token-123"

