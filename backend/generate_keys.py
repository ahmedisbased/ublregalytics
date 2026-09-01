"""
Generate an RSA key pair for signing/verifying JWTs with RS256.

Why RS256 (asymmetric) instead of HS256 (symmetric)?
  - HS256 uses ONE shared secret for both signing and verifying. Anyone who can
    read that secret (e.g. it was committed to the repo, printed to a log, or
    shipped to a client) can forge valid tokens. That is exactly how the
    pentest team forged tokens in the report.
  - RS256 uses a PRIVATE key to sign and a PUBLIC key to verify. Only the auth
    service ever needs the private key; the public key can be shared freely and
    cannot be used to mint new tokens. Compromise of the verification key does
    not let an attacker forge tokens.

Usage:
    python generate_keys.py

This writes keys/jwt_private.pem and keys/jwt_public.pem.

IMPORTANT (production):
  - Generate a FRESH key pair on the production host. Do NOT reuse the dev keys
    that ship with this repo, and never commit private keys to source control.
  - Restrict file permissions on the private key (chmod 600 on Linux).
  - Point JWT_PRIVATE_KEY_PATH / JWT_PUBLIC_KEY_PATH (in .env) at the prod keys,
    or load them from a secrets vault.
"""
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

KEYS_DIR = Path(__file__).resolve().parent / "keys"
KEYS_DIR.mkdir(exist_ok=True)

PRIVATE_PATH = KEYS_DIR / "jwt_private.pem"
PUBLIC_PATH = KEYS_DIR / "jwt_public.pem"


def main() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    PRIVATE_PATH.write_bytes(private_pem)
    PUBLIC_PATH.write_bytes(public_pem)

    # Best-effort tighten permissions on the private key (POSIX only).
    try:
        PRIVATE_PATH.chmod(600)
    except (OSError, NotImplementedError):
        pass

    print(f"Wrote {PRIVATE_PATH}")
    print(f"Wrote {PUBLIC_PATH}")


if __name__ == "__main__":
    main()
