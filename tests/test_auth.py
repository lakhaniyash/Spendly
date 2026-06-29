# ------------------------------------------------------------------ #
# Register                                                             #
# ------------------------------------------------------------------ #

def test_register_page_loads(client):
    assert client.get("/register").status_code == 200


def test_register_success_redirects_to_dashboard(client):
    r = client.post("/register", data={
        "name": "New User",
        "email": "newuser@example.com",
        "password": "securepass123",
    })
    assert r.status_code == 302
    assert "/dashboard" in r.headers["Location"]


def test_register_missing_name(client):
    r = client.post("/register", data={
        "name": "",
        "email": "newuser@example.com",
        "password": "securepass123",
    })
    assert r.status_code == 200
    assert b"required" in r.data


def test_register_short_password(client):
    r = client.post("/register", data={
        "name": "New User",
        "email": "newuser@example.com",
        "password": "short",
    })
    assert r.status_code == 200
    assert b"8 characters" in r.data


def test_register_duplicate_email(client):
    r = client.post("/register", data={
        "name": "Duplicate",
        "email": "yash.lakhani@smartsensesolutions.com",
        "password": "securepass123",
    })
    assert r.status_code == 200
    assert b"already exists" in r.data


def test_register_redirects_if_already_logged_in(user_client):
    r = user_client.get("/register")
    assert r.status_code == 302
    assert "/dashboard" in r.headers["Location"]


# ------------------------------------------------------------------ #
# Login                                                                #
# ------------------------------------------------------------------ #

def test_login_page_loads(client):
    assert client.get("/login").status_code == 200


def test_login_success(client):
    r = client.post("/login", data={
        "email": "yash.lakhani@smartsensesolutions.com",
        "password": "Smart@12345",
    })
    assert r.status_code == 302
    assert "/dashboard" in r.headers["Location"]


def test_login_wrong_password(client):
    r = client.post("/login", data={
        "email": "yash.lakhani@smartsensesolutions.com",
        "password": "wrongpassword",
    })
    assert r.status_code == 200
    assert b"Invalid email or password" in r.data


def test_login_unknown_email(client):
    r = client.post("/login", data={
        "email": "ghost@example.com",
        "password": "anything",
    })
    assert r.status_code == 200
    assert b"Invalid email or password" in r.data


def test_login_redirects_if_already_logged_in(user_client):
    r = user_client.get("/login")
    assert r.status_code == 302
    assert "/dashboard" in r.headers["Location"]


# ------------------------------------------------------------------ #
# Logout                                                               #
# ------------------------------------------------------------------ #

def test_logout_requires_login(client):
    r = client.get("/logout")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_logout_clears_session(user_client):
    user_client.get("/logout")
    r = user_client.get("/dashboard")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


# ------------------------------------------------------------------ #
# Profile                                                              #
# ------------------------------------------------------------------ #

def test_profile_requires_login(client):
    r = client.get("/profile")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_profile_page_loads(user_client):
    assert user_client.get("/profile").status_code == 200


def test_profile_update_name(user_client):
    r = user_client.post("/profile", data={
        "name": "Updated Yash",
        "current_password": "",
        "new_password": "",
    })
    assert r.status_code == 302
    assert "/profile" in r.headers["Location"]


def test_profile_empty_name(user_client):
    r = user_client.post("/profile", data={
        "name": "",
        "current_password": "",
        "new_password": "",
    })
    assert r.status_code == 200
    assert b"cannot be empty" in r.data


def test_profile_new_password_too_short(user_client):
    r = user_client.post("/profile", data={
        "name": "Yash Lakhani",
        "current_password": "Smart@12345",
        "new_password": "short",
    })
    assert r.status_code == 200
    assert b"8 characters" in r.data


def test_profile_wrong_current_password(user_client):
    r = user_client.post("/profile", data={
        "name": "Yash Lakhani",
        "current_password": "wrongpassword",
        "new_password": "newpassword123",
    })
    assert r.status_code == 200
    assert b"incorrect" in r.data


def test_profile_update_password_success(user_client):
    r = user_client.post("/profile", data={
        "name": "Yash Lakhani",
        "current_password": "Smart@12345",
        "new_password": "newpassword123",
    })
    assert r.status_code == 302
