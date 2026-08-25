HTML = '<!doctype html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>VOID INTEL-V2</title>\n<style>\nbody{margin:0;background:#050709;color:#eee;font-family:Arial}header{padding:18px 6%;background:#080b0e;border-bottom:1px solid #252b30;display:flex;justify-content:space-between;position:sticky;top:0}.g{color:#78ff00}nav a{color:#aaa;text-decoration:none;margin:0 8px}button{padding:12px 18px;border:0;border-radius:6px;font-weight:bold;cursor:pointer}.btn{background:#78ff00;color:#050709}main{max-width:1150px;margin:auto;padding:0 6%}.hero{padding:90px 0}.hero h1{font-size:clamp(60px,9vw,110px);line-height:.9}.muted{color:#90979d;max-width:750px}section{padding:60px 0;border-top:1px solid #20262b}.label{color:#78ff00;letter-spacing:3px;font-size:12px}h2{font-size:40px}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}.card,.result{background:#0b0f13;border:1px solid #283038;border-radius:9px;padding:22px}.wide{grid-column:1/-1}input{width:100%;padding:13px;background:#0b0f13;color:#fff;border:1px solid #303840;border-radius:6px;margin:8px 0 12px;box-sizing:border-box}.bar{height:8px;background:#20262b;border-radius:8px}.fill{height:100%;background:#78ff00;width:0}.modal{display:none;position:fixed;inset:0;background:#000d;align-items:center;justify-content:center}.box{background:#0b0f13;border:1px solid #303840;padding:25px;width:90%;max-width:420px}@media(max-width:800px){.grid{grid-template-columns:1fr}nav{display:none}}\n</style></head><body>\n<header><b><span class="g">VOID</span> INTEL-V2</b><nav><a href="#pc">PC INTEL</a><a href="#network">NETWORK</a><a href="#about">ABOUT</a></nav><button class="btn" onclick="openLogin()">LOGIN</button></header>\n<main>\n<div class="hero"><div class="label">INTELLIGENCE • DIAGNOSTICS • SECURITY</div><h1>VOID <span class="g">INTEL</span></h1><p class="muted">Fast authorized PC and network diagnostics with secure login and admin reporting.</p><button class="btn" onclick="scan()">RUN PC SCAN</button></div>\n<section id="pc"><div class="label">PC INTELLIGENCE</div><h2>PC Health</h2><div class="grid">\n<div class="card"><h3>CPU</h3><p id="cpu">Not scanned</p><div class="bar"><div id="cb" class="fill"></div></div></div>\n<div class="card"><h3>MEMORY</h3><p id="ram">Not scanned</p><div class="bar"><div id="rb" class="fill"></div></div></div>\n<div class="card"><h3>DEVICE</h3><p id="device">Not scanned</p></div>\n<div class="card wide"><h3>Diagnostic report</h3><div id="report" class="result">Run the scan.</div></div></div></section>\n<section id="network"><div class="label">NETWORK INTELLIGENCE</div><h2>IP Intelligence</h2><input id="ip" placeholder="Enter public IP address"><button class="btn" onclick="lookup()">ANALYZE IP</button><div id="ipResult" class="result">No IP analyzed.</div></section>\n<section><div class="label">SERVER HEALTH</div><h2>Service</h2><div class="grid"><div class="card"><h3>APPLICATION</h3><p class="g">ONLINE</p></div><div class="card"><h3>DATABASE</h3><p class="g">READY</p></div><div class="card"><h3>API</h3><p id="health">CHECKING...</p></div></div></section>\n<section id="about"><div class="label">ABOUT</div><h2>Authorized use</h2><p class="muted">Only inspect computers and networks you own or have permission to inspect. A normal webpage cannot silently read private Windows security data.</p></section>\n</main>\n<div id="modal" class="modal"><div class="box"><h2>VOID INTEL LOGIN</h2><input id="email" type="email" placeholder="Email"><input id="pw" type="password" placeholder="Password"><button class="btn" onclick="loginUser()">LOGIN</button> <button onclick="closeLogin()">CLOSE</button><p id="msg"></p></div></div>\n<script>\nconst e=s=>String(s??"").replace(/[&<>"\']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",\'"\':"&quot;","\'":"&#39;"}[c]));\nfunction openLogin(){modal.style.display="flex"}function closeLogin(){modal.style.display="none"}\nasync function loginUser(){msg.textContent="Signing in...";let r=await fetch("/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email:email.value,password:pw.value})});let d=await r.json();msg.textContent=d.message;if(d.success)setTimeout(()=>{closeLogin();d.admin?location="/admin":alert("Welcome to VOID INTEL-V2")},400)}\nfunction scan(){let c=navigator.hardwareConcurrency||0,m=navigator.deviceMemory||0;cpu.textContent=c?c+" logical CPU cores detected":"Not exposed";ram.textContent=m?m+" GB approximate device memory":"Not exposed";device.textContent=(navigator.platform||"Unknown")+" • "+(navigator.language||"Unknown");cb.style.width=Math.min(100,c*8)+"%";rb.style.width=Math.min(100,m*12)+"%";report.innerHTML="<b>Browser-visible PC intelligence</b><p>CPU cores: "+e(c||"Not exposed")+"</p><p>Approx memory: "+e(m?m+" GB":"Not exposed")+"</p><p>Platform: "+e(navigator.platform)+"</p><p>Language: "+e(navigator.language)+"</p><p>Online: "+(navigator.onLine?"YES":"NO")+"</p><p>Browser: "+e(navigator.userAgent)+"</p><p>Full Windows hardware, Defender and firewall diagnostics require a local client.</p>"}\nasync function lookup(){let v=ip.value.trim();if(!v)return ipResult.textContent="Enter an IP.";ipResult.textContent="Analyzing...";try{let d=await(await fetch("/api/ip?ip="+encodeURIComponent(v))).json();if(!d.success)return ipResult.textContent=d.message;ipResult.innerHTML="<b>IP:</b> "+e(d.ip)+"<br><b>Type:</b> "+e(d.type)+"<br><b>Country:</b> "+e(d.country)+"<br><b>City:</b> "+e(d.city)+"<br><b>Region:</b> "+e(d.region)+"<br><b>Timezone:</b> "+e(d.timezone)+"<br><b>Organization:</b> "+e(d.org)}catch(x){ipResult.textContent="Lookup failed."}}\nfetch("/healthz").then(r=>r.json()).then(d=>health.textContent=d.status.toUpperCase()).catch(()=>health.textContent="OFFLINE");\n</script></body></html>'
from flask import Flask,request,jsonify,session
from werkzeug.security import generate_password_hash,check_password_hash
import sqlite3,os,ipaddress,urllib.request,urllib.parse,json
from datetime import datetime,timezone
app=Flask(__name__)
app.secret_key=os.getenv("SECRET_KEY","CHANGE_THIS_IN_RENDER")
DB=os.getenv("DATABASE_PATH","void_intel.db")
def db():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;return c
def setup():
 c=db();c.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT UNIQUE,email TEXT UNIQUE,password_hash TEXT,is_admin INTEGER DEFAULT 0,created_at TEXT)")
 c.execute("CREATE TABLE IF NOT EXISTS activity(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT,action TEXT,created_at TEXT,ip TEXT)")
 ae=os.getenv("ADMIN_EMAIL","").strip().lower();ap=os.getenv("ADMIN_PASSWORD","")
 if ae and ap and not c.execute("SELECT id FROM users WHERE email=?",(ae,)).fetchone():
  c.execute("INSERT INTO users(username,email,password_hash,is_admin,created_at) VALUES(?,?,?,?,?)",("VOID_ADMIN",ae,generate_password_hash(ap),1,datetime.now(timezone.utc).isoformat()))
 c.commit();c.close()
