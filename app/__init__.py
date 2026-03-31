from flask import Flask, flash, redirect, url_for

from .blueprints.main import main_bp
from .config import Config
from .db_init import init_database
from .extensions import db, login_manager
from .models import User


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "main.login"
    login_manager.login_message = "Для доступа к странице выполните вход."
    login_manager.login_message_category = "error"

    app.register_blueprint(main_bp)
    register_login_manager()
    register_error_handlers(app)
    register_cli_commands(app)

    return app


def register_login_manager() -> None:
    @login_manager.user_loader
    def load_user(user_id: str):
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(403)
    def forbidden(_error):
        flash("Доступ запрещен.", "error")
        return redirect(url_for("main.home"))


def register_cli_commands(app: Flask) -> None:
    @app.cli.command("init-db")
    def init_db_command() -> None:
        """Create all tables and seed base data."""
        init_database()
        print("Database initialized and seed data applied.")
