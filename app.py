from flask import Flask, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import platform
import socket
import shutil
import subprocess
import ipaddress
import urllib.request
import urllib.parse
import json
from datetime import datetime, timezone

try:
    import pycountry
except ImportError:
    pycountry = None

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")
DATABASE = os.environ.get("DATABASE_PATH", "void_intel.db")


def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


def init_database():
    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            action TEXT NOT NULL,
            created_at TEXT NOT NULL,
            ip_address TEXT
        )
    """)

    db.commit()

    admin_email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "")

    if admin_email and admin_password:
        existing = db.execute(
            "SELECT id FROM users WHERE email = ?",
            (admin_email,)
        ).fetchone()

        if existing is None:
            db.execute(
                """
                INSERT INTO users
                (username, email, password_hash, is_admin, created_at)
                VALUES (?, ?, ?, 1, ?)
                """,
                (
                    "VOID_ADMIN",
                    admin_email,
                    generate_password_hash(admin_password),
                    datetime.now(timezone.utc).isoformat()
                )
            )
            db.commit()

    db.close()


init_database()


def client_ip():
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


def log_activity(action, user_id=None, username=None):
    try:
        db = get_db()
        db.execute(
            """
            INSERT INTO activity
            (user_id, username, action, created_at, ip_address)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                username,
                action,
                datetime.now(timezone.utc).isoformat(),
                client_ip()
            )
        )
        db.commit()
        db.close()
    except Exception:
        pass


def admin_required():
    return bool(session.get("is_admin"))


def country_search(search):
    results = []

    if pycountry is None:
        return results

    search = search.strip().lower()

    for country in pycountry.countries:
        name = getattr(country, "name", "")
        alpha2 = getattr(country, "alpha_2", "")
        alpha3 = getattr(country, "alpha_3", "")
        numeric = getattr(country, "numeric", "")

        if not search or (
            search in name.lower()
            or search == alpha2.lower()
            or search == alpha3.lower()
            or search == numeric.lower()
        ):
            results.append({
                "name": name,
                "code": alpha2,
                "code3": alpha3,
                "numeric": numeric
            })

    return results


PAGE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>VOID INTEL-V2</title>

