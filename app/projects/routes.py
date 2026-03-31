from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from app.extensions import db
from app.models import Project, ProjectEvent, ProjectTask

projects_bp = Blueprint("projects", __name__, url_prefix="/projects")


VALID_PROJECT_STATUSES = {
    "idea": "Idea",
    "pendiente": "Pendiente",
    "en_progreso": "En progreso",
    "finalizado": "Finalizado",
}

KANBAN_COLUMNS = {
    "pendiente": "Pendientes",
    "en_progreso": "En Progreso",
    "completado": "Completado",
}


def parse_optional_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def is_ajax_request():
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def serialize_project_task(task):
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description or "",
        "column_name": task.column_name,
    }


def serialize_project_event(event):
    return {
        "id": event.id,
        "title": event.title,
        "description": event.description or "",
        "event_date": event.event_date.isoformat() if event.event_date else "",
        "event_date_display": event.event_date.strftime("%d/%m/%Y") if event.event_date else "Sin fecha definida",
    }


def get_next_task_order(project_id, column_name):
    last_task = (
        ProjectTask.query
        .filter_by(project_id=project_id, column_name=column_name)
        .order_by(ProjectTask.order_index.desc())
        .first()
    )
    return (last_task.order_index + 1) if last_task else 0


def normalize_column_order(project_id, column_name):
    tasks = (
        ProjectTask.query
        .filter_by(project_id=project_id, column_name=column_name)
        .order_by(ProjectTask.order_index.asc(), ProjectTask.created_at.asc())
        .all()
    )
    for index, task in enumerate(tasks):
        task.order_index = index


@projects_bp.route("/", methods=["GET", "POST"])
def projects_page():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        status = request.form.get("status", "idea").strip()
        start_date = parse_optional_date(request.form.get("start_date", "").strip())
        end_date = parse_optional_date(request.form.get("end_date", "").strip())

        if status not in VALID_PROJECT_STATUSES:
            status = "idea"

        if name:
            project = Project(
                name=name,
                description=description or None,
                status=status,
                start_date=start_date,
                end_date=end_date
            )
            db.session.add(project)
            db.session.commit()
            return redirect(url_for("projects.projects_page"))

    projects = Project.query.order_by(Project.created_at.desc()).all()

    return render_template(
        "projects/projects.html",
        projects=projects,
        status_labels=VALID_PROJECT_STATUSES
    )


@projects_bp.route("/<int:project_id>")
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)

    kanban_tasks = {key: [] for key in KANBAN_COLUMNS.keys()}
    for task in project.tasks:
        if task.column_name in kanban_tasks:
            kanban_tasks[task.column_name].append(task)

    return render_template(
        "projects/project_detail.html",
        project=project,
        status_labels=VALID_PROJECT_STATUSES,
        kanban_columns=KANBAN_COLUMNS,
        kanban_tasks=kanban_tasks
    )


@projects_bp.route("/<int:project_id>/edit", methods=["POST"])
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)

    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    status = request.form.get("status", "idea").strip()
    start_date = parse_optional_date(request.form.get("start_date", "").strip())
    end_date = parse_optional_date(request.form.get("end_date", "").strip())

    if status not in VALID_PROJECT_STATUSES:
        status = "idea"

    if name:
        project.name = name
        project.description = description or None
        project.status = status
        project.start_date = start_date
        project.end_date = end_date
        db.session.commit()

    return redirect(url_for("projects.project_detail", project_id=project.id))


@projects_bp.route("/<int:project_id>/delete", methods=["POST"])
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    return redirect(url_for("projects.projects_page"))


@projects_bp.route("/<int:project_id>/events/new", methods=["POST"])
def create_project_event(project_id):
    project = Project.query.get_or_404(project_id)

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    event_date = parse_optional_date(request.form.get("event_date", "").strip())

    if title:
        event = ProjectEvent(
            project_id=project.id,
            title=title,
            description=description or None,
            event_date=event_date
        )
        db.session.add(event)
        db.session.commit()

        if is_ajax_request():
            return jsonify({"ok": True, "event": serialize_project_event(event)})

    if is_ajax_request():
        return jsonify({"ok": False}), 400

    return redirect(url_for("projects.project_detail", project_id=project.id))


@projects_bp.route("/events/<int:event_id>/edit", methods=["POST"])
def edit_project_event(event_id):
    event = ProjectEvent.query.get_or_404(event_id)

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    event_date = parse_optional_date(request.form.get("event_date", "").strip())

    if title:
        event.title = title
        event.description = description or None
        event.event_date = event_date
        db.session.commit()

        if is_ajax_request():
            return jsonify({"ok": True, "event": serialize_project_event(event)})

    if is_ajax_request():
        return jsonify({"ok": False}), 400

    return redirect(url_for("projects.project_detail", project_id=event.project_id))


