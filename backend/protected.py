import json

def handler(event, context):
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",          # <— REQUIRED
            "Access-Control-Allow-Headers": "*",         # <— ALSO IMPORTANT
        },
        "body": json.dumps({"message": "protected endpoint ok"})
    }
