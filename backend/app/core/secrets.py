import os, json, time, boto3
REGION = os.getenv("AWS_REGION")
sm = boto3.client("secretsmanager", region_name=REGION)
_cache: dict[str, tuple[dict, float]] = {}
TTL = 60*15

def get(name: str) -> dict:
    if name in _cache and time.time() - _cache[name][1] < TTL:
        return _cache[name][0]
    s = json.loads(sm.get_secret_value(SecretId=name)["SecretString"])
    _cache[name] = (s, time.time())
    return s

