from flask import Flask, request, redirect, session, render_template_string, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import platform
import socket
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.parse
import json
import ipaddress
from datetime import datetime


app = Flask(__name__)

app.secret_key = os.environ.get(
    "VOID_INTEL_SECRET",
    "change-this-secret-before-publishing"
)

DATABASE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "void_intel.db"
)


# ============================================================
# ADMIN CONFIGURATION
# ============================================================

ADMIN_EMAIL = os.environ.get(
    "VOID_INTEL_ADMIN_EMAIL",
    "admin@example.com"
)

ADMIN_PASSWORD = os.environ.get(
    "VOID_INTEL_ADMIN_PASSWORD",
    ""
)

ADMIN_PASSWORD_HASH = os.environ.get(
    "VOID_INTEL_ADMIN_PASSWORD_HASH",
    generate_password_hash(
        ADMIN_PASSWORD if ADMIN_PASSWORD else "change-me-now"
    )
)


# ============================================================
# DATABASE
# ============================================================

def database():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


def setup_database():

    db = database()

    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            email TEXT,
            ip_address TEXT,
            created_at TEXT NOT NULL
        )
    """)

    db.commit()
    db.close()


# ============================================================
# EVENT LOGGING
# ============================================================

def client_ip():

    value = request.headers.get(
        "X-Forwarded-For",
        request.remote_addr or ""
    )

    return value.split(",")[0].strip()


def log_event(event_type, email=None):

    try:

        db = database()

        db.execute(
            """
            INSERT INTO events
            (
                event_type,
                email,
                ip_address,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                event_type,
                email,
                client_ip(),
                datetime.utcnow().isoformat()
            )
        )

        db.commit()
        db.close()

    except Exception:
        pass


# ============================================================
# AUTHENTICATION
# ============================================================

def logged_in():

    return bool(
        session.get("user_id")
        or session.get("admin")
    )


# ============================================================
# SYSTEM COMMAND HELPER
# ============================================================

def safe_run(command, timeout=8):

    try:

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False
        )

        return result.stdout.strip()

    except Exception as error:

        return "Unavailable: " + str(error)


# ============================================================
# SIZE CONVERSION
# ============================================================

def bytes_to_gb(value):

    try:
        return round(
            value / (1024 ** 3),
            2
        )

    except Exception:
        return 0


# ============================================================
# LOCAL IP
# ============================================================

def get_local_ip():

    try:

        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        )

        sock.settimeout(2)

        sock.connect(
            ("8.8.8.8", 80)
        )

        ip = sock.getsockname()[0]

        sock.close()

        return ip

    except Exception:

        try:

            return socket.gethostbyname(
                socket.gethostname()
            )

        except Exception:

            return "Unavailable"


# ============================================================
# PUBLIC IP
# ============================================================

def get_public_ip():

    services = [
        "https://api.ipify.org?format=json",
        "https://api64.ipify.org?format=json"
    ]

    for url in services:

        try:

            with urllib.request.urlopen(
                url,
                timeout=5
            ) as response:

                data = json.loads(
                    response.read().decode("utf-8")
                )

                ip = data.get("ip")

                if ip:
                    return ip

        except Exception:
            continue

    return "Unavailable"


# ============================================================
# FIREWALL
# ============================================================

def get_firewall_status():

    if platform.system().lower() != "windows":

        return "Available on Windows only"

    output = safe_run(
        [
            "netsh",
            "advfirewall",
            "show",
            "allprofiles"
        ],
        timeout=10
    )

    if output.startswith("Unavailable:"):

        return output

    lower = output.lower()

    if "state" in lower and "on" in lower:

        return "ON"

    if "state" in lower and "off" in lower:

        return "OFF"

    return "Unknown"


# ============================================================
# DISK INFORMATION
# ============================================================

def get_disk_info():

    try:

        total, used, free = shutil.disk_usage(
            os.path.abspath(os.sep)
        )

        return {
            "total_gb": bytes_to_gb(total),
            "used_gb": bytes_to_gb(used),
            "free_gb": bytes_to_gb(free),
            "used_percent": round(
                (used / total) * 100,
                1
            ) if total else 0
        }

    except Exception:

        return {
            "total_gb": 0,
            "used_gb": 0,
            "free_gb": 0,
            "used_percent": 0
        }


# ============================================================
# NETWORK INTERFACES
# ============================================================

def get_network_interfaces():

    if platform.system().lower() == "windows":

        return safe_run(
            [
                "ipconfig",
                "/all"
            ],
            timeout=10
        )

    return safe_run(
        ["ifconfig"],
        timeout=10
    )


