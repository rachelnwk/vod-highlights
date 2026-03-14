import boto3
from config.reader import CONFIG, require_value

AWS_REGION = require_value("s3", "region_name")
AWS_S3_BUCKET = require_value("s3", "bucket_name")
AWS_S3_URL_EXPIRATION_SECONDS = CONFIG.getint("s3", "url_expiration_seconds", fallback=3600)

s3_client = boto3.client("s3", region_name=AWS_REGION)


def build_s3_object_url(
    bucket: str,
    key: str,
    response_content_disposition: str | None = None,
) -> str:
    params = {
        "Bucket": bucket,
        "Key": key,
    }
    if response_content_disposition:
        params["ResponseContentDisposition"] = response_content_disposition

    return s3_client.generate_presigned_url(
        "get_object",
        Params=params,
        ExpiresIn=AWS_S3_URL_EXPIRATION_SECONDS,
    )
