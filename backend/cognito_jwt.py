import os
import requests
from jose import jwt, JWTError

AWS_REGION = os.getenv("AWS_REGION")
USER_POOL_ID = os.getenv("COG_USER_POOL_ID")
COGNITO_CLIENT_ID = os.getenv("COG_APP_CLIENT_ID")

COGNITO_ISSUER = f"https://cognito-idp.{AWS_REGION}.amazonaws.com/{USER_POOL_ID}"
JWKS_URL = f"{COGNITO_ISSUER}/.well-known/jwks.json"

_jwks = None  # cache keys

def get_jwks():
    global _jwks
    if not _jwks:
        _jwks = requests.get(JWKS_URL).json()["keys"]
    return _jwks

def get_public_key(kid):
    jwks = get_jwks()
    for key in jwks:
        if key["kid"] == kid:
            return key
    return None

def verify_cognito_jwt(token):
    try:
        headers = jwt.get_unverified_header(token)
        key = get_public_key(headers["kid"])
        if key is None:
            raise Exception("Public key not found in Cognito JWKS")

        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=COGNITO_CLIENT_ID,  # For ID tokens
            issuer=COGNITO_ISSUER
        )
        return payload
    except JWTError as e:
        raise Exception(f"Token validation error: {str(e)}")
    except Exception as e:
        raise Exception(f"JWT verification failed: {str(e)}")