# ============================================================
# PROCESS COUNT
# ============================================================

def get_process_count():

    if platform.system().lower() == "windows":

        output = safe_run(
            ["tasklist"],
            timeout=10
        )

        if output.startswith("Unavailable:"):
            return None

        lines = [
            line
            for line in output.splitlines()
            if line.strip()
        ]

        return max(
            0,
            len(lines) - 3
        )

    output = safe_run(
        ["ps", "-e"],
        timeout=10
    )

    if output.startswith("Unavailable:"):
        return None

    return max(
        0,
        len(output.splitlines()) - 1
    )


# ============================================================
# UPTIME
# ============================================================

def get_uptime():

    try:

        if os.path.exists("/proc/uptime"):

            with open(
                "/proc/uptime",
                "r",
                encoding="utf-8"
            ) as file:

                seconds = float(
                    file.read().split()[0]
                )

            return time.strftime(
                "%Hh %Mm %Ss",
                time.gmtime(seconds)
            )

        if platform.system().lower() == "windows":

            output = safe_run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToString('o')"
                ],
                timeout=8
            )

            return output or "Unavailable"

        return "Unavailable"

    except Exception:

        return "Unavailable"


# ============================================================
# MEMORY
# ============================================================

def get_memory():

    try:

        import psutil

        memory = psutil.virtual_memory()

        return {
            "ram_total_gb": bytes_to_gb(
                memory.total
            ),
            "ram_available_gb": bytes_to_gb(
                memory.available
            ),
            "ram_used_percent": memory.percent
        }

    except Exception:

        return {
            "ram_total_gb": "Install psutil",
            "ram_available_gb": "Install psutil",
            "ram_used_percent": "Install psutil"
        }


# ============================================================
# COMPLETE PC SCAN
# ============================================================

def scan_pc():

    disk = get_disk_info()
    memory = get_memory()

    local_ip = get_local_ip()
    public_ip = get_public_ip()

    return {

        "scan_time":
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

        "computer_name":
            socket.gethostname(),

        "operating_system":
            platform.system(),

        "os_version":
            platform.release(),

        "os_build":
            platform.version(),

        "architecture":
            platform.machine(),

        "processor":
            platform.processor()
            or "Unavailable",

        "cpu_cores":
            os.cpu_count() or 0,

        "python_version":
            sys.version.split()[0],

        "ram_total_gb":
            memory["ram_total_gb"],

        "ram_available_gb":
            memory["ram_available_gb"],

        "ram_used_percent":
            memory["ram_used_percent"],

        "disk_total_gb":
            disk["total_gb"],

        "disk_used_gb":
            disk["used_gb"],

        "disk_free_gb":
            disk["free_gb"],

        "disk_used_percent":
            disk["used_percent"],

        "local_ip":
            local_ip,

        "public_ip":
            public_ip,

        "firewall":
            get_firewall_status(),

        "process_count":
            get_process_count(),

        "uptime":
            get_uptime(),

        "network_interfaces":
            get_network_interfaces()
    }


# ============================================================
# IP LOOKUP
# ============================================================

def ip_lookup(target):

    target = (target or "").strip()

    if not target:

        return {
            "success": False,
            "error":
                "Enter an IP address."
        }

    try:

        parsed = ipaddress.ip_address(
            target
        )

    except ValueError:

        return {
            "success": False,
            "error":
                "That is not a valid IP address."
        }


    if (
        parsed.is_private
        or parsed.is_loopback
        or parsed.is_reserved
        or parsed.is_link_local
    ):

        return {

            "success": True,

            "ip":
                target,

            "country":
                "Private/local network",

            "city":
                "Not publicly geolocated",

            "region":
                "Not publicly geolocated",

            "timezone":
                "Not publicly geolocated",

            "isp":
                "Private/local address",

            "organization":
                "Private/local address",

            "note":
                "Private IP addresses do not have public geographic information."
        }


    url = (
        "https://ipwho.is/"
        + urllib.parse.quote(
            target,
            safe=""
        )
    )

    try:

        with urllib.request.urlopen(
            url,
            timeout=8
        ) as response:

            data = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )


        if not data.get(
            "success",
            False
        ):

            return {

                "success": False,

                "error":
                    data.get(
                        "message",
                        "IP information was not found."
                    )
            }


        connection = (
            data.get("connection")
            or {}
        )

        timezone = (
            data.get("timezone")
            or {}
        )


        return {

            "success": True,

            "ip":
                data.get(
                    "ip",
                    target
                ),

            "country":
                data.get(
                    "country",
                    "Unknown"
                ),

            "country_code":
                data.get(
                    "country_code",
                    "Unknown"
                ),

            "region":
                data.get(
                    "region",
                    "Unknown"
                ),

            "city":
                data.get(
                    "city",
                    "Unknown"
                ),

            "postal":
                data.get(
                    "postal",
                    "Unknown"
                ),

            "latitude":
                data.get(
                    "latitude",
                    "Unknown"
                ),

            "longitude":
                data.get(
                    "longitude",
                    "Unknown"
                ),

            "timezone":
                timezone.get(
                    "id",
                    "Unknown"
                ),

            "utc":
                timezone.get(
                    "utc",
                    "Unknown"
                ),

            "isp":
                connection.get(
                    "isp",
                    "Unknown"
                ),

            "organization":
                connection.get(
                    "org",
                    "Unknown"
                ),

            "asn":
                connection.get(
                    "asn",
                    "Unknown"
                ),

            "domain":
                connection.get(
                    "domain",
                    "Unknown"
                )
        }


    except Exception as error:

        return {

            "success": False,

            "error":
                "The IP lookup service could not be reached.",

            "detail":
                str(error)
        }


