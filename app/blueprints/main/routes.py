from decimal import Decimal, InvalidOperation
from functools import wraps

from flask import abort, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ...extensions import db
from ...models import Order, OrderItem, OrderStatus, Product, User, UserRole
from . import main_bp


def admin_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view_func(*args, **kwargs)

    return wrapped_view


def add_product_to_session_cart(product_id: int, quantity: int = 1) -> None:
    cart = session.get("cart", {})
    key = str(product_id)
    current_quantity = int(cart.get(key, 0))
    cart[key] = current_quantity + quantity
    session["cart"] = cart
    session.modified = True


def remove_product_from_session_cart(product_id: int) -> None:
    cart = session.get("cart", {})
    key = str(product_id)
    if key in cart:
        del cart[key]
        session["cart"] = cart
        session.modified = True


def set_product_quantity_in_session_cart(product_id: int, quantity: int) -> None:
    cart = session.get("cart", {})
    key = str(product_id)

    if quantity <= 0:
        cart.pop(key, None)
    else:
        cart[key] = quantity

    session["cart"] = cart
    session.modified = True


def clear_session_cart() -> None:
    session["cart"] = {}
    session.modified = True


def build_cart_view_data():
    cart_data = session.get("cart", {})
    cart_product_ids = [int(product_id) for product_id in cart_data.keys()]

    products = []
    if cart_product_ids:
        products = Product.query.filter(Product.id.in_(cart_product_ids)).all()

    cart_items = []
    total_items = 0
    total_price = Decimal("0.00")

    for product in products:
        quantity = int(cart_data.get(str(product.id), 0))
        if quantity <= 0:
            continue

        subtotal = product.price * quantity
        cart_items.append(
            {
                "product": product,
                "quantity": quantity,
                "unit_price": product.price,
                "subtotal": subtotal,
            }
        )
        total_items += quantity
        total_price += subtotal

    return {
        "cart_items": cart_items,
        "total_items": total_items,
        "total_price": total_price,
    }


def parse_product_form(form_data):
    name = form_data.get("name", "").strip()
    description = form_data.get("description", "").strip()
    image_url = form_data.get("image_url", "").strip()
    price_raw = form_data.get("price", "").strip()
    stock_raw = form_data.get("stock_quantity", "").strip()
    category = form_data.get("category", "").strip()

    if not name or not description or not price_raw or not stock_raw or not category:
        return None, "Заполните все обязательные поля товара."

    try:
        price = Decimal(price_raw)
    except InvalidOperation:
        return None, "Цена должна быть числом."

    if price < 0:
        return None, "Цена не может быть отрицательной."

    try:
        stock_quantity = int(stock_raw)
    except ValueError:
        return None, "Количество на складе должно быть целым числом."

    if stock_quantity < 0:
        return None, "Количество на складе не может быть отрицательным."

    product_data = {
        "name": name,
        "description": description,
        "image_url": image_url or None,
        "price": price,
        "stock_quantity": stock_quantity,
        "category": category,
    }
    return product_data, None


@main_bp.get("/")
def home():
    return render_template("pages/home.html", page_title="Главная")


@main_bp.get("/catalog")
def catalog():
    products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template("pages/catalog.html", page_title="Каталог", products=products)


@main_bp.get("/products/<int:product_id>")
def product_details(product_id: int):
    product = db.get_or_404(Product, product_id)
    return render_template(
        "pages/product_details.html",
        page_title=product.name,
        product=product,
    )


@main_bp.post("/cart/add/<int:product_id>")
def add_to_cart(product_id: int):
    product = db.get_or_404(Product, product_id)

    if product.stock_quantity <= 0:
        flash("Товар временно отсутствует на складе.", "error")
        return redirect(request.referrer or url_for("main.catalog"))

    add_product_to_session_cart(product_id)
    flash(f"Товар «{product.name}» добавлен в корзину.", "success")
    return redirect(request.referrer or url_for("main.catalog"))


@main_bp.post("/cart/update/<int:product_id>")
def update_cart_item(product_id: int):
    product = db.get_or_404(Product, product_id)
    quantity_raw = request.form.get("quantity", "1").strip()

    try:
        quantity = int(quantity_raw)
    except ValueError:
        flash("Количество должно быть целым числом.", "error")
        return redirect(url_for("main.cart"))

    if quantity < 0:
        flash("Количество не может быть отрицательным.", "error")
        return redirect(url_for("main.cart"))

    if quantity > product.stock_quantity:
        flash("Недостаточно товара на складе.", "error")
        return redirect(url_for("main.cart"))

    set_product_quantity_in_session_cart(product_id, quantity)
    flash("Количество товара обновлено.", "success")
    return redirect(url_for("main.cart"))


@main_bp.post("/cart/remove/<int:product_id>")
def remove_from_cart(product_id: int):
    product = db.get_or_404(Product, product_id)
    remove_product_from_session_cart(product_id)
    flash(f"Товар «{product.name}» удален из корзины.", "success")
    return redirect(url_for("main.cart"))


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Введите email и пароль.", "error")
            return render_template("pages/login.html", page_title="Вход")

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Неверный email или пароль.", "error")
            return render_template("pages/login.html", page_title="Вход")

        login_user(user)
        flash("Вы успешно вошли в систему.", "success")
        return redirect(url_for("main.home"))

    return render_template("pages/login.html", page_title="Вход")


