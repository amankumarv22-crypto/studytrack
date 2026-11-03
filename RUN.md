# StudyTrack - Aman Verma

## Run on your computer
    py -m venv .venv
    .venv\\Scripts\\activate
    pip install -r requirements.txt
    python app.py
Open http://127.0.0.1:5000 and press "Try the demo".

## Run online (Render)
1. Upload these files to GitHub.
2. Render: build `pip install -r requirements.txt`, start `gunicorn app:app`.
3. Environment variables: DATABASE_URL (Supabase pooler string), SECRET_KEY (long random text), PYTHON_VERSION 3.11.9.