<style>
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{background:#050607;color:#f0f0f0;font-family:Arial,Helvetica,sans-serif;line-height:1.6}
header{position:fixed;top:0;left:0;width:100%;height:72px;display:flex;align-items:center;justify-content:space-between;padding:0 6%;background:rgba(5,6,7,.97);border-bottom:1px solid #24282d;z-index:1000}
.logo{font-size:20px;font-weight:800;letter-spacing:1px}.green{color:#7cff00}
nav{display:flex;gap:24px}nav a{color:#aaa;text-decoration:none;font-size:14px}nav a:hover{color:#7cff00}
button{cursor:pointer;font-weight:700}
.header-login,.primary-button{background:#7cff00;color:#050607;border:1px solid #7cff00;border-radius:5px;padding:11px 20px}
.secondary-button{background:transparent;color:#fff;border:1px solid #444;border-radius:5px;padding:11px 20px}
.hero{min-height:100vh;display:flex;align-items:center;padding:130px 8% 100px;background:radial-gradient(circle at 50% 45%,rgba(70,130,0,.18),transparent 42%)}
.hero-content{max-width:1000px}.label{color:#7cff00;font-size:12px;letter-spacing:4px;margin-bottom:20px}
.hero h1{font-size:clamp(60px,10vw,125px);line-height:.9;letter-spacing:-6px;margin-bottom:35px}
.hero h1 span{color:#7cff00}.hero-description{max-width:720px;color:#9c9c9c;font-size:18px;margin-bottom:30px}
.buttons{display:flex;gap:15px}
section{padding:110px 8%;border-top:1px solid #1d2125}
.section-title{font-size:45px;margin-bottom:25px}.section-description{color:#888;max-width:750px;margin-bottom:30px}
.search-box{display:flex;max-width:900px}.search-box input{flex:1;margin:0;border-radius:5px 0 0 5px}.search-box button{width:140px;border:0;background:#7cff00;color:#050607;border-radius:0 5px 5px 0}
input{width:100%;background:#0b0e11;color:#fff;border:1px solid #292e33;border-radius:5px;padding:14px;margin-bottom:12px;outline:none}input:focus{border-color:#7cff00}
.result{max-width:1000px;margin-top:25px;padding:25px;background:#0b0e11;border:1px solid #292e33;border-radius:8px;color:#aaa}
.result h3{color:#7cff00;margin-bottom:12px}.result p{margin:7px 0}
.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px}
.card{background:#0b0e11;border:1px solid #292e33;border-radius:8px;padding:30px}.card h3{margin-bottom:12px}.card p{color:#888;margin-bottom:25px}
.card button{background:#7cff00;color:#050607;border:0;padding:11px 15px}
.country-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:15px;margin-top:20px}
.country-card{background:#080a0c;border:1px solid #252a30;border-radius:7px;padding:20px}.country-card h4{color:#7cff00;margin-bottom:8px}.country-card p{color:#888;font-size:14px}
.admin{display:none}table{width:100%;border-collapse:collapse;margin-top:20px}th,td{padding:12px;border-bottom:1px solid #292e33;text-align:left}th{color:#7cff00}td{color:#aaa}
.about-text{max-width:800px;color:#888}footer{border-top:1px solid #24282d;padding:40px 8%;color:#666}
.modal{display:none;position:fixed;inset:0;background:rgba(0,0,0,.88);align-items:center;justify-content:center;z-index:3000;padding:20px}
.modal-box{width:100%;max-width:460px;background:#0b0e11;border:1px solid #343a40;border-radius:10px;padding:30px;position:relative}
.modal-box h2{margin-bottom:20px}.close{position:absolute;right:15px;top:8px;background:transparent;border:0;color:#888;font-size:30px}.close:hover{color:#fff}
.full{width:100%}.message{min-height:25px;margin-top:10px;color:#7cff00}.error{color:#ff6666}hr{border:0;border-top:1px solid #292e33;margin:25px 0}
pre{white-space:pre-wrap;word-break:break-word;color:#777;margin-top:15px}.admin-buttons{display:flex;gap:10px;flex-wrap:wrap}
@media(max-width:900px){nav{display:none}.cards,.country-grid{grid-template-columns:1fr}.search-box{flex-direction:column}.search-box input{border-radius:5px;margin-bottom:10px}.search-box button{width:100%;padding:14px;border-radius:5px}.hero h1{font-size:65px;letter-spacing:-3px}.buttons{flex-direction:column}}
</style>
</head>

<body>

<header>
<div class="logo"><span class="green">VOID</span> INTEL-V2</div>
<nav>
<a href="#home">Home</a>
<a href="#intel">Intel</a>
<a href="#countries">Countries</a>
<a href="#system">System</a>
<a href="#about">About</a>
</nav>
<button class="header-login" onclick="openLogin()">Login</button>
</header>

<section id="home" class="hero">
<div class="hero-content">
<div class="label">INTELLIGENCE • DIAGNOSTICS • ANALYSIS</div>
<h1>VOID <span>INTEL-V2</span></h1>
<p class="hero-description">A modern intelligence and diagnostic dashboard for authorized network, country and system analysis.</p>
<div class="buttons">
<button class="primary-button" onclick="openLogin()">ACCESS VOID INTEL</button>
<button class="secondary-button" onclick="goTo('intel')">START SEARCH</button>
</div>
</div>
</section>

<section id="intel">
<div class="label">INTELLIGENCE SEARCH</div>
<h2 class="section-title">IP Intelligence</h2>
<p class="section-description">Enter an IP address to validate it and request coarse public network information.</p>
<div class="search-box">
<input id="ipInput" type="text" placeholder="Enter an IP address">
<button onclick="lookupIP()">SEARCH</button>
</div>
<div id="ipResult" class="result">Enter an IP address to begin.</div>
</section>

<section id="countries">
<div class="label">GLOBAL INTELLIGENCE</div>
<h2 class="section-title">Countries</h2>
<p class="section-description">Search by country name, two-letter code, three-letter code, or numeric code.</p>
<div class="search-box">
<input id="countryInput" type="text" placeholder="Example: Netherlands, NL, USA">
<button onclick="searchCountries()">SEARCH</button>
</div>
<div id="countryResult" class="result">Enter a country or country code.</div>
</section>

<section id="system">
<div class="label">DEVICE ANALYSIS</div>
<h2 class="section-title">System Diagnostics</h2>
<div class="cards">
<div class="card">
<h3>PC HEALTH</h3>
<p>Check CPU, memory, disk and operating-system information on the machine running the application.</p>
<button onclick="systemCheck()">RUN CHECK</button>
</div>
<div class="card">
<h3>FIREWALL</h3>
<p>Check the firewall status of the machine running the server.</p>
<button onclick="firewallCheck()">CHECK FIREWALL</button>
</div>
<div class="card">
<h3>VOID AI</h3>
<p>Get explanations about the diagnostic information.</p>
<button onclick="openAI()">OPEN AI</button>
</div>
</div>
<div id="systemResult" class="result">System results will appear here.</div>
</section>

<section id="adminSection" class="admin">
<div class="label">ADMINISTRATION</div>
<h2 class="section-title">VOID INTEL ADMIN</h2>
<div class="admin-buttons">
<button class="primary-button" onclick="loadAdminUsers()">USERS</button>
<button class="secondary-button" onclick="loadActivity()">ACTIVITY</button>
</div>
<div id="adminResult" class="result">Administrator controls.</div>
</section>

<section id="about">
<div class="label">ABOUT</div>
<h2 class="section-title">VOID INTEL-V2</h2>
<p class="about-text">VOID INTEL-V2 is a diagnostic and intelligence dashboard designed for authorized security, network and system analysis. Only inspect computers, networks and IP information that you own or have permission to inspect.</p>
</section>

<footer><span>VOID INTEL-V2</span><br>Authorized diagnostic use only.</footer>

<div id="loginModal" class="modal">
<div class="modal-box">
<button class="close" onclick="closeLogin()">×</button>
<h2>VOID INTEL LOGIN</h2>
<input id="loginEmail" type="email" placeholder="Email">
<input id="loginPassword" type="password" placeholder="Password">
<button class="primary-button full" onclick="login()">LOGIN</button>
<div id="loginMessage" class="message"></div>
<hr>
<h3>CREATE ACCOUNT</h3><br>
<input id="registerUsername" type="text" placeholder="Username">
<input id="registerEmail" type="email" placeholder="Email">
<input id="registerPassword" type="password" placeholder="Password">
<button class="secondary-button full" onclick="registerUser()">SIGN UP</button>
<div id="registerMessage" class="message"></div>
</div>
</div>

<div id="aiModal" class="modal">
<div class="modal-box">
<button class="close" onclick="closeAI()">×</button>
<h2>VOID AI</h2>
<p class="section-description">Ask a general question about the diagnostic information.</p>
<input id="aiQuestion" type="text" placeholder="Ask VOID AI">
<button class="primary-button full" onclick="askAI()">ASK VOID AI</button>
<div id="aiAnswer" class="message"></div>
</div>
</div>

<script>
function goTo(id){const e=document.getElementById(id);if(e)e.scrollIntoView({behavior:"smooth"})}
function openLogin(){document.getElementById("loginModal").style.display="flex"}
function closeLogin(){document.getElementById("loginModal").style.display="none"}

async function registerUser(){
const username=document.getElementById("registerUsername").value.trim();
const email=document.getElementById("registerEmail").value.trim();
const password=document.getElementById("registerPassword").value;
const message=document.getElementById("registerMessage");
if(!username||!email||!password){message.textContent="Please fill in all fields.";return}
if(!email.includes("@")){message.textContent="Enter a valid email address.";return}
if(password.length<8){message.textContent="Password must contain at least 8 characters.";return}
message.textContent="Creating account...";
try{
const r=await fetch("/register",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({username,email,password})});
const d=await r.json();message.textContent=d.message||"Done.";
}catch(e){message.textContent="Could not connect to server."}
}

async function login(){
const email=document.getElementById("loginEmail").value.trim();
const password=document.getElementById("loginPassword").value;
const message=document.getElementById("loginMessage");
if(!email||!password){message.textContent="Enter your email and password.";return}
message.textContent="Logging in...";
try{
const r=await fetch("/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email,password})});
const d=await r.json();
if(!d.success){message.textContent=d.message;return}
message.textContent="Login successful.";
setTimeout(()=>{
closeLogin();
if(d.admin){document.getElementById("adminSection").style.display="block";goTo("adminSection")}
else alert("Welcome to VOID INTEL-V2.");
},500);
}catch(e){message.textContent="Server connection failed."}
}

async function lookupIP(){
const ip=document.getElementById("ipInput").value.trim();
const result=document.getElementById("ipResult");
if(!ip){result.textContent="Please enter an IP address.";return}
result.textContent="Analyzing IP...";
try{
const r=await fetch("/api/ip?ip="+encodeURIComponent(ip));
const d=await r.json();
if(!d.success){result.innerHTML="<p class='error'>"+escapeHTML(d.message)+"</p>";return}
let html="<h3>IP INTELLIGENCE</h3><p><strong>IP:</strong> "+escapeHTML(d.ip)+"</p><p><strong>Type:</strong> "+escapeHTML(d.type)+"</p><p><strong>Valid:</strong> "+escapeHTML(d.valid)+"</p>";
if(d.network)html+="<p><strong>Network:</strong> "+escapeHTML(d.network)+"</p>";
if(d.live)html+="<hr><h3>PUBLIC NETWORK INFORMATION</h3><p><strong>Country:</strong> "+escapeHTML(d.country)+"</p><p><strong>Country Code:</strong> "+escapeHTML(d.country_code)+"</p><p><strong>City:</strong> "+escapeHTML(d.city)+"</p><p><strong>Region:</strong> "+escapeHTML(d.region)+"</p><p><strong>Timezone:</strong> "+escapeHTML(d.timezone)+"</p><p><strong>ISP / Organization:</strong> "+escapeHTML(d.org)+"</p>";
html+="<br><p>"+escapeHTML(d.note)+"</p>";
result.innerHTML=html;
}catch(e){result.innerHTML="<p class='error'>IP lookup failed.</p>"}
}

async function searchCountries(){
const search=document.getElementById("countryInput").value.trim();
const result=document.getElementById("countryResult");
result.textContent="Searching countries...";
try{
const r=await fetch("/api/countries?search="+encodeURIComponent(search));
const d=await r.json();
if(!d.success||d.countries.length===0){result.textContent="No country found.";return}
let html="<h3>COUNTRY RESULTS ("+d.count+")</h3><div class='country-grid'>";
d.countries.forEach(c=>{html+="<div class='country-card'><h4>"+escapeHTML(c.name)+"</h4><p>Code: "+escapeHTML(c.code)+"</p><p>Code 3: "+escapeHTML(c.code3)+"</p><p>Numeric: "+escapeHTML(c.numeric)+"</p></div>"});
html+="</div>";result.innerHTML=html;
}catch(e){result.textContent="Country search failed."}
}

async function systemCheck(){
const result=document.getElementById("systemResult");
result.textContent="Running diagnostics...";
try{
const r=await fetch("/api/system");const d=await r.json();
if(!d.success){result.textContent=d.message;return}
result.innerHTML="<h3>SYSTEM REPORT</h3><p><strong>Operating System:</strong> "+escapeHTML(d.system)+"</p><p><strong>Release:</strong> "+escapeHTML(d.release)+"</p><p><strong>Machine:</strong> "+escapeHTML(d.machine)+"</p><p><strong>CPU:</strong> "+escapeHTML(d.cpu_percent)+"%</p><p><strong>Memory:</strong> "+escapeHTML(d.memory_percent)+"% used</p><p><strong>Memory Total:</strong> "+escapeHTML(d.memory_total_gb)+" GB</p><p><strong>Memory Used:</strong> "+escapeHTML(d.memory_used_gb)+" GB</p><p><strong>Disk:</strong> "+escapeHTML(d.disk_used_gb)+" / "+escapeHTML(d.disk_total_gb)+" GB</p><p><strong>Disk Free:</strong> "+escapeHTML(d.disk_free_gb)+" GB</p>";
}catch(e){result.textContent="System check failed."}
}

async function firewallCheck(){
const result=document.getElementById("systemResult");
result.textContent="Checking firewall...";
try{
const r=await fetch("/api/firewall");const d=await r.json();
if(!d.success){result.textContent=d.message;return}
result.innerHTML="<h3>FIREWALL REPORT</h3><p><strong>Operating System:</strong> "+escapeHTML(d.platform)+"</p><p><strong>Status:</strong> "+escapeHTML(d.status)+"</p><pre>"+escapeHTML(d.details||"")+"</pre>";
}catch(e){result.textContent="Firewall check failed."}
}

function openAI(){document.getElementById("aiModal").style.display="flex"}
function closeAI(){document.getElementById("aiModal").style.display="none"}

function askAI(){
const q=document.getElementById("aiQuestion").value.trim().toLowerCase();
const a=document.getElementById("aiAnswer");
if(!q){a.textContent="Enter a question first.";return}
if(q.includes("cpu")||q.includes("processor"))a.textContent="CPU usage shows how much processor capacity is currently being used. Short spikes can be normal.";
else if(q.includes("memory")||q.includes("ram"))a.textContent="Memory usage shows how much RAM is currently being used by the system.";
else if(q.includes("firewall"))a.textContent="A firewall controls network traffic according to its configured rules.";
else if(q.includes("ip"))a.textContent="An IP address identifies a network endpoint. Public IP geolocation is approximate.";
else a.textContent="VOID AI can explain CPU, memory, firewall, disk and IP information.";
}

async function loadAdminUsers(){
const result=document.getElementById("adminResult");result.textContent="Loading users...";
try{
const r=await fetch("/api/admin/users");const d=await r.json();
if(!d.success){result.innerHTML="<p class='error'>"+escapeHTML(d.message)+"</p>";return}
let html="<h3>USERS: "+d.count+"</h3><table><tr><th>ID</th><th>Username</th><th>Email</th><th>Admin</th><th>Created</th></tr>";
d.users.forEach(u=>{html+="<tr><td>"+escapeHTML(u.id)+"</td><td>"+escapeHTML(u.username)+"</td><td>"+escapeHTML(u.email)+"</td><td>"+(u.is_admin?"YES":"NO")+"</td><td>"+escapeHTML(u.created_at)+"</td></tr>"});
html+="</table>";result.innerHTML=html;
}catch(e){result.textContent="Could not load users."}
}

async function loadActivity(){
const result=document.getElementById("adminResult");result.textContent="Loading activity...";
try{
const r=await fetch("/api/admin/activity");const d=await r.json();
if(!d.success){result.innerHTML="<p class='error'>"+escapeHTML(d.message)+"</p>";return}
let html="<h3>RECENT ACTIVITY</h3><table><tr><th>User</th><th>Action</th><th>Time</th></tr>";
d.activity.forEach(i=>{html+="<tr><td>"+escapeHTML(i.username||"Unknown")+"</td><td>"+escapeHTML(i.action)+"</td><td>"+escapeHTML(i.created_at)+"</td></tr>"});
html+="</table>";result.innerHTML=html;
}catch(e){result.textContent="Could not load activity."}
}

function escapeHTML(v){return String(v).replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;")}

window.addEventListener("click",function(e){
const lm=document.getElementById("loginModal"),am=document.getElementById("aiModal");
if(e.target===lm)closeLogin();
if(e.target===am)closeAI();
});

async function checkLogin(){
try{
const r=await fetch("/api/me");const d=await r.json();
if(d.logged_in&&d.admin)document.getElementById("adminSection").style.display="block";
}catch(e){}
}
checkLogin();
</script>
</body>
</html>
"""


@app.route("/")
def home():
    return PAGE


@app.route("/healthz")
def healthz():
    return jsonify({"status": "online", "application": "VOID INTEL-V2"}), 200


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not username or not email or not password:
        return jsonify({"success": False, "message": "All fields are required."}), 400

    if "@" not in email:
        return jsonify({"success": False, "message": "Enter a valid email address."}), 400

    if len(username) < 3:
        return jsonify({"success": False, "message": "Username must contain at least 3 characters."}), 400

    if len(password) < 8:
        return jsonify({"success": False, "message": "Password must contain at least 8 characters."}), 400

    db = get_db()
    existing = db.execute(
        "SELECT id FROM users WHERE username = ? OR email = ?",
        (username, email)
    ).fetchone()

    if existing:
        db.close()
        return jsonify({"success": False, "message": "Username or email already exists."}), 409

    cursor = db.execute(
        """
        INSERT INTO users
        (username, email, password_hash, is_admin, created_at)
        VALUES (?, ?, ?, 0, ?)
        """,
        (
            username,
            email,
            generate_password_hash(password),
            datetime.now(timezone.utc).isoformat()
        )
    )

    db.commit()
    user_id = cursor.lastrowid
    db.close()

    log_activity("ACCOUNT_CREATED", user_id, username)

    return jsonify({"success": True, "message": "Account created successfully."})


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE email = ?",
        (email,)
    ).fetchone()
    db.close()

    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify({"success": False, "message": "Invalid email or password."}), 401

    session.clear()
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["is_admin"] = bool(user["is_admin"])

    log_activity("LOGIN", user["id"], user["username"])

    return jsonify({
        "success": True,
        "message": "Login successful.",
        "admin": bool(user["is_admin"])
    })


@app.route("/logout")
def logout():
    if session.get("user_id"):
        log_activity("LOGOUT", session.get("user_id"), session.get("username"))
    session.clear()
    return jsonify({"success": True, "message": "Logged out."})


@app.route("/api/me")
def me():
    if "user_id" not in session:
        return jsonify({"logged_in": False})

    return jsonify({
        "logged_in": True,
        "username": session.get("username"),
        "admin": bool(session.get("is_admin"))
    })


@app.route("/api/ip")
def ip_lookup():
    raw_ip = request.args.get("ip", "").strip()

    if not raw_ip:
        return jsonify({"success": False, "message": "Enter an IP address."}), 400

    try:
        parsed = ipaddress.ip_address(raw_ip)
    except ValueError:
        return jsonify({"success": False, "message": "Invalid IP address."}), 400

    if parsed.is_loopback:
        ip_type = "Loopback"
    elif parsed.is_private:
        ip_type = "Private"
    elif parsed.is_reserved:
        ip_type = "Reserved"
    elif parsed.is_multicast:
        ip_type = "Multicast"
    else:
        ip_type = "Public"

    response = {
        "success": True,
        "ip": raw_ip,
        "valid": "YES",
        "type": ip_type,
        "network": None,
        "live": False,
        "country": "",
        "country_code": "",
        "city": "",
        "region": "",
        "timezone": "",
        "org": "",
        "note": "IP information is approximate and should not be used to determine a person's exact physical location."
    }

    if parsed.version == 4:
        try:
            response["network"] = str(ipaddress.ip_network(raw_ip + "/24", strict=False))
        except Exception:
            pass

    if ip_type == "Public":
        try:
            url = "https://ipwho.is/" + urllib.parse.quote(raw_ip, safe="")
            req = urllib.request.Request(url, headers={"User-Agent": "VOID-INTEL-V2"})

            with urllib.request.urlopen(req, timeout=5) as connection:
                live_data = json.loads(connection.read().decode("utf-8"))

            if live_data.get("success"):
                response["live"] = True
                response["country"] = live_data.get("country", "")
                response["country_code"] = live_data.get("country_code", "")
                response["city"] = live_data.get("city", "")
                response["region"] = live_data.get("region", "")
                response["timezone"] = (live_data.get("timezone") or {}).get("id", "")
                response["org"] = (live_data.get("connection") or {}).get("org", "")
        except Exception:
            response["note"] += " Live public-IP information was unavailable at this time."

    return jsonify(response)


@app.route("/api/countries")
def countries():
    search = request.args.get("search", "").strip()
    results = country_search(search)
    return jsonify({"success": True, "count": len(results), "countries": results})


@app.route("/api/system")
def system_info():
    try:
        import psutil

        memory = psutil.virtual_memory()
        disk = shutil.disk_usage("/")

        return jsonify({
            "success": True,
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "hostname": socket.gethostname(),
            "cpu_percent": psutil.cpu_percent(interval=0.5),
            "memory_percent": memory.percent,
            "memory_total_gb": round(memory.total / (1024 ** 3), 2),
            "memory_used_gb": round(memory.used / (1024 ** 3), 2),
            "disk_total_gb": round(disk.total / (1024 ** 3), 2),
            "disk_used_gb": round(disk.used / (1024 ** 3), 2),
            "disk_free_gb": round(disk.free / (1024 ** 3), 2)
        })
    except Exception:
        return jsonify({"success": False, "message": "System diagnostics failed."}), 500


@app.route("/api/firewall")
def firewall():
    operating_system = platform.system()

    try:
        if operating_system == "Windows":
            result = subprocess.run(
                ["netsh", "advfirewall", "show", "allprofiles"],
                capture_output=True,
                text=True,
                timeout=10
            )

            output = result.stdout.strip()
            status = "ACTIVE" if "STATE" in output.upper() and "ON" in output.upper() else "CHECK REQUIRED"

            return jsonify({
                "success": True,
                "platform": "Windows",
                "status": status,
                "details": output[:5000]
            })

        if operating_system == "Linux":
            try:
                result = subprocess.run(
                    ["ufw", "status"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                return jsonify({
                    "success": True,
                    "platform": "Linux",
                    "status": "CHECKED",
                    "details": result.stdout.strip()[:5000]
                })
            except FileNotFoundError:
                return jsonify({
                    "success": True,
                    "platform": "Linux",
                    "status": "UFW NOT INSTALLED",
                    "details": ""
                })

        return jsonify({
            "success": True,
            "platform": operating_system,
            "status": "Automatic firewall check unavailable.",
            "details": ""
        })

    except Exception:
        return jsonify({"success": False, "message": "Firewall check failed."}), 500


@app.route("/api/admin/users")
def admin_users():
    if not admin_required():
        return jsonify({"success": False, "message": "Administrator access required."}), 403

    db = get_db()
    users = db.execute(
        """
        SELECT id, username, email, is_admin, created_at
        FROM users
        ORDER BY id DESC
        """
    ).fetchall()
    db.close()

    return jsonify({
        "success": True,
        "count": len(users),
        "users": [dict(user) for user in users]
    })


@app.route("/api/admin/activity")
def admin_activity():
    if not admin_required():
        return jsonify({"success": False, "message": "Administrator access required."}), 403

    db = get_db()
    activity = db.execute(
        """
        SELECT id, username, action, created_at
        FROM activity
        ORDER BY id DESC
        LIMIT 100
        """
    ).fetchall()
    db.close()

    return jsonify({
        "success": True,
        "activity": [dict(item) for item in activity]
    })


@app.route("/api/admin/stats")
def admin_stats():
    if not admin_required():
        return jsonify({"success": False, "message": "Administrator access required."}), 403

    db = get_db()

    user_count = db.execute("SELECT COUNT(*) AS total FROM users").fetchone()["total"]
    admin_count = db.execute("SELECT COUNT(*) AS total FROM users WHERE is_admin = 1").fetchone()["total"]
    activity_count = db.execute("SELECT COUNT(*) AS total FROM activity").fetchone()["total"]

    db.close()

    return jsonify({
        "success": True,
        "users": user_count,
        "admins": admin_count,
        "activity": activity_count
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
