import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import text, inspect

from .config import get_settings
from .database import Base, engine
from .routers import auth, users, lessons, progress, stats, tts, review, pronunciation, rewards, tools, profile, images

settings = get_settings()

Base.metadata.create_all(bind=engine)


def _ensure_columns():
    """Add columns introduced after the DB was first created (SQLite-safe)."""
    wanted = {
        "users": [
            ("carryover_pesos", "INTEGER NOT NULL DEFAULT 0"),
            ("is_admin", "INTEGER NOT NULL DEFAULT 0"),
        ],
        "daily_activity": [("review_xp", "INTEGER NOT NULL DEFAULT 0")],
    }
    insp = inspect(engine)
    with engine.begin() as conn:
        for table, cols in wanted.items():
            if not insp.has_table(table):
                continue
            existing = {c["name"] for c in insp.get_columns(table)}
            for name, ddl in cols:
                if name not in existing:
                    conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {ddl}'))

        # Mark configured admin account(s) — excluded from family competition stats.
        admin_emails = [e.strip().lower() for e in settings.admin_emails.split(",") if e.strip()]
        if admin_emails and insp.has_table("users"):
            placeholders = ", ".join(f":e{i}" for i in range(len(admin_emails)))
            params = {f"e{i}": e for i, e in enumerate(admin_emails)}
            conn.execute(
                text(f"UPDATE users SET is_admin = 1 WHERE lower(email) IN ({placeholders}) OR name = 'Anatolii'"),
                params,
            )


def _migrate_xp_to_pesos():
    """One-time conversion: legacy XP points → pesos (1 XP = 0.25 peso)."""
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS app_meta (key TEXT PRIMARY KEY, value TEXT)"))
        row = conn.execute(text("SELECT value FROM app_meta WHERE key='xp_to_pesos_v1'")).fetchone()
        if row and row[0] == "1":
            return
        conn.execute(text("UPDATE users SET xp = CAST(ROUND(xp * 0.25) AS INTEGER)"))
        conn.execute(text(
            "UPDATE daily_activity SET xp = CAST(ROUND(xp * 0.25) AS INTEGER), "
            "review_xp = CAST(ROUND(review_xp * 0.25) AS INTEGER)"
        ))
        conn.execute(text(
            "UPDATE lesson_progress SET xp_earned = CAST(ROUND(xp_earned * 0.25) AS INTEGER)"
        ))
        conn.execute(text(
            "INSERT OR REPLACE INTO app_meta (key, value) VALUES ('xp_to_pesos_v1', '1')"
        ))


def _drop_spanish_ui():
    """Spanish is no longer a UI language — keep Russian/English only."""
    with engine.begin() as conn:
        if not inspect(engine).has_table("users"):
            return
        conn.execute(text("UPDATE users SET ui_language = 'ru' WHERE ui_language = 'es'"))


_ensure_columns()
_migrate_xp_to_pesos()
_drop_spanish_ui()

app = FastAPI(title=settings.app_name, version="1.0.0")

origins = ["*"] if settings.cors_origins.strip() == "*" else [
    o.strip() for o in settings.cors_origins.split(",") if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(lessons.router)
app.include_router(progress.router)
app.include_router(stats.router)
app.include_router(tts.router)
app.include_router(review.router)
app.include_router(pronunciation.router)
app.include_router(rewards.router)
app.include_router(tools.router)
app.include_router(profile.router)
app.include_router(images.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}


# --- Serve the built frontend (single-service deployment behind nginx) ---
# Frontend build is expected at ../frontend/dist relative to the backend dir.
_here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_dist = os.path.abspath(os.path.join(_here, "..", "frontend", "dist"))

if os.path.isdir(_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(_dist, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        # Let the SPA router handle client-side routes.
        candidate = os.path.join(_dist, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(_dist, "index.html"))
