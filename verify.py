#!/usr/bin/env python3
"""Small, bounded verifier for this local training target.

It refuses non-loopback targets so it cannot be repurposed as a remote scanner.
"""
from http.client import HTTPConnection
from urllib.parse import quote, urlencode
import os
import sys

HOST, PORT = "127.0.0.1", int(os.environ.get("PORT", "8000"))

def get(path):
    c = HTTPConnection(HOST, PORT, timeout=3)
    c.request("GET", path)
    r = c.getresponse()
    body = r.read().decode(errors="replace")
    return r.status, body

def post(path, form):
    c = HTTPConnection(HOST, PORT, timeout=3)
    payload = urlencode(form)
    c.request("POST", path, payload, {"Content-Type": "application/x-www-form-urlencoded"})
    r = c.getresponse()
    return r.status, r.read().decode(errors="replace")

checks = [
    ("Reflected XSS", "/search?q=" + quote("<script>pentest</script>"), "<script>pentest</script>"),
    ("IDOR / missing object authorization", "/users?id=2", "bob-admin-training-secret"),
    ("Path traversal", "/download?file=" + quote("../local-pentest-lab/README.md"), "Local Pentest Lab"),
]
failed = 0
for name, path, marker in checks:
    try:
        status, body = get(path)
        ok = status == 200 and marker in body
    except OSError as e:
        print(f"[ERROR] target unavailable: {e}")
        sys.exit(2)
    print(f"[{ 'FOUND' if ok else 'MISS' }] {name} ({status})")
    failed += not ok

try:
    post_status, _ = post("/comments", {"comment": "<script>stored-pentest</script>"})
    status, body = get("/comments")
    ok = post_status == 303 and status == 200 and "<script>stored-pentest</script>" in body
except OSError as e:
    print(f"[ERROR] target unavailable: {e}")
    sys.exit(2)
print(f"[{ 'FOUND' if ok else 'MISS' }] Stored XSS ({status})")
failed += not ok

total_checks = len(checks) + 1
print(f"\nResult: {total_checks - failed}/{total_checks} intentionally vulnerable checks reproduced")
sys.exit(0 if failed == 0 else 1)