# ============================================================
# VOID INTEL AI
# ============================================================

def local_ai(question):

    q = question.lower().strip()


    if not q:

        return (
            "Please enter a question."
        )


    if q in {
        "hi",
        "hello",
        "hey",
        "yo"
    }:

        return (
            "Hello. I am the VOID INTEL "
            "assistant. Ask me about the "
            "PC scanner, IP lookup, security, "
            "networking, Python or this project."
        )


    if (
        "who are you" in q
        or "what are you" in q
    ):

        return (
            "I am the VOID INTEL assistant. "
            "I can explain the information "
            "collected by this project and "
            "help with general technology "
            "questions."
        )


    if "what can you do" in q:

        return (
            "I can explain the PC scanner, "
            "IP information, firewall status, "
            "networking, the VOID INTEL login "
            "system, Python and basic security."
        )


    if (
        "scan" in q
        and "pc" in q
    ):

        return (
            "The PC scanner checks the computer "
            "running VOID INTEL. It can show "
            "the operating system, processor, "
            "CPU cores, RAM, storage, local IP, "
            "public IP, firewall status, uptime, "
            "process count and network information."
        )


    if (
        "ip" in q
        and (
            "country" in q
            or "location" in q
        )
    ):

        return (
            "For a public IP address, VOID INTEL "
            "uses an IP geolocation service to "
            "return available information such "
            "as country, region, city, timezone, "
            "ISP, organization and ASN. Private "
            "IP addresses do not have public "
            "geographic information."
        )


    if "public ip" in q:

        return (
            "A public IP is the address visible "
            "to internet services. VOID INTEL "
            "can obtain the current public IP "
            "using a public IP service."
        )


    if (
        "private ip" in q
        or "local ip" in q
    ):

        return (
            "A local or private IP identifies "
            "a device inside a local network. "
            "Common private ranges include "
            "10.x.x.x, 172.16.x.x through "
            "172.31.x.x, and 192.168.x.x."
        )


    if "firewall" in q:

        return (
            "On Windows, VOID INTEL checks "
            "the Windows firewall profile "
            "state using the built-in netsh "
            "command."
        )


    if (
        "ram" in q
        or "memory" in q
    ):

        return (
            "RAM is temporary working memory "
            "used by programs. VOID INTEL can "
            "show total RAM, available RAM and "
            "current RAM usage when psutil is installed."
        )


    if (
        "cpu" in q
        or "processor" in q
    ):

        return (
            "The CPU is the processor that "
            "executes instructions. VOID INTEL "
            "shows the processor description "
            "and number of logical CPU cores."
        )


    if (
        "disk" in q
        or "storage" in q
    ):

        return (
            "VOID INTEL shows the total, used "
            "and available storage on the main "
            "system drive."
        )


    if (
        "database" in q
        or "sqlite" in q
    ):

        return (
            "VOID INTEL uses SQLite to store "
            "users and security events. "
            "Passwords are stored as hashes "
            "rather than plain-text passwords."
        )


    if (
        "login" in q
        or "password" in q
    ):

        return (
            "VOID INTEL requires authentication "
            "before the application can be used. "
            "Passwords should be hashed and "
            "important secrets should be stored "
            "in environment variables."
        )


    if "flask" in q:

        return (
            "Flask is the Python web framework "
            "used by VOID INTEL. It handles the "
            "web pages, routes, sessions and APIs."
        )


    if "python" in q:

        return (
            "Python is the programming language "
            "used by VOID INTEL for the web server, "
            "system information, database and "
            "IP lookup functionality."
        )


    if "security" in q:

        return (
            "Good security practices include "
            "password hashing, secret environment "
            "variables, authentication, input "
            "validation, HTTPS when deployed and "
            "limiting server permissions."
        )


    if "country" in q:

        return (
            "Country information for public IP "
            "addresses comes from IP geolocation. "
            "It should not be treated as an exact "
            "physical location."
        )


    if (
        "time" in q
        or "timezone" in q
    ):

        return (
            "The timezone shown for a public IP "
            "comes from the IP geolocation service."
        )


    if "status" in q:

        return (
            "VOID INTEL is running and the "
            "authenticated application interface "
            "is active."
        )


    if "help" in q:

        return (
            "Try asking: What does the PC scanner "
            "check? What is a public IP? How does "
            "the firewall check work? What is RAM? "
            "What does SQLite do?"
        )


    return (
        "I can help with technology questions. "
        "Try asking me about the PC scan, IP "
        "lookup, country, firewall, RAM, CPU, "
        "storage, networking, Python, Flask, "
        "SQLite, login or security."
    )


