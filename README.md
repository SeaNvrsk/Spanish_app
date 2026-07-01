# Español para la Familia 🌮

A mobile-first web app for learning **Mexican Spanish** as a family, from **A1 → A2 → B1**.
Personal accounts, XP & streaks, progress tracking, a family leaderboard, and
audio pronunciation with a Mexican accent.

- **Goal path:** A1 in 3 months · A2 in 6 months · B1 in 12 months
- **Works on phone & desktop** (responsive, installable as a PWA)
- **Interface languages:** English (default), Русский, Español — switch in Settings
- **Pronunciation:** browser `es-MX` voice for free, or high-quality AI Mexican voice with an OpenAI key

## Tech stack

| Layer     | Choice                                             |
| --------- | -------------------------------------------------- |
| Backend   | FastAPI + SQLAlchemy + SQLite (Postgres-ready)     |
| Frontend  | React + Vite + Tailwind CSS                        |
| Auth      | JWT (bcrypt password hashing)                      |
| Audio     | Web Speech API (`es-MX`) + optional OpenAI TTS     |
| Deploy    | gunicorn (uvicorn workers) behind nginx            |

## Quick start (local)

```bash
# one command starts backend (:8010) + frontend (:5173)
./dev.sh
# then open http://localhost:5173
```

Or run each side manually:

```bash
# Backend
cd backend
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
cp .env.example .env          # edit SECRET_KEY etc.
./.venv/bin/uvicorn app.main:app --reload --port 8010

# Frontend
cd frontend
npm install
npm run dev
```

Everyone in the family just signs up with their own email and starts learning —
they'll all appear together on the ranking screen.

## AI Mexican pronunciation (optional)

Free by default: the app uses the browser's built-in `es-MX` voice.

For a more natural Mexican accent, add an OpenAI key in `backend/.env`:

```
OPENAI_API_KEY=sk-...
OPENAI_TTS_MODEL=gpt-4o-mini-tts
OPENAI_TTS_VOICE=alloy
```

The backend proxies audio requests (the key is **never** exposed to the browser)
and instructs the model to speak in a warm, learner-friendly central-Mexican accent.

## Adding lessons

All content lives in `backend/app/curriculum/content.py` as simple vocab lists
(`spanish, english, russian`). Exercises (flashcards, listening, multiple choice,
typing) are generated automatically in `builder.py`. Add a unit or lesson there
and it instantly appears in the app.

## Production deploy (AWS, nginx + gunicorn)

```bash
# On the server (example paths under /opt/espanol)
cd /opt/espanol/backend
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
cp .env.example .env   # set a strong SECRET_KEY, CORS_ORIGINS, optional OPENAI_API_KEY

cd /opt/espanol/frontend
npm ci && npm run build      # produces frontend/dist served by nginx

# Service + reverse proxy
sudo cp deploy/espanol.service /etc/systemd/system/
sudo systemctl enable --now espanol
sudo cp deploy/nginx.conf.example /etc/nginx/sites-available/espanol
sudo ln -s /etc/nginx/sites-available/espanol /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Notes:
- `deploy/nginx.conf.example` includes TLS, security headers, gzip, asset caching
  and rate-limiting on the auth endpoints.
- With 4 cores, 4 gunicorn workers is a good starting point (already set in the unit file).
- To move from SQLite to PostgreSQL, set `DATABASE_URL` in `.env`
  (e.g. `postgresql+psycopg://user:pass@localhost/espanol`) and reinstall with the pg driver.

## Project layout

```
backend/
  app/
    main.py            # app + serves built frontend
    models.py          # User, LessonProgress, DailyActivity
    routers/           # auth, users, lessons, progress, stats, tts
    curriculum/        # content.py (vocab) + builder.py (exercise generator)
frontend/
  src/
    pages/             # Login, Dashboard, Lesson, Leaderboard, Profile
    components/        # TopBar, BottomNav
    i18n.jsx, auth.jsx, api.js, tts.js
deploy/                # systemd + nginx examples
```
