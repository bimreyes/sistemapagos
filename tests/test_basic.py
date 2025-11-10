import pytest
from backend.app import create_app
@pytest.fixture
def app():
    app = create_app()
    app.config.update({"TESTING": True})
    yield app
def test_index(app):
    client = app.test_client()
    resp = client.get('/')
    assert resp.status_code == 200
