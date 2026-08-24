from flask import Flask, request, redirect, url_for, session, jsonify, render_template_string
import hashlib
import json
import os
import platform
import socket
import subprocess
import urllib.parse
import urllib.request

import psutil

APP_NAME = "VOID INTEL-V2"
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "LATINVOID@outlook.com")
# Admin password is read from an environment variable for security.
# Set ADMIN_PASSWORD in your environment or in a .env file (not committed).
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

app = Flask(__name__)
# Use an environment variable for the Flask secret key in production.
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "CHANGE_THIS_SECRET_BEFORE_PUBLIC_DEPLOYMENT")
USERS_FILE = "users.json"


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)


BASE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ app_name }}</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#05070b;color:#fff;font-family:Arial,sans-serif}
header{background:#090d14;padding:26px;text-align:center;border-bottom:1px solid #1f2937}
header h1{margin:0;font-size:42px;letter-spacing:6px}
header p{color:#9ca3af}
main{width:92%;max-width:1150px;margin:25px auto}
.panel,.box{background:#0b1018;border:1px solid #1f2937;border-radius:12px;padding:24px;margin-bottom:20px}
.box{width:470px;max-width:94%;margin:0 auto}
.center{min-height:100vh;display:flex;align-items:center;justify-content:center}
h2{color:#60a5fa}
label{display:block;color:#9ca3af;margin:12px 0 6px}
input{width:100%;background:#111827;color:#fff;border:1px solid #1f2937;border-radius:7px;padding:12px;margin-bottom:10px}
button,.button{display:inline-block;background:#2563eb;color:#fff;border:0;border-radius:7px;padding:12px 18px;cursor:pointer;text-decoration:none;font-weight:bold;margin:6px 4px 6px 0}
button:hover,.button:hover{background:#1d4ed8}
.secondary{background:#374151}
.error{background:#401010;color:#fca5a5;padding:10px;border-radius:7px;margin-bottom:12px}
.notice{color:#9ca3af;font-size:14px;line-height:1.6}
.score{text-align:center}
.scorevalue{font-size:60px;font-weight:bold;color:#4ade80}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:15px}
.card{background:#111827;border:1px solid #1f2937;padding:18px;border-radius:9px}
.card h3{color:#9ca3af;margin-top:0}
.value{color:#60a5fa;font-weight:bold;word-break:break-word}
pre{white-space:pre-wrap;background:#111827;padding:15px;border-radius:8px;min-height:60px}
.status{font-size:20px;font-weight:bold}
.good{color:#4ade80}.warning{color:#facc15}.bad{color:#f87171}
ul{line-height:1.8}
@media(max-width:750px){.grid{grid-template-columns:1fr}header h1{font-size:28px}}
</style>
</head>
<body>
{{ content|safe }}
</body>
</html>
"""


def page(content, **context):
    return render_template_string(
        BASE,
        content=render_template_string(content, **context),
        app_name=APP_NAME
    )


LOGIN = """
<div class="center">
<div class="box">
<h1>{{ app_name }}</h1>
<h2>LOGIN</h2>
{% if error %}<div class="error">{{ error }}</div>{% endif %}
<form method="post" action="/login">
<label>Email / Username</label>
<input name="username" required>
<label>Password</label>
<input name="password" type="password" required>
<button type="submit">LOGIN</button>
</form>
<a class="button secondary" href="/signup">CREATE ACCOUNT</a>
<a class="button secondary" href="/admin-login">ADMIN LOGIN</a>
</div>
</div>
"""

SIGNUP = """
<div class="center">
<div class="box">
<h1>{{ app_name }}</h1>
<h2>CREATE ACCOUNT</h2>
{% if error %}<div class="error">{{ error }}</div>{% endif %}
<form method="post">
<label>Username</label>
<input name="username" required>
<label>Password</label>
<input name="password" type="password" minlength="6" required>
<label>Confirm Password</label>
<input name="confirm" type="password" required>
<button type="submit">CREATE ACCOUNT</button>
</form>
<a class="button secondary" href="/">BACK TO LOGIN</a>
</div>
</div>
"""

ADMIN_LOGIN = """
<div class="center">
<div class="box">
<h1>{{ app_name }}</h1>
<h2>ADMIN LOGIN</h2>
{% if error %}<div class="error">{{ error }}</div>{% endif %}
<form method="post">
<label>Admin Email</label>
<input name="email" type="email" required>
<label>Admin Password</label>
<input name="password" type="password" required>
<button type="submit">ADMIN LOGIN</button>
</form>
<a class="button secondary" href="/">BACK</a>
</div>
</div>
"""

DASHBOARD = """
<header>
<h1>{{ app_name }}</h1>
<p>Personal PC Health & Diagnostic System</p>
<p>Welcome, {{ username }}</p>
<a class="button secondary" href="/logout">LOG OUT</a>
</header>

<main>

<section class="panel score">
<h2>🖥️ PC HEALTH</h2>
<div id="score" class="scorevalue">--%</div>
<p id="healthText">Press START PC SCAN.</p>
<button onclick="scanPC()">🔍 START PC SCAN</button>
</section>

<section class="panel">
<h2>💻 SYSTEM INFORMATION</h2>
<div class="grid">
<div class="card"><h3>Operating System</h3><div id="os" class="value">Not checked</div></div>
<div class="card"><h3>Computer Name</h3><div id="computer" class="value">Not checked</div></div>
<div class="card"><h3>Processor</h3><div id="processor" class="value">Not checked</div></div>
<div class="card"><h3>CPU Usage</h3><div id="cpu" class="value">Not checked</div></div>
<div class="card"><h3>RAM Usage</h3><div id="ram" class="value">Not checked</div></div>
<div class="card"><h3>Disk Usage</h3><div id="disk" class="value">Not checked</div></div>
<div class="card"><h3>Local IP</h3><div id="localip" class="value">Not checked</div></div>
<div class="card"><h3>Architecture</h3><div id="architecture" class="value">Not checked</div></div>
</div>
</section>

<section class="panel">
<h2>🛡️ FIREWALL CHECK</h2>
<button onclick="checkFirewall()">CHECK FIREWALL</button>
<p id="firewall" class="status">Not checked</p>
</section>

<section class="panel">
<h2>🌐 IP CHECK</h2>
<input id="ipInput" placeholder="Enter an IP or leave blank for your public IP">
<button onclick="checkIP()">CHECK IP</button>
<pre id="ipResult">No lookup yet.</pre>
<p class="notice">IP information is approximate. It does not reliably identify an exact home address or person.</p>
</section>

<section class="panel">
<h2>📁 FILE INFORMATION</h2>
<input type="file" id="fileInput">
<pre id="fileResult">Choose a file to view basic metadata. The file is not uploaded.</pre>
</section>

<section class="panel">
<h2>🤖 VOID INTEL AI ASSISTANT</h2>
<input id="question" placeholder="Ask about CPU, RAM, firewall, IP or files">
<button onclick="askAI()">ASK ASSISTANT</button>
<p id="aiAnswer">Ready.</p>
</section>

<section class="panel">
<h2>ℹ️ ABOUT</h2>
<p class="notice">
{{ app_name }} is a local diagnostic dashboard. Performance results are basic indicators
and do not prove that a computer is hacked or malware-free.
</p>
</section>

</main>

<script>
async function scanPC(){
    const response = await fetch("/api/health");
    const data = await response.json();
    if(data.error){ alert(data.error); return; }

    document.getElementById("os").textContent = data.os;
    document.getElementById("computer").textContent = data.computer;
    document.getElementById("processor").textContent = data.processor;
    document.getElementById("cpu").textContent = data.cpu + "%";
    document.getElementById("ram").textContent = data.ram + "%";
    document.getElementById("disk").textContent = data.disk + "%";
    document.getElementById("localip").textContent = data.ip;
    document.getElementById("architecture").textContent = data.architecture;
    document.getElementById("score").textContent = data.score + "%";

    if(data.score >= 80){
        document.getElementById("score").className = "scorevalue good";
        document.getElementById("healthText").textContent = "PC looks healthy ✓";
    }else if(data.score >= 60){
        document.getElementById("score").className = "scorevalue warning";
        document.getElementById("healthText").textContent = "Some things need attention ⚠";
    }else{
        document.getElementById("score").className = "scorevalue bad";
        document.getElementById("healthText").textContent = "PC needs attention ⚠";
    }
}

async function checkFirewall(){
    const response = await fetch("/api/firewall");
    const data = await response.json();
    const el = document.getElementById("firewall");
    el.textContent = "Firewall: " + data.status;
    el.className = "status " + (data.status === "ON" ? "good" : data.status === "OFF" ? "bad" : "warning");
}

async function checkIP(){
    const ip = document.getElementById("ipInput").value;
    const response = await fetch("/api/ip?ip=" + encodeURIComponent(ip));
    const data = await response.json();

    if(data.error){
        document.getElementById("ipResult").textContent = data.error;
        return;
    }

    document.getElementById("ipResult").textContent =
        "IP: " + data.ip +
        "\nCountry: " + data.country +
        "\nRegion: " + data.region +
        "\nApprox. City: " + data.city +
        "\nTimezone: " + data.timezone +
        "\nNetwork: " + data.network;
}

document.getElementById("fileInput").addEventListener("change", function(event){
    const file = event.target.files[0];
    if(!file) return;

    document.getElementById("fileResult").textContent =
        "Name: " + file.name +
        "\nType: " + (file.type || "Unknown") +
        "\nSize: " + file.size.toLocaleString() + " bytes" +
        "\nModified: " + new Date(file.lastModified).toLocaleString() +
        "\n\nThe file was not uploaded.";
});

function askAI(){
    const q = document.getElementById("question").value.toLowerCase();
    let answer =
        "I can explain PC health, CPU/RAM usage, firewall status, IP lookup limitations and file information.";

    if(q.includes("ram")){
        answer = "High RAM usage can happen when many programs or browser tabs are open. Task Manager can show which programs use the most memory.";
    }else if(q.includes("cpu")){
        answer = "High CPU usage can come from demanding programs, updates or background tasks. Task Manager can show which process is using the CPU.";
    }else if(q.includes("firewall")){
        answer = "A firewall controls network connections. VOID INTEL reports its status but does not change your firewall settings.";
    }else if(q.includes("ip")){
        answer = "An IP can provide approximate country, region, city, timezone and network information. It cannot reliably reveal an exact address or identity.";
    }else if(q.includes("file")){
        answer = "The file feature displays basic metadata such as name, type, size and modified time. The selected file is not uploaded by this feature.";
    }

    document.getElementById("aiAnswer").textContent = answer;
}
</script>
"""


ADMIN = """
<header>
<h1>{{ app_name }}</h1>
<p>👑 ADMIN DASHBOARD</p>
<a class="button secondary" href="/logout">LOG OUT</a>
</header>
<main>
<section class="panel">
<h2>REGISTERED ACCOUNTS</h2>
{% if users %}
<ul>
{% for user in users %}<li>{{ user }}</li>{% endfor %}
</ul>
{% else %}
<p>No customer accounts yet.</p>
{% endif %}
</section>
</main>
"""


@app.route("/")
def home():
    if session.get("admin"):
        return redirect(url_for("admin"))
    if session.get("user"):
        return redirect(url_for("dashboard"))
    return page(LOGIN, app_name=APP_NAME)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if len(username) < 3 or len(password) < 6:
            return page(
                SIGNUP,
                app_name=APP_NAME,
                error="Username needs at least 3 characters and password at least 6 characters."
            )

        if password != confirm:
            return page(SIGNUP, app_name=APP_NAME, error="Passwords do not match.")

        users = load_users()

        if username.lower() == ADMIN_EMAIL.lower() or username in users:
            return page(SIGNUP, app_name=APP_NAME, error="That account already exists.")

        users[username] = hash_password(password)
        save_users(users)
        return redirect(url_for("home"))

    return page(SIGNUP, app_name=APP_NAME)


@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    # Admin login will only succeed if ADMIN_PASSWORD is set in the environment.
    if ADMIN_PASSWORD and username.lower() == ADMIN_EMAIL.lower() and password == ADMIN_PASSWORD:
        session["admin"] = True
        return redirect(url_for("admin"))

    users = load_users()

    if username in users and users[username] == hash_password(password):
        session["user"] = username
        return redirect(url_for("dashboard"))

    return page(LOGIN, app_name=APP_NAME, error="Incorrect account details.")


@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if ADMIN_PASSWORD and email.lower() == ADMIN_EMAIL.lower() and password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin"))

        return page(ADMIN_LOGIN, app_name=APP_NAME, error="Invalid admin login.")

    return page(ADMIN_LOGIN, app_name=APP_NAME)


@app.route("/dashboard")
def dashboard():
    if not session.get("user"):
        return redirect(url_for("home"))

    return page(DASHBOARD, app_name=APP_NAME, username=session["user"])


@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    return page(ADMIN, app_name=APP_NAME, users=list(load_users().keys()))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/api/health")
def api_health():
    if not session.get("user"):
        return jsonify({"error": "Login required"}), 401

    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory().percent

    disk_path = os.environ.get("SystemDrive")
    if not disk_path:
        disk_path = os.path.abspath(os.sep)

    try:
        disk = psutil.disk_usage(disk_path).percent
    except Exception:
        disk = 0

    score = 100
    problems = []

    if cpu >= 90:
        score -= 30
        problems.append("CPU usage is very high.")
    elif cpu >= 75:
        score -= 15
        problems.append("CPU usage is elevated.")

    if ram >= 90:
        score -= 30
        problems.append("RAM usage is very high.")
    elif ram >= 75:
        score -= 15
        problems.append("RAM usage is elevated.")

    if disk >= 95:
        score -= 30
        problems.append("Disk usage is critically high.")
    elif disk >= 85:
        score -= 15
        problems.append("Disk usage is getting high.")

    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        local_ip = "Unknown"

    return jsonify({
        "os": f"{platform.system()} {platform.release()}",
        "computer": socket.gethostname(),
        "processor": platform.processor() or "Unknown",
        "cpu": round(cpu, 1),
        "ram": round(ram, 1),
        "disk": round(disk, 1),
        "ip": local_ip,
        "architecture": platform.machine(),
        "score": max(0, score),
        "problems": problems
    })


@app.route("/api/firewall")
def api_firewall():
    if not session.get("user"):
        return jsonify({"error": "Login required"}), 401

    if platform.system() != "Windows":
        return jsonify({"status": "Windows only"})

    try:
        result = subprocess.run(
            ["netsh", "advfirewall", "show", "allprofiles"],
            capture_output=True,
            text=True,
            timeout=10
        )

        output = result.stdout.upper()

        if "STATE" in output and "ON" in output:
            status = "ON"
        elif "STATE" in output and "OFF" in output:
            status = "OFF"
        else:
            status = "UNKNOWN"

        return jsonify({"status": status})
    except Exception:
        return jsonify({"status": "UNKNOWN"})


@app.route("/api/ip")
def api_ip():
    if not session.get("user"):
        return jsonify({"error": "Login required"}), 401

    ip = request.args.get("ip", "").strip()

    try:
        if not ip:
            with urllib.request.urlopen(
                "https://api.ipify.org?format=json", timeout=8
            ) as response:
                ip = json.loads(response.read().decode())["ip"]

        safe_ip = urllib.parse.quote(ip, safe="")

        with urllib.request.urlopen(
            f"https://ipapi.co/{safe_ip}/json/", timeout=8
        ) as response:
            data = json.loads(response.read().decode())

        return jsonify({
            "ip": ip,
            "country": data.get("country_name", "Unknown"),
            "region": data.get("region", "Unknown"),
            "city": data.get("city", "Unknown"),
            "timezone": data.get("timezone", "Unknown"),
            "network": data.get("org", "Unknown")
        })

    except Exception as exc:
        return jsonify({"error": f"IP lookup failed: {exc}"}), 400


@app.route("/healthz")
def healthz():
    return "OK", 200


if __name__ == "__main__":
    print("=" * 40)
    print("        VOID INTEL-V2")
    print("=" * 40)
    print("Open: http://127.0.0.1:5000")
    print("Press CTRL+C to stop.")
    app.run(host="127.0.0.1", port=5000, debug=False)
