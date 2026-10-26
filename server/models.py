import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import validates

db = SQLAlchemy()

""" Allowed exercise categories. Shared by the model, the database constraint,
 and the schema, so there is one place to change the list. """
CATEGORIES = ("strength", "cardio", "flexibility", "balance", "mobility", "other")


def _check_positive_int(field, value, allow_none=False):
    """Shared validation."""
    if value is None:
        if allow_none:
            return None
        raise ValueError(f"{field} is required.")
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be a whole number.")
    if value <= 0:
        raise ValueError(f"{field} must be greater than 0.")
    return value


class Exercise(db.Model):
    """A reusable exercise (e.g. Squat) that can appear in many workouts."""
    __tablename__ = 'exercises'
    __table_args__ = (
        # Table constraints (enforced by the database itself)
        db.UniqueConstraint('name', name='uq_exercises_name'),
        db.CheckConstraint('length(trim(name)) > 0', name='ck_exercises_name_not_blank'),
        db.CheckConstraint(
            "category IN (" + ", ".join(f"'{c}'" for c in CATEGORIES) + ")",
            name='ck_exercises_category',
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    equipment_needed = db.Column(db.Boolean, nullable=False, default=False)

    # Deleting an exercise also deletes its WorkoutExercise rows
    workout_exercises = db.relationship(
        'WorkoutExercise', back_populates='exercise', cascade='all, delete-orphan'
    )
    # exercise.workouts -> every Workout this exercise appears in
    workouts = association_proxy('workout_exercises', 'workout')

    @validates('name')
    def validate_name(self, key, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Exercise name is required.")
        value = value.strip()
        if len(value) > 100:
            raise ValueError("Exercise name must be 100 characters or fewer.")
        return value

    @validates('category')
    def validate_category(self, key, value):
        if not isinstance(value, str) or value.strip().lower() not in CATEGORIES:
            raise ValueError(f"Category must be one of: {', '.join(CATEGORIES)}.")
        return value.strip().lower()

    @validates('equipment_needed')
    def validate_equipment_needed(self, key, value):
        if not isinstance(value, bool):
            raise ValueError("equipment_needed must be true or false.")
        return value

    def __repr__(self):
        return f"<Exercise {self.id}: {self.name}>"


class Workout(db.Model):
    """A single training session on a given date."""
    __tablename__ = 'workouts'
    __table_args__ = (
        db.CheckConstraint('duration_minutes > 0', name='ck_workouts_duration_positive'),
    )

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.Text)

    # Deleting a workout also deletes its WorkoutExercise rows
    workout_exercises = db.relationship(
        'WorkoutExercise', back_populates='workout', cascade='all, delete-orphan'
    )
    # workout.exercises -> every Exercise in this workout
    exercises = association_proxy('workout_exercises', 'exercise')

    @validates('date')
    def validate_date(self, key, value):
        # datetime is a subclass of date, so exclude it explicitly
        if not isinstance(value, datetime.date) or isinstance(value, datetime.datetime):
            raise ValueError("date must be a calendar date (YYYY-MM-DD).")
        return value

    @validates('duration_minutes')
    def validate_duration(self, key, value):
        return _check_positive_int('duration_minutes', value)

    @validates('notes')
    def validate_notes(self, key, value):
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("notes must be text.")
        value = value.strip()
        if len(value) > 1000:
            raise ValueError("notes must be 1000 characters or fewer.")
        return value or None

    def __repr__(self):
        return f"<Workout {self.id}: {self.date}>"


class WorkoutExercise(db.Model):
    """Join table: one exercise performed in one workout, with its reps/sets/duration."""
    __tablename__ = 'workout_exercises'
    __table_args__ = (
        db.UniqueConstraint('workout_id', 'exercise_id', name='uq_workout_exercises_pair'),
        db.CheckConstraint('reps IS NULL OR reps > 0', name='ck_workout_exercises_reps_positive'),
        db.CheckConstraint('sets IS NULL OR sets > 0', name='ck_workout_exercises_sets_positive'),
        db.CheckConstraint(
            'duration_seconds IS NULL OR duration_seconds > 0',
            name='ck_workout_exercises_duration_positive',
        ),
        db.CheckConstraint(
            'reps IS NOT NULL OR sets IS NOT NULL OR duration_seconds IS NOT NULL',
            name='ck_workout_exercises_has_measure',
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    workout_id = db.Column(
        db.Integer, db.ForeignKey('workouts.id', ondelete='CASCADE'), nullable=False
    )
    exercise_id = db.Column(
        db.Integer, db.ForeignKey('exercises.id', ondelete='CASCADE'), nullable=False
    )
    reps = db.Column(db.Integer)
    sets = db.Column(db.Integer)
    duration_seconds = db.Column(db.Integer)

    workout = db.relationship('Workout', back_populates='workout_exercises')
    exercise = db.relationship('Exercise', back_populates='workout_exercises')

    @validates('reps', 'sets', 'duration_seconds')
    def validate_measure(self, key, value):
        return _check_positive_int(key, value, allow_none=True)

    def __repr__(self):
        return f"<WorkoutExercise workout={self.workout_id} exercise={self.exercise_id}>"