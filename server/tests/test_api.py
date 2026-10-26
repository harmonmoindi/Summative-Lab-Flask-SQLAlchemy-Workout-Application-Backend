"""Tests for every endpoint: success paths, validation errors, and 404/409 cases."""
from models import Exercise, Workout, WorkoutExercise


# --- Workouts ----------------------------------------------------------------
def test_get_workouts_lists_all(client, sample):
    response = client.get("/workouts")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]["duration_minutes"] == 60
    assert data[0]["date"] == "2026-10-20"


def test_get_workouts_empty(client, app):
    response = client.get("/workouts")
    assert response.status_code == 200
    assert response.get_json() == []


def test_get_workout_includes_exercises_with_reps_sets_duration(client, sample):
    response = client.get(f"/workouts/{sample['workout_id']}")
    assert response.status_code == 200
    data = response.get_json()
    link = data["workout_exercises"][0]
    assert link["reps"] == 8
    assert link["sets"] == 4
    assert link["duration_seconds"] is None
    assert link["exercise"]["name"] == "Squat"


def test_get_workout_not_found(client, app):
    response = client.get("/workouts/999")
    assert response.status_code == 404
    assert "not found" in response.get_json()["error"]


def test_create_workout(client, app):
    payload = {"date": "2026-10-30", "duration_minutes": 50, "notes": "Upper body"}
    response = client.post("/workouts", json=payload)
    assert response.status_code == 201
    created = response.get_json()
    assert created["id"] is not None
    assert created["notes"] == "Upper body"
    assert Workout.query.count() == 1


def test_create_workout_notes_are_optional(client, app):
    response = client.post("/workouts", json={"date": "2026-10-30", "duration_minutes": 20})
    assert response.status_code == 201
    assert response.get_json()["notes"] is None


def test_create_workout_missing_fields(client, app):
    response = client.post("/workouts", json={})
    assert response.status_code == 400
    errors = response.get_json()["errors"]
    assert "date" in errors and "duration_minutes" in errors


def test_create_workout_invalid_values(client, app):
    bad_payloads = [
        {"date": "not-a-date", "duration_minutes": 30},
        {"date": "2026-10-30", "duration_minutes": 0},
        {"date": "2026-10-30", "duration_minutes": -5},
        {"date": "2026-10-30", "duration_minutes": "30"},
        {"date": "2026-10-30", "duration_minutes": 5000},
        {"id": 7, "date": "2026-10-30", "duration_minutes": 30},  # clients can't set id
    ]
    for payload in bad_payloads:
        assert client.post("/workouts", json=payload).status_code == 400, payload
    assert Workout.query.count() == 0


def test_create_workout_rejects_non_json_body(client, app):
    response = client.post("/workouts", data="nope", content_type="application/json")
    assert response.status_code == 400


def test_delete_workout_also_deletes_its_workout_exercises(client, sample):
    response = client.delete(f"/workouts/{sample['workout_id']}")
    assert response.status_code == 204
    assert Workout.query.count() == 0
    assert WorkoutExercise.query.count() == 0
    assert Exercise.query.count() == 2


def test_delete_workout_not_found(client, app):
    assert client.delete("/workouts/999").status_code == 404


# --- Exercises ---------------------------------------------------------------
def test_get_exercises_lists_all_sorted_by_name(client, sample):
    response = client.get("/exercises")
    assert response.status_code == 200
    assert [e["name"] for e in response.get_json()] == ["Run", "Squat"]


def test_get_exercise_includes_workouts(client, sample):
    response = client.get(f"/exercises/{sample['squat_id']}")
    assert response.status_code == 200
    link = response.get_json()["workout_exercises"][0]
    assert link["workout"]["id"] == sample["workout_id"]
    assert link["reps"] == 8


def test_get_exercise_with_no_workouts(client, sample):
    response = client.get(f"/exercises/{sample['run_id']}")
    assert response.status_code == 200
    assert response.get_json()["workout_exercises"] == []


def test_get_exercise_not_found(client, app):
    assert client.get("/exercises/999").status_code == 404


