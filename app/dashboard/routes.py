from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from app.extensions import db
from app.models import DashboardConfig, HomeTask, HomeNote

dashboard_bp = Blueprint("dashboard", __name__)


def get_dashboard_config():
    config = DashboardConfig.query.first()
    if not config:
        config = DashboardConfig()
        db.session.add(config)
        db.session.commit()
    return config


def get_home_note():
    note = HomeNote.query.first()
    if not note:
        note = HomeNote()
        db.session.add(note)
        db.session.commit()
    return note


def get_next_home_task_order():
    last_task = HomeTask.query.order_by(HomeTask.order_index.desc()).first()
    return (last_task.order_index + 1) if last_task else 0


def is_ajax_request():
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def serialize_home_task(task):
    return {
        "id": task.id,
        "title": task.title,
        "completed": task.completed,
    }


def serialize_home_note(note):
    return {
        "id": note.id,
        "title": note.title or "Nota principal",
        "content": note.content or "",
    }


def serialize_dashboard_config(config):
    return {
        "title": config.title,
        "description": config.description or "",
    }


@dashboard_bp.route("/")
def index():
    config = get_dashboard_config()
    note = get_home_note()
    tasks = HomeTask.query.order_by(HomeTask.order_index.asc(), HomeTask.created_at.asc()).all()

    return render_template(
        "index.html",
        dashboard_config=config,
        home_note=note,
        home_tasks=tasks
    )


@dashboard_bp.route("/dashboard/edit-header", methods=["POST"])
def edit_dashboard_header():
    config = get_dashboard_config()

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()

    if title:
        config.title = title
    config.description = description or ""

    db.session.commit()

    if is_ajax_request():
        return jsonify({"ok": True, "config": serialize_dashboard_config(config)})

    return redirect(url_for("dashboard.index"))


@dashboard_bp.route("/dashboard/tasks/new", methods=["POST"])
def create_home_task():
    title = request.form.get("title", "").strip()

    if title:
        task = HomeTask(
            title=title,
            completed=False,
            order_index=get_next_home_task_order()
        )
        db.session.add(task)
        db.session.commit()

        if is_ajax_request():
            return jsonify({"ok": True, "task": serialize_home_task(task)})

    if is_ajax_request():
        return jsonify({"ok": False}), 400

    return redirect(url_for("dashboard.index"))


@dashboard_bp.route("/dashboard/tasks/<int:task_id>/toggle", methods=["POST"])
def toggle_home_task(task_id):
    task = HomeTask.query.get_or_404(task_id)
    task.completed = not task.completed
    db.session.commit()

    if is_ajax_request():
        return jsonify({"ok": True, "task": serialize_home_task(task)})

    return redirect(url_for("dashboard.index"))


@dashboard_bp.route("/dashboard/tasks/<int:task_id>/delete", methods=["POST"])
def delete_home_task(task_id):
    task = HomeTask.query.get_or_404(task_id)
    deleted_id = task.id
    db.session.delete(task)
    db.session.commit()

    if is_ajax_request():
        return jsonify({"ok": True, "task_id": deleted_id})

    return redirect(url_for("dashboard.index"))


@dashboard_bp.route("/dashboard/note/edit", methods=["POST"])
def edit_home_note():
    note = get_home_note()

    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()

    note.title = title or "Nota principal"
    note.content = content or ""

    db.session.commit()

    if is_ajax_request():
        return jsonify({"ok": True, "note": serialize_home_note(note)})

    return redirect(url_for("dashboard.index"))