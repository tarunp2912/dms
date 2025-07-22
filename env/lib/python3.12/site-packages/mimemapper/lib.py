import json, os
import mimetypes
import importlib.resources
from pathlib import PosixPath

MODULE_PATH = importlib.resources.files(__package__) if __package__ else PosixPath("./")

with open(MODULE_PATH / "mime_to_ext.json") as f:
    MIME_TO_EXT_MAP = json.load(f)
with open(MODULE_PATH / "ext_to_mime.json") as f:
    EXT_TO_MIME_MAP = json.load(f)


def get_mime_type(ext, all=False, native_first=True):
    ext = ext.split(".")[-1]
    # Based on config, use native eagerly
    native = mimetypes.guess_type(f"test.{ext}")[0]
    if (not all and native_first) and native:
        return native

    # Use as fallback always
    if ext not in EXT_TO_MIME_MAP or not EXT_TO_MIME_MAP[ext]:
        return native

    mimes = sorted(EXT_TO_MIME_MAP[ext], key=len)
    if all:
        return mimes
    return mimes[0] if EXT_TO_MIME_MAP[ext] else None


def get_extension(mime, all=False):
    return MIME_TO_EXT_MAP[mime] if all else MIME_TO_EXT_MAP[mime][0]
