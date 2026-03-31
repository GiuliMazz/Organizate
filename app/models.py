from datetime import datetime
from app.extensions import db


class Habit(db.Model):
    __tablename__ = "habits"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    color = db.Column(db.String(20), nullable=False, default="#22c55e")
    weekly_goal = db.Column(db.Integer, nullable=False, default=3)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    checks = db.relationship(
        "HabitCheck",
        backref="habit",
        lazy=True,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Habit {self.name}>"


class HabitCheck(db.Model):
    __tablename__ = "habit_checks"

    id = db.Column(db.Integer, primary_key=True)
    habit_id = db.Column(db.Integer, db.ForeignKey("habits.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    completed = db.Column(db.Boolean, nullable=False, default=True)

    __table_args__ = (
        db.UniqueConstraint("habit_id", "date", name="unique_habit_check_per_day"),
    )

    def __repr__(self):
        return f"<HabitCheck habit_id={self.habit_id} date={self.date}>"


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), nullable=False, default="idea")
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    events = db.relationship(
        "ProjectEvent",
        backref="project",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="ProjectEvent.event_date.asc(), ProjectEvent.created_at.asc()"
    )

    tasks = db.relationship(
        "ProjectTask",
        backref="project",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="ProjectTask.order_index.asc(), ProjectTask.created_at.asc()"
    )

    def __repr__(self):
        return f"<Project {self.name}>"


class ProjectEvent(db.Model):
    __tablename__ = "project_events"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=True)
    event_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<ProjectEvent {self.title}>"


class ProjectTask(db.Model):
    __tablename__ = "project_tasks"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=True)
    column_name = db.Column(db.String(30), nullable=False, default="pendiente")
    order_index = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<ProjectTask {self.title}>"
    

class DashboardConfig(db.Model):
    __tablename__ = "dashboard_config"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, default="Organizate")
    description = db.Column(
        db.Text,
        nullable=False,
        default="Tu centro personal para hábitos, proyectos y enfoque diario."
    )

    def __repr__(self):
        return f"<DashboardConfig {self.title}>"



class HomeTask(db.Model):
    __tablename__ = "home_tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, nullable=False, default=False)
    order_index = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<HomeTask {self.title}>"



class HomeNote(db.Model):
    __tablename__ = "home_notes"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=True, default="Nota principal")
    content = db.Column(
        db.Text,
        nullable=False,
        default="Escribí acá tu nota principal."
    )
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    def __repr__(self):
        return f"<HomeNote {self.title}>"