"""Bounded parsing for private clinical uploads; no network access or public paths."""

import warnings
from io import BytesIO

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader


def validate_pdf(content: bytes) -> bytes:
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(413, "PDF must be at most 5 MB")
    forbidden = {
        "/JavaScript",
        "/JS",
        "/Launch",
        "/EmbeddedFile",
        "/EmbeddedFiles",
        "/RichMedia",
        "/OpenAction",
        "/AA",
        "/XFA",
    }
    try:
        reader = PdfReader(BytesIO(content), strict=True)
        if reader.is_encrypted or not 0 < len(reader.pages) <= 500:
            raise ValueError()
        visited = set()
        remaining = [reader.trailer]
        while remaining:
            obj = remaining.pop()
            identity = (obj.idnum, obj.generation) if hasattr(obj, "idnum") else id(obj)
            if identity in visited:
                continue
            visited.add(identity)
            if len(visited) > 20000:
                raise ValueError()
            obj = obj.get_object() if hasattr(obj, "get_object") else obj
            if isinstance(obj, dict):
                if forbidden.intersection(str(k) for k in obj):
                    raise ValueError()
                remaining.extend(obj.values())
            elif isinstance(obj, list):
                remaining.extend(obj)
            elif isinstance(obj, str) and obj in forbidden:
                raise ValueError()
    except Exception:
        raise HTTPException(
            422, "Use a readable PDF without encryption, active actions or embedded files"
        ) from None
    return content


def validate_photo(content: bytes) -> tuple[bytes, str]:
    if len(content) > 3 * 1024 * 1024:
        raise HTTPException(413, "Photo must be at most 3 MB")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            picture = Image.open(BytesIO(content))
            if picture.format not in {"JPEG", "PNG"} or picture.width * picture.height > 20_000_000:
                raise ValueError()
            picture.load()
            format_name = picture.format
            cleaned = BytesIO()
            picture.convert("RGBA" if format_name == "PNG" else "RGB").save(
                cleaned, format=format_name
            )
            encoded = cleaned.getvalue()
            if len(encoded) > 3 * 1024 * 1024:
                raise ValueError()
    except (
        ValueError,
        OSError,
        UnidentifiedImageError,
        Image.DecompressionBombWarning,
        Image.DecompressionBombError,
    ):
        raise HTTPException(
            422, "Use a valid JPEG or PNG photo within the size and pixel limits"
        ) from None
    return encoded, "image/png" if format_name == "PNG" else "image/jpeg"