@projects_bp.route("/events/<int:event_id>/delete", methods=["POST"])
def delete_project_event(event_id):
    event = ProjectEvent.query.get_or_404(event_id)
    project_id = event.project_id
    event_id_deleted = event.id
    db.session.delete(event)
    db.session.commit()

    if is_ajax_request():
        return jsonify({"ok": True, "event_id": event_id_deleted})

    return redirect(url_for("projects.project_detail", project_id=project_id))


@projects_bp.route("/<int:project_id>/tasks/new", methods=["POST"])
def create_project_task(project_id):
    project = Project.query.get_or_404(project_id)

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    column_name = request.form.get("column_name", "pendiente").strip()

    if column_name not in KANBAN_COLUMNS:
        column_name = "pendiente"

    if title:
        task = ProjectTask(
            project_id=project.id,
            title=title,
            description=description or None,
            column_name=column_name,
            order_index=get_next_task_order(project.id, column_name)
        )
        db.session.add(task)
        db.session.commit()

        if is_ajax_request():
            return jsonify({"ok": True, "task": serialize_project_task(task)})

    if is_ajax_request():
        return jsonify({"ok": False}), 400

    return redirect(url_for("projects.project_detail", project_id=project.id))


@projects_bp.route("/tasks/<int:task_id>/edit", methods=["POST"])
def edit_project_task(task_id):
    task = ProjectTask.query.get_or_404(task_id)

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    column_name = request.form.get("column_name", "pendiente").strip()

    if column_name not in KANBAN_COLUMNS:
        column_name = "pendiente"

    if title:
        old_column = task.column_name
        moved_column = old_column != column_name

        task.title = title
        task.description = description or None
        task.column_name = column_name

        if moved_column:
            task.order_index = get_next_task_order(task.project_id, column_name)
            normalize_column_order(task.project_id, old_column)
            normalize_column_order(task.project_id, column_name)

        db.session.commit()

        if is_ajax_request():
            return jsonify({
                "ok": True,
                "task": serialize_project_task(task),
                "old_column": old_column
            })

    if is_ajax_request():
        return jsonify({"ok": False}), 400

    return redirect(url_for("projects.project_detail", project_id=task.project_id))


@projects_bp.route("/tasks/<int:task_id>/delete", methods=["POST"])
def delete_project_task(task_id):
    task = ProjectTask.query.get_or_404(task_id)
    project_id = task.project_id
    old_column = task.column_name
    task_id_deleted = task.id

    db.session.delete(task)
    normalize_column_order(project_id, old_column)
    db.session.commit()

    if is_ajax_request():
        return jsonify({
            "ok": True,
            "task_id": task_id_deleted,
            "old_column": old_column
        })

    return redirect(url_for("projects.project_detail", project_id=project_id))


@projects_bp.route("/tasks/<int:task_id>/move", methods=["POST"])
def move_project_task(task_id):
    task = ProjectTask.query.get_or_404(task_id)
    data = request.get_json(silent=True) or {}

    target_column = (data.get("target_column") or "").strip()
    target_index = data.get("target_index", 0)

    if target_column not in KANBAN_COLUMNS:
        return jsonify({"ok": False, "error": "Invalid column"}), 400

    try:
        target_index = int(target_index)
    except (TypeError, ValueError):
        target_index = 0

    old_column = task.column_name
    project_id = task.project_id

    if old_column == target_column:
        tasks_in_target = (
            ProjectTask.query
            .filter_by(project_id=project_id, column_name=target_column)
            .order_by(ProjectTask.order_index.asc(), ProjectTask.created_at.asc())
            .all()
        )
        tasks_in_target = [t for t in tasks_in_target if t.id != task.id]
        target_index = max(0, min(target_index, len(tasks_in_target)))
        tasks_in_target.insert(target_index, task)

        for idx, item in enumerate(tasks_in_target):
            item.column_name = target_column
            item.order_index = idx
    else:
        tasks_in_old = (
            ProjectTask.query
            .filter_by(project_id=project_id, column_name=old_column)
            .order_by(ProjectTask.order_index.asc(), ProjectTask.created_at.asc())
            .all()
        )
        tasks_in_old = [t for t in tasks_in_old if t.id != task.id]

        tasks_in_target = (
            ProjectTask.query
            .filter_by(project_id=project_id, column_name=target_column)
            .order_by(ProjectTask.order_index.asc(), ProjectTask.created_at.asc())
            .all()
        )

        target_index = max(0, min(target_index, len(tasks_in_target)))
        tasks_in_target.insert(target_index, task)

        for idx, item in enumerate(tasks_in_old):
            item.column_name = old_column
            item.order_index = idx

        for idx, item in enumerate(tasks_in_target):
            item.column_name = target_column
            item.order_index = idx

    db.session.commit()
    return jsonify({"ok": True})