from datetime import datetime
from decimal import Decimal
from enum import Enum

from flask_login import UserMixin
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Numeric
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class OrderStatus(str, Enum):
    CREATED = "CREATED"
    CANCELED = "CANCELED"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(
        SQLEnum(UserRole, name="user_role", native_enum=False),
        nullable=False,
        default=UserRole.USER,
    )
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    orders = db.relationship("Order", back_populates="user", lazy=True)

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    price = db.Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    stock_quantity = db.Column(db.Integer, nullable=False, default=0)
    category = db.Column(db.String(120), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    order_items = db.relationship("OrderItem", back_populates="product", lazy=True)

    def __repr__(self) -> str:
        return f"<Product id={self.id} name={self.name}>"


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    status = db.Column(
        SQLEnum(OrderStatus, name="order_status", native_enum=False),
        nullable=False,
        default=OrderStatus.CREATED,
    )
    total_price = db.Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", back_populates="orders")
    items = db.relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy=True,
    )

    def __repr__(self) -> str:
        return f"<Order id={self.id} user_id={self.user_id}>"


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True)
    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id"),
        nullable=False,
        index=True,
    )
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price_at_purchase = db.Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))

    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product", back_populates="order_items")

    def __repr__(self) -> str:
        return f"<OrderItem id={self.id} order_id={self.order_id} product_id={self.product_id}>"
