# app/core/db.py

"""
Low-level DynamoDB helpers for Triagely integrations.

Defines two main tables:

  1. triagely-oauth     → stores OAuth tokens for each user and provider
        • Partition Key (PK):  UserID (Cognito sub)
        • Sort Key      (SK):  provider_key (e.g., 'gmail:alice@x.com', 'slack')

  2. triagely-messages  → caches email/slack messages per user
        • PK:  UserID (Cognito sub)
        • SK:  MessageID (unique per message/thread)

Provides functions to save and retrieve tokens, list all Gmail tokens,
and put/query messages with deduplication.
"""
from __future__ import annotations
import os
import time
import json
import boto3
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key, Attr

# Initialize DynamoDB resource using AWS_REGION from environment
REGION = os.getenv("AWS_REGION")
ddb    = boto3.resource("dynamodb", region_name=REGION)
# Tables: triagely-oauth, triagely-messages
_t_oauth = ddb.Table("triagely-oauth")
_t_msg   = ddb.Table("triagely-messages")

# ───────────────────────────── OAuth rows ──────────────────────────────

def save_token(uid: str, provider_key: str, token: dict | str) -> None:
    """
    Persist an OAuth token for a given user and provider.

    Args:
      uid: Cognito user sub (string) used as partition key.
      provider_key: unique key for service, e.g. 'gmail:alice@example.com' or 'slack'.
      token: OAuth token payload (dict) or raw string; if dict, will be JSON-encoded.

    Effect:
      Inserts or overwrites an item in 'triagely-oauth' with a timestamp.
    """
    item = {
        "UserID":       uid,
        "Provider":     provider_key,
        # Ensure token is stored as JSON string
        "token":        json.dumps(token) if isinstance(token, dict) else token,
        # Record when connection happened (epoch seconds)
        "connected_at": int(time.time()),
    }
    _t_oauth.put_item(Item=item)


def get_token(uid: str, provider_key: str) -> dict | None:
    """
    Retrieve a stored OAuth token for a user-provider.

    Args:
      uid: Cognito user sub.
      provider_key: provider sort key.

    Returns:
      Decoded token dict if found, otherwise None.
    """
    res = _t_oauth.get_item(
        Key={"UserID": uid, "Provider": provider_key}
    )
    if "Item" in res:
        # Parse JSON back into dict
        return json.loads(res["Item"]["token"])
    return None


def list_gmail_tokens(uid: str) -> list[dict]:
    """
    List all Gmail OAuth tokens for a single user.

    Gmail provider_key entries start with 'gmail:'.

    Args:
      uid: Cognito user sub.

    Returns:
      List of DynamoDB items (dicts) with keys 'UserID', 'Provider', 'token', etc.
    """
    res = _t_oauth.query(
        KeyConditionExpression=
            Key("UserID").eq(uid) & Key("Provider").begins_with("gmail:")
    )
    return res.get("Items", [])


def all_gmail_tokens() -> list[tuple[str, str]]:
    """
    Scan and return every Gmail token entry across all users.

    Note: a full table scan may be expensive at scale.

    Returns:
      List of tuples: (UserID, Provider) for each Gmail row.
    """
    out = []
    start_key = None

    while True:
        scan_args = {
            # Only fetch keys to minimize data transfer
            "ProjectionExpression": "UserID, Provider",
            # Filter for Gmail provider entries
            "FilterExpression": Key("Provider").begins_with("gmail:"),
        }
        if start_key:
            scan_args["ExclusiveStartKey"] = start_key
        page = _t_oauth.scan(**scan_args)
        # Append tuple list
        for item in page.get("Items", []):
            out.append((item["UserID"], item["Provider"]))
        start_key = page.get("LastEvaluatedKey")
        if not start_key:
            break
    return out

# ───────────────────────────── Messages table ──────────────────────────

def put_msg(uid: str, msg_id: str, body: dict) -> None:
    """
    Insert a message into 'triagely-messages' if not already present.

    Uses a conditional put to enforce idempotency (no duplicates).

    Args:
      uid: Cognito user sub (partition key).
      msg_id: unique message/thread ID for sort key.
      body: dict of message attributes (subject, snippet, etc.).

    Raises:
      ConditionalCheckFailedException if item already exists.
    """
    item = {"UserID": uid, "MessageID": msg_id, **body}
    _t_msg.put_item(
        Item=item,
        ConditionExpression="attribute_not_exists(MessageID)",
    )