@main_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Заполните все поля формы.", "error")
            return render_template("pages/register.html", page_title="Регистрация")

        if len(password) < 6:
            flash("Пароль должен содержать минимум 6 символов.", "error")
            return render_template("pages/register.html", page_title="Регистрация")

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Пользователь с таким email уже существует.", "error")
            return render_template("pages/register.html", page_title="Регистрация")

        user = User(name=name, email=email, role=UserRole.USER)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash("Регистрация успешна. Теперь войдите в систему.", "success")
        return redirect(url_for("main.login"))

    return render_template("pages/register.html", page_title="Регистрация")


@main_bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("Вы вышли из аккаунта.", "success")
    return redirect(url_for("main.home"))


@main_bp.get("/cart")
def cart():
    return render_template("pages/cart.html", page_title="Корзина", **build_cart_view_data())


@main_bp.get("/profile")
@login_required
def profile():
    return render_template("pages/profile.html", page_title="Профиль")


@main_bp.get("/admin")
@admin_required
def admin_panel():
    products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template(
        "pages/admin.html",
        page_title="Панель администратора",
        products=products,
    )


@main_bp.route("/admin/products/create", methods=["GET", "POST"])
@admin_required
def admin_create_product():
    if request.method == "POST":
        product_data, error_message = parse_product_form(request.form)
        if error_message:
            flash(error_message, "error")
            return render_template(
                "pages/admin_product_form.html",
                page_title="Добавление товара",
                form_title="Добавление товара",
                submit_text="Создать товар",
                product=None,
            )

        product = Product(**product_data)
        db.session.add(product)
        db.session.commit()
        flash("Товар успешно создан.", "success")
        return redirect(url_for("main.admin_panel"))

    return render_template(
        "pages/admin_product_form.html",
        page_title="Добавление товара",
        form_title="Добавление товара",
        submit_text="Создать товар",
        product=None,
    )


@main_bp.route("/admin/products/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_edit_product(product_id: int):
    product = db.get_or_404(Product, product_id)

    if request.method == "POST":
        product_data, error_message = parse_product_form(request.form)
        if error_message:
            flash(error_message, "error")
            return render_template(
                "pages/admin_product_form.html",
                page_title="Редактирование товара",
                form_title="Редактирование товара",
                submit_text="Сохранить изменения",
                product=product,
            )

        product.name = product_data["name"]
        product.description = product_data["description"]
        product.image_url = product_data["image_url"]
        product.price = product_data["price"]
        product.stock_quantity = product_data["stock_quantity"]
        product.category = product_data["category"]

        db.session.commit()
        flash("Товар успешно обновлен.", "success")
        return redirect(url_for("main.admin_panel"))

    return render_template(
        "pages/admin_product_form.html",
        page_title="Редактирование товара",
        form_title="Редактирование товара",
        submit_text="Сохранить изменения",
        product=product,
    )


@main_bp.route("/admin/products/<int:product_id>/delete", methods=["GET", "POST"])
@admin_required
def admin_delete_product(product_id: int):
    product = db.get_or_404(Product, product_id)

    if request.method == "POST":
        db.session.delete(product)
        db.session.commit()
        flash("Товар удален.", "success")
        return redirect(url_for("main.admin_panel"))

    return render_template(
        "pages/admin_product_delete.html",
        page_title="Удаление товара",
        product=product,
    )


@main_bp.get("/admin/orders")
@admin_required
def admin_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template("pages/admin_orders.html", page_title="Все заказы", orders=orders)


@main_bp.get("/orders")
@login_required
def orders():
    user_orders = (
        Order.query.filter_by(user_id=current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return render_template("pages/orders.html", page_title="Мои заказы", orders=user_orders)


@main_bp.post("/orders/create")
@login_required
def create_order():
    cart_data = build_cart_view_data()
    cart_items = cart_data["cart_items"]
    total_price = cart_data["total_price"]

    if not cart_items:
        flash("Корзина пуста. Добавьте товары перед оформлением заказа.", "error")
        return redirect(url_for("main.cart"))

    for item in cart_items:
        if item["quantity"] > item["product"].stock_quantity:
            flash(
                f"Недостаточно товара «{item['product'].name}» на складе.",
                "error",
            )
            return redirect(url_for("main.cart"))

    order = Order(user_id=current_user.id, status=OrderStatus.CREATED, total_price=total_price)
    db.session.add(order)
    db.session.flush()

    for item in cart_items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=item["product"].id,
            quantity=item["quantity"],
            price_at_purchase=item["unit_price"],
        )
        db.session.add(order_item)
        item["product"].stock_quantity -= item["quantity"]

    db.session.commit()
    clear_session_cart()
    flash("Заказ успешно создан.", "success")
    return redirect(url_for("main.orders"))


@main_bp.post("/orders/<int:order_id>/cancel")
@login_required
def cancel_order(order_id: int):
    order = db.get_or_404(Order, order_id)

    if order.user_id != current_user.id:
        abort(403)

    if order.status != OrderStatus.CREATED:
        flash("Этот заказ уже отменен.", "error")
        return redirect(url_for("main.orders"))

    order.status = OrderStatus.CANCELED

    for item in order.items:
        item.product.stock_quantity += item.quantity

    db.session.commit()
    flash("Заказ отменен.", "success")
    return redirect(url_for("main.orders"))
