import boto3
from config import settings

s3_client = boto3.client("s3", region_name=settings.AWS_REGION)
sqs_client = boto3.client("sqs", region_name=settings.AWS_REGION)
