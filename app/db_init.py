from .extensions import db
from .models import User, UserRole


def seed_admin_user() -> None:
    admin = User.query.filter_by(email="admin").first()

    if not admin:
        admin = User(name="Administrator", email="admin", role=UserRole.ADMIN)
        db.session.add(admin)

    admin.role = UserRole.ADMIN
    admin.set_password("admin")
    db.session.commit()


def init_database() -> None:
    db.create_all()
    seed_admin_user()
