"""
JWT security core.

Responsibilities:
  - Create access & refresh tokens signed with the RS256 PRIVATE key.
  - Verify tokens with the RS256 PUBLIC key, with the algorithm pinned to
    ["RS256"] so an attacker cannot downgrade to "none" or pull off an
    HS256/RS256 confusion attack.
  - Enforce standard registered claims (exp, nbf, iat, iss, aud) on verify.
  - Maintain a revocation list of token IDs (jti) so logout actually
    invalidates a token server-side.

NOTE ON THE REVOCATION STORE:
    The blacklist below is an in-memory set. That is correct and sufficient for
    a single-process deployment, but it is wiped on restart and is NOT shared
    across multiple workers/instances. In production back it with Redis (or a
    small DB table) keyed by jti with a TTL equal to the token's remaining
    lifetime. The interface (revoke / is_revoked) stays the same.
"""
import uuid
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

import jwt

from app.core import config


# --- key loading ------------------------------------------------------------
@lru_cache(maxsize=1)
def _private_key() -> str:
    path = Path(config.JWT_PRIVATE_KEY_PATH)
    if not path.exists():
        raise RuntimeError(
            f"JWT private key not found at {path}. Run `python generate_keys.py`."
        )
    return path.read_text()


@lru_cache(maxsize=1)
def _public_key() -> str:
    path = Path(config.JWT_PUBLIC_KEY_PATH)
    if not path.exists():
        raise RuntimeError(
            f"JWT public key not found at {path}. Run `python generate_keys.py`."
        )
    return path.read_text()


# --- revocation store -------------------------------------------------------
_REVOKED_JTIS: set[str] = set()


def revoke(jti: str) -> None:
    if jti:
        _REVOKED_JTIS.add(jti)


def is_revoked(jti: str | None) -> bool:
    return jti is None or jti in _REVOKED_JTIS


# --- token creation ---------------------------------------------------------
def _create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,           # "access" or "refresh"
        "iss": config.JWT_ISSUER,
        "aud": config.JWT_AUDIENCE,
        "iat": now,
        "nbf": now,
        "exp": now + expires_delta,
        "jti": uuid.uuid4().hex,      # unique id, enables targeted revocation
    }
    return jwt.encode(payload, _private_key(), algorithm=config.JWT_ALGORITHM)


def create_access_token(subject: str) -> str:
    return _create_token(
        subject, "access", timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    )


def create_refresh_token(subject: str) -> str:
    return _create_token(
        subject, "refresh", timedelta(minutes=config.REFRESH_TOKEN_EXPIRE_MINUTES)
    )


# --- token verification -----------------------------------------------------
class TokenError(Exception):
    """Raised when a token is missing, malformed, expired, revoked, or wrong type."""


def decode_token(token: str, *, expected_type: str) -> dict:
    """
    Verify signature + registered claims and return the payload.

    Raises TokenError on ANY problem. Callers translate that into a generic
    401 so we never leak *why* a token was rejected.
    """
    try:
        payload = jwt.decode(
            token,
            _public_key(),
            algorithms=[config.JWT_ALGORITHM],   # pinned: no "none", no HS256
            audience=config.JWT_AUDIENCE,
            issuer=config.JWT_ISSUER,
            options={"require": ["exp", "iat", "nbf", "sub", "jti"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc

    if payload.get("type") != expected_type:
        raise TokenError("unexpected token type")

    if is_revoked(payload.get("jti")):
        raise TokenError("token revoked")

    return payload
