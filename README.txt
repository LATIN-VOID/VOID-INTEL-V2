VOID INTEL-V2 COMPLETE ONE-FILE VERSION

The application code is all in app.py.

Install:
pip install -r requirements.txt

Run:
python app.py

Open:
http://127.0.0.1:5000

Admin:
Set the ADMIN_PASSWORD and FLASK_SECRET_KEY environment variables before running.

Features:
- Login
- Sign Up
- Admin Dashboard (requires ADMIN_PASSWORD env var)
- PC Health
- System Information
- Windows Firewall Check
- IP information lookup
- File metadata viewer
- Built-in basic AI assistant
- Logout
- /healthz endpoint for hosting

IMPORTANT:
- The admin password and Flask secret key must be provided via environment variables for safety.
- Before public release, replace the Flask secret key and keep credentials out of repository files. Add a .env file locally (do NOT commit it).
