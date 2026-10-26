import datetime
import os

# Must be set before app.py is imported, because the database engine is created on import.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest

from app import app as flask_app
from models import Exercise, Workout, WorkoutExercise, db


@pytest.fixture
def app():
    """A fresh, empty database for every test."""
    flask_app.config["TESTING"] = True
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def sample(app):
    """One workout, two exercises, and one link (Squat is in the workout).

    Returns plain ids so tests don't depend on live ORM objects.
    """
    squat = Exercise(name="Squat", category="strength", equipment_needed=True)
    run = Exercise(name="Run", category="cardio", equipment_needed=False)
    workout = Workout(date=datetime.date(2026, 10, 20), duration_minutes=60, notes="Leg day")
    db.session.add_all([squat, run, workout])
    db.session.commit()
    db.session.add(WorkoutExercise(workout=workout, exercise=squat, reps=8, sets=4))
    db.session.commit()
    return {"workout_id": workout.id, "squat_id": squat.id, "run_id": run.id}