# ============================================================
# MAIN PAGE
# ============================================================

PAGE = r"""
<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>VOID INTEL-V2</title>


<style>

* {
    box-sizing: border-box;
}


body {

    margin: 0;

    font-family:
        Arial,
        Helvetica,
        sans-serif;

    background: #f4f6f2;

    color: #101410;
}


header {

    background: #080b09;

    color: white;

    border-bottom:
        5px solid #25c56f;

    padding:
        18px 6%;

    display: flex;

    align-items: center;

    justify-content: space-between;

    position: sticky;

    top: 0;

    z-index: 20;
}


.logo {

    font-size: 28px;

    font-weight: 900;

    letter-spacing: 3px;
}


.logo span {

    color: #25c56f;
}


nav a {

    color: white;

    text-decoration: none;

    margin-left: 18px;

    font-weight: bold;
}


nav a:hover {

    color: #25c56f;
}


main {

    max-width: 1250px;

    margin: auto;

    padding:
        40px 22px;
}


.hero {

    background: white;

    border:
        1px solid #dce2dc;

    border-radius: 18px;

    padding: 45px;

    margin-bottom: 25px;

    box-shadow:
        0 10px 30px
        rgba(0,0,0,.06);
}


.hero h1 {

    margin: 0;

    font-size:
        clamp(
            52px,
            9vw,
            110px
        );

    line-height: .95;

    color: #111;
}


.hero h1 span {

    color: #25c56f;
}


.hero p {

    font-size: 18px;

    color: #566056;

    max-width: 800px;

    line-height: 1.7;
}


.badge {

    display: inline-block;

    padding:
        7px 12px;

    border-radius: 30px;

    background: #e6f8ed;

    color: #08753a;

    font-weight: bold;

    margin-bottom: 18px;
}


.grid {

    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(280px, 1fr)
        );

    gap: 20px;
}


.card {

    background: white;

    border:
        1px solid #dce2dc;

    border-radius: 16px;

    padding: 25px;

    box-shadow:
        0 8px 25px
        rgba(0,0,0,.05);
}


.card h2 {

    margin-top: 0;
}


button {

    background: #080b09;

    color: white;

    border:
        2px solid #25c56f;

    border-radius: 9px;

    padding:
        12px 18px;

    font-weight: bold;

    cursor: pointer;
}


button:hover {

    background: #25c56f;

    color: #07100a;
}


input,
textarea {

    width: 100%;

    padding: 13px;

    border:
        1px solid #bfc8bf;

    border-radius: 9px;

    background: #fbfcfb;

    color: #111;

    margin:
        8px 0 12px;
}


textarea {

    min-height: 120px;

    resize: vertical;
}


.result {

    margin-top: 15px;

    background: #f7faf7;

    border-left:
        5px solid #25c56f;

    border-radius: 8px;

    padding: 16px;

    white-space: pre-wrap;

    overflow: auto;
}


.info {

    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(190px, 1fr)
        );

    gap: 12px;

    margin-top: 15px;
}


.item {

    background: #f7faf7;

    border:
        1px solid #dce2dc;

    border-radius: 10px;

    padding: 13px;
}


.item small {

    display: block;

    color: #667166;

    margin-bottom: 5px;
}


.item strong {

    word-break: break-word;
}


footer {

    text-align: center;

    padding: 35px;

    margin-top: 30px;

    background: #080b09;

    color: #aab4aa;
}


@media(max-width:700px) {

    header {

        padding:
            15px 18px;

        align-items:
            flex-start;
    }


    nav {

        display: flex;

        flex-wrap: wrap;

        justify-content:
            flex-end;
    }


    nav a {

        margin:
            4px 0 4px 10px;
    }


    .hero {

        padding: 28px;
    }

}

</style>

</head>


<body>


<header>

<div class="logo">

VOID

<span>
INTEL-V2
</span>

</div>


<nav>

<a href="/">
HOME
</a>

<a href="#scan">
PC SCAN
</a>

<a href="#ip">
IP CHECK
</a>

<a href="#ai">
AI
</a>


{% if session.get("admin") %}

<a href="/admin">
ADMIN
</a>

{% endif %}


<a href="/logout">
LOGOUT
</a>

</nav>

</header>


<main>


<section class="hero">

<div class="badge">

TECHNOLOGY • DIAGNOSTICS • INTELLIGENCE

</div>


<h1>

VOID

<span>
INTEL-V2
</span>

</h1>


<p>

A classic technology dashboard for learning
about the computer running the application,
public IP information, networking,
system information and security basics.

</p>

</section>



<section class="grid">


<div
    class="card"
    id="scan"
>

<h2>
PC INFORMATION
</h2>


<p>

Scan this computer and display
detailed system information.

</p>


<button onclick="scanPC()">

START PC SCAN

</button>


<div
    id="scanStatus"
    class="result"
>

Ready to scan.

</div>


<div
    id="pcInfo"
    class="info"
></div>

</div>



<div
    class="card"
    id="ip"
>

<h2>
IP INTELLIGENCE
</h2>


<p>

Enter a public IP to display
available geographic and network
information.

</p>


<input
    id="ipInput"
    placeholder="Example: 8.8.8.8"
>


<button onclick="lookupIP()">

CHECK IP

</button>


<div
    id="ipStatus"
    class="result"
>

Enter an IP address.

</div>


<div
    id="ipInfo"
    class="info"
></div>

</div>

</section>



<section
    class="card"
    id="ai"
    style="margin-top:20px"
>

<h2>
VOID INTEL AI
</h2>


<p>

Ask the assistant about the project
or general technology topics.

</p>


<textarea
    id="question"
    placeholder="Ask something like: What does RAM do?"
></textarea>


<button onclick="askAI()">

ASK VOID INTEL

</button>


<div
    id="answer"
    class="result"
>

AI is ready.

</div>

</section>


</main>


<footer>

VOID INTEL-V2

<br>

Technology School Project • 2026

</footer>



<script>

function escapeHtml(value) {

    return value.replace(
        /[&<>"']/g,

        function(c) {

            return {

                "&": "&amp;",

                "<": "&lt;",

                ">": "&gt;",

                '"': "&quot;",

                "'": "&#039;"

            }[c];

        }
    );

}


function showInfo(
    target,
    data
) {

    const box =
        document.getElementById(target);


    box.innerHTML = "";


    Object.entries(data).forEach(
        function(entry) {

            const key = entry[0];

            const value = entry[1];


            if (
                value === null
                ||
                value === undefined
                ||
                value === ""
            ) {

                return;

            }


            const div =
                document.createElement(
                    "div"
                );


            div.className = "item";


            const label =
                key
                    .replaceAll(
                        "_",
                        " "
                    )
                    .replace(
                        /\b\w/g,
                        function(c) {
                            return c.toUpperCase();
                        }
                    );


            div.innerHTML =

                "<small>"
                +
                escapeHtml(label)
                +
                "</small>"
                +
                "<strong>"
                +
                escapeHtml(
                    String(value)
                )
                +
                "</strong>";


            box.appendChild(div);

        }
    );

}


async function scanPC() {

    const status =
        document.getElementById(
            "scanStatus"
        );


    status.textContent =
        "Scanning this PC...";


    try {

        const response =
            await fetch(
                "/api/pc-scan"
            );


        const data =
            await response.json();


        if (!data.success) {

            status.textContent =
                data.error
                ||
                "PC scan failed.";

            return;
        }


        status.textContent =
            "PC scan completed.";


        showInfo(
            "pcInfo",
            data.system
        );


    } catch (error) {

        status.textContent =
            "PC scan failed: "
            +
            error.message;

    }

}



async function lookupIP() {

    const ip =
        document
            .getElementById(
                "ipInput"
            )
            .value
            .trim();


    const status =
        document.getElementById(
            "ipStatus"
        );


    status.textContent =
        "Looking up IP...";


    try {

        const response =
            await fetch(
                "/api/ip-lookup",
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body:
                        JSON.stringify({
                            ip: ip
                        })

                }
            );


        const data =
            await response.json();


        if (!data.success) {

            status.textContent =
                data.error
                ||
                "IP lookup failed.";

            document
                .getElementById(
                    "ipInfo"
                )
                .innerHTML = "";

            return;

        }


        status.textContent =
            "IP lookup completed.";


        showInfo(
            "ipInfo",
            data
        );


    } catch (error) {

        status.textContent =
            "IP lookup failed: "
            +
            error.message;

    }

}



async function askAI() {

    const question =
        document
            .getElementById(
                "question"
            )
            .value
            .trim();


    const answer =
        document.getElementById(
            "answer"
        );


    if (!question) {

        answer.textContent =
            "Please enter a question.";

        return;
    }


    answer.textContent =
        "VOID INTEL is thinking...";


    try {

        const response =
            await fetch(
                "/api/ai",
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body:
                        JSON.stringify({
                            question:
                                question
                        })

                }
            );


        const data =
            await response.json();


        answer.textContent =
            data.answer
            ||
            "No answer returned.";


    } catch (error) {

        answer.textContent =
            "AI request failed: "
            +
            error.message;

    }

}

</script>


</body>

</html>
"""


