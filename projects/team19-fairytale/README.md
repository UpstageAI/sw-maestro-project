# fairytale

Backend Phase 0 scaffold is available in `backend/app/main.py`.

Quick start:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
uvicorn app.main:app --reload --app-dir backend
```

Useful endpoints:

- `GET /api/v1/health`
- `GET /api/v1/health/db`

Supabase workflow:

```bash
supabase link --project-ref <project-ref> --password <db-password>
supabase db push
```