setup()
def log(a):
 try:
  c=db();c.execute("INSERT INTO activity(username,action,created_at,ip) VALUES(?,?,?,?)",(session.get("username","guest"),a,datetime.now(timezone.utc).isoformat(),request.remote_addr));c.commit();c.close()
 except:pass
@app.get("/")
def home(): return HTML
@app.get("/healthz")
def health(): return jsonify(status="online",app="VOID INTEL-V2")
@app.post("/login")
def login():
 d=request.get_json() or {};em=str(d.get("email","")).strip().lower();pw=str(d.get("password",""))
 c=db();u=c.execute("SELECT * FROM users WHERE email=?",(em,)).fetchone();c.close()
 if not u or not check_password_hash(u["password_hash"],pw):return jsonify(success=False,message="Invalid email or password."),401
 session["user_id"]=u["id"];session["username"]=u["username"];session["is_admin"]=bool(u["is_admin"]);log("LOGIN")
 return jsonify(success=True,message="Login successful.",admin=bool(u["is_admin"]))
@app.get("/admin")
def admin():
 if not session.get("is_admin"):return "Administrator access required.",403
 c=db();us=c.execute("SELECT id,username,email,is_admin,created_at FROM users ORDER BY id DESC").fetchall();ac=c.execute("SELECT username,action,created_at FROM activity ORDER BY id DESC LIMIT 50").fetchall();c.close()
 rows="".join(f"<tr><td>{u['id']}</td><td>{u['username']}</td><td>{u['email']}</td><td>{'YES' if u['is_admin'] else 'NO'}</td><td>{u['created_at']}</td></tr>" for u in us)
 acts="".join(f"<tr><td>{a['username']}</td><td>{a['action']}</td><td>{a['created_at']}</td></tr>" for a in ac)
 return f"<html><body style='background:#050709;color:#eee;font:15px Arial;padding:30px'><h1>VOID INTEL ADMIN</h1><h2>Users ({len(us)})</h2><table border=1 cellpadding=8>{rows}</table><h2>Activity</h2><table border=1 cellpadding=8>{acts}</table></body></html>"
@app.get("/api/ip")
def ip():
 raw=request.args.get("ip","").strip()
 try:p=ipaddress.ip_address(raw)
 except:return jsonify(success=False,message="Invalid IP address."),400
 typ="Private" if p.is_private else "Loopback" if p.is_loopback else "Reserved" if p.is_reserved else "Public";o={"success":True,"ip":raw,"type":typ,"country":"","city":"","region":"","timezone":"","org":""}
 if typ=="Public":
  try:
   q=urllib.request.Request("https://ipwho.is/"+urllib.parse.quote(raw),headers={"User-Agent":"VOID-INTEL-V2"})
   with urllib.request.urlopen(q,timeout=4) as z:d=json.loads(z.read())
   if d.get("success"):o.update(country=d.get("country",""),city=d.get("city",""),region=d.get("region",""),timezone=(d.get("timezone") or {}).get("id",""),org=(d.get("connection") or {}).get("org",""))
  except:pass
 log("IP_LOOKUP");return jsonify(o)
if __name__=="__main__":app.run(host="0.0.0.0",port=int(os.getenv("PORT","5000")))
