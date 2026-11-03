#!/usr/bin/env python3
"""Local-only intentionally vulnerable multi-page training application."""
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
import html
import json
import os
import sqlite3

HOST = "127.0.0.1"
PORT = int(os.environ.get("PORT", "8000"))
ROOT = os.path.dirname(__file__)
DB = os.path.join(ROOT, "lab.db")


def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
      create table if not exists users (id integer primary key, username text, role text, secret text, password text);
      create table if not exists comments (id integer primary key, body text, author text);
      create table if not exists orders (id integer primary key, user_id integer, item text, amount text, status text);
    """)
    # Upgrade databases created by the original minimal lab.
    columns = {r[1] for r in conn.execute("pragma table_info(users)")}
    if "password" not in columns:
        conn.execute("alter table users add column password text")
        conn.execute("update users set password = case username when 'alice' then 'alice123' else 'bob123' end")
    if "author" not in {r[1] for r in conn.execute("pragma table_info(comments)")}: conn.execute("alter table comments add column author text")
    if conn.execute("select count(*) from users").fetchone()[0] == 0:
        conn.executemany("insert into users(username, role, secret, password) values (?, ?, ?, ?)", [("alice", "viewer", "alice-training-secret", "alice123"), ("bob", "admin", "bob-admin-training-secret", "bob123")])
    if conn.execute("select count(*) from orders").fetchone()[0] == 0:
        conn.executemany("insert into orders(user_id, item, amount, status) values (?, ?, ?, ?)", [(1, "Security Starter Kit", "¥199", "Paid"), (2, "Admin Console License", "¥999", "Pending")])
    conn.commit()
    return conn


CSS = """
:root{font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#172033;background:#f4f7fb}*{box-sizing:border-box}body{margin:0}.top{height:64px;background:#10233f;color:white;display:flex;align-items:center;padding:0 32px;gap:28px}.brand{font-weight:800;letter-spacing:.3px}.nav{display:flex;gap:18px;flex:1}.nav a{color:#d6e3f5;text-decoration:none;font-size:14px}.nav a:hover{color:white}.pill{font-size:12px;border:1px solid #d5e1f0;padding:5px 9px;border-radius:999px;color:#eaf2ff}.wrap{max-width:1120px;margin:0 auto;padding:34px 24px 64px}.hero{background:white;border:1px solid #e3eaf4;border-radius:10px;padding:26px;margin-bottom:20px}.hero h1{margin:0 0 8px;font-size:28px}.muted{color:#66758b}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}.card{background:white;border:1px solid #e3eaf4;border-radius:9px;padding:20px}.card h2{font-size:18px;margin:0 0 8px}.card a{color:#0b66c3;text-decoration:none}.stat{font-size:28px;font-weight:800;margin:12px 0}.table{width:100%;border-collapse:collapse;background:white;border:1px solid #e3eaf4}.table th,.table td{text-align:left;padding:13px 14px;border-bottom:1px solid #edf1f6;font-size:14px}.table th{background:#f8fafc;color:#53637a}.button{display:inline-block;border:0;border-radius:6px;background:#1769c2;color:#fff;padding:10px 15px;text-decoration:none;cursor:pointer}.input,textarea{width:100%;padding:11px;border:1px solid #cbd7e6;border-radius:6px;font:inherit;margin:7px 0 13px}.search{display:flex;gap:10px;max-width:600px}.search .input{margin:0}.footer{margin-top:30px;color:#718198;font-size:12px}.tag{font-size:12px;background:#eef5ff;color:#2464a4;padding:4px 8px;border-radius:4px}
"""


def page(title, content, user=None):
    label = f"Signed in as {html.escape(user['username'])}" if user else "Guest"
    return f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{html.escape(title)} | Local Pentest Lab</title><style>{CSS}</style></head><body><header class='top'><div class='brand'>Local Pentest Lab</div><nav class='nav'><a href='/'>Dashboard</a><a href='/catalog'>Catalog</a><a href='/orders'>Orders</a><a href='/comments'>Community</a><a href='/files'>Files</a><a href='/admin'>Admin</a></nav><span class='pill'>{label}</span></header><main class='wrap'>{content}<div class='footer'>Intentionally vulnerable training application. Run locally or in an isolated lab only.</div></main></body></html>"


class Handler(BaseHTTPRequestHandler):
    server_version = "LocalPentestLab/2.0"

    def user(self):
        cookie = SimpleCookie(self.headers.get("Cookie", "")); item = cookie.get("user")
        return db().execute("select id, username, role, secret from users where username = ?", (item.value,)).fetchone() if item else None

    def send(self, body, status=200, content_type="text/html; charset=utf-8", headers=None):
        data = body.encode(); self.send_response(status); self.send_header("Content-Type", content_type); self.send_header("Content-Length", str(len(data)))
        for key, value in (headers or {}).items(): self.send_header(key, value)
        self.end_headers(); self.wfile.write(data)

    def redirect(self, location, headers=None):
        self.send_response(303); self.send_header("Location", location)
        for key, value in (headers or {}).items(): self.send_header(key, value)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path); q = parse_qs(parsed.query); user = self.user()
        if parsed.path == "/":
            conn = db(); counts = [conn.execute("select count(*) from users").fetchone()[0], conn.execute("select count(*) from orders").fetchone()[0], conn.execute("select count(*) from comments").fetchone()[0]]
            content = f"<section class='hero'><span class='tag'>INTERACTIVE TRAINING</span><h1>Security operations workspace</h1><p class='muted'>A multi-page application for testing crawling, sessions, forms and authorization checks.</p><form class='search' action='/search'><input class='input' name='q' placeholder='Search products, guides, tickets'><button class='button'>Search</button></form></section><div class='grid'><div class='card'><h2>Accounts</h2><div class='stat'>{counts[0]}</div><a href='/users?id=1'>Browse user profiles</a></div><div class='card'><h2>Orders</h2><div class='stat'>{counts[1]}</div><a href='/orders'>Review order history</a></div><div class='card'><h2>Community</h2><div class='stat'>{counts[2]}</div><a href='/comments'>Read and post comments</a></div></div>"
            return self.send(page("Dashboard", content, user))
        if parsed.path == "/login":
            content = "<section class='hero'><h1>Sign in</h1><p class='muted'>Training accounts: alice/alice123 or bob/bob123.</p><form method='post' action='/login'><label>Username<input class='input' name='username'></label><label>Password<input class='input' type='password' name='password'></label><button class='button'>Sign in</button></form></section>"
            return self.send(page("Login", content, user))
        if parsed.path == "/logout": return self.redirect("/", {"Set-Cookie": "user=; Max-Age=0; Path=/"})
        if parsed.path == "/search":
            term = q.get("q", [""])[0]
            # Intentional reflected XSS for local training.
            content = f"<section class='hero'><h1>Search results</h1><form class='search' action='/search'><input class='input' name='q' value='{html.escape(term, quote=True)}'><button class='button'>Search</button></form><p>Results for: {term}</p><p class='muted'>Try searching the catalog or help center.</p></section>"
            return self.send(page("Search", content, user))
        if parsed.path == "/catalog":
            content = "<section class='hero'><h1>Catalog</h1><p class='muted'>Training products and security guides.</p></section><div class='grid'><div class='card'><h2>Security Starter Kit</h2><p>Practical controls for small teams.</p><a class='button' href='/product?id=101'>View product</a></div><div class='card'><h2>Incident Playbook</h2><p>Response checklists and templates.</p><a class='button' href='/product?id=102'>View product</a></div></div>"
            return self.send(page("Catalog", content, user))
        if parsed.path == "/product":
            pid = q.get("id", ["101"])[0]; content = f"<section class='hero'><span class='tag'>PRODUCT {html.escape(pid)}</span><h1>Security Starter Kit</h1><p>Includes a sandbox checklist, sample policy and response cards.</p><a class='button' href='/orders?add={html.escape(pid)}'>Add to order</a></section>"
            return self.send(page("Product", content, user))
        if parsed.path == "/orders":
            rows = db().execute("select id, item, amount, status from orders order by id desc").fetchall(); body = "".join(f"<tr><td><a href='/order?id={r['id']}'>#{r['id']}</a></td><td>{html.escape(r['item'])}</td><td>{html.escape(r['amount'])}</td><td>{html.escape(r['status'])}</td></tr>" for r in rows)
            content = f"<section class='hero'><h1>Orders</h1><p class='muted'>Order history and account activity.</p></section><table class='table'><tr><th>Order</th><th>Item</th><th>Amount</th><th>Status</th></tr>{body}</table>"
            return self.send(page("Orders", content, user))
        if parsed.path == "/order":
            oid = q.get("id", ["1"])[0]; row = db().execute("select * from orders where id = ?", (oid,)).fetchone()
            if not row: return self.send("not found", 404)
            # Intentional IDOR: order ownership is not checked.
            content = f"<section class='hero'><h1>Order #{row['id']}</h1><p>Item: {html.escape(row['item'])}</p><p>Amount: {html.escape(row['amount'])}</p><p>Status: <span class='tag'>{html.escape(row['status'])}</span></p></section>"
            return self.send(page("Order detail", content, user))
        if parsed.path == "/comments":
            rows = db().execute("select body, author from comments order by id desc").fetchall(); body = "".join(f"<article class='card'><strong>{html.escape(r['author'] or 'guest')}</strong><p>{r['body']}</p></article>" for r in rows)
            # Intentional stored XSS: body is rendered without escaping.
            content = f"<section class='hero'><h1>Community</h1><form method='post' action='/comments'><label>Share a note<textarea name='comment' rows='4' placeholder='Write a comment'></textarea></label><button class='button'>Publish</button></form></section><div class='grid'>{body or '<p class=muted>No comments yet.</p>'}</div>"
            return self.send(page("Community", content, user))
        if parsed.path == "/users":
            uid = q.get("id", ["1"])[0]; row = db().execute("select id, username, role, secret from users where id = ?", (uid,)).fetchone()
            if not row: return self.send("not found", 404)
            # Intentional IDOR: no authorization check on numeric object id.
            if q.get("format", [""])[0] == "json": return self.send(json.dumps(dict(row)), content_type="application/json")
            content = f"<section class='hero'><h1>User profile</h1><p>Username: {html.escape(row['username'])}</p><p>Role: {html.escape(row['role'])}</p><p>Training secret: {html.escape(row['secret'])}</p></section>"
            return self.send(page("User profile", content, user))
        if parsed.path == "/files":
            content = "<section class='hero'><h1>File center</h1><p class='muted'>Download training resources.</p><ul><li><a href='/download?file=README.md'>README.md</a></li><li><a href='/download?file=app.py'>Application source</a></li></ul></section>"
            return self.send(page("Files", content, user))
        if parsed.path == "/download":
            # Intentional path traversal for local training.
            name = q.get("file", ["README.md"])[0]
            try:
                with open(os.path.join(ROOT, name), encoding="utf-8") as f: return self.send(f.read(), content_type="text/plain; charset=utf-8")
            except (OSError, UnicodeDecodeError): return self.send("not found", 404)
        if parsed.path == "/admin":
            # Intentional missing function-level authorization.
            content = "<section class='hero'><span class='tag'>ADMIN CONSOLE</span><h1>Operations control panel</h1><p>Manage users, exports and incident queues.</p><div class='grid'><a class='card' href='/users?id=2'><h2>User management</h2><p>Review account profiles</p></a><a class='card' href='/download?file=lab.db'><h2>Data export</h2><p>Download the training database</p></a></div></section>"
            return self.send(page("Admin", content, user))
        return self.send("not found", 404)

    def do_POST(self):
        parsed = urlparse(self.path); length = int(self.headers.get("Content-Length", "0")); form = parse_qs(self.rfile.read(length).decode())
        if parsed.path == "/login":
            row = db().execute("select username from users where username = ? and password = ?", (form.get("username", [""])[0], form.get("password", [""])[0])).fetchone()
            if row: return self.redirect("/", {"Set-Cookie": f"user={row['username']}; Path=/"})
            return self.send(page("Login failed", "<section class='hero'><h1>Login failed</h1><p>Check the training credentials and try again.</p><a class='button' href='/login'>Back to login</a></section>"), 401)
        if parsed.path == "/comments":
            body = form.get("comment", [""])[0]; user = self.user(); author = user["username"] if user else "guest"; conn = db(); conn.execute("insert into comments(body, author) values (?, ?)", (body, author)); conn.commit()
            return self.redirect("/comments")
        return self.send("not found", 404)


if __name__ == "__main__":
    print(f"Local Pentest Lab listening on http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
