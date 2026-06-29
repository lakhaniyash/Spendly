import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import session, redirect, url_for, abort

REFRESH_TOKEN_DAYS = 30


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    """Enforce that the logged-in user has one of the given roles."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if session.get('user_role') not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator


def _now_str():
    return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')


def generate_refresh_token(db, user_id):
    token = secrets.token_urlsafe(48)
    expires_at = (datetime.utcnow() + timedelta(days=REFRESH_TOKEN_DAYS)).strftime('%Y-%m-%d %H:%M:%S')
    db.execute(
        "INSERT INTO refresh_tokens (user_id, token, expires_at) VALUES (?, ?, ?)",
        (user_id, token, expires_at)
    )
    db.commit()
    return token


def validate_refresh_token(db, token):
    return db.execute(
        """SELECT u.id, u.name, u.role
           FROM refresh_tokens rt
           JOIN users u ON rt.user_id = u.id
           WHERE rt.token = ? AND rt.revoked = 0 AND rt.expires_at > ?""",
        (token, _now_str())
    ).fetchone()


def revoke_refresh_token(db, token):
    db.execute("UPDATE refresh_tokens SET revoked = 1 WHERE token = ?", (token,))
    db.commit()


def revoke_all_user_refresh_tokens(db, user_id):
    db.execute("UPDATE refresh_tokens SET revoked = 1 WHERE user_id = ?", (user_id,))
    db.commit()
