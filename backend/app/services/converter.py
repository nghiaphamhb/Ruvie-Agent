import hashlib
import json
from pathlib import Path

from markitdown import MarkItDown

from app.core.config import settings


SUPPORTED_EXTENSIONS = {
    ".md",
    ".pdf",
    ".docx",
    ".pptx",
    ".xlsx",
    ".html",
    ".csv",
    ".json",
    ".txt",
}


class UnsupportedFileTypeError(ValueError):
    pass


class MarkdownConversionError(RuntimeError):
    pass


# clean file name: "My Report 2025" -> "My_Report_2025"
def _safe_stem(path: Path) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in path.stem)


# create hashcode from file
def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()[:16]


def _cache_path(output_path: Path) -> Path:
    return output_path.with_suffix(".json")


def _build_metadata(input_path: Path, output_path: Path, extension: str) -> dict:
    return {
        "original_file": str(input_path),
        "markdown_file": str(output_path),
        "converter": "markitdown",
        "original_extension": extension,
    }


def _write_cache(cache_path: Path, input_path: Path, output_path: Path, extension: str) -> None:
    cache_path.write_text(
        json.dumps(
            _build_metadata(input_path, output_path, extension),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def convert_to_markdown(input_path: Path) -> Path:
    input_path = Path(input_path)
    extension = input_path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeError(f"Unsupported file type: {extension}")

    if not input_path.exists():
        raise MarkdownConversionError(f"Input file does not exist: {input_path}")

    if extension == ".md":
        return input_path

    output_dir = settings.CONVERTED_MARKDOWN_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    fingerprint = _file_hash(input_path)
    output_path = output_dir / f"{_safe_stem(input_path)}-{fingerprint}.md"
    cache_path = _cache_path(output_path)

    if output_path.exists() and output_path.stat().st_size > 0:
        if not cache_path.exists():
            _write_cache(cache_path, input_path, output_path, extension)
        return output_path

    try:
        try:
            converter = MarkItDown(enable_plugins=False)
        except TypeError:
            converter = MarkItDown()

        if hasattr(converter, "convert_local"):
            result = converter.convert_local(str(input_path))
        else:
            result = converter.convert(str(input_path))

        markdown = (result.text_content or "").strip()
    except UnicodeDecodeError as exc:
        raise MarkdownConversionError(f"Encoding error while converting {input_path}") from exc
    except Exception as exc:
        raise MarkdownConversionError(f"Failed to convert {input_path}: {exc}") from exc

    if not markdown:
        raise MarkdownConversionError(f"Converted Markdown is empty: {input_path}")

    output_path.write_text(markdown + "\n", encoding="utf-8")
    _write_cache(cache_path, input_path, output_path, extension)

    return output_path


def conversion_metadata(original_path: Path, markdown_path: Path) -> dict:
    original_path = Path(original_path)
    markdown_path = Path(markdown_path)

    if original_path.suffix.lower() == ".md":
        converter = "none"
    else:
        converter = "markitdown"

    return {
        **_build_metadata(original_path, markdown_path, original_path.suffix.lower()),
        "converter": converter,
    }
