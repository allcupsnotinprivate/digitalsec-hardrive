import abc
from collections.abc import Mapping
from typing import Any

import aioboto3
from botocore.exceptions import ClientError

from .aClasses import AInfrastructure


class AS3Client(AInfrastructure, abc.ABC):
    @abc.abstractmethod
    async def ensure_bucket(self, bucket: str) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def upload(
        self,
        *,
        bucket: str,
        key: str,
        body: bytes,
        content_type: str | None,
        metadata: Mapping[str, str] | None = None,
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def delete(self, *, bucket: str, key: str) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def generate_presigned_url(self, *, bucket: str, key: str, expires_in: int) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_metadata(self, *, bucket: str, key: str) -> dict[str, Any]:
        raise NotImplementedError


class S3MinioClient(AS3Client):
    def __init__(
        self,
        *,
        endpoint_url: str | None,
        region: str | None,
        access_key: str,
        secret_key: str,
        use_ssl: bool,
    ) -> None:
        self._session = aioboto3.Session()
        self._client_kwargs: dict[str, Any] = {
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "use_ssl": use_ssl,
        }
        if endpoint_url:
            self._client_kwargs["endpoint_url"] = endpoint_url
        if region:
            self._client_kwargs["region_name"] = region

    def _client(self) -> Any:
        return self._session.client("s3", **self._client_kwargs)

    async def ensure_bucket(self, bucket: str) -> None:
        async with self._client() as client:
            try:
                await client.head_bucket(Bucket=bucket)
            except ClientError as exc:  # pragma: no cover - network errors
                error_code = exc.response.get("Error", {}).get("Code", "")
                if error_code in {"404", "NoSuchBucket"}:
                    await client.create_bucket(Bucket=bucket)
                else:
                    raise

    async def upload(
        self,
        *,
        bucket: str,
        key: str,
        body: bytes,
        content_type: str | None,
        metadata: Mapping[str, str] | None = None,
    ) -> None:
        put_kwargs: dict[str, Any] = {
            "Bucket": bucket,
            "Key": key,
            "Body": body,
        }
        if content_type:
            put_kwargs["ContentType"] = content_type
        if metadata:
            put_kwargs["Metadata"] = {k: str(v) for k, v in metadata.items()}

        async with self._client() as client:
            await client.put_object(**put_kwargs)

    async def delete(self, *, bucket: str, key: str) -> None:
        async with self._client() as client:
            await client.delete_object(Bucket=bucket, Key=key)

    async def generate_presigned_url(self, *, bucket: str, key: str, expires_in: int) -> str:
        async with self._client() as client:
            return await client.generate_presigned_url(  # type: ignore[no-any-return]
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expires_in,
            )

    async def get_metadata(self, *, bucket: str, key: str) -> dict[str, Any]:
        async with self._client() as client:
            result = await client.head_object(Bucket=bucket, Key=key)
            metadata = result.get("Metadata", {})
            metadata["content_type"] = result.get("ContentType")
            metadata["content_length"] = result.get("ContentLength")
            return metadata  # type: ignore[no-any-return]
