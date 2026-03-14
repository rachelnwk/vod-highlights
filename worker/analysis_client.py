import json
import sys
from pathlib import Path
from urllib import error, request

from config import settings


def _load_local_lambda_result(payload: dict) -> dict:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from lambda_functions.highlight_analysis import analyze_highlight_request

    return analyze_highlight_request(payload)


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
    if not settings.ANALYSIS_API_BASE_URL:
        return _load_local_lambda_result(payload)

    url = f"{settings.ANALYSIS_API_BASE_URL.rstrip('/')}{settings.ANALYSIS_API_PATH}"
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=settings.ANALYSIS_REQUEST_TIMEOUT_SECONDS) as response:
            return _parse_response_body(response.read())
    except error.HTTPError as exc:
        try:
            payload = _parse_response_body(exc.read())
        except Exception:
            payload = {"error": exc.reason}
        raise RuntimeError(payload.get("error", f"Remote analysis failed with status {exc.code}")) from exc
    except error.URLError as exc:
        raise RuntimeError(f"Could not reach the analysis API: {exc.reason}") from exc
