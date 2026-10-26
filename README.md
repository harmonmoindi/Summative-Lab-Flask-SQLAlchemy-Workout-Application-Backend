# Workout Application Backend

A REST API for a workout-tracking app used by personal trainers, built with **Flask**, **SQLAlchemy**, and **Marshmallow**.

## Project Description

Trainers can record **workouts** and build a library of reusable **exercises**. An exercise (for example, _Squat_) is created once and can then be added to many workouts, with the reps, sets, and/or duration recorded for each workout it appears in.

The API follows REST conventions and validates data at three levels:

| Level                  | Purpose                                                              | Where                                 |
| ---------------------- | -------------------------------------------------------------------- | ------------------------------------- |
| **Table constraints**  | The database refuses bad rows, no matter how they arrive             | `server/models.py` (`__table_args__`) |
| **Model validations**  | Python rules (`@validates`) run when an object is created or changed | `server/models.py`                    |
| **Schema validations** | Marshmallow checks every request body before it reaches the database | `server/schemas.py`                   |

### Data model

- **Exercise**: `id`, `name`, `category`, `equipment_needed`
- **Workout**: `id`, `date`, `duration_minutes`, `notes`
- **WorkoutExercise** (join table): `id`, `workout_id`, `exercise_id`, `reps`, `sets`, `duration_seconds`

Relationships:

- A workout has many exercises through `WorkoutExercise`, and an exercise has many workouts through `WorkoutExercise`.
- A `WorkoutExercise` belongs to one workout and one exercise.
- Deleting a workout or an exercise also deletes its `WorkoutExercise` rows.

### Validation rules

- **Exercise:** the name is required, at most 100 characters, and unique (case-insensitive). The category must be one of `strength`, `cardio`, `flexibility`, `balance`, `mobility`, or `other` (input is trimmed and lowercased). `equipment_needed` defaults to `false`.
- **Workout:** the date must be a valid `YYYY-MM-DD` date. `duration_minutes` must be a whole number from 1 to 1440. Notes are optional, up to 1000 characters.
- **WorkoutExercise:** `reps`, `sets`, and `duration_seconds` must be whole numbers greater than 0, and at least one of them is required. The same exercise can only be added to a given workout once.
- Request bodies containing unknown fields (such as `id`) are rejected.

## Installation

