#!/usr/bin/env python3
"""Local-only intentionally vulnerable training service.

Do not expose this process to a network. It binds to 127.0.0.1 by default.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
import json
import os
import sqlite3

HOST = "127.0.0.1"
PORT = int(os.environ.get("PORT", "8000"))
DB = os.path.join(os.path.dirname(__file__), "lab.db")


def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("create table if not exists users (id integer primary key, username text, role text, secret text)")
    if conn.execute("select count(*) from users").fetchone()[0] == 0:
        conn.executemany("insert into users(username, role, secret) values (?, ?, ?)", [
            ("alice", "viewer", "alice-training-secret"),
            ("bob", "admin", "bob-admin-training-secret"),
        ])
        conn.commit()
    return conn


class Handler(BaseHTTPRequestHandler):
    server_version = "LocalPentestLab/1.0"

    def send(self, body, status=200, content_type="text/html; charset=utf-8"):
        data = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        q = parse_qs(parsed.query)
        if parsed.path == "/":
            return self.send("""<!doctype html><title>Local Pentest Lab</title>
            <h1>Local Pentest Lab</h1><p>Training routes:</p>
            <ul><li><a href='/search?q=hello'>Reflected search</a></li>
            <li><a href='/users?id=1'>User lookup</a></li>
            <li><a href='/download?file=README.md'>File download</a></li></ul>
            <form method='post' action='/comments'><input name='comment'><button>Post comment</button></form>""")
        if parsed.path == "/search":
            # Intentional reflected XSS for local training.
            term = q.get("q", [""])[0]
            return self.send("<h1>Search</h1><p>Results for: " + term + "</p>")
        if parsed.path == "/comments":
            conn = db()
            rows = conn.execute("select body from comments order by id desc").fetchall() if self.comments_table(conn) else []
            return self.send("<h1>Comments</h1>" + "".join("<p>" + r[0] + "</p>" for r in rows))
        if parsed.path == "/users":
            # Intentional IDOR: no authorization check on numeric object id.
            uid = q.get("id", ["1"])[0]
            conn = db()
            row = conn.execute("select id, username, role, secret from users where id = ?", (uid,)).fetchone()
            if not row:
                return self.send("not found", 404)
            return self.send(json.dumps(dict(row)), content_type="application/json")
        if parsed.path == "/download":
            # Intentional path traversal: training-only demonstration.
            name = q.get("file", ["README.md"])[0]
            try:
                with open(os.path.join(os.path.dirname(__file__), name), "r", encoding="utf-8") as f:
                    return self.send(f.read(), content_type="text/plain; charset=utf-8")
            except (OSError, UnicodeDecodeError):
                return self.send("not found", 404)
        return self.send("not found", 404)

    @staticmethod
    def comments_table(conn):
        conn.execute("create table if not exists comments (id integer primary key, body text)")
        return True

    def do_POST(self):
        if urlparse(self.path).path != "/comments":
            return self.send("not found", 404)
        length = int(self.headers.get("Content-Length", "0"))
        form = parse_qs(self.rfile.read(length).decode())
        body = form.get("comment", [""])[0]
        conn = db()
        self.comments_table(conn)
        # Intentional stored XSS: body is rendered without escaping.
        conn.execute("insert into comments(body) values (?)", (body,))
        conn.commit()
        self.send_response(303)
        self.send_header("Location", "/comments")
        self.end_headers()


if __name__ == "__main__":
    print(f"Local Pentest Lab listening on http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
