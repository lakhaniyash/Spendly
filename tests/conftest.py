import pytest
import database.db as db_module
from app import app as flask_app


@pytest.fixture
def app(tmp_path):
    db_path = str(tmp_path / "test.db")
    db_module.DATABASE = db_path
    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret"

    with flask_app.app_context():
        db_module.init_db()
        db_module.seed_db()

    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user_client(client):
    client.post("/login", data={"email": "nitish@example.com", "password": "user123"})
    return client


@pytest.fixture
def admin_client(client):
    client.post("/login", data={"email": "admin@spendly.com", "password": "admin123"})
    return client


@pytest.fixture
def user_expense_id(user_client, app):
    """Create a fresh expense as the regular user and return its ID."""
    user_client.post("/expenses/add", data={
        "title": "Test expense",
        "amount": "500",
        "category": "Food",
        "date": "2026-06-15",
        "note": "test note",
    })
    with app.app_context():
        db = db_module.get_db()
        row = db.execute("SELECT MAX(id) as id FROM expenses").fetchone()
        return row["id"]
