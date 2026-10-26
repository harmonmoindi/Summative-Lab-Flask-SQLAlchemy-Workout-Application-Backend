import datetime

from app import app
from models import *

with app.app_context():

    # Reset: delete child rows first, then parents, so the seed can be re-run safely
    print("Clearing old data...")
    WorkoutExercise.query.delete()
    Workout.query.delete()
    Exercise.query.delete()
    db.session.commit()

    print("Creating exercises...")
    squat = Exercise(name="Squat", category="strength", equipment_needed=True)
    bench = Exercise(name="Bench Press", category="strength", equipment_needed=True)
    deadlift = Exercise(name="Deadlift", category="strength", equipment_needed=True)
    pushup = Exercise(name="Push-up", category="strength", equipment_needed=False)
    plank = Exercise(name="Plank", category="strength", equipment_needed=False)
    running = Exercise(name="Treadmill Run", category="cardio", equipment_needed=True)
    jump_rope = Exercise(name="Jump Rope", category="cardio", equipment_needed=True)
    hamstring = Exercise(name="Hamstring Stretch", category="flexibility", equipment_needed=False)
    yoga = Exercise(name="Downward Dog", category="flexibility", equipment_needed=False)
    exercises = [squat, bench, deadlift, pushup, plank, running, jump_rope, hamstring, yoga]
    db.session.add_all(exercises)

    print("Creating workouts...")
    today = datetime.date.today()
    leg_day = Workout(
        date=today - datetime.timedelta(days=6), duration_minutes=60,
        notes="Leg day: focus on form, go heavy on squats.",
    )
    upper_body = Workout(
        date=today - datetime.timedelta(days=4), duration_minutes=45,
        notes="Upper body push session.",
    )
    cardio_core = Workout(
        date=today - datetime.timedelta(days=2), duration_minutes=30,
        notes="Light cardio and core.",
    )
    recovery = Workout(date=today, duration_minutes=25, notes=None)
    workouts = [leg_day, upper_body, cardio_core, recovery]
    db.session.add_all(workouts)
    db.session.commit()  # commit now so every row has an id

    print("Linking exercises to workouts...")
    workout_exercises = [
        WorkoutExercise(workout=leg_day, exercise=squat, reps=8, sets=4),
        WorkoutExercise(workout=leg_day, exercise=deadlift, reps=5, sets=3),
        WorkoutExercise(workout=leg_day, exercise=hamstring, duration_seconds=60, sets=2),
        WorkoutExercise(workout=upper_body, exercise=bench, reps=10, sets=4),
        WorkoutExercise(workout=upper_body, exercise=pushup, reps=20, sets=3),
        WorkoutExercise(workout=upper_body, exercise=plank, duration_seconds=60, sets=3),
        WorkoutExercise(workout=cardio_core, exercise=running, duration_seconds=900),
        WorkoutExercise(workout=cardio_core, exercise=jump_rope, duration_seconds=300, sets=3),
        WorkoutExercise(workout=cardio_core, exercise=plank, duration_seconds=45, sets=3),
        WorkoutExercise(workout=recovery, exercise=yoga, duration_seconds=120, sets=2),
        WorkoutExercise(workout=recovery, exercise=hamstring, duration_seconds=45, sets=2),
    ]
    db.session.add_all(workout_exercises)
    db.session.commit()

    print(
        f"Done! {Exercise.query.count()} exercises, {Workout.query.count()} workouts, "
        f"{WorkoutExercise.query.count()} workout_exercises."
    )