def test_landing_page(client):
    assert client.get("/").status_code == 200


def test_terms_page(client):
    assert client.get("/terms").status_code == 200


def test_privacy_page(client):
    assert client.get("/privacy").status_code == 200


def test_404_on_unknown_route(client):
    assert client.get("/this-does-not-exist").status_code == 404
