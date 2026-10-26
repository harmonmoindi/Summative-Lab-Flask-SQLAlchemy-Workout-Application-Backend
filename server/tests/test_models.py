"""Tests for model validations, table constraints, relationships, and cascades."""
import datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from models import Exercise, Workout, WorkoutExercise, db


# --- Model validations (@validates) -------------------------------------------
@pytest.mark.parametrize(
    "kwargs",
    [
        {"name": "", "category": "cardio"},
        {"name": "   ", "category": "cardio"},
        {"name": "A" * 101, "category": "cardio"},
        {"name": "Plank", "category": "magic"},
        {"name": "Plank", "category": "strength", "equipment_needed": "yes"},
    ],
)
def test_exercise_rejects_invalid_values(kwargs):
    with pytest.raises(ValueError):
        Exercise(**kwargs)


def test_exercise_normalizes_name_and_category():
    exercise = Exercise(name="  Push-up ", category=" Strength ")
    assert exercise.name == "Push-up"
    assert exercise.category == "strength"


@pytest.mark.parametrize("duration", [0, -5, 1.5, "30", True, None])
def test_workout_rejects_invalid_duration(duration):
    with pytest.raises(ValueError):
        Workout(date=datetime.date.today(), duration_minutes=duration)


@pytest.mark.parametrize("bad_date", ["2026-10-20", None, datetime.datetime.now()])
def test_workout_rejects_invalid_date(bad_date):
    with pytest.raises(ValueError):
        Workout(date=bad_date, duration_minutes=30)


def test_workout_rejects_overlong_notes():
    with pytest.raises(ValueError):
        Workout(date=datetime.date.today(), duration_minutes=30, notes="x" * 1001)


@pytest.mark.parametrize("field", ["reps", "sets", "duration_seconds"])
@pytest.mark.parametrize("value", [0, -1, 2.5, "3", True])
def test_workout_exercise_rejects_invalid_measures(field, value):
    with pytest.raises(ValueError):
        WorkoutExercise(**{field: value})


# --- Table constraints (enforced by the database, so we bypass the validators) --
def run_sql(sql):
    db.session.execute(text(sql))
    db.session.commit()


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO workouts (date, duration_minutes) VALUES ('2026-01-01', 0)",
        "INSERT INTO exercises (name, category, equipment_needed) VALUES ('X', 'magic', 1)",
        "INSERT INTO exercises (name, category, equipment_needed) VALUES ('   ', 'cardio', 1)",
        "INSERT INTO workout_exercises (workout_id, exercise_id, reps) VALUES (1, 1, -3)",
        "INSERT INTO workout_exercises (workout_id, exercise_id) VALUES (1, 2)",  # no reps/sets/duration
    ],
)
def test_database_check_constraints_reject_bad_rows(sample, sql):
    with pytest.raises(IntegrityError):
        run_sql(sql)
    db.session.rollback()


def test_exercise_names_must_be_unique(sample):
    db.session.add(Exercise(name="Squat", category="cardio"))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_same_exercise_cannot_be_added_to_a_workout_twice(sample):
    workout = db.session.get(Workout, sample["workout_id"])
    squat = db.session.get(Exercise, sample["squat_id"])
    db.session.add(WorkoutExercise(workout=workout, exercise=squat, reps=5))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


# --- Relationships -----------------------------------------------------------
def test_workout_has_many_exercises_through_workout_exercises(sample):
    workout = db.session.get(Workout, sample["workout_id"])
    assert [e.name for e in workout.exercises] == ["Squat"]
    assert len(workout.workout_exercises) == 1
    assert workout.workout_exercises[0].reps == 8


def test_exercise_has_many_workouts_through_workout_exercises(sample):
    squat = db.session.get(Exercise, sample["squat_id"])
    assert [w.id for w in squat.workouts] == [sample["workout_id"]]
    assert list(db.session.get(Exercise, sample["run_id"]).workouts) == []


def test_workout_exercise_belongs_to_both_parents(sample):
    link = WorkoutExercise.query.first()
    assert link.workout.id == sample["workout_id"]
    assert link.exercise.name == "Squat"


# --- Cascades ----------------------------------------------------------------
def test_deleting_a_workout_deletes_its_workout_exercises(sample):
    db.session.delete(db.session.get(Workout, sample["workout_id"]))
    db.session.commit()
    assert WorkoutExercise.query.count() == 0
    assert Exercise.query.count() == 2  # exercises themselves are kept


def test_deleting_an_exercise_deletes_its_workout_exercises(sample):
    db.session.delete(db.session.get(Exercise, sample["squat_id"]))
    db.session.commit()
    assert WorkoutExercise.query.count() == 0
    assert Workout.query.count() == 1  # the workout itself is kept