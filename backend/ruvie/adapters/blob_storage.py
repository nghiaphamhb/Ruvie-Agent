from os import name as os_name
from pathlib import Path
from typing import Protocol
from urllib.parse import unquote, urlparse

from ruvie.services.documents.upload import UploadValidationError


DEFAULT_BLOB_ROOT = Path(__file__).resolve().parents[3] / "data" / "uploads"


class S3Client(Protocol):
    def put_object(self, **kwargs: object) -> object: ...

    def delete_object(self, **kwargs: object) -> object: ...

    def get_object(self, **kwargs: object) -> object: ...


class LocalBlobStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def put(self, *, key: str, content: bytes, mime_type: str) -> str:
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path.as_uri()

    def delete(self, uri: str) -> None:
        path = unquote(urlparse(uri).path)
        resolved = Path(path[1:] if os_name == "nt" and path.startswith("/") else path).resolve()
        if resolved.is_relative_to(self.root):
            resolved.unlink(missing_ok=True)

    def get(self, uri: str) -> bytes:
        path = unquote(urlparse(uri).path)
        resolved = Path(path[1:] if os_name == "nt" and path.startswith("/") else path).resolve()
        if not resolved.is_relative_to(self.root):
            raise PermissionError("blob is outside private storage")
        return resolved.read_bytes()

    def _path_for(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise UploadValidationError("blob key must stay inside local storage")
        return path


class S3BlobStore:
    def __init__(self, client: S3Client, *, bucket: str, prefix: str = "") -> None:
        self.client = client
        self.bucket = bucket
        self.prefix = prefix.strip("/")

    def put(self, *, key: str, content: bytes, mime_type: str) -> str:
        object_key = self._object_key(key)
        self.client.put_object(Bucket=self.bucket, Key=object_key, Body=content, ContentType=mime_type, ACL="private")
        return f"s3://{self.bucket}/{object_key}"

    def delete(self, uri: str) -> None:
        object_key = uri.removeprefix(f"s3://{self.bucket}/")
        self.client.delete_object(Bucket=self.bucket, Key=object_key)

    def get(self, uri: str) -> bytes:
        object_key = uri.removeprefix(f"s3://{self.bucket}/")
        return self.client.get_object(Bucket=self.bucket, Key=object_key)["Body"].read()

    def _object_key(self, key: str) -> str:
        key = key.lstrip("/")
        return f"{self.prefix}/{key}" if self.prefix else key
