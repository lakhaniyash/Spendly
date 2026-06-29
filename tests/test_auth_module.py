"""
Tests for the enhanced auth module:
  - Refresh token issuance, auto-login, rotation, revocation
  - Forgot-password flow (token creation, anti-enumeration)
  - Reset-password flow (validation, password update, token expiry)
"""

import secrets
import pytest
import database.db as db_module
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _get_user_id(app, email):
    with app.app_context():
        return db_module.get_db().execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()["id"]


def _insert_refresh_token(app, user_id, *, revoked=False, expired=False):
    token = secrets.token_urlsafe(48)
    if expired:
        expires_at = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
    else:
        expires_at = (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
    with app.app_context():
        db = db_module.get_db()
        db.execute(
            "INSERT INTO refresh_tokens (user_id, token, expires_at, revoked) VALUES (?, ?, ?, ?)",
            (user_id, token, expires_at, int(revoked)),
        )
        db.commit()
    return token


def _insert_reset_token(app, user_id, *, used=False, expired=False):
    token = secrets.token_urlsafe(32)
    if expired:
        expires_at = (datetime.utcnow() - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
    else:
        expires_at = (datetime.utcnow() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
    with app.app_context():
        db = db_module.get_db()
        db.execute(
            "INSERT INTO password_resets (user_id, token, expires_at, used) VALUES (?, ?, ?, ?)",
            (user_id, token, expires_at, int(used)),
        )
        db.commit()
    return token


# ------------------------------------------------------------------ #
# Login — refresh cookie issuance                                      #
# ------------------------------------------------------------------ #

def test_login_sets_refresh_cookie(client):
    client.post("/login", data={"email": "yash.lakhani@smartsensesolutions.com", "password": "Smart@12345"})
    cookie = client.get_cookie("refresh_token")
    assert cookie is not None
    assert len(cookie.value) > 0


def test_login_refresh_token_stored_in_db(client, app):
    client.post("/login", data={"email": "yash.lakhani@smartsensesolutions.com", "password": "Smart@12345"})
    cookie = client.get_cookie("refresh_token")
    user_id = _get_user_id(app, "yash.lakhani@smartsensesolutions.com")
    with app.app_context():
        row = db_module.get_db().execute(
            "SELECT * FROM refresh_tokens WHERE token = ? AND user_id = ? AND revoked = 0",
            (cookie.value, user_id),
        ).fetchone()
    assert row is not None


def test_register_sets_refresh_cookie(client):
    client.post("/register", data={
        "name": "New User",
        "email": "newuser@example.com",
        "password": "securepass123",
    })
    cookie = client.get_cookie("refresh_token")
    assert cookie is not None
    assert len(cookie.value) > 0


# ------------------------------------------------------------------ #
# Logout — refresh token revocation                                    #
# ------------------------------------------------------------------ #

def test_logout_revokes_refresh_token_in_db(user_client, app):
    cookie = user_client.get_cookie("refresh_token")
    assert cookie is not None
    token_value = cookie.value

    user_client.get("/logout")

    with app.app_context():
        row = db_module.get_db().execute(
            "SELECT revoked FROM refresh_tokens WHERE token = ?", (token_value,)
        ).fetchone()
    assert row is not None
    assert row["revoked"] == 1


def test_logout_clears_refresh_cookie(user_client):
    user_client.get("/logout")
    cookie = user_client.get_cookie("refresh_token")
    assert cookie is None or cookie.value == ""


# ------------------------------------------------------------------ #
# Login page — forgot password link                                    #
# ------------------------------------------------------------------ #

def test_login_page_has_forgot_password_link(client):
    r = client.get("/login")
    assert b"forgot-password" in r.data


# ------------------------------------------------------------------ #
# Refresh token — auto-login                                           #
# ------------------------------------------------------------------ #

def test_refresh_token_auto_login_restores_session(client, app):
    user_id = _get_user_id(app, "yash.lakhani@smartsensesolutions.com")
    token = _insert_refresh_token(app, user_id)

    client.set_cookie("refresh_token", token)
    r = client.get("/dashboard")
    assert r.status_code == 200


def test_refresh_token_invalid_value_does_not_login(client):
    client.set_cookie("refresh_token", "completely-invalid-token-xyz")
    r = client.get("/dashboard")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_refresh_token_revoked_does_not_login(client, app):
    user_id = _get_user_id(app, "yash.lakhani@smartsensesolutions.com")
    token = _insert_refresh_token(app, user_id, revoked=True)
    client.set_cookie("refresh_token", token)
    r = client.get("/dashboard")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_refresh_token_expired_does_not_login(client, app):
    user_id = _get_user_id(app, "yash.lakhani@smartsensesolutions.com")
    token = _insert_refresh_token(app, user_id, expired=True)
    client.set_cookie("refresh_token", token)
    r = client.get("/dashboard")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


# ------------------------------------------------------------------ #
# Refresh token — rotation on use                                      #
# ------------------------------------------------------------------ #

def test_refresh_token_is_rotated_on_use(client, app):
    user_id = _get_user_id(app, "yash.lakhani@smartsensesolutions.com")
    old_token = _insert_refresh_token(app, user_id)

    client.set_cookie("refresh_token", old_token)
    client.get("/dashboard")

    new_cookie = client.get_cookie("refresh_token")
    assert new_cookie is not None
    assert new_cookie.value != old_token

    with app.app_context():
        old_row = db_module.get_db().execute(
            "SELECT revoked FROM refresh_tokens WHERE token = ?", (old_token,)
        ).fetchone()
    assert old_row["revoked"] == 1


def test_rotated_refresh_token_is_valid_in_db(client, app):
    user_id = _get_user_id(app, "yash.lakhani@smartsensesolutions.com")
    old_token = _insert_refresh_token(app, user_id)

    client.set_cookie("refresh_token", old_token)
    client.get("/dashboard")

    new_token = client.get_cookie("refresh_token").value
    with app.app_context():
        row = db_module.get_db().execute(
            "SELECT revoked FROM refresh_tokens WHERE token = ? AND revoked = 0",
            (new_token,)
        ).fetchone()
    assert row is not None


# ------------------------------------------------------------------ #
# Forgot password — page                                              #
# ------------------------------------------------------------------ #

def test_forgot_password_page_loads(client):
    assert client.get("/forgot-password").status_code == 200


def test_forgot_password_redirects_if_logged_in(user_client):
    r = user_client.get("/forgot-password")
    assert r.status_code == 302
    assert "/dashboard" in r.headers["Location"]


# ------------------------------------------------------------------ #
# Forgot password — token creation                                     #
# ------------------------------------------------------------------ #

def test_forgot_password_known_email_shows_dev_reset_link(client):
    r = client.post("/forgot-password", data={"email": "yash.lakhani@smartsensesolutions.com"})
    assert r.status_code == 200
    assert b"reset-password" in r.data


def test_forgot_password_unknown_email_no_reset_link(client):
    r = client.post("/forgot-password", data={"email": "ghost@nowhere.com"})
    assert r.status_code == 200
    assert b"reset-password" not in r.data


def test_forgot_password_both_cases_show_sent_confirmation(client):
    r_known = client.post("/forgot-password", data={"email": "yash.lakhani@smartsensesolutions.com"})
    r_unknown = client.post("/forgot-password", data={"email": "ghost@nowhere.com"})
    assert b"sent" in r_known.data.lower()
    assert b"sent" in r_unknown.data.lower()


def test_forgot_password_creates_reset_token_in_db(client, app):
    client.post("/forgot-password", data={"email": "yash.lakhani@smartsensesolutions.com"})
    user_id = _get_user_id(app, "yash.lakhani@smartsensesolutions.com")
    with app.app_context():
        row = db_module.get_db().execute(
            "SELECT * FROM password_resets WHERE user_id = ? AND used = 0",
            (user_id,)
        ).fetchone()
    assert row is not None


def test_forgot_password_invalidates_previous_unused_tokens(client, app):
    user_id = _get_user_id(app, "yash.lakhani@smartsensesolutions.com")
    old_token = _insert_reset_token(app, user_id)

    client.post("/forgot-password", data={"email": "yash.lakhani@smartsensesolutions.com"})

    with app.app_context():
        row = db_module.get_db().execute(
            "SELECT used FROM password_resets WHERE token = ?", (old_token,)
        ).fetchone()
    assert row["used"] == 1


def test_forgot_password_unknown_email_creates_no_token(client, app):
    client.post("/forgot-password", data={"email": "ghost@nowhere.com"})
    with app.app_context():
        count = db_module.get_db().execute(
            "SELECT COUNT(*) FROM password_resets"
        ).fetchone()[0]
    assert count == 0


# ------------------------------------------------------------------ #
# Reset password — token validation                                    #
# ------------------------------------------------------------------ #

def test_reset_password_invalid_token_shows_expired_page(client):
    r = client.get("/reset-password/not-a-real-token")
    assert r.status_code == 200
    assert b"expired" in r.data.lower() or b"invalid" in r.data.lower()


def test_reset_password_used_token_shows_expired_page(client, app):
    user_id = _get_user_id(app, "yash.lakhani@smartsensesolutions.com")
    token = _insert_reset_token(app, user_id, used=True)
    r = client.get(f"/reset-password/{token}")
    assert r.status_code == 200
    assert b"expired" in r.data.lower() or b"invalid" in r.data.lower()


def test_reset_password_expired_token_shows_expired_page(client, app):
    user_id = _get_user_id(app, "yash.lakhani@smartsensesolutions.com")
    token = _insert_reset_token(app, user_id, expired=True)
    r = client.get(f"/reset-password/{token}")
    assert r.status_code == 200
    assert b"expired" in r.data.lower() or b"invalid" in r.data.lower()


def test_reset_password_valid_token_shows_form(client, app):
    user_id = _get_user_id(app, "yash.lakhani@smartsensesolutions.com")
    token = _insert_reset_token(app, user_id)
    r = client.get(f"/reset-password/{token}")
    assert r.status_code == 200
    assert b"Reset password" in r.data
    assert b"yash.lakhani@smartsensesolutions.com" in r.data


def test_reset_password_valid_token_shows_confirm_field(client, app):
    user_id = _get_user_id(app, "yash.lakhani@smartsensesolutions.com")
    token = _insert_reset_token(app, user_id)
    r = client.get(f"/reset-password/{token}")
    assert b"confirm_password" in r.data


def test_reset_password_redirects_if_logged_in(user_client, app):
    user_id = _get_user_id(app, "yash.lakhani@smartsensesolutions.com")
    token = _insert_reset_token(app, user_id)
    r = user_client.get(f"/reset-password/{token}")
    assert r.status_code == 302
    assert "/dashboard" in r.headers["Location"]


# ------------------------------------------------------------------ #
# Reset password — form validation                                     #
# ------------------------------------------------------------------ #

def test_reset_password_short_password_rejected(client, app):
    user_id = _get_user_id(app, "yash.lakhani@smartsensesolutions.com")
    token = _insert_reset_token(app, user_id)
    r = client.post(f"/reset-password/{token}", data={
        "password": "short",
        "confirm_password": "short",
    })
    assert r.status_code == 200
    assert b"8 characters" in r.data


def test_reset_password_mismatch_rejected(client, app):
    user_id = _get_user_id(app, "yash.lakhani@smartsensesolutions.com")
    token = _insert_reset_token(app, user_id)
    r = client.post(f"/reset-password/{token}", data={
        "password": "newpassword123",
        "confirm_password": "differentpassword",
    })
    assert r.status_code == 200
    assert b"do not match" in r.data


# ------------------------------------------------------------------ #
# Reset password — success flow                                        #
# ------------------------------------------------------------------ #

def test_reset_password_success_redirects_to_login(client, app):
    user_id = _get_user_id(app, "yash.lakhani@smartsensesolutions.com")
    token = _insert_reset_token(app, user_id)
    r = client.post(f"/reset-password/{token}", data={
        "password": "brandnewpass123",
        "confirm_password": "brandnewpass123",
    })
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_reset_password_success_updates_password_hash(client, app):
    user_id = _get_user_id(app, "yash.lakhani@smartsensesolutions.com")
    token = _insert_reset_token(app, user_id)
    client.post(f"/reset-password/{token}", data={
        "password": "brandnewpass123",
        "confirm_password": "brandnewpass123",
    })
    with app.app_context():
        row = db_module.get_db().execute(
            "SELECT password_hash FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    assert check_password_hash(row["password_hash"], "brandnewpass123")


def test_reset_password_success_marks_token_used(client, app):
    user_id = _get_user_id(app, "yash.lakhani@smartsensesolutions.com")
    token = _insert_reset_token(app, user_id)
    client.post(f"/reset-password/{token}", data={
        "password": "brandnewpass123",
        "confirm_password": "brandnewpass123",
    })
    with app.app_context():
        row = db_module.get_db().execute(
            "SELECT used FROM password_resets WHERE token = ?", (token,)
        ).fetchone()
    assert row["used"] == 1


def test_reset_password_token_cannot_be_reused(client, app):
    user_id = _get_user_id(app, "yash.lakhani@smartsensesolutions.com")
    token = _insert_reset_token(app, user_id)
    client.post(f"/reset-password/{token}", data={
        "password": "brandnewpass123",
        "confirm_password": "brandnewpass123",
    })
    r = client.get(f"/reset-password/{token}")
    assert r.status_code == 200
    assert b"expired" in r.data.lower() or b"invalid" in r.data.lower()


def test_reset_password_revokes_all_user_refresh_tokens(client, app):
    user_id = _get_user_id(app, "yash.lakhani@smartsensesolutions.com")
    _insert_refresh_token(app, user_id)
    _insert_refresh_token(app, user_id)

    token = _insert_reset_token(app, user_id)
    client.post(f"/reset-password/{token}", data={
        "password": "brandnewpass123",
        "confirm_password": "brandnewpass123",
    })

    with app.app_context():
        active = db_module.get_db().execute(
            "SELECT COUNT(*) FROM refresh_tokens WHERE user_id = ? AND revoked = 0",
            (user_id,)
        ).fetchone()[0]
    assert active == 0


def test_reset_password_new_password_allows_login(client, app):
    user_id = _get_user_id(app, "yash.lakhani@smartsensesolutions.com")
    token = _insert_reset_token(app, user_id)
    client.post(f"/reset-password/{token}", data={
        "password": "brandnewpass123",
        "confirm_password": "brandnewpass123",
    })
    r = client.post("/login", data={
        "email": "yash.lakhani@smartsensesolutions.com",
        "password": "brandnewpass123",
    })
    assert r.status_code == 302
    assert "/dashboard" in r.headers["Location"]


def test_reset_password_old_password_no_longer_works(client, app):
    user_id = _get_user_id(app, "yash.lakhani@smartsensesolutions.com")
    token = _insert_reset_token(app, user_id)
    client.post(f"/reset-password/{token}", data={
        "password": "brandnewpass123",
        "confirm_password": "brandnewpass123",
    })
    r = client.post("/login", data={
        "email": "yash.lakhani@smartsensesolutions.com",
        "password": "Smart@12345",
    })
    assert r.status_code == 200
    assert b"Invalid email or password" in r.data