# ============================================================
# LOGIN PAGE
# ============================================================

LOGIN_PAGE = r"""

<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width,initial-scale=1"
>

<title>
VOID INTEL LOGIN
</title>


<style>

body {

    margin: 0;

    background: #f4f6f2;

    color: #101410;

    font-family: Arial;
}


.box {

    max-width: 450px;

    margin:
        70px auto;

    padding: 35px;

    background: white;

    border:
        1px solid #dce2dc;

    border-radius: 18px;

    box-shadow:
        0 12px 35px
        rgba(0,0,0,.08);
}


.logo {

    text-align: center;

    font-size: 30px;

    font-weight: 900;

    letter-spacing: 3px;

    margin-bottom: 30px;
}


.logo span {

    color: #25c56f;
}


input {

    width: 100%;

    box-sizing: border-box;

    padding: 13px;

    margin:
        8px 0 15px;

    border:
        1px solid #bfc8bf;

    border-radius: 8px;
}


button {

    width: 100%;

    padding: 14px;

    background: #080b09;

    color: white;

    border:
        2px solid #25c56f;

    border-radius: 8px;

    font-weight: bold;

    cursor: pointer;
}


button:hover {

    background: #25c56f;

    color: #07100a;
}


.error {

    background: #fff0f0;

    border:
        1px solid #e2b4b4;

    padding: 12px;

    border-radius: 8px;

    margin-bottom: 15px;
}


.message {

    margin-top: 15px;

    color: #08753a;
}


hr {

    border: 0;

    border-top:
        1px solid #dce2dc;

    margin: 30px 0;
}


a {

    color: #08753a;

}

</style>

</head>


<body>


<div class="box">


<div class="logo">

VOID

<span>
INTEL-V2
</span>

</div>


<h1>
Login
</h1>


{% if error %}

<div class="error">

{{ error }}

</div>

{% endif %}


<form method="POST">


<input
    type="email"
    name="email"
    placeholder="Email"
    required
>


<input
    type="password"
    name="password"
    placeholder="Password"
    required
>


<button type="submit">

LOGIN

</button>


</form>


<hr>


<h2>
Create Account
</h2>


<form id="signup">


<input
    type="email"
    id="signupEmail"
    placeholder="Email"
    required
>


<input
    type="password"
    id="signupPassword"
    placeholder="Password — 8+ characters"
    minlength="8"
    required
>


<button type="submit">

SIGN UP

</button>


</form>


<div
    id="message"
    class="message"
></div>


<p>

<a href="/">

Back to VOID INTEL

</a>

</p>


</div>



<script>

document
    .getElementById(
        "signup"
    )
    .addEventListener(
        "submit",
        async function(event) {

            event.preventDefault();


            const email =
                document
                    .getElementById(
                        "signupEmail"
                    )
                    .value
                    .trim();


            const password =
                document
                    .getElementById(
                        "signupPassword"
                    )
                    .value;


            const message =
                document
                    .getElementById(
                        "message"
                    );


            if (!email.includes("@")) {

                message.textContent =
                    "Enter a valid email.";

                return;

            }


            if (password.length < 8) {

                message.textContent =
                    "Password must have at least 8 characters.";

                return;

            }


            try {

                const response =
                    await fetch(
                        "/signup",
                        {

                            method: "POST",

                            headers: {

                                "Content-Type":
                                    "application/json"

                            },

                            body:
                                JSON.stringify({
                                    email: email,
                                    password: password
                                })

                        }
                    );


                const data =
                    await response.json();


                message.textContent =
                    data.message;


            } catch (error) {

                message.textContent =
                    "Could not connect to VOID INTEL.";

            }

        }
    );

</script>


</body>

</html>

"""


