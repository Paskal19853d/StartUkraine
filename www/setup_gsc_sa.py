#!/usr/bin/env python3
"""
Одноразовий скрипт: додає service account як verified owner у Google Search Console.
Запустити один раз: python3 setup_gsc_sa.py
Не потребує pip install requests — тільки google-auth (вже встановлено).
"""
import json, os, sys, time, urllib.request, urllib.error, urllib.parse
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

KEY_FILE = os.getenv("GOOGLE_INDEXING_KEY_FILE", "google-service-account.json")
SITE_URL = os.getenv("SITE_BASE_URL", "https://xn----7sbbz2acglf0a4i2ag.xn--j1amh").rstrip("/") + "/"

print(f"Key file : {KEY_FILE}")
print(f"Site URL : {SITE_URL}")
print()

if not os.path.exists(KEY_FILE):
    sys.exit(f"ERROR: файл {KEY_FILE} не знайдено")

try:
    import google.auth.crypt
    import google.auth.jwt
except ImportError as e:
    sys.exit(f"ERROR: {e}\nRun: pip install google-auth")

# Завантажити ключ
with open(KEY_FILE) as f:
    sa = json.load(f)

sa_email = sa["client_email"]
print(f"Service account: {sa_email}")

# Отримати access token через JWT (без requests)
def get_access_token(scope):
    now = int(time.time())
    payload = {
        "iss": sa_email,
        "sub": sa_email,
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now,
        "exp": now + 3600,
        "scope": scope,
    }
    signer = google.auth.crypt.RSASigner.from_service_account_info(sa)
    jwt_token = google.auth.jwt.encode(signer, payload)
    if isinstance(jwt_token, bytes):
        jwt_token = jwt_token.decode()

    body = urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": jwt_token,
    }).encode()
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST"
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())["access_token"]

print("[0] Отримання access token...")
bearer = get_access_token("https://www.googleapis.com/auth/siteverification")
print("    OK")
print()

def api_post(url, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Authorization": f"Bearer {bearer}", "Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        sys.exit(f"HTTP {e.code}: {err}")

# Крок 1: Отримати токен верифікації
print("[1] Запит токену верифікації...")
r1 = api_post(
    "https://www.googleapis.com/siteVerification/v1/token",
    {"site": {"type": "SITE", "identifier": SITE_URL}, "verificationMethod": "FILE"}
)
vfile = r1["token"]
print(f"    Файл: {vfile}")
print()

# Крок 2: Створити файл (FastAPI вже має роут для google*.html)
Path(vfile).write_text(f"google-site-verification: {vfile}")
print(f"[2] Файл створено: {vfile}")
print()

# Крок 3: Підтвердити верифікацію через API
print("[3] Підтвердження верифікації...")
r2 = api_post(
    "https://www.googleapis.com/siteVerification/v1/webResource?verificationMethod=FILE",
    {"site": {"type": "SITE", "identifier": SITE_URL}, "verificationMethod": "FILE"}
)
owners = r2.get("owners", [])
print(f"    Власники: {owners}")
print()
print("=" * 55)
print("ГОТОВО! Service account тепер є verified owner.")
print("Поверніться в адмінку і натисніть 'Надіслати URL до Google'.")
print("=" * 55)

# Крок 4: Видалити тимчасовий файл
try:
    Path(vfile).unlink()
    print(f"\nТимчасовий файл {vfile} видалено.")
except Exception:
    pass
