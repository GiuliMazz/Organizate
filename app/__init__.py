from flask import Flask
from config import Config
from app.extensions import db


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    db.init_app(app)

    from app.dashboard.routes import dashboard_bp
    from app.habits.routes import habits_bp
    from app.projects.routes import projects_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(habits_bp)
    app.register_blueprint(projects_bp)

    with app.app_context():
        from app import models
        db.create_all()

    return app