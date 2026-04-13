#!/usr/bin/env python3
"""
Upload all source documents to the Render server.
Usage: UPLOAD_TOKEN=your-token python upload_sources.py
"""
import os
import sys
import uuid
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

TOKEN = os.environ.get("UPLOAD_TOKEN")
if not TOKEN:
    sys.exit("Error: UPLOAD_TOKEN is not set.\nRun: UPLOAD_TOKEN=your-token python upload_sources.py")

BASE_URL = "https://pest-7ij8.onrender.com"
SOURCES = Path(__file__).parent / "sources"

if not SOURCES.exists():
    sys.exit(f"Error: sources/ not found at {SOURCES}")


def multipart_encode(fields: dict, filename: str, filedata: bytes):
    boundary = uuid.uuid4().hex
    lines = []
    for name, value in fields.items():
        lines += [
            f"--{boundary}".encode(),
            f'Content-Disposition: form-data; name="{name}"'.encode(),
            b"",
            value.encode(),
        ]
    lines += [
        f"--{boundary}".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode(),
        b"Content-Type: application/octet-stream",
        b"",
        filedata,
        f"--{boundary}--".encode(),
    ]
    body = b"\r\n".join(lines)
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type


files = sorted(f for f in SOURCES.rglob("*") if f.is_file())
print(f"Found {len(files)} files to upload\n")

success, failed = 0, 0

for path in files:
    subpath = str(path.relative_to(SOURCES))
    print(f"  {subpath} ... ", end="", flush=True)

    body, content_type = multipart_encode(
        {"subpath": subpath},
        path.name,
        path.read_bytes(),
    )
    req = Request(
        f"{BASE_URL}/upload",
        data=body,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": content_type,
        },
        method="POST",
    )
    try:
        with urlopen(req) as resp:
            print(f"OK")
            success += 1
    except HTTPError as e:
        print(f"FAILED (HTTP {e.code}: {e.read().decode()[:120]})")
        failed += 1
    except URLError as e:
        print(f"FAILED ({e.reason})")
        failed += 1

print(f"\nDone. {success} uploaded, {failed} failed.")