# ============================================================
# ADMIN PAGE
# ============================================================

ADMIN_PAGE = r"""

<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width,initial-scale=1"
>

<title>
VOID INTEL ADMIN
</title>


<style>

body {

    margin: 0;

    background: #f4f6f2;

    color: #101410;

    font-family: Arial;
}


header {

    padding:
        18px 6%;

    background: #080b09;

    color: white;

    border-bottom:
        5px solid #25c56f;

    display: flex;

    justify-content:
        space-between;
}


header a {

    color: white;

    margin-left: 18px;
}


main {

    max-width: 1200px;

    margin: auto;

    padding:
        50px 22px;
}


.stats {

    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(220px, 1fr)
        );

    gap: 20px;
}


.stat,
.events {

    background: white;

    border:
        1px solid #dce2dc;

    border-radius: 15px;

    padding: 25px;

    margin-bottom: 25px;
}


strong {

    font-size: 40px;

    display: block;

    margin-top: 8px;

    color: #08753a;
}


.table {

    overflow: auto;
}


table {

    width: 100%;

    border-collapse:
        collapse;
}


th,
td {

    padding: 12px;

    border-bottom:
        1px solid #ddd;

    text-align: left;
}


th {

    color: #08753a;
}

</style>

</head>


<body>


<header>

<b>
VOID INTEL-V2 ADMIN
</b>


<div>

<a href="/">
HOME
</a>


<a href="/logout">
LOGOUT
</a>

</div>

</header>


<main>


<h1>
ADMIN DASHBOARD
</h1>


<div class="stats">


<div class="stat">

TOTAL USERS

<strong>
{{ user_count }}
</strong>

</div>


<div class="stat">

TOTAL EVENTS

<strong>
{{ event_count }}
</strong>

</div>


</div>



<div class="events">


<h2>
Recent Events
</h2>


<div class="table">


<table>


<tr>

<th>
Event
</th>

<th>
Email
</th>

<th>
IP
</th>

<th>
Time
</th>

</tr>


{% for event in events %}


<tr>

<td>
{{ event["event_type"] }}
</td>

<td>
{{ event["email"] or "-" }}
</td>

<td>
{{ event["ip_address"] or "-" }}
</td>

<td>
{{ event["created_at"] }}
</td>

</tr>


{% else %}


<tr>

<td colspan="4">

No events yet.

</td>

</tr>


{% endfor %}


</table>

</div>

</div>


</main>


</body>

</html>

"""


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    if not logged_in():

        return redirect("/login")

    return render_template_string(
        PAGE
    )


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "GET":

        if logged_in():

            return redirect("/")

        return render_template_string(
            LOGIN_PAGE
        )


    email = request.form.get(
        "email",
        ""
    ).strip().lower()


    password = request.form.get(
        "password",
        ""
    )


    if not email or not password:

        return render_template_string(
            LOGIN_PAGE,
            error=
                "Enter your email and password."
        )


    # ADMIN

    if (
        email == ADMIN_EMAIL.lower()
        and check_password_hash(
            ADMIN_PASSWORD_HASH,
            password
        )
    ):

        session.clear()

        session["admin"] = True

        session["admin_email"] = email

        log_event(
            "admin_login",
            email
        )

        return redirect("/")


    # USER

    db = database()


    user = db.execute(
        """
        SELECT *
        FROM users
        WHERE email = ?
        """,
        (email,)
    ).fetchone()


    db.close()


    if (
        user
        and check_password_hash(
            user["password_hash"],
            password
        )
    ):

        session.clear()

        session["user_id"] = user["id"]

        session["user_email"] = user["email"]

        log_event(
            "user_login",
            email
        )

        return redirect("/")


    log_event(
        "failed_login",
        email
    )


    return render_template_string(
        LOGIN_PAGE,
        error=
            "Invalid email or password."
    )


