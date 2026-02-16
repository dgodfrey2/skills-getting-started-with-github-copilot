from fastapi.testclient import TestClient

from src.app import app, activities

client = TestClient(app)


def test_root_redirects_to_static_index():
    response = client.get("/", follow_redirects=False)
    assert response.status_code in (302, 307)
    # Location header should point to the static index
    assert "/static/index.html" in response.headers.get("location", "")


def test_get_activities_returns_all_activities():
    response = client.get("/activities")
    assert response.status_code == 200
    data = response.json()

    # Should return the same keys as the in-memory activities dict
    assert set(data.keys()) == set(activities.keys())

    # Each activity should include required fields
    for name, details in data.items():
        assert "description" in details
        assert "schedule" in details
        assert "max_participants" in details
        assert "participants" in details
        assert isinstance(details["participants"], list)


def test_successful_signup_adds_participant_and_prevents_duplicates():
    activity_name = "Chess Club"
    email = "newstudent@mergington.edu"

    # Ensure clean state for this email
    activities[activity_name]["participants"] = [
        e for e in activities[activity_name]["participants"] if e != email
    ]
    original_len = len(activities[activity_name]["participants"])

    # First signup should succeed
    response = client.post(f"/activities/{activity_name}/signup", params={"email": email})
    assert response.status_code == 200
    assert email in activities[activity_name]["participants"]
    assert len(activities[activity_name]["participants"]) == original_len + 1

    # Second signup should fail with 400
    response_dup = client.post(
        f"/activities/{activity_name}/signup", params={"email": email}
    )
    assert response_dup.status_code == 400
    assert response_dup.json()["detail"] == "Student already signed up for this activity"


def test_signup_fails_for_unknown_activity():
    response = client.post("/activities/UnknownActivity/signup", params={"email": "x@y.com"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_signup_fails_when_activity_is_full():
    activity_name = "Science Olympiad"

    # Fill the activity to its max capacity with dummy emails
    max_participants = activities[activity_name]["max_participants"]
    activities[activity_name]["participants"] = [
        f"student{i}@mergington.edu" for i in range(max_participants)
    ]

    # Attempting another signup should fail with 400 and "Activity is full"
    response = client.post(
        f"/activities/{activity_name}/signup",
        params={"email": "overflow@mergington.edu"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Activity is full"


def test_unregister_participant_success_and_not_found_cases():
    activity_name = "Programming Class"
    email = "tempstudent@mergington.edu"

    # Ensure the participant is in the list
    if email not in activities[activity_name]["participants"]:
        activities[activity_name]["participants"].append(email)

    # Successful removal
    response = client.delete(
        f"/activities/{activity_name}/signup", params={"email": email}
    )
    assert response.status_code == 200
    assert email not in activities[activity_name]["participants"]

    # Removing again should yield 404 for not registered
    response_missing = client.delete(
        f"/activities/{activity_name}/signup", params={"email": email}
    )
    assert response_missing.status_code == 404
    assert response_missing.json()["detail"] == "Student not registered for this activity"


def test_unregister_fails_for_unknown_activity():
    response = client.delete(
        "/activities/UnknownActivity/signup", params={"email": "x@y.com"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_signup_rejects_invalid_email_format():
    response = client.post(
        "/activities/Chess Club/signup",
        params={"email": "not-a-valid-email"},
    )
    # EmailStr validation should fail and FastAPI should return 422
    assert response.status_code == 422


def test_unregister_rejects_invalid_email_format():
    response = client.delete(
        "/activities/Chess Club/signup",
        params={"email": ""},  # empty string is not a valid email
    )
    assert response.status_code == 422
