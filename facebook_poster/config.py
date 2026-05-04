import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

FB_APP_ID = os.environ.get("FB_APP_ID")
FB_APP_SECRET = os.environ.get("FB_APP_SECRET")
REDIRECT_URI = os.environ.get("FB_REDIRECT_URI", "http://localhost:8101/callback")

# Permanent Long-Lived User Access Token
FB_USER_ACCESS_TOKEN = os.environ.get("FB_USER_ACCESS_TOKEN")
