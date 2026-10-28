# StudyTrack starter project

## Included features
- Add assignments with subject and optional deadline
- Mark assignments pending/completed
- Delete assignments
- Record subject-wise assessment marks
- Calculate percentage and show a dashboard average
- Persist records using SQLAlchemy
- SQLite is used by default for local testing
- Set `DATABASE_URL` to use a hosted PostgreSQL database online

## Run locally
1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Create a virtual environment (optional but recommended):
   - Windows: `py -m venv .venv`
   - Windows PowerShell: `.venv\Scripts\Activate.ps1`
4. Install dependencies: `pip install -r requirements.txt`
5. Run: `python app.py`
6. Open `http://127.0.0.1:5000`

## Online deployment (free tier)
Suggested route: GitHub + Render free web service + Supabase free PostgreSQL.

1. Create a GitHub account and a new repository called `studytrack`.
2. Upload the contents of this folder to the repository (not the outer folder itself).
3. Create a Supabase project and copy its PostgreSQL connection string from project database settings. Use the direct or session-pooler URI compatible with your client. Keep the password private.
4. In Render, create a new Web Service and connect your GitHub repository.
5. Build command: `pip install -r requirements.txt`
6. Start command: `gunicorn app:app`
7. Add environment variable `DATABASE_URL` with the Supabase PostgreSQL connection string.
8. Add environment variable `SECRET_KEY` with a long random value.
9. Deploy and open the Render URL.

Important:
- Never commit database passwords or secret keys to GitHub.
- Render free web services can sleep when idle. Supabase free projects can pause after a week of low activity. Free tiers can change; check current terms.
- Do not use Render's free PostgreSQL for data you need to keep indefinitely: its free database currently expires after 30 days.
- This starter does not include user accounts. Do not enter real private student information. Anyone with the public link may be able to view or change records until authentication and access controls are added.
- For a classroom demo, use sample data only. Back up data you care about.
