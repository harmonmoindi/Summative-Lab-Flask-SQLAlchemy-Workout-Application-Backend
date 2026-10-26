import os

from flask import Flask, make_response, request
from flask_migrate import Migrate
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from models import *
from schemas import (
    ExerciseDetailSchema,
    ExerciseSchema,
    WorkoutDetailSchema,
    WorkoutExerciseSchema,
    WorkoutSchema,
)

app = Flask(__name__)
# DATABASE_URL lets the test suite swap in a throwaway database
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.json.compact = False  # readable JSON responses

migrate = Migrate(app, db)

db.init_app(app)

# One schema instance per use
workout_schema = WorkoutSchema()
workouts_schema = WorkoutSchema(many=True)
workout_detail_schema = WorkoutDetailSchema()
exercise_schema = ExerciseSchema()
exercises_schema = ExerciseSchema(many=True)
exercise_detail_schema = ExerciseDetailSchema()
workout_exercise_schema = WorkoutExerciseSchema()


# Error handlers
# ----------------------
def error_response(message, status):
    return make_response({'error': message}, status)


def get_json_body():
    """Return the JSON body as a dict, or raise a ValidationError."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError({'_schema': ['Request body must be a JSON object.']})
    return data


@app.errorhandler(ValidationError)
def handle_validation_error(err):
    """Any schema validation failure becomes a 400 with per-field messages."""
    return make_response({'errors': err.messages}, 400)


@app.errorhandler(404)
def handle_not_found(_err):
    return error_response('Not found', 404)


@app.errorhandler(405)
def handle_method_not_allowed(_err):
    return error_response('Method not allowed', 405)


def save(obj):
    """Add obj and commit. Returns an error response on failure, otherwise None.

    ValueError  -> a model @validates rule rejected the data (400)
    IntegrityError -> a database constraint rejected the data (409)
    """
    try:
        db.session.add(obj)
        db.session.commit()
    except ValueError as err:
        db.session.rollback()
        return error_response(str(err), 400)
    except IntegrityError:
        db.session.rollback()
        return error_response('That record conflicts with existing data.', 409)
    return None


# Workouts
# ------------
@app.route('/workouts', methods=['GET'])
def get_workouts():
    workouts = Workout.query.order_by(Workout.date.desc(), Workout.id).all()
    return make_response(workouts_schema.dump(workouts), 200)


@app.route('/workouts/<int:id>', methods=['GET'])
def get_workout(id):
    workout = db.session.get(Workout, id)
    if workout is None:
        return error_response(f'Workout {id} not found', 404)
    return make_response(workout_detail_schema.dump(workout), 200)


@app.route('/workouts', methods=['POST'])
def create_workout():
    data = workout_schema.load(get_json_body())
    try:
        workout = Workout(**data)
    except ValueError as err:
        return error_response(str(err), 400)
    failure = save(workout)
    if failure:
        return failure
    return make_response(workout_schema.dump(workout), 201)


@app.route('/workouts/<int:id>', methods=['DELETE'])
def delete_workout(id):
    workout = db.session.get(Workout, id)
    if workout is None:
        return error_response(f'Workout {id} not found', 404)
    # The relationship cascade also deletes this workout's WorkoutExercises
    db.session.delete(workout)
    db.session.commit()
    return make_response('', 204)


# Exercises
# ---------------
@app.route('/exercises', methods=['GET'])
def get_exercises():
    exercises = Exercise.query.order_by(Exercise.name).all()
    return make_response(exercises_schema.dump(exercises), 200)


@app.route('/exercises/<int:id>', methods=['GET'])
def get_exercise(id):
    exercise = db.session.get(Exercise, id)
    if exercise is None:
        return error_response(f'Exercise {id} not found', 404)
    return make_response(exercise_detail_schema.dump(exercise), 200)


@app.route('/exercises', methods=['POST'])
def create_exercise():
    data = exercise_schema.load(get_json_body())

    # Friendly duplicate check (case-insensitive); the unique constraint is the backstop
    duplicate = Exercise.query.filter(db.func.lower(Exercise.name) == data['name'].lower()).first()
    if duplicate:
        return error_response(f"An exercise named '{duplicate.name}' already exists.", 409)

    try:
        exercise = Exercise(**data)
    except ValueError as err:
        return error_response(str(err), 400)
    failure = save(exercise)
    if failure:
        return failure
    return make_response(exercise_schema.dump(exercise), 201)


@app.route('/exercises/<int:id>', methods=['DELETE'])
def delete_exercise(id):
    exercise = db.session.get(Exercise, id)
    if exercise is None:
        return error_response(f'Exercise {id} not found', 404)
    # The relationship cascade also deletes this exercise's WorkoutExercises
    db.session.delete(exercise)
    db.session.commit()
    return make_response('', 204)


# Adding an exercise to a workout
# -------------------------------------
@app.route(
    '/workouts/<int:workout_id>/exercises/<int:exercise_id>/workout_exercises',
    methods=['POST'],
)
def add_exercise_to_workout(workout_id, exercise_id):
    workout = db.session.get(Workout, workout_id)
    if workout is None:
        return error_response(f'Workout {workout_id} not found', 404)
    exercise = db.session.get(Exercise, exercise_id)
    if exercise is None:
        return error_response(f'Exercise {exercise_id} not found', 404)

    data = workout_exercise_schema.load(get_json_body())

    already_added = WorkoutExercise.query.filter_by(
        workout_id=workout_id, exercise_id=exercise_id
    ).first()
    if already_added:
        return error_response('That exercise is already part of this workout.', 409)

    try:
        workout_exercise = WorkoutExercise(workout=workout, exercise=exercise, **data)
    except ValueError as err:
        return error_response(str(err), 400)
    failure = save(workout_exercise)
    if failure:
        return failure
    return make_response(workout_exercise_schema.dump(workout_exercise), 201)


if __name__ == '__main__':
    app.run(port=5555, debug=True)