import os, time, json, boto3
from boto3.dynamodb.conditions import Key

REGION = os.getenv("AWS_REGION")
ddb  = boto3.resource("dynamodb", region_name=REGION)
t_msg  = ddb.Table("triagely-messages")
t_oauth = ddb.Table("triagely-oauth")

# ---- OAuth tokens ----------------------------------------------------------
def save_token(uid: str, provider: str, token: dict | str):
    if isinstance(token, dict):
        token = json.dumps(token)
    t_oauth.put_item(Item={
        "UserID": uid,
        "Provider": provider,
        "token": token,
        "connected_at": int(time.time())
    })

def get_token(uid: str, provider: str) -> dict | None:
    r = t_oauth.get_item(Key={"UserID": uid, "Provider": provider})
    return json.loads(r["Item"]["token"]) if "Item" in r else None

# ---- Messages --------------------------------------------------------------
def put_msg(uid: str, msg_id: str, source: str, body: dict):
    
    t_msg.put_item(Item={"UserID": uid, "MessageID": msg_id, "Source": source, **body})

def list_msgs(uid: str, limit=50):
    return t_msg.query(KeyConditionExpression=Key("UserID").eq(uid), Limit=limit)["Items"]
