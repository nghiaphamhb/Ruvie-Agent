from os import name as os_name
from pathlib import Path
from typing import Protocol
from urllib.parse import unquote, urlparse

from ruvie.services.documents.upload import UploadValidationError


# Internal upload root; storage URIs must never be returned as public download links.
DEFAULT_BLOB_ROOT = Path(__file__).resolve().parents[3] / "data" / "uploads"


class S3Client(Protocol):
    def put_object(self, **kwargs: object) -> object: ...

    def delete_object(self, **kwargs: object) -> object: ...

    def get_object(self, **kwargs: object) -> object: ...


class LocalBlobStore:
    """Read/write private files inside root; URIs are internal storage references."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def put(self, *, key: str, content: bytes, mime_type: str) -> str:
        """Store bytes under a checked key and return an internal file URI."""
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path.as_uri()

    def delete(self, uri: str) -> None:
        """Remove a blob inside root; ignore missing files and paths outside root."""
        path = unquote(urlparse(uri).path)
        # file:///C:/... has a leading slash that Windows filesystem paths do not use.
        resolved = Path(path[1:] if os_name == "nt" and path.startswith("/") else path).resolve()
        if resolved.is_relative_to(self.root):
            resolved.unlink(missing_ok=True)

    def get(self, uri: str) -> bytes:
        """Read an internal URI inside root; caller authorizes document access first."""
        path = unquote(urlparse(uri).path)
        # file:///C:/... has a leading slash that Windows filesystem paths do not use.
        resolved = Path(path[1:] if os_name == "nt" and path.startswith("/") else path).resolve()
        if not resolved.is_relative_to(self.root):
            raise PermissionError("blob is outside private storage")
        return resolved.read_bytes()

    def _path_for(self, key: str) -> Path:
        """Resolve a key and reject traversal outside the private storage root."""
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise UploadValidationError("blob key must stay inside local storage")
        return path


class S3BlobStore:
    """Store private S3 objects; callers authorize access before using internal URIs."""

    def __init__(self, client: S3Client, *, bucket: str, prefix: str = "") -> None:
        self.client = client
        self.bucket = bucket
        self.prefix = prefix.strip("/")

    def put(self, *, key: str, content: bytes, mime_type: str) -> str:
        """Upload bytes with private ACL and return an internal s3:// URI."""
        object_key = self._object_key(key)
        self.client.put_object(Bucket=self.bucket, Key=object_key, Body=content, ContentType=mime_type, ACL="private")
        return f"s3://{self.bucket}/{object_key}"

    def delete(self, uri: str) -> None:
        """Delete an internal object URI from the configured bucket."""
        object_key = uri.removeprefix(f"s3://{self.bucket}/")
        self.client.delete_object(Bucket=self.bucket, Key=object_key)

    def get(self, uri: str) -> bytes:
        """Read an internal URI from the configured bucket; caller checks access first."""
        object_key = uri.removeprefix(f"s3://{self.bucket}/")
        return self.client.get_object(Bucket=self.bucket, Key=object_key)["Body"].read()

    def _object_key(self, key: str) -> str:
        key = key.lstrip("/")
        return f"{self.prefix}/{key}" if self.prefix else key
