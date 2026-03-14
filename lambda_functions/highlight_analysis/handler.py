import json

from .analysis import analyze_highlight_request


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "OPTIONS,POST",
        },
        "body": json.dumps(body),
    }


def lambda_handler(event, context):
    try:
        if event is None:
            payload = {}
        elif isinstance(event, dict) and "body" in event:
            body = event.get("body") or "{}"
            payload = json.loads(body) if isinstance(body, str) else body
        else:
            payload = event

        result = analyze_highlight_request(payload)
        return _response(200, result)
    except ValueError as exc:
        return _response(400, {"error": str(exc)})
    except Exception as exc:
        return _response(500, {"error": str(exc)})
