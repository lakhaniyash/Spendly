# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Spendly** is a Flask-based personal expense tracker web application targeting Indian users (currency: ₹). The app is in early development — authentication, expense CRUD, and dashboard features are not yet implemented. Routes exist as stubs with "coming in Step N" placeholders.

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

## Running Tests

```bash
pytest
# or a single test file
pytest tests/test_routes.py
```

## Architecture

- **`app.py`** — Flask app with all route definitions. Single-file for now; routes will grow as features are added step by step.
- **`database/db.py`** — SQLite helpers (stub). Students implement `get_db()`, `init_db()`, and `seed_db()`. Database file is `expense_tracker.db` (gitignored).
- **`templates/`** — Jinja2 templates. `base.html` is the shared layout (navbar + footer). All pages extend it.
- **`static/css/style.css`** — Single stylesheet. Uses CSS custom properties (`--ink`, `--paper`, `--accent`, etc.) defined in `:root`. All new styles should follow these tokens.
- **`static/js/main.js`** — Vanilla JS, no framework. Currently handles the "How it works" YouTube modal.

## Design System

The app uses a warm off-white paper theme. Key CSS tokens:
- Colors: `--ink`, `--paper`, `--accent` (`#1a472a` green), `--accent-2` (gold), `--danger`
- Fonts: `DM Serif Display` for headings, `DM Sans` for body
- Max widths: `--max-width: 1200px`, `--auth-width: 440px`

New UI components must use these variables — do not hardcode hex values.

## Planned Features (Not Yet Built)

The app is being built incrementally. Placeholder routes exist for: logout, profile, add/edit/delete expenses. The database schema (`get_db`, `init_db`, `seed_db`) needs to be implemented first before any auth or expense routes can be wired up.
