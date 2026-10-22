import os
from urllib.parse import urlsplit
import uvicorn
from liara_guard.api import create_app

if __name__ == "__main__":
    origin = urlsplit(os.environ.get("PUBLIC_ORIGIN", "http://127.0.0.1:8661"))
    if origin.hostname not in ("127.0.0.1", "localhost"):
        raise SystemExit("Local operator helper binds loopback only")
    uvicorn.run(create_app(), host="127.0.0.1", port=origin.port or 8661, log_level="warning")
