import database.db as db_module


def _get_user_id(app, email):
    with app.app_context():
        db = db_module.get_db()
        return db.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()["id"]


# ------------------------------------------------------------------ #
# Admin dashboard                                                      #
# ------------------------------------------------------------------ #

def test_admin_dashboard_requires_login(client):
    r = client.get("/admin")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_admin_dashboard_forbidden_for_regular_user(user_client):
    assert user_client.get("/admin").status_code == 403


def test_admin_dashboard_loads_for_admin(admin_client):
    assert admin_client.get("/admin").status_code == 200


# ------------------------------------------------------------------ #
# Change role                                                          #
# ------------------------------------------------------------------ #

def test_change_role_requires_login(client, app):
    user_id = _get_user_id(app, "yash.lakhani@smartsensesolutions.com")
    r = client.post(f"/admin/users/{user_id}/role", data={"role": "admin"})
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_change_role_forbidden_for_regular_user(user_client, app):
    user_id = _get_user_id(app, "yash.lakhani@smartsensesolutions.com")
    assert user_client.post(f"/admin/users/{user_id}/role", data={"role": "admin"}).status_code == 403


def test_change_role_success(admin_client, app):
    user_id = _get_user_id(app, "yash.lakhani@smartsensesolutions.com")
    r = admin_client.post(f"/admin/users/{user_id}/role", data={"role": "admin"})
    assert r.status_code == 302
    assert "/admin" in r.headers["Location"]

    with app.app_context():
        db = db_module.get_db()
        role = db.execute("SELECT role FROM users WHERE id = ?", (user_id,)).fetchone()["role"]
    assert role == "admin"


def test_change_role_invalid_role(admin_client, app):
    user_id = _get_user_id(app, "yash.lakhani@smartsensesolutions.com")
    assert admin_client.post(
        f"/admin/users/{user_id}/role", data={"role": "superuser"}
    ).status_code == 400


def test_change_role_nonexistent_user(admin_client):
    assert admin_client.post("/admin/users/99999/role", data={"role": "user"}).status_code == 404


def test_admin_cannot_change_own_role(admin_client, app):
    admin_id = _get_user_id(app, "yash.lakhani+admin@smartsensesolutions.com")
    r = admin_client.post(f"/admin/users/{admin_id}/role", data={"role": "user"})
    assert r.status_code == 302

    # Role must not have changed
    with app.app_context():
        db = db_module.get_db()
        role = db.execute("SELECT role FROM users WHERE id = ?", (admin_id,)).fetchone()["role"]
    assert role == "admin"
