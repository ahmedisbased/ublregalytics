"""
Authentication & authorization service.

Security fixes applied (see remediation document for full rationale):
  - JWT now uses RS256 (private-key sign / public-key verify) via app.core.security,
    instead of HS256 with a hardcoded, log-printed secret. Forged/altered tokens
    are rejected because the attacker does not hold the private key.
  - AUTHENTICATION happens BEFORE AUTHORIZATION, and every authentication failure
    returns an identical generic 401. This removes the username-enumeration
    oracle (previously: unknown user -> 403 "Not authorized", known user/bad
    password -> 401 "Invalid credentials").
  - Tokens are short-lived; logout/refresh and server-side revocation live in
    app.core.security.
  - All print() calls that leaked the secret key / tokens have been removed.
"""
import json
from pathlib import Path

import ldap3
from ldap3.core.exceptions import LDAPException
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core import security

security_scheme = HTTPBearer(auto_error=True)

BASE_DIR = Path(__file__).resolve().parent.parent
PERMISSIONS_FILE = BASE_DIR / "services" / "user_permissions.json"

# Identical credentials error for every auth failure (no enumeration oracle).
_INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid username or password",
    headers={"WWW-Authenticate": "Bearer"},
)

USER_PERMISSIONS: dict = {}
_LAST_MTIME = None


# ---------------------------------------------------------------------------
# Permission catalogue loading (unchanged behaviour, just tidied)
# ---------------------------------------------------------------------------
def _load_permissions() -> None:
    global USER_PERMISSIONS
    with open(PERMISSIONS_FILE, "r", encoding="utf-8") as f:
        USER_PERMISSIONS = json.load(f)


def ensure_permissions_loaded() -> None:
    global _LAST_MTIME
    try:
        mtime = PERMISSIONS_FILE.stat().st_mtime
    except FileNotFoundError as exc:
        raise RuntimeError("Permissions file not found") from exc
    if _LAST_MTIME is None or mtime != _LAST_MTIME:
        _load_permissions()
        _LAST_MTIME = mtime


def _normalize_username(user_name: str) -> str:
    """Strip a leading domain (e.g. 'pkubl\\918642' -> '918642')."""
    if "\\" in user_name:
        return user_name.split("\\")[-1]
    return user_name


def get_user_permissions(user_name: str):
    ensure_permissions_loaded()
    record = USER_PERMISSIONS.get(_normalize_username(user_name), {})
    values = list(record.values())
    return values[0] if values else []


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
def _ldap_login(username: str, password: str) -> bool:
    """Real authentication against the corporate LDAP/AD server."""
    try:
        with ldap3.Connection("10.1.107.51", user=username, password=password) as conn:
            return bool(conn.bound)
    except LDAPException:
        print(f"could not connect to ldap")
        return False


def _authenticate(employee_id: str, password: str) -> bool:
    """
    Verify the user's credentials.

    NOTE: The real implementation is the LDAP bind above. It is intentionally
    left commented out for now (per request) because this copy of the app runs
    off-network, away from the LDAP server. The simple if/else below is a
    TEMPORARY stand-in so the rest of the app can be exercised locally.

    >> RESTORE THIS BEFORE PRODUCTION <<<
    """
    return _ldap_login(employee_id, password)

    # --- TEMPORARY LOCAL BYPASS (replace with _ldap_login in production) ----
    # return employee_id == "pkubl\\918642" and password == "KeepTheFlagHigh_786"
    # ------------------------------------------------------------------------


def authenticate_and_authorize_user(employee_id: str, password: str) -> dict:
    """
    Step 1: AUTHENTICATE. On failure -> generic 401 (no info about why).
    Step 2: AUTHORIZE (permissions). Only reachable once authenticated, so a
            403 here can no longer be used to enumerate valid usernames.
    Step 3: Issue short-lived access + refresh tokens.
    """
    domain_id = f"pkubl\\{employee_id}"

    # Step 1 - authentication
    if not _authenticate(domain_id, password):
        print(f"could not auth the user")
        raise _INVALID_CREDENTIALS

    # Step 2 - authorization
    permissions = get_user_permissions(employee_id)
    if not permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    # Step 3 - tokens
    access_token = security.create_access_token(domain_id)
    refresh_token = security.create_refresh_token(domain_id)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "permissions": permissions,
    }


# ---------------------------------------------------------------------------
# Token handling for protected routes
# ---------------------------------------------------------------------------
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> dict:
    """FastAPI dependency: validate the bearer access token on every request."""
    try:
        payload = security.decode_token(credentials.credentials, expected_type="access")
    except security.TokenError:
        raise _INVALID_CREDENTIALS

    user_id = payload.get("sub")
    user = get_user(user_id)  # confirms the subject still exists / is permitted
    return {"user": user, "token_data": payload}


def get_user(user_name: str) -> str:
    ensure_permissions_loaded()
    normalized = _normalize_username(user_name or "")
    if not USER_PERMISSIONS.get(normalized):
        raise _INVALID_CREDENTIALS
    return normalized


def logout(access_token: str, refresh_token: str | None = None) -> None:
    """Revoke the presented tokens server-side (by jti)."""
    for token, ttype in ((access_token, "access"), (refresh_token, "refresh")):
        if not token:
            continue
        try:
            payload = security.decode_token(token, expected_type=ttype)
            security.revoke(payload.get("jti"))
        except security.TokenError:
            # Already invalid/expired -> nothing to revoke.
            pass


def refresh_access_token(refresh_token: str) -> dict:
    """Exchange a valid refresh token for a new access token."""
    try:
        payload = security.decode_token(refresh_token, expected_type="refresh")
    except security.TokenError:
        raise _INVALID_CREDENTIALS
    subject = payload.get("sub")
    get_user(subject)  # ensure the user is still valid/permitted
    return {"access_token": security.create_access_token(subject)}