# ============================================================
# SIGNUP
# ============================================================

@app.route(
    "/signup",
    methods=["POST"]
)
def signup():

    data = request.get_json(
        silent=True
    ) or {}


    email = str(
        data.get(
            "email",
            ""
        )
    ).strip().lower()


    password = str(
        data.get(
            "password",
            ""
        )
    )


    if "@" not in email:

        return jsonify({
            "success": False,
            "message":
                "Enter a valid email."
        }), 400


    if len(password) < 8:

        return jsonify({
            "success": False,
            "message":
                "Password must have at least 8 characters."
        }), 400


    db = database()


    try:

        db.execute(
            """
            INSERT INTO users
            (
                email,
                password_hash,
                created_at
            )
            VALUES (?, ?, ?)
            """,
            (
                email,
                generate_password_hash(
                    password
                ),
                datetime.utcnow().isoformat()
            )
        )


        db.commit()


    except sqlite3.IntegrityError:

        db.close()


        return jsonify({
            "success": False,
            "message":
                "That account already exists."
        }), 409


    db.close()


    log_event(
        "signup",
        email
    )


    return jsonify({

        "success": True,

        "message":
            "Account created successfully. "
            "You can now log in."

    })


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    email = (
        session.get("admin_email")
        or
        session.get("user_email")
    )


    if email:

        log_event(
            "logout",
            email
        )


    session.clear()


    return redirect("/login")


