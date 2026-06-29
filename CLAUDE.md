# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Spendly** is a Flask-based personal expense tracker web application targeting Indian users (currency: ₹). Core features — authentication, expense CRUD, user profiles, and an admin panel — are fully implemented. The app uses SQLite for storage and a warm off-white paper design system.

## Branch Strategy

- `master` — production-ready, stable releases only
- `development` — integration branch; all feature branches merge here first
- `feature/*` — short-lived feature branches cut from `development`

PRs must target `development`, not `master`.

## Running the App

```bash
# Create and activate virtualenv (one-time)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run dev server on port 5001
python app.py
```

The app initialises and seeds the database automatically on first run (see `database/db.py`).

**Default dev credentials (seeded on empty DB):**
| Email | Password | Role |
|---|---|---|
| admin@spendly.com | admin123 | admin |
| nitish@example.com | user123 | user |

## Running Tests

```bash
pytest
# single module
pytest tests/test_auth.py
```

Each test gets a fresh isolated SQLite database via `tmp_path` — no shared state between tests.

## Architecture

### Backend

- **`app.py`** — Flask app with all route definitions. Registers `close_db` as a teardown, runs `init_db()` + `seed_db()` at startup inside an app context.
- **`auth.py`** — Two decorators: `@login_required` (redirects to `/login` if unauthenticated) and `@role_required(*roles)` (403 if logged-in user's role is not in the given set). Both read from `session`.
- **`database/db.py`** — SQLite helpers using Flask's `g` object. `get_db()` opens a connection (once per request), `close_db()` closes it on teardown, `init_db()` creates tables, `seed_db()` inserts dev data if the DB is empty.

### Routes

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | — | Landing page |
| GET/POST | `/register` | — | User registration |
| GET/POST | `/login` | — | Login |
| GET | `/logout` | login | Clear session |
| GET | `/terms` | — | Terms of service |
| GET | `/privacy` | — | Privacy policy |
| GET | `/dashboard` | login | Expense list + totals |
| GET/POST | `/profile` | login | Update name / password |
| GET/POST | `/expenses/add` | login | Add expense |
| GET/POST | `/expenses/<id>/edit` | login | Edit own expense (admin: any) |
| POST | `/expenses/<id>/delete` | login | Delete own expense (admin: any) |
| GET | `/admin` | admin | Admin dashboard |
| POST | `/admin/users/<id>/role` | admin | Change a user's role |

### Database Schema

```sql
users (id, name, email, password_hash, role CHECK('user','admin'), created_at)
expenses (id, user_id FK→users, title, amount, category, date, note, created_at)
```

`FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE` is enforced via `PRAGMA foreign_keys = ON`.

**Expense categories:** Food, Transport, Utilities, Entertainment, Shopping, Health, Education, Other.

### Templates

All templates extend `templates/base.html`. The base layout includes the navbar, flash message renderer, and footer.

- `templates/macros.html` — `protected` Jinja2 call-macro for template-level role guards. Import and use:
  ```jinja
  {% from 'macros.html' import protected %}
  {% call protected('admin') %}<a href="/admin">Admin</a>{% endcall %}
  ```
- `templates/expenses/` — `add.html`, `edit.html`
- `templates/403.html`, `templates/404.html` — custom error pages

### Tests

```
tests/
  conftest.py        # app fixture (temp DB), client, user_client, admin_client, user_expense_id
  test_public.py     # landing, terms, privacy, 404
  test_auth.py       # register, login, logout, profile
  test_expenses.py   # dashboard, add/edit/delete, ownership enforcement
  test_admin.py      # admin dashboard, role change, access control
```

## Design System

The app uses a warm off-white paper theme. All styles live in `static/css/style.css`.

**CSS custom properties (defined in `:root`):**
| Token | Usage |
|---|---|
| `--ink` | Primary text |
| `--paper` | Background |
| `--accent` | `#1a472a` green — primary actions |
| `--accent-2` | Gold — highlights |
| `--danger` | Errors / destructive actions |
| `--max-width` | `1200px` page container |
| `--auth-width` | `440px` auth form container |

**Fonts:** `DM Serif Display` for headings, `DM Sans` for body (loaded from Google Fonts in `base.html`).

**Rules:** Never hardcode hex values — always use CSS tokens. New components must follow existing token usage.

`static/js/main.js` — Vanilla JS only (no framework). Currently handles the "How it works" YouTube modal (open/close/keyboard dismiss).

## Known Issues (to fix before production)

- **Secret key** — `app.py` falls back to a hardcoded default if `SECRET_KEY` env var is not set. Always set `SECRET_KEY` in production.
- **CSRF** — No CSRF protection on any POST endpoint. Add `flask-wtf` before going live.
- **DB path** — `DATABASE = 'expense_tracker.db'` in `db.py` is relative to CWD. Use an absolute path derived from `__file__` for reliable deployment.
- **Seed credentials** — `seed_db()` inserts a known admin account. Remove or gate behind `app.debug` before production.
- **Amount validation** — `float()` accepts `inf` and `nan`; add `math.isfinite()` check to expense add/edit.