**Requirements:** Python 3.12 and [pipenv](https://pipenv.pypa.io/). The `Pipfile` pins Python 3.12; if you use a different version, change `python_version` in the Pipfile.

```bash
git clone https://github.com/harmonmoindi/Summative-Lab-Flask-SQLAlchemy-Workout-Application-Backend.git
cd Summative-Lab-Flask-SQLAlchemy-Workout-Application-Backend

pipenv install --dev      # installs the dependencies (and pytest for the tests)
pipenv shell              # activates the virtual environment

cd server
flask db upgrade head     # creates the database from the migrations in server/migrations
python seed.py            # fills it with example exercises and workouts
```

The migrations are already included in the repository. You only need `flask db init` and `flask db migrate -m "message"` if you change the models and want to generate a new migration.

`seed.py` clears the tables before adding data, so you can run it again at any time to reset the database without creating duplicates.

## Running the App

From the `server/` folder, with the virtual environment active:

```bash
python app.py
```

or

```bash
flask run -p 5555
```

The API is then available at **http://127.0.0.1:5555**. (Port 5555 is used because macOS often reserves Flask's default port 5000 for AirPlay.)

## API Endpoints

All requests and responses use JSON.

| Method | Endpoint                                                           | Description                                                                          |
| ------ | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------ |
| GET    | `/workouts`                                                        | List all workouts (newest first)                                                     |
| GET    | `/workouts/<id>`                                                   | Show one workout with its exercises, including the reps, sets, and duration for each |
| POST   | `/workouts`                                                        | Create a workout                                                                     |
| DELETE | `/workouts/<id>`                                                   | Delete a workout and its associated workout exercises                                |
| GET    | `/exercises`                                                       | List all exercises (alphabetical)                                                    |
| GET    | `/exercises/<id>`                                                  | Show one exercise with the workouts it appears in                                    |
| POST   | `/exercises`                                                       | Create an exercise                                                                   |
| DELETE | `/exercises/<id>`                                                  | Delete an exercise and its associated workout exercises                              |
| POST   | `/workouts/<workout_id>/exercises/<exercise_id>/workout_exercises` | Add an existing exercise to a workout, with reps, sets, and/or duration              |

### Status codes

| Code  | Meaning                                                                       |
| ----- | ----------------------------------------------------------------------------- |
| `200` | Success (GET)                                                                 |
| `201` | Created (POST)                                                                |
| `204` | Deleted (DELETE), no body returned                                            |
| `400` | Invalid input                                                                 |
| `404` | Workout, exercise, or route not found                                         |
| `409` | Conflict: duplicate exercise name, or the exercise is already in that workout |

Schema validation failures return `{"errors": {"field": ["message"]}}`. Other errors return `{"error": "message"}`.

### Request and response examples

**Create a workout**

```http
POST /workouts
{"date": "2026-10-30", "duration_minutes": 50, "notes": "Upper body"}
```

```json
{ "date": "2026-10-30", "duration_minutes": 50, "id": 5, "notes": "Upper body" }
```

`notes` is optional.

**Create an exercise**

```http
POST /exercises
{"name": "Lunge", "category": "strength", "equipment_needed": false}
```

```json
{ "category": "strength", "equipment_needed": false, "id": 10, "name": "Lunge" }
```

**Add an exercise to a workout.** Send at least one of `reps`, `sets`, or `duration_seconds`.

```http
POST /workouts/5/exercises/10/workout_exercises
{"reps": 12, "sets": 3}
```

```json
{
  "duration_seconds": null,
  "exercise": {
    "category": "strength",
    "equipment_needed": false,
    "id": 10,
    "name": "Lunge"
  },
  "exercise_id": 10,
  "id": 12,
  "reps": 12,
  "sets": 3,
  "workout": {
    "date": "2026-10-30",
    "duration_minutes": 50,
    "id": 5,
    "notes": "Upper body"
  },
  "workout_id": 5
}
```

**Show a workout with its exercises**

```http
GET /workouts/5
```

```json
{
  "date": "2026-10-30",
  "duration_minutes": 50,
  "id": 5,
  "notes": "Upper body",
  "workout_exercises": [
    {
      "duration_seconds": null,
      "exercise": {
        "category": "strength",
        "equipment_needed": false,
        "id": 10,
        "name": "Lunge"
      },
      "exercise_id": 10,
      "id": 12,
      "reps": 12,
      "sets": 3,
      "workout_id": 5
    }
  ]
}
```

**Validation error**

```http
POST /exercises
{"name": "Plank", "category": "magic"}
```

```json
{
  "errors": {
    "category": [
      "Must be one of: strength, cardio, flexibility, balance, mobility, other."
    ]
  }
}
```

## Running the Tests

The test suite uses a temporary in-memory database, so it never touches your real data.

```bash
cd server
pytest
```

- `tests/test_models.py`: model validations, database table constraints, relationships, and cascade deletes
- `tests/test_api.py`: every endpoint, including validation errors and 404/409 responses

## Project Structure

```
.
├── Pipfile / Pipfile.lock
├── README.md
└── server/
    ├── app.py          # Flask app, routes, error handlers
    ├── models.py       # SQLAlchemy models, relationships, constraints, validations
    ├── schemas.py      # Marshmallow schemas (serialization, deserialization, validation)
    ├── seed.py         # Resets and fills the database with example data
    ├── conftest.py     # Test fixtures
    ├── pytest.ini
    ├── migrations/     # Alembic/Flask-Migrate database migrations
    └── tests/
        ├── test_models.py
        └── test_api.py
```
