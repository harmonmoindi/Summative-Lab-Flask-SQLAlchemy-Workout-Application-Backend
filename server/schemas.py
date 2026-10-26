from marshmallow import Schema, ValidationError, fields, pre_load, validate, validates, validates_schema

from models import CATEGORIES


class ExerciseSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    category = fields.Str(required=True, validate=validate.OneOf(CATEGORIES))
    equipment_needed = fields.Bool(load_default=False)

    @pre_load
    def normalize(self, data, **kwargs):
        """Trim the name and lowercase the category before validating them."""
        if isinstance(data, dict):
            data = dict(data)
            if isinstance(data.get('name'), str):
                data['name'] = data['name'].strip()
            if isinstance(data.get('category'), str):
                data['category'] = data['category'].strip().lower()
        return data

    @validates('name')
    def validate_name(self, value):
        if not value.strip():
            raise ValidationError("Name cannot be blank.")


class WorkoutSchema(Schema):
    id = fields.Int(dump_only=True)
    date = fields.Date(required=True)
    duration_minutes = fields.Int(
        required=True,
        strict=True,
        validate=validate.Range(min=1, max=1440, error="Duration must be between 1 and 1440 minutes."),
    )
    notes = fields.Str(allow_none=True, load_default=None, validate=validate.Length(max=1000))


class WorkoutExerciseSchema(Schema):
    id = fields.Int(dump_only=True)
    workout_id = fields.Int(dump_only=True)
    exercise_id = fields.Int(dump_only=True)
    reps = fields.Int(allow_none=True, load_default=None, strict=True, validate=validate.Range(min=1))
    sets = fields.Int(allow_none=True, load_default=None, strict=True, validate=validate.Range(min=1))
    duration_seconds = fields.Int(
        allow_none=True, load_default=None, strict=True, validate=validate.Range(min=1)
    )
    # Output only: nested details used when displaying results
    exercise = fields.Nested(ExerciseSchema, dump_only=True)
    workout = fields.Nested(WorkoutSchema, dump_only=True)

    @validates_schema
    def require_a_measure(self, data, **kwargs):
        """An exercise in a workout needs at least one of reps, sets, or duration."""
        if all(data.get(key) is None for key in ('reps', 'sets', 'duration_seconds')):
            raise ValidationError(
                "Provide at least one of reps, sets, or duration_seconds.", "_schema"
            )


class WorkoutDetailSchema(WorkoutSchema):
    """A workout plus its exercises, including reps/sets/duration for each."""
    workout_exercises = fields.Nested(
        WorkoutExerciseSchema, many=True, exclude=('workout',), dump_only=True
    )


class ExerciseDetailSchema(ExerciseSchema):
    """An exercise plus the workouts it appears in (with reps/sets/duration)."""
    workout_exercises = fields.Nested(
        WorkoutExerciseSchema, many=True, exclude=('exercise',), dump_only=True
    )