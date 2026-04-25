from datetime import date, timedelta, datetime
from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from app.extensions import db
from app.models import Habit, HabitCheck

habits_bp = Blueprint("habits", __name__, url_prefix="/habits")


def get_week_dates():
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    return [start_of_week + timedelta(days=i) for i in range(7)]


def get_day_letter(weekday_index):
    letters = ["L", "M", "X", "J", "V", "S", "D"]
    return letters[weekday_index]

def calculate_weekly_streak(habit, all_checks_map):
    completed_dates = [d for d, c in all_checks_map.items() if c.completed]
    if not completed_dates:
        return 0

    weekly_counts = {}
    for d in completed_dates:
        year, week, _ = d.isocalendar()
        weekly_counts[(year, week)] = weekly_counts.get((year, week), 0) + 1

    curr_year, curr_week, _ = date.today().isocalendar()
    streak = 0
    
    # Evaluar semana actual
    if weekly_counts.get((curr_year, curr_week), 0) >= habit.weekly_goal:
        streak += 1
        check_date = date.today() - timedelta(days=7)
    else:
        # Si aún no cumplió la de esta semana, evalúa desde la semana pasada sin cortar la racha
        check_date = date.today() - timedelta(days=7)

    # Evaluar semanas anteriores
    while True:
        y, w, _ = check_date.isocalendar()
        if weekly_counts.get((y, w), 0) >= habit.weekly_goal:
            streak += 1
            check_date -= timedelta(days=7)
        else:
            break

    return streak


@habits_bp.route("/", methods=["GET", "POST"])
def habits_page():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        color = request.form.get("color", "#22c55e").strip()
        weekly_goal = request.form.get("weekly_goal", 3)

        if name:
            try:
                weekly_goal = int(weekly_goal)
            except ValueError:
                weekly_goal = 3

            weekly_goal = max(1, min(7, weekly_goal))

            new_habit = Habit(name=name, color=color, weekly_goal=weekly_goal)
            db.session.add(new_habit)
            db.session.commit()

        return redirect(url_for("habits.habits_page"))

    week_dates = get_week_dates()
    habits = Habit.query.order_by(Habit.position).all()

    # --- LÓGICA DEL MAPA DE CALOR GLOBAL ---
    heatmap_days_count = 90
    today = date.today()
    heatmap_start = today - timedelta(days=heatmap_days_count - 1)
    
    # Orden invertido: desde hoy hacia el pasado
    heatmap_dates = [today - timedelta(days=i) for i in range(heatmap_days_count)]

    
    recent_checks = HabitCheck.query.filter(
        HabitCheck.date >= heatmap_start, 
        HabitCheck.completed == True
    ).all()
    
    completions_per_day = {}
    for check in recent_checks:
        completions_per_day[check.date] = completions_per_day.get(check.date, 0) + 1
        
    global_heatmap = []
    max_habits = len(habits) if habits else 1
    
    for hd in heatmap_dates:
        count = completions_per_day.get(hd, 0)
        intensity = 0
        if count > 0:
            ratio = count / max_habits
            if ratio <= 0.25: intensity = 1
            elif ratio <= 0.5: intensity = 2
            elif ratio <= 0.75: intensity = 3
            else: intensity = 4
            
        global_heatmap.append({
            "date": hd,
            "count": count,
            "intensity": intensity
        })
    # ---------------------------------------

    habits_data = []

    for habit in habits:
        all_checks_map = {check.date: check for check in habit.checks}

        week_days = []
        completed_count = 0

        for day_date in week_dates:
            completed = day_date in all_checks_map and all_checks_map[day_date].completed
            if completed:
                completed_count += 1

            week_days.append({
                "date": day_date,
                "letter": get_day_letter(day_date.weekday()),
                "completed": completed,
                "is_today": day_date == date.today()
            })

        # Si tenés tu función calculate_weekly_streak arriba, la dejamos; si no, podés poner streak = 0
        streak = calculate_weekly_streak(habit, all_checks_map) if 'calculate_weekly_streak' in globals() else 0

        progress_percent = 0
        if habit.weekly_goal > 0:
            progress_percent = min((completed_count / habit.weekly_goal) * 100, 100)

        habits_data.append({
            "habit": habit,
            "week_days": week_days,
            "completed_count": completed_count,
            "progress_percent": progress_percent,
            "streak": streak
        })

    chart_labels = [item["habit"].name for item in habits_data]
    chart_completed = [item["completed_count"] for item in habits_data]
    chart_goals = [item["habit"].weekly_goal for item in habits_data]
    chart_colors = [item["habit"].color for item in habits_data]

    return render_template(
        "habits/habits.html",
        habits_data=habits_data,
        chart_labels=chart_labels,
        chart_completed=chart_completed,
        chart_goals=chart_goals,
        chart_colors=chart_colors,
        global_heatmap=global_heatmap
    )

@habits_bp.route("/toggle/<int:habit_id>/<day_str>", methods=["POST"])
def toggle_habit_day(habit_id, day_str):
    habit = Habit.query.get_or_404(habit_id)

    try:
        target_date = datetime.strptime(day_str, "%Y-%m-%d").date()
    except ValueError:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"ok": False}), 400
        return redirect(url_for("habits.habits_page"))

    check = HabitCheck.query.filter_by(habit_id=habit.id, date=target_date).first()

    if check:
        db.session.delete(check)
        completed = False
    else:
        check = HabitCheck(
            habit_id=habit.id,
            date=target_date,
            completed=True
        )
        db.session.add(check)
        completed = True

    db.session.commit()

    week_dates = get_week_dates()
    completed_count = sum(
        1 for d in week_dates
        if HabitCheck.query.filter_by(habit_id=habit.id, date=d).first()
    )

    progress_percent = 0
    if habit.weekly_goal > 0:
        progress_percent = min((completed_count / habit.weekly_goal) * 100, 100)

    all_checks_map = {c.date: c for c in habit.checks}
    new_streak = calculate_weekly_streak(habit, all_checks_map)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({
            "ok": True,
            "completed": completed,
            "completed_count": completed_count,
            "weekly_goal": habit.weekly_goal,
            "progress_percent": progress_percent,
            "color": habit.color,
            "streak": new_streak
        })

    return redirect(url_for("habits.habits_page"))


@habits_bp.route("/edit/<int:habit_id>", methods=["POST"])
def edit_habit(habit_id):
    habit = Habit.query.get_or_404(habit_id)

    name = request.form.get("name", "").strip()
    color = request.form.get("color", "#22c55e").strip()
    weekly_goal = request.form.get("weekly_goal", 3)

    if name:
        try:
            weekly_goal = int(weekly_goal)
        except ValueError:
            weekly_goal = 3

        weekly_goal = max(1, min(7, weekly_goal))

        habit.name = name
        habit.color = color
        habit.weekly_goal = weekly_goal

        db.session.commit()

    return redirect(url_for("habits.habits_page"))

@habits_bp.route("/delete/<int:habit_id>", methods=["POST"])
def delete_habit(habit_id):
    habit = Habit.query.get_or_404(habit_id)
    db.session.delete(habit)
    db.session.commit()
    return redirect(url_for("habits.habits_page"))


@habits_bp.route('/reorder', methods=['POST'])
def reorder_habits():
    data = request.get_json()
    
    # Recorremos la lista que nos manda el Javascript y actualizamos la base de datos
    for item in data:
        habit = Habit.query.get(item['id'])
        if habit:
            habit.position = item['position']
    
    db.session.commit()
    return jsonify({'status': 'success'})