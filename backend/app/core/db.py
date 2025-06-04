"""
Low-level Dynamo helpers shared by every integration.
Tables:

    triagely-oauth     PK = UserID   SK = gmail:<addr> | slack | …
    triagely-messages  PK = UserID   SK = MessageID
"""
from __future__ import annotations
import os, time, json, boto3
from boto3.dynamodb.conditions import Key, Attr

REGION = os.getenv("AWS_REGION")
ddb    = boto3.resource("dynamodb", region_name=REGION)
t_oauth = ddb.Table("triagely-oauth")
t_msg   = ddb.Table("triagely-messages")

# ───────────────────────────── OAuth rows ──────────────────────────────
def save_token(uid: str, provider_key: str, token: dict | str) -> None:
    """provider_key examples →  gmail:karthik@x.com   |   slack"""
    t_oauth.put_item(
        Item={
            "UserID":       uid,
            "Provider":     provider_key,
            "token":        json.dumps(token) if isinstance(token, dict) else token,
            "connected_at": int(time.time()),
        }
    )

def get_token(uid: str, provider_key: str) -> dict | None:
    res = t_oauth.get_item(Key={"UserID": uid, "Provider": provider_key})
    return json.loads(res["Item"]["token"]) if "Item" in res else None

def list_gmail_tokens(uid: str) -> list[dict]:
    """
    All Gmail rows for **one** user.
    (Provider sort-key starts with  "gmail:")
    """
    res = t_oauth.query(
        KeyConditionExpression=Key("UserID").eq(uid)           # PK
                              & Key("Provider").begins_with("gmail:")  # SK prefix
    )
    return res.get("Items", [])


def all_gmail_tokens() -> list[tuple[str, str]]:
    """
    Every Gmail row in the whole table.
    Returns  [(UserID, ProviderKey), …]
    """
    out, start_key = [], None
    while True:
        scan_args = {
            "ProjectionExpression": "UserID, Provider",
            "FilterExpression":     Key("Provider").begins_with("gmail:"),  # SK prefix
        }
        if start_key:                            # ← only present after 1st page
            scan_args["ExclusiveStartKey"] = start_key
        page = t_oauth.scan(**scan_args)
        out.extend((i["UserID"], i["Provider"]) for i in page.get("Items", []))
        start_key = page.get("LastEvaluatedKey")
        if not start_key:
            break
    return out

# ───────────────────────────── Messages table ──────────────────────────
def put_msg(uid: str, msg_id: str, body: dict) -> None:
    """
    Write exactly once: the ConditionExpression guarantees we never
    create a duplicate row for the same (UserID , MessageID).
    """
    t_msg.put_item(
        Item={"UserID": uid, "MessageID": msg_id, **body},
        ConditionExpression="attribute_not_exists(MessageID)",   # 👈 NEW
    )

def list_msgs(uid: str, limit: int = 50) -> list[dict]:
    return t_msg.query(
        KeyConditionExpression=Key("UserID").eq(uid),
        Limit=limit,
        ScanIndexForward=False,       # newest-first
    )["Items"]