def list_msgs(uid: str, limit: int = 50, page: int = 1, priority_filter: str = None) -> dict:
    """
    Query recent cached messages for a user with pagination support.

    Args:
      uid: Cognito user sub.
      limit: maximum number of items to return per page.
      page: page number (1-indexed).
      priority_filter: optional priority filter ('High', 'Normal', None for all).

    Returns:
      Dict with pagination metadata and items: {
        "items": [...],
        "pagination": {
          "current_page": int,
          "total_pages": int,
          "total_count": int,
          "page_size": int
        }
      }
    """
    # Calculate 60 days ago timestamp for filtering
    sixty_days_ago = datetime.now() - timedelta(days=60)
    sixty_days_ago_iso = sixty_days_ago.isoformat()
    
    
    
    # Build filter expression
    filter_expr = Attr("dateISO").gte(sixty_days_ago_iso)
    if priority_filter:
        filter_expr = filter_expr & Attr("priority").eq(priority_filter)
    
    
    # Fetch ALL emails from the 60-day window using DynamoDB pagination
    all_items = []
    last_evaluated_key = None
    max_safety_limit = 10000  # Safety limit to prevent excessive memory usage
    
    while len(all_items) < max_safety_limit:
        query_args = {
            "KeyConditionExpression": Key("UserID").eq(uid),
            "FilterExpression": filter_expr,
            "ScanIndexForward": False  # Get newest MessageIDs first
        }
        
        if last_evaluated_key:
            query_args["ExclusiveStartKey"] = last_evaluated_key
            
        res = _t_msg.query(**query_args)
        batch_items = res.get("Items", [])
        all_items.extend(batch_items)
        
        last_evaluated_key = res.get("LastEvaluatedKey")
        if not last_evaluated_key:
            break
    
    # Sort ALL items by date in descending order (newest first)
    all_items.sort(key=lambda x: x.get("dateISO", ""), reverse=True)
    
    # Recalculate pagination based on actual results
    actual_total_count = len(all_items)
    actual_total_pages = (actual_total_count + limit - 1) // limit if actual_total_count > 0 else 1
    current_page = max(1, min(page, actual_total_pages)) if actual_total_pages > 0 else 1
    
    # Apply pagination to the sorted results
    start_idx = (current_page - 1) * limit
    end_idx = start_idx + limit
    items = all_items[start_idx:end_idx]
    
    return {
        "items": items,
        "pagination": {
            "current_page": current_page,
            "total_pages": actual_total_pages,
            "total_count": actual_total_count,
            "page_size": limit
        }
    }


def cleanup_old_messages() -> int:
    """
    Remove messages older than 90 days from all users.
    
    Returns:
        Number of messages deleted.
    """
    # Calculate 60 days ago timestamp for filtering
    sixty_days_ago = datetime.now() - timedelta(days=60)
    sixty_days_ago_iso = sixty_days_ago.isoformat()
    
    deleted_count = 0
    
    # Scan for old messages across all users
    try:
        response = _t_msg.scan(
            FilterExpression=Attr("dateISO").lt(sixty_days_ago_iso),
            ProjectionExpression="UserID, MessageID"
        )
        
        # Batch delete old messages
        with _t_msg.batch_writer() as batch:
            for item in response.get("Items", []):
                try:
                    batch.delete_item(
                        Key={
                            "UserID": item["UserID"],
                            "MessageID": item["MessageID"]
                        }
                    )
                    deleted_count += 1
                except Exception as e:
                    print(f"Failed to delete message {item['MessageID']}: {e}")
        
        # Handle pagination if there are more results
        while 'LastEvaluatedKey' in response:
            response = _t_msg.scan(
                FilterExpression=Attr("dateISO").lt(sixty_days_ago_iso),
                ProjectionExpression="UserID, MessageID",
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            
            with _t_msg.batch_writer() as batch:
                for item in response.get("Items", []):
                    try:
                        batch.delete_item(
                            Key={
                                "UserID": item["UserID"],
                                "MessageID": item["MessageID"]
                            }
                        )
                        deleted_count += 1
                    except Exception as e:
                        print(f"Failed to delete message {item['MessageID']}: {e}")
                        
    except Exception as e:
        print(f"Failed to cleanup old messages: {e}")
        
    return deleted_count


def cleanup_old_messages_for_user(user_id: str) -> int:
    """
    Remove messages older than 90 days for a specific user.
    
    Args:
        user_id: Cognito user sub.
        
    Returns:
        Number of messages deleted.
    """
    # Calculate 60 days ago timestamp for filtering
    sixty_days_ago = datetime.now() - timedelta(days=60)
    sixty_days_ago_iso = sixty_days_ago.isoformat()
    
    deleted_count = 0
    
    try:
        response = _t_msg.query(
            KeyConditionExpression=Key("UserID").eq(user_id),
            FilterExpression=Attr("dateISO").lt(sixty_days_ago_iso),
            ProjectionExpression="UserID, MessageID"
        )
        
        # Batch delete old messages for this user
        with _t_msg.batch_writer() as batch:
            for item in response.get("Items", []):
                try:
                    batch.delete_item(
                        Key={
                            "UserID": item["UserID"],
                            "MessageID": item["MessageID"]
                        }
                    )
                    deleted_count += 1
                except Exception as e:
                    print(f"Failed to delete message {item['MessageID']}: {e}")
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = _t_msg.query(
                KeyConditionExpression=Key("UserID").eq(user_id),
                FilterExpression=Attr("dateISO").lt(sixty_days_ago_iso),
                ProjectionExpression="UserID, MessageID",
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            
            with _t_msg.batch_writer() as batch:
                for item in response.get("Items", []):
                    try:
                        batch.delete_item(
                            Key={
                                "UserID": item["UserID"],
                                "MessageID": item["MessageID"]
                            }
                        )
                        deleted_count += 1
                    except Exception as e:
                        print(f"Failed to delete message {item['MessageID']}: {e}")
                        
    except Exception as e:
        print(f"Failed to cleanup old messages for user {user_id}: {e}")
        
    return deleted_count