# ============================================================
# ADMIN
# ============================================================

@app.route("/admin")
def admin():

    if not session.get("admin"):

        return redirect("/login")


    db = database()


    user_count = db.execute(
        """
        SELECT COUNT(*) AS total
        FROM users
        """
    ).fetchone()["total"]


    event_count = db.execute(
        """
        SELECT COUNT(*) AS total
        FROM events
        """
    ).fetchone()["total"]


    events = db.execute(
        """
        SELECT *
        FROM events
        ORDER BY id DESC
        LIMIT 100
        """
    ).fetchall()


    db.close()


    return render_template_string(
        ADMIN_PAGE,
        user_count=user_count,
        event_count=event_count,
        events=events
    )


# ============================================================
# PC SCAN API
# ============================================================

@app.route("/api/pc-scan")
def api_pc_scan():

    if not logged_in():

        return jsonify({

            "success": False,

            "error":
                "Login required."

        }), 401


    try:

        result = scan_pc()


        log_event(
            "pc_scan",
            session.get(
                "admin_email"
            )
            or
            session.get(
                "user_email"
            )
        )


        return jsonify({

            "success": True,

            "system": result

        })


    except Exception as error:

        return jsonify({

            "success": False,

            "error":
                "PC scan failed: "
                + str(error)

        }), 500


# ============================================================
# IP LOOKUP API
# ============================================================

@app.route(
    "/api/ip-lookup",
    methods=["POST"]
)
def api_ip_lookup():

    if not logged_in():

        return jsonify({

            "success": False,

            "error":
                "Login required."

        }), 401


    data = request.get_json(
        silent=True
    ) or {}


    result = ip_lookup(
        data.get(
            "ip",
            ""
        )
    )


    if result.get("success"):

        log_event(
            "ip_lookup",
            session.get(
                "admin_email"
            )
            or
            session.get(
                "user_email"
            )
        )


    return jsonify(
        result
    )


# ============================================================
# AI API
# ============================================================

@app.route(
    "/api/ai",
    methods=["POST"]
)
def api_ai():

    if not logged_in():

        return jsonify({

            "answer":
                "Please log in before using VOID INTEL AI."

        }), 401


    data = request.get_json(
        silent=True
    ) or {}


    question = str(
        data.get(
            "question",
            ""
        )
    ).strip()


    answer = local_ai(
        question
    )


    return jsonify({

        "answer":
            answer

    })


# ============================================================
# START
# ============================================================

setup_database()


if __name__ == "__main__":

    print("")

    print(
        "==================================="
    )

    print(
        "          VOID INTEL-V2"
    )

    print(
        "==================================="
    )

    print("")

    print("Server:")

    print(
        "http://VOID-INTEL-V2:5000"
    )

    print("")

    print(
        "Login is required before using the app."
    )

    print("")

    print(
        "Press CTRL+C to stop."
    )

    print("")


    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )