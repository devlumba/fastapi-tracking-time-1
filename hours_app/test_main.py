from typing import Annotated
from datetime import date

from fastapi.responses import RedirectResponse
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool

from hours_app.main import app
from hours_app.database import get_session

client = TestClient(app)

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
SQLModel.metadata.create_all(engine)

with Session(engine) as session:
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200


def test_create_user():
    response = client.post("/users", params={"username": "user3", "password": "secret", "confirm_password": "secret"})
    print(response.json())
    assert response.status_code == 200


def test_login():  # login for swagger, obv, it's more about "test whether I can login in tests"
    form_data = {"username": "user3", "password": "secret"}
    response = client.post("/users", params={"username": "user3", "password": "secret", "confirm_password": "secret"})
    response = client.post("/token", data=form_data)
    assert response.status_code == 200


def test_msg_json():
    response = client.get("/test-msg")
    assert response.json()["msg"] == "heya"


def test_create_sesh():
    form_data = {"username": "user3", "password": "secret"}
    client.post("/users", params={"username": "user3", "password": "secret", "confirm_password": "secret"})
    response = client.post("/token", data=form_data)
    assert  response.status_code == 200
    print("TEXT TEXT TEXT TEXT", response.text, response.status_code)
    print("TEXT TEXT TEXT TEXT", response.text)
    print("TEXT TEXT TEXT TEXT", response.text)
    token = response.json()["access_token"]
    print("token", token)
    print("token", token)
    print("token", token)

    response = client.post("/seshs", data={"sesh_length": 1, "sesh_type": "programming", "sesh_day": "2026-06-08"},
                           headers={"Authorization": f"Bearer {token}"},
                           cookies={"access_token": token})
    print("12222222TEXT TEXT TEXT TEXT", response.text)
    print("TEXT TEXT TEXT TEXT", response.text)
    print("TEXT TEXT TEXT TEXT", response.text)
    print(response.headers)
    print(response.cookies)
    assert response.status_code == 200


def test_update_sesh():
    form_data = {"username": "user3", "password": "secret"}
    client.post("/users", params={"username": "user3", "password": "secret", "confirm_password": "secret"})
    response = client.post("/token", data=form_data)
    token = response.json()["access_token"]

    response = client.post("/seshs", data={"sesh_length": 1, "sesh_type": "programming", "sesh_day": "2026-06-08"},
                           headers={"Authorization": f"Bearer {token}"})
    print(response.text)
    print(response.text)
    print(response.text)
    sesh_id = response.json()["id"]

    response = client.put(f"/seshs/{sesh_id}", data={"sesh_length": 2, "sesh_type": "programming", "sesh_day": "2026-06-09"},
                           headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["length"] == 2
    assert response.json()["day"] == "2026-06-09"


def test_delete_sesh():
    form_data = {"username": "user3", "password": "secret"}
    client.post("/users", params={"username": "user3", "password": "secret", "confirm_password": "secret"})
    response = client.post("/token", data=form_data)
    token = response.json()["access_token"]

    response = client.post("/seshs", data={"sesh_length": 1, "sesh_type": "programming", "sesh_day": "2026-06-08"},
                           headers={"Authorization": f"Bearer {token}"})
    sesh_id = response.json()["id"]

    response = client.delete(f"/seshs/", params={"sesh_id": sesh_id},
                           headers={"Authorization": f"Bearer {token}"})
    print(response.text)
    assert response.status_code == 200


def test_delete_sesh_404():
    form_data = {"username": "user3", "password": "secret"}
    client.post("/users", params={"username": "user3", "password": "secret", "confirm_password": "secret"})
    response = client.post("/token", data=form_data)
    token = response.json()["access_token"]

    response = client.post("/seshs", data={"sesh_length": 1, "sesh_type": "programming", "sesh_day": "2026-06-08"},
                           headers={"Authorization": f"Bearer {token}"})
    sesh_id = response.json()["id"]

    client.delete(f"/seshs/", params={"sesh_id": sesh_id},
                             headers={"Authorization": f"Bearer {token}"})
    response = client.get(f"/seshs/{sesh_id}",
                             headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404


def test_update_user():
    response = client.post("/users", params={"username": "user01", "password": "secret", "confirm_password": "secret"})
    print(response.text)
    print(response.json())
    user_id = response.json()["id"]
    response = client.put("")
    assert response.status_code == 200


