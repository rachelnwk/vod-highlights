import json
from urllib import error, request

from config.reader import CONFIG, require_value

ANALYSIS_API_BASE_URL = require_value("analysis_api", "base_url").rstrip("/")
ANALYSIS_API_PATH = require_value("analysis_api", "path")
ANALYSIS_REQUEST_TIMEOUT_SECONDS = CONFIG.getint("analysis_api", "timeout_seconds")


def _parse_response_body(raw_body: bytes) -> dict:
    if not raw_body:
        return {}

    parsed = json.loads(raw_body.decode("utf-8"))
    if isinstance(parsed, dict) and "statusCode" in parsed and "body" in parsed:
        if int(parsed["statusCode"]) >= 400:
            body = parsed["body"]
            if isinstance(body, str):
                try:
                    body = json.loads(body)
                except json.JSONDecodeError:
                    body = {"error": body}
            raise RuntimeError(body.get("error", f"Remote analysis failed with status {parsed['statusCode']}"))

        body = parsed["body"]
        return json.loads(body) if isinstance(body, str) else body

    return parsed


def analyze_observations(payload: dict) -> dict:
    url = f"{ANALYSIS_API_BASE_URL}{ANALYSIS_API_PATH}"
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=ANALYSIS_REQUEST_TIMEOUT_SECONDS) as response:
            return _parse_response_body(response.read())
    except error.HTTPError as exc:
        try:
            payload = _parse_response_body(exc.read())
        except Exception:
            payload = {"error": exc.reason}
        raise RuntimeError(payload.get("error", f"Remote analysis failed with status {exc.code}")) from exc
    except error.URLError as exc:
        raise RuntimeError(f"Could not reach the analysis API: {exc.reason}") from exc
