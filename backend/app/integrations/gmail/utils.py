import os, json, boto3

# Make sure REGION is set in your env
ddb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION"))

def load_thread_plain(user_id: str, message_id: str) -> str:
    """
    Return the cached plain-text body for a message/thread.
    Falls back to snippet if plain is empty. Returns '' if not found.
    """
    table = ddb.Table("triagely-messages")
    try:
        item = table.get_item(Key={"UserID": user_id, "MessageID": message_id})["Item"]
    except KeyError:
        return ""
    return item.get("plain") or item.get("snippet", "")