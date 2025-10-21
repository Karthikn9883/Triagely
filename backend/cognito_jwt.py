# app/core/cognito_jwt.py

"""
Utilities for verifying AWS Cognito JSON Web Tokens (JWTs).

Fetches the JSON Web Key Set (JWKS) from Cognito once and caches it in memory,
extracts the appropriate public key by `kid`, and uses `python-jose` to decode
and verify JWT signatures, audience, and issuer claims.
"""
import os
import requests
from jose import jwt, JWTError

# Environment-driven configuration for Cognito
AWS_REGION        = os.getenv("AWS_REGION")
USER_POOL_ID      = os.getenv("COG_USER_POOL_ID")
COGNITO_CLIENT_ID = os.getenv("COG_APP_CLIENT_ID")

# Construct the issuer URL based on region and user pool
COGNITO_ISSUER = f"https://cognito-idp.{AWS_REGION}.amazonaws.com/{USER_POOL_ID}"
# URL where Cognito publishes its JWKS (public keys)
JWKS_URL       = f"{COGNITO_ISSUER}/.well-known/jwks.json"

# In-memory cache for JWKS keys to avoid refetching on every verification
_jwks: list[dict] | None = None


def get_jwks() -> list[dict]:  # noqa: C901
    """
    Retrieve the JWKS from Cognito, caching the result on first call.

    Returns:
      A list of JWK dicts, each containing a `kid` and key material.
    """
    global _jwks
    if _jwks is None:
        # HTTP GET to fetch the JWKS JSON payload
        resp = requests.get(JWKS_URL, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        # Extract the `keys` list
        _jwks = data.get("keys", [])
    return _jwks


def get_public_key(kid: str) -> dict | None:
    """
    Given a key ID (`kid`), find the corresponding JWK in the JWKS.

    Args:
      kid: The key ID from the JWT header to match.

    Returns:
      The JWK dict if found, else None.
    """
    for key in get_jwks():
        if key.get("kid") == kid:
            return key
    return None


def verify_cognito_jwt(token: str) -> dict:
    """
    Verify and decode a Cognito JWT using the matching public key.

    Steps:
      1. Extract the unverified JWT header to read the `kid`.
      2. Lookup the corresponding public key via `get_public_key`.
      3. Use `jose.jwt.decode` to verify signature, `audience`, and `issuer`.

    Args:
      token: The raw JWT string to validate.

    Returns:
      The decoded JWT claims as a dict on successful verification.

    Raises:
      Exception on any retrieval or verification error (with details).
    """
    try:
        # 1️⃣ Get unverified header to read the `kid`
        headers = jwt.get_unverified_header(token)
        kid     = headers.get("kid")

        # 2️⃣ Retrieve the matching public key from JWKS
        key = get_public_key(kid)
        if key is None:
            raise Exception(f"Public key for kid '{kid}' not found in JWKS")

        # 3️⃣ Verify token signature and standard claims
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=COGNITO_CLIENT_ID,
            issuer=COGNITO_ISSUER,
        )

        return payload

    except JWTError as jwt_err:
        # JWT-specific verification failure
        raise Exception(f"JWT validation error: {jwt_err}")
    except requests.RequestException as req_err:
        # Network or HTTP error when fetching JWKS
        raise Exception(f"Failed to fetch JWKS: {req_err}")
    except Exception as err:
        # Fallback for any other error
        raise Exception(f"JWT verification failed: {err}")
