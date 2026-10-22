import hashlib
import hmac
import secrets
import sqlite3
import time
from pathlib import Path


def hash_password(password):
    if not isinstance(password, str) or not 12 <= len(password) <= 1024:
        raise ValueError("Password length must be12–1024")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    return "scrypt:" + salt.hex() + ":" + digest.hex()


def valid_hash(encoded):
    try:
        kind, salt, digest = encoded.split(":")
        return kind == "scrypt" and len(bytes.fromhex(salt)) == 16 and len(bytes.fromhex(digest)) == 32
    except (AttributeError, ValueError):
        return False


def verify_password(password, encoded):
    if not valid_hash(encoded) or not isinstance(password, str) or len(password) > 1024:
        return False
    _, salt, expected = encoded.split(":")
    actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1, dklen=32)
    return hmac.compare_digest(actual, bytes.fromhex(expected))


class AuthStore:
    def __init__(self, path, secret, password_hash, *, clock=time.time):
        if len(secret) < 32 or not valid_hash(password_hash):
            raise ValueError("Strong session secret and password hash required")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.secret = secret.encode()
        # One configured account owns this operator instance; sessions are revocable credentials.
        # Keep durable data ownership independent of random browser session tokens.
        self.owner_id = hmac.new(
            self.secret, b"liara-service-watch:instance-owner:v1", hashlib.sha256
        ).hexdigest()
        self.password_hash = password_hash
        self.clock = clock
        with sqlite3.connect(self.path) as db:
            db.executescript(
                "CREATE TABLE IF NOT EXISTS owner_sessions(id TEXT PRIMARY KEY,expires REAL); CREATE TABLE IF NOT EXISTS login_failures(ip TEXT,at REAL);"
            )
        self.path.chmod(0o600)

    def login(self, password, ip):
        with sqlite3.connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            now = self.clock()
            db.execute("DELETE FROM login_failures WHERE at<=?", (now - 60,))
            if db.execute("SELECT COUNT(*) FROM login_failures WHERE ip=?", (ip,)).fetchone()[0] >= 5:
                raise ValueError("rate_limited")
            if not verify_password(password, self.password_hash):
                db.execute("INSERT INTO login_failures VALUES(?,?)", (ip, now))
                db.commit()
                raise ValueError("invalid_login")
            session = secrets.token_hex(24)
            db.execute("INSERT INTO owner_sessions VALUES(?,?)", (session, now + 86400))
        signature = hmac.new(self.secret, session.encode(), hashlib.sha256).hexdigest()
        return session + "." + signature, self.owner_id

    def resolve(self, cookie):
        if not isinstance(cookie, str) or len(cookie) > 200 or cookie.count(".") != 1:
            raise ValueError("unauthenticated")
        owner, signature = cookie.split(".")
        expected = hmac.new(self.secret, owner.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected.encode(), signature.encode()):
            raise ValueError("unauthenticated")
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT expires FROM owner_sessions WHERE id=?", (owner,)).fetchone()
        if not row or row[0] <= self.clock():
            raise ValueError("unauthenticated")
        return self.owner_id

    def logout(self, cookie):
        self.resolve(cookie)
        session = cookie.split(".", 1)[0]
        with sqlite3.connect(self.path) as db:
            db.execute("DELETE FROM owner_sessions WHERE id=?", (session,))