def test_create_exercise(client, app):
    response = client.post(
        "/exercises", json={"name": "  Lunge ", "category": "Strength", "equipment_needed": False}
    )
    assert response.status_code == 201
    created = response.get_json()
    assert created["name"] == "Lunge"  # trimmed
    assert created["category"] == "strength"  # lowercased


def test_create_exercise_equipment_defaults_to_false(client, app):
    response = client.post("/exercises", json={"name": "Burpee", "category": "cardio"})
    assert response.status_code == 201
    assert response.get_json()["equipment_needed"] is False


def test_create_exercise_invalid_values(client, app):
    bad_payloads = [
        {"category": "cardio"},  # missing name
        {"name": "X"},  # missing category
        {"name": "   ", "category": "cardio"},
        {"name": "X", "category": "magic"},
        {"name": "A" * 101, "category": "cardio"},
        {"name": "X", "category": "cardio", "equipment_needed": "maybe"},
    ]
    for payload in bad_payloads:
        assert client.post("/exercises", json=payload).status_code == 400, payload
    assert Exercise.query.count() == 0


def test_create_exercise_duplicate_name_is_rejected_case_insensitively(client, sample):
    response = client.post("/exercises", json={"name": "squat", "category": "strength"})
    assert response.status_code == 409
    assert Exercise.query.count() == 2


def test_delete_exercise_also_deletes_its_workout_exercises(client, sample):
    response = client.delete(f"/exercises/{sample['squat_id']}")
    assert response.status_code == 204
    assert WorkoutExercise.query.count() == 0
    assert Workout.query.count() == 1


def test_delete_exercise_not_found(client, app):
    assert client.delete("/exercises/999").status_code == 404


# --- Adding an exercise to a workout -------------------------------------------
def add_url(workout_id, exercise_id):
    return f"/workouts/{workout_id}/exercises/{exercise_id}/workout_exercises"


def test_add_exercise_to_workout(client, sample):
    response = client.post(
        add_url(sample["workout_id"], sample["run_id"]), json={"duration_seconds": 900}
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["duration_seconds"] == 900
    assert data["reps"] is None
    assert data["exercise"]["name"] == "Run"
    assert data["workout"]["id"] == sample["workout_id"]
    assert WorkoutExercise.query.count() == 2


def test_add_exercise_with_reps_and_sets(client, sample):
    response = client.post(
        add_url(sample["workout_id"], sample["run_id"]), json={"reps": 10, "sets": 3}
    )
    assert response.status_code == 201
    assert response.get_json()["sets"] == 3


def test_add_exercise_requires_at_least_one_measure(client, sample):
    response = client.post(add_url(sample["workout_id"], sample["run_id"]), json={})
    assert response.status_code == 400
    assert "_schema" in response.get_json()["errors"]


def test_add_exercise_rejects_invalid_measures(client, sample):
    for payload in [{"reps": 0}, {"reps": -1}, {"sets": 1.5}, {"duration_seconds": "60"}]:
        response = client.post(add_url(sample["workout_id"], sample["run_id"]), json=payload)
        assert response.status_code == 400, payload
    assert WorkoutExercise.query.count() == 1


def test_add_exercise_twice_to_same_workout_is_rejected(client, sample):
    response = client.post(add_url(sample["workout_id"], sample["squat_id"]), json={"reps": 5})
    assert response.status_code == 409
    assert WorkoutExercise.query.count() == 1


def test_add_exercise_unknown_workout_or_exercise(client, sample):
    assert client.post(add_url(999, sample["run_id"]), json={"reps": 5}).status_code == 404
    assert client.post(add_url(sample["workout_id"], 999), json={"reps": 5}).status_code == 404


# --- Error handlers ----------------------------------------------------------
def test_unknown_route_returns_json_404(client, app):
    response = client.get("/nope")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Not found"}


def test_unsupported_method_returns_json_405(client, app):
    response = client.put("/workouts")
    assert response.status_code == 405
    assert response.get_json() == {"error": "Method not allowed"}