"""
Authentication routes: /login, /refresh, /logout.

/login is protected by:
  - A sliding-window request throttle (anti-automation), and
  - An account-style lockout after repeated FAILED logins.
Both are keyed by client IP + submitted username and return generic errors,
so the endpoint can no longer be used to brute-force or enumerate users.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services import (
    authenticate_and_authorize_user,
    get_current_user,
    logout as logout_service,
    refresh_access_token,
)
from app.schemas import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    LogoutRequest,
)
from app.core import rate_limit

router = APIRouter()
bearer = HTTPBearer(auto_error=True)


def _client_key(request: Request, username: str) -> str:
    client_ip = request.client.host if request.client else "unknown"
    return f"{client_ip}:{username.lower().strip()}"


@router.post("/login", response_model=LoginResponse)
def login(request: Request, body: LoginRequest):
    print(f"in login and the body is {body}")
    key = _client_key(request, body.username)

    # Lockout check (after too many failures).
    locked = rate_limit.is_locked(key)
    if locked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Try again later.",
            headers={"Retry-After": str(locked)},
        )

    # Sliding-window throttle (anti-automation).
    wait = rate_limit.throttle(key)
    if wait:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Try again later.",
            headers={"Retry-After": str(wait)},
        )

    try:
        result = authenticate_and_authorize_user(body.username, body.password)
    except HTTPException as exc:
        # Count only credential failures (401) towards lockout.
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            rate_limit.record_failure(key)
        raise

    rate_limit.clear(key)
    return result


@router.post("/refresh", response_model=RefreshResponse)
def refresh(body: RefreshRequest):
    return refresh_access_token(body.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    body: LogoutRequest,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
):
    logout_service(credentials.credentials, body.refresh_token)
    return None

@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    return {"sub": current_user["token_data"].get("sub")}