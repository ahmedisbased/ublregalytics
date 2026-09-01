"""
Centralised application configuration.

Everything that is environment-specific or secret is read from environment
variables / the .env file here, in ONE place, instead of being hardcoded and
scattered across the codebase. Hardcoded secrets (the old SECRET_KEY in source,
the Teradata password in fetch_data) were a major part of the findings; this
module is where they should now come from instead.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# backend/app/core/config.py -> backend/app
APP_DIR = Path(__file__).resolve().parent.parent
# backend/
BACKEND_DIR = APP_DIR.parent

# Load .env (kept OUTSIDE source control) once, at import time.
load_dotenv(APP_DIR / ".env")


def _get(name: str, default: str | None = None, *, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and (value is None or value == ""):
        raise RuntimeError(
            f"Required environment variable '{name}' is not set. "
            f"Copy .env.example to .env and fill it in."
        )
    return value if value is not None else ""


# --- JWT / signing ----------------------------------------------------------
# RS256: sign with the private key, verify with the public key.
JWT_ALGORITHM = "RS256"
JWT_PRIVATE_KEY_PATH = _get("JWT_PRIVATE_KEY_PATH", str(BACKEND_DIR / "keys" / "jwt_private.pem"))
JWT_PUBLIC_KEY_PATH = _get("JWT_PUBLIC_KEY_PATH", str(BACKEND_DIR / "keys" / "jwt_public.pem"))

# Issuer / audience are validated on every token so a token minted for some
# other service (or a stale token) can't be replayed here.
JWT_ISSUER = _get("JWT_ISSUER", "regalytics-auth")
JWT_AUDIENCE = _get("JWT_AUDIENCE", "regalytics-api")

# Short-lived access token + longer refresh token (see security.py).
ACCESS_TOKEN_EXPIRE_MINUTES = int(_get("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_MINUTES = int(_get("REFRESH_TOKEN_EXPIRE_MINUTES", "720"))  # 12h

# --- CORS -------------------------------------------------------------------
# Comma-separated allow-list. NEVER use "*" together with credentials.
_origins = _get(
    "CORS_ALLOW_ORIGINS",
    "http://127.0.0.1:8080,http://127.0.0.1:8081,http://127.0.0.1:8082,http://localhost:8080,http://localhost:8081,http://localhost:8082",
)
CORS_ALLOW_ORIGINS = [o.strip() for o in _origins.split(",") if o.strip()]


# --- Rate limiting / lockout ------------------------------------------------
LOGIN_RATE_MAX_ATTEMPTS = int(_get("LOGIN_RATE_MAX_ATTEMPTS", "100"))
LOGIN_RATE_WINDOW_SECONDS = int(_get("LOGIN_RATE_WINDOW_SECONDS", "60"))
LOGIN_LOCKOUT_SECONDS = int(_get("LOGIN_LOCKOUT_SECONDS", "900"))  # 15 min

# --- Teradata (used by the XML generation service) --------------------------
TERADATA_HOST = _get("TERADATA_HOST", "")
TERADATA_USER = _get("TERADATA_USER", "")
TERADATA_PASSWORD = _get("TERADATA_PASSWORD", "")
TERADATA_DATABASE = _get("TERADATA_DATABASE", "")
TERADATA_LOGMECH = _get("TERADATA_LOGMECH", "TD2")

# --- Misc -------------------------------------------------------------------
# Toggle HSTS only when the app is actually served over HTTPS at the edge.
ENABLE_HSTS = _get("ENABLE_HSTS", "true").lower() == "true"

#-------Teradata (used in RCOA)
TD_HOST = _get("TD_HOST", "")
TD_USER = _get("TD_USER", "")
TD_PASSWORD = _get("TD_PASSWORD", "")
TD_DATABASE = _get("TD_DATABASE", "")
TD_LOGMECH = _get("TD_LOGMECH", "TD2")
TD_POOL_SIZE = int(_get("TD_POOL_SIZE", "3"))
TD_POOL_TIMEOUT_SECONDS = int(_get("TD_POOL_TIMEOUT_SECONDS", "30"))
TD_POOL_RECYCLE_SECONDS = int(_get("TD_POOL_RECYCLE_SECONDS", "1800"))
