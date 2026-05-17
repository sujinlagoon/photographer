import boto3
import os
import uuid

from backend.app.core.config import settings


class CloudflareR2Uploader:

    def __init__(self):

        self.bucket_name = (
            settings.R2_BUCKET_NAME
        )

        endpoint_url = (
            f"https://"
            f"{settings.R2_ACCOUNT_ID}"
            f".r2.cloudflarestorage.com"
        )

        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=(
                settings.R2_ACCESS_KEY
            ),
            aws_secret_access_key=(
                settings.R2_SECRET_KEY
            )
        )

    def upload_file(
        self,
        file_path
    ):

        original_name = (
            os.path.basename(
                file_path
            )
        )

        extension = (
            os.path.splitext(
                original_name
            )[1]
        )

        unique_file_name = (
            f"{uuid.uuid4()}"
            f"{extension}"
        )

        self.client.upload_file(
            file_path,
            self.bucket_name,
            unique_file_name
        )

        public_url = (
            f"{settings.R2_PUBLIC_URL.rstrip('/')}"
            f"/{unique_file_name}"
        )

        print(
            f"☁ Uploaded URL: "
            f"{public_url}"
        )

        return public_url

    def upload_fileobj(self, file_obj, filename):
        extension = os.path.splitext(filename)[1]
        unique_file_name = f"logos/{uuid.uuid4()}{extension}"
        
        self.client.upload_fileobj(
            file_obj,
            self.bucket_name,
            unique_file_name
        )
        
        return f"{settings.R2_PUBLIC_URL.rstrip('/')}/{unique_file_name}"