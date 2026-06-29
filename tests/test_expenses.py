import database.db as db_module


# ------------------------------------------------------------------ #
# Dashboard                                                            #
# ------------------------------------------------------------------ #

def test_dashboard_requires_login(client):
    r = client.get("/dashboard")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_dashboard_loads(user_client):
    assert user_client.get("/dashboard").status_code == 200


# ------------------------------------------------------------------ #
# Add expense                                                          #
# ------------------------------------------------------------------ #

def test_add_expense_requires_login(client):
    r = client.get("/expenses/add")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_add_expense_page_loads(user_client):
    assert user_client.get("/expenses/add").status_code == 200


def test_add_expense_success(user_client):
    r = user_client.post("/expenses/add", data={
        "title": "Coffee",
        "amount": "80",
        "category": "Food",
        "date": "2026-06-20",
        "note": "",
    })
    assert r.status_code == 302
    assert "/dashboard" in r.headers["Location"]


def test_add_expense_missing_title(user_client):
    r = user_client.post("/expenses/add", data={
        "title": "",
        "amount": "100",
        "category": "Food",
        "date": "2026-06-20",
        "note": "",
    })
    assert r.status_code == 200
    assert b"required" in r.data


def test_add_expense_missing_date(user_client):
    r = user_client.post("/expenses/add", data={
        "title": "Something",
        "amount": "100",
        "category": "Food",
        "date": "",
        "note": "",
    })
    assert r.status_code == 200
    assert b"required" in r.data


def test_add_expense_invalid_category(user_client):
    r = user_client.post("/expenses/add", data={
        "title": "Something",
        "amount": "100",
        "category": "FakeCategory",
        "date": "2026-06-20",
        "note": "",
    })
    assert r.status_code == 200
    assert b"Invalid category" in r.data


def test_add_expense_negative_amount(user_client):
    r = user_client.post("/expenses/add", data={
        "title": "Something",
        "amount": "-50",
        "category": "Food",
        "date": "2026-06-20",
        "note": "",
    })
    assert r.status_code == 200
    assert b"positive number" in r.data


def test_add_expense_zero_amount(user_client):
    r = user_client.post("/expenses/add", data={
        "title": "Something",
        "amount": "0",
        "category": "Food",
        "date": "2026-06-20",
        "note": "",
    })
    assert r.status_code == 200
    assert b"positive number" in r.data


def test_add_expense_non_numeric_amount(user_client):
    r = user_client.post("/expenses/add", data={
        "title": "Something",
        "amount": "abc",
        "category": "Food",
        "date": "2026-06-20",
        "note": "",
    })
    assert r.status_code == 200
    assert b"positive number" in r.data


# ------------------------------------------------------------------ #
# Edit expense                                                         #
# ------------------------------------------------------------------ #

def test_edit_expense_page_loads(user_client, user_expense_id):
    assert user_client.get(f"/expenses/{user_expense_id}/edit").status_code == 200


def test_edit_expense_not_found(user_client):
    assert user_client.get("/expenses/99999/edit").status_code == 404


def test_edit_expense_forbidden_for_other_user(user_client, app):
    with app.app_context():
        db = db_module.get_db()
        admin_id = db.execute(
            "SELECT id FROM users WHERE email = 'admin@spendly.com'"
        ).fetchone()["id"]
        db.execute(
            "INSERT INTO expenses (user_id, title, amount, category, date) "
            "VALUES (?, 'Admin expense', 999, 'Other', '2026-06-01')",
            (admin_id,),
        )
        db.commit()
        admin_expense_id = db.execute("SELECT MAX(id) as id FROM expenses").fetchone()["id"]

    assert user_client.get(f"/expenses/{admin_expense_id}/edit").status_code == 403


def test_edit_expense_success(user_client, user_expense_id):
    r = user_client.post(f"/expenses/{user_expense_id}/edit", data={
        "title": "Updated Coffee",
        "amount": "95",
        "category": "Food",
        "date": "2026-06-21",
        "note": "updated note",
    })
    assert r.status_code == 302
    assert "/dashboard" in r.headers["Location"]


def test_edit_expense_missing_fields(user_client, user_expense_id):
    r = user_client.post(f"/expenses/{user_expense_id}/edit", data={
        "title": "",
        "amount": "100",
        "category": "Food",
        "date": "2026-06-20",
        "note": "",
    })
    assert r.status_code == 200
    assert b"required" in r.data


def test_edit_expense_invalid_category(user_client, user_expense_id):
    r = user_client.post(f"/expenses/{user_expense_id}/edit", data={
        "title": "Something",
        "amount": "100",
        "category": "FakeCategory",
        "date": "2026-06-20",
        "note": "",
    })
    assert r.status_code == 200
    assert b"Invalid category" in r.data


def test_edit_expense_invalid_amount(user_client, user_expense_id):
    r = user_client.post(f"/expenses/{user_expense_id}/edit", data={
        "title": "Something",
        "amount": "-10",
        "category": "Food",
        "date": "2026-06-20",
        "note": "",
    })
    assert r.status_code == 200
    assert b"positive number" in r.data


def test_admin_can_edit_any_expense(admin_client, app):
    with app.app_context():
        db = db_module.get_db()
        user_id = db.execute(
            "SELECT id FROM users WHERE email = 'nitish@example.com'"
        ).fetchone()["id"]
        expense_id = db.execute(
            "SELECT id FROM expenses WHERE user_id = ? LIMIT 1", (user_id,)
        ).fetchone()["id"]

    assert admin_client.get(f"/expenses/{expense_id}/edit").status_code == 200


# ------------------------------------------------------------------ #
# Delete expense                                                       #
# ------------------------------------------------------------------ #

def test_delete_expense_requires_login(client):
    r = client.post("/expenses/1/delete")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_delete_expense_success(user_client, user_expense_id):
    r = user_client.post(f"/expenses/{user_expense_id}/delete")
    assert r.status_code == 302
    assert "/dashboard" in r.headers["Location"]


def test_delete_expense_not_found(user_client):
    assert user_client.post("/expenses/99999/delete").status_code == 404


def test_delete_expense_forbidden_for_other_user(user_client, app):
    with app.app_context():
        db = db_module.get_db()
        admin_id = db.execute(
            "SELECT id FROM users WHERE email = 'admin@spendly.com'"
        ).fetchone()["id"]
        db.execute(
            "INSERT INTO expenses (user_id, title, amount, category, date) "
            "VALUES (?, 'Admin expense', 999, 'Other', '2026-06-01')",
            (admin_id,),
        )
        db.commit()
        admin_expense_id = db.execute("SELECT MAX(id) as id FROM expenses").fetchone()["id"]

    assert user_client.post(f"/expenses/{admin_expense_id}/delete").status_code == 403


def test_admin_can_delete_any_expense(admin_client, app):
    with app.app_context():
        db = db_module.get_db()
        user_id = db.execute(
            "SELECT id FROM users WHERE email = 'nitish@example.com'"
        ).fetchone()["id"]
        expense_id = db.execute(
            "SELECT id FROM expenses WHERE user_id = ? LIMIT 1", (user_id,)
        ).fetchone()["id"]

    r = admin_client.post(f"/expenses/{expense_id}/delete")
    assert r.status_code == 302
    assert "/dashboard" in r.headers["Location"]
