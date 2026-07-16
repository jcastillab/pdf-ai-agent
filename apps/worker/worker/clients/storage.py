from pathlib import Path

import boto3
from botocore.config import Config

from worker.config import WorkerSettings


class ObjectStorage:
    def __init__(self, settings: WorkerSettings) -> None:
        self.bucket = settings.r2_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.r2_endpoint_url,
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            region_name=settings.r2_region,
            config=Config(signature_version="s3v4"),
        )

    def download(self, key: str, destination: Path) -> None:
        self.client.download_file(self.bucket, key, str(destination))
