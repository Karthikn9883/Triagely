# app/core/secrets.py

"""
Helper for fetching and caching secrets from AWS Secrets Manager.

Provides a simple in-memory TTL cache to avoid repeated network calls
and JSON-parses the secret payload for downstream use (e.g. OAuth client IDs).
"""
import os
import json
import time
import boto3

# AWS region where Secrets Manager resides (from environment)
REGION = os.getenv("AWS_REGION")

# Initialize a Boto3 client for Secrets Manager
sm = boto3.client("secretsmanager", region_name=REGION)

# In-memory cache mapping secret name -> (parsed_secret_dict, timestamp)
_cache: dict[str, tuple[dict, float]] = {}
# Cache entries are valid for 15 minutes
TTL = 60 * 15  # seconds


def get(name: str) -> dict:
    """
    Retrieve a secret by name, using a local TTL cache.

    If the secret is cached and the cache is still fresh (<TTL), returns
    the cached dict. Otherwise, fetches from AWS Secrets Manager,
    parses the JSON string, stores in cache, and returns the dict.

    Args:
      name: Identifier of the secret in AWS Secrets Manager.

    Returns:
      A Python dict deserialized from the stored JSON secret string.
    """
    # Check cache first
    if name in _cache:
        secret_dict, ts = _cache[name]
        # If cache entry is still fresh, return it
        if time.time() - ts < TTL:
            return secret_dict

    # Cache miss or stale: fetch from AWS Secrets Manager
    resp = sm.get_secret_value(SecretId=name)
    raw_str = resp.get("SecretString", "{}")

    # Parse the JSON string into dict
    secret_dict = json.loads(raw_str)

    # Update cache with current timestamp
    _cache[name] = (secret_dict, time.time())

    return secret_dict
