"""Fixed, registered checks. Resolve once and connect to that approved IP, without redirects."""

import hashlib
import ipaddress
import json
import re
import socket
import time
import uuid
from urllib.parse import urlsplit
import httpx
from pydantic import Field, field_validator
from .redaction import redact
from .types import Record


class RegisteredHttpCheck(Record):
    id: str = Field(min_length=1, max_length=100)
    target_id: str
    origin: str
    path: str
    timeout_seconds: float = Field(default=3, gt=0, le=5)
    expected_status: int = Field(default=200, ge=100, le=599)
    require_request_echo: bool = False

    @field_validator("path")
    @classmethod
    def safe_path(cls, value):
        if not re.fullmatch(r"/[A-Za-z0-9/_.-]*", value) or "//" in value or ".." in value.split("/"):
            raise ValueError("A fixed absolute path is required")
        return value


class ProbeResult(Record):
    id: str
    target_id: str
    check_id: str
    request_id: str
    observed_at: float
    available_at: float
    http_status: int | None
    elapsed_ms: float
    check_pass: bool | None
    contract_pass: bool | None = None
    reason: str
    body_digest: str | None
    payload: dict


def unsafe_origin(origin, allow_loopback=False):
    try:
        p = urlsplit(origin)
        if not p.hostname or p.username or p.password or p.path not in ("", "/") or p.query or p.fragment:
            return True
        if p.scheme not in ("https", "http"):
            return True
        p.port
        try:
            address = ipaddress.ip_address(p.hostname)
        except ValueError:
            address = None
        local = p.hostname == "localhost" or bool(address and address.is_loopback)
        if p.scheme == "http" and not (allow_loopback and local):
            return True
        if address and not address.is_global and not (allow_loopback and address.is_loopback):
            return True
        if p.hostname == "localhost" and not allow_loopback:
            return True
        return False
    except ValueError:
        return True


def resolve(host, port):
    return list(dict.fromkeys(row[4][0] for row in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)))


class PinnedTransport(httpx.BaseTransport):
    def __init__(self, ip, hostname, port, scheme):
        self.ip, self.hostname, self.port, self.scheme = ip, hostname, port, scheme
        self.transport = httpx.HTTPTransport(retries=0, trust_env=False)

    def handle_request(self, request):
        headers = request.headers.copy()
        headers["Host"] = self.hostname + (f":{self.port}" if self.port not in (80, 443) else "")
        pinned = httpx.Request(
            request.method,
            request.url.copy_with(host=self.ip),
            headers=headers,
            stream=request.stream,
            extensions={**request.extensions, "sni_hostname": self.hostname.encode("ascii")},
        )
        return self.transport.handle_request(pinned)

    def close(self):
        self.transport.close()


class ProbeRunner:
    def __init__(self, targets, *, allow_loopback=False, resolver=resolve, transport=None, clock=time.time):
        self.targets, self.allow_loopback, self.resolver, self.transport, self.clock = (
            targets,
            allow_loopback,
            resolver,
            transport,
            clock,
        )
        self.seen = set()

    def run(self, check, *, request_id=None):
        check = RegisteredHttpCheck.model_validate(check.model_dump())
        target = self.targets.get(check.target_id)
        if not target or not target.origin or check.origin.rstrip("/") != target.origin.rstrip("/"):
            raise ValueError("Unregistered check origin/target")
        request_id = request_id or uuid.uuid4().hex
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", request_id) or request_id in self.seen:
            raise ValueError("Fresh unique request ID required")
        if len(self.seen) >= 10000:
            raise ValueError("Probe lifetime budget exhausted")
        self.seen.add(request_id)
        began = time.perf_counter()
        observed = self.clock()
        status = None
        payload = {}
        digest = None

        def result(passed, reason):
            return ProbeResult(
                id=uuid.uuid4().hex,
                target_id=check.target_id,
                check_id=check.id,
                request_id=request_id,
                observed_at=observed,
                available_at=self.clock(),
                http_status=status,
                elapsed_ms=(time.perf_counter() - began) * 1000,
                check_pass=passed,
                reason=reason,
                body_digest=digest,
                payload=payload,
            )

        if unsafe_origin(check.origin, self.allow_loopback):
            return result(None, "unsafe_destination")
        parsed = urlsplit(check.origin)
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        try:
            addresses = self.resolver(parsed.hostname, port)
            if not addresses or any(
                not ipaddress.ip_address(ip).is_global
                and not (self.allow_loopback and ipaddress.ip_address(ip).is_loopback)
                for ip in addresses
            ):
                return result(None, "unsafe_destination")
        except (OSError, ValueError):
            return result(None, "dns_unavailable")
        transport = self.transport or PinnedTransport(addresses[0], parsed.hostname, port, parsed.scheme)
        try:
            with httpx.Client(
                transport=transport, timeout=check.timeout_seconds, follow_redirects=False, trust_env=False
            ) as client:
                with client.stream(
                    "GET",
                    check.origin.rstrip("/") + check.path,
                    headers={"X-Request-ID": request_id, "Cache-Control": "no-cache"},
                ) as response:
                    status = response.status_code
                    raw = bytearray()
                    for chunk in response.iter_bytes():
                        raw.extend(chunk)
                        if len(raw) > 4096:
                            return result(None, "response_too_large")
                        if time.perf_counter() - began > check.timeout_seconds:
                            return result(False, "timeout")
                    digest = hashlib.sha256(raw).hexdigest()
                    try:
                        decoded = json.loads(raw)
                        payload = redact(decoded) if isinstance(decoded, dict) else {"body": redact(decoded)}
                    except (ValueError, UnicodeError):
                        payload = {"text": redact(raw.decode("utf-8", errors="replace"))}
            if check.require_request_echo and payload.get("request_id") != request_id:
                return result(False, "request_id_mismatch")
            return result(
                status == check.expected_status,
                "pass" if status == check.expected_status else "unexpected_status",
            )
        except httpx.TimeoutException:
            return result(False, "timeout")
        except httpx.TransportError:
            return result(None, "observer_network")
