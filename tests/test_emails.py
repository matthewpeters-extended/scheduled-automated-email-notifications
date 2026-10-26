from datetime import datetime, timedelta

from conftest import login


def _future(minutes=60):
    return (datetime.utcnow() + timedelta(minutes=minutes)).isoformat()


def test_schedule_email_requires_login(client):
    response = client.post(
        "/emails",
        json={
            "recipient_email": "someone@example.com",
            "subject": "Hi",
            "body": "Hello there",
            "scheduled_time": _future(),
        },
    )
    assert response.status_code == 401


def test_schedule_and_fetch_email(client, user):
    login(client, "nina@test-suite.dev", "nina12345")

    response = client.post(
        "/emails",
        json={
            "recipient_email": "someone@example.com",
            "subject": "Reminder",
            "body": "Don't forget the meeting",
            "scheduled_time": _future(),
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "pending"
    assert body["attempts"] == 0

    response = client.get(f"/emails/{body['id']}")
    assert response.status_code == 200
    assert response.json()["subject"] == "Reminder"


def test_list_emails_paginates_and_filters_by_status(client, user):
    login(client, "nina@test-suite.dev", "nina12345")
    for i in range(3):
        client.post(
            "/emails",
            json={
                "recipient_email": "someone@example.com",
                "subject": f"Email {i}",
                "body": "body",
                "scheduled_time": _future(),
            },
        )

    response = client.get("/emails?limit=2")
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2

    response = client.get("/emails?status=pending")
    assert response.json()["total"] == 3

    response = client.get("/emails?status=sent")
    assert response.json()["total"] == 0


def test_cancel_pending_email(client, user):
    login(client, "nina@test-suite.dev", "nina12345")
    created = client.post(
        "/emails",
        json={
            "recipient_email": "someone@example.com",
            "subject": "Cancel me",
            "body": "body",
            "scheduled_time": _future(),
        },
    ).json()

    response = client.delete(f"/emails/{created['id']}")
    assert response.status_code == 204
    assert client.get(f"/emails/{created['id']}").status_code == 404


def test_cannot_access_another_users_email(client, second_client, user, other_user):
    login(client, "nina@test-suite.dev", "nina12345")
    login(second_client, "omar@test-suite.dev", "omar12345")

    created = client.post(
        "/emails",
        json={
            "recipient_email": "someone@example.com",
            "subject": "Private",
            "body": "body",
            "scheduled_time": _future(),
        },
    ).json()

    assert second_client.get(f"/emails/{created['id']}").status_code == 404
    assert second_client.delete(f"/emails/{created['id']}").status_code == 404
