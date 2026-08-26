VOID INTEL-V2 FINAL
Render build: pip install -r requirements.txt
Render start: gunicorn app:app
Health: /healthz
Set ADMIN_EMAIL, ADMIN_PASSWORD and SECRET_KEY in Render Environment Variables.
