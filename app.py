"""
CampusCart - Student Marketplace
Flask Backend
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback_secret_key")

# ─────────────────────────────────────────
#  In-Memory Storage
# ─────────────────────────────────────────

# Users: { username: password }
users = {
    "alice": "pass123",
    "bob": "pass456",
}

# Items list: each item is a dict
items = []


# Cart: { username: [item_id, ...] }
carts = {}

# Chat: { item_id: [ {sender, message, timestamp}, ... ] }
chats = {}

# Allowed image extensions
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "pdf"}
UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_item(item_id):
    """Helper to find an item by ID."""
    return next((i for i in items if i["id"] == item_id), None)


def get_cart_items(username):
    """Return full item dicts for a user's cart."""
    cart_ids = carts.get(username, [])
    return [get_item(iid) for iid in cart_ids if get_item(iid)]


# ─────────────────────────────────────────
#  Auth Routes
# ─────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Please fill in all fields.", "error")
            return redirect(url_for("login"))

        if users.get(username) == password:
            session["user"] = username
            flash(f"Welcome back, {username}! 👋", "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid username or password.", "error")
            return redirect(url_for("login"))

    return render_template("index.html", page="login")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Please fill in all fields.", "error")
            return redirect(url_for("register"))

        if username in users:
            flash("Username already taken. Try another.", "error")
            return redirect(url_for("register"))

        if len(password) < 4:
            flash("Password must be at least 4 characters.", "error")
            return redirect(url_for("register"))

        users[username] = password
        session["user"] = username
        flash(f"Account created! Welcome, {username}! 🎉", "success")
        return redirect(url_for("index"))

    return render_template("index.html", page="register")


@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("You've been logged out.", "info")
    return redirect(url_for("login"))


# ─────────────────────────────────────────
#  Home / Listings
# ─────────────────────────────────────────

@app.route("/")
def index():
    if "user" not in session:
        return redirect(url_for("login"))

    category_filter = request.args.get("category", "All")
    search_query = request.args.get("q", "").strip().lower()

    filtered = items[:]
    if category_filter and category_filter != "All":
        filtered = [i for i in filtered if i["category"] == category_filter]
    if search_query:
        filtered = [i for i in filtered if search_query in i["name"].lower() or search_query in i["description"].lower()]

    categories = ["All", "Books", "Electronics", "Fashion", "Sports", "Stationery", "Other"]
    cart_count = len(carts.get(session["user"], []))

    return render_template(
        "index.html",
        page="home",
        items=filtered,
        categories=categories,
        active_category=category_filter,
        search_query=search_query,
        cart_count=cart_count,
        user=session["user"],
    )


# ─────────────────────────────────────────
#  Post Item
# ─────────────────────────────────────────

@app.route("/post", methods=["GET", "POST"])
def post_item():
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        price = request.form.get("price", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()

        # Validation
        if not name or not price or not category or not description:
            flash("Please fill in all fields.", "error")
            return redirect(url_for("post_item"))

        try:
            price = float(price)
            if price < 0:
                raise ValueError
        except ValueError:
            flash("Enter a valid price.", "error")
            return redirect(url_for("post_item"))

        # Image upload
        image_filename = "default_item.png"
        file = request.files.get("image")
        if file and file.filename and allowed_file(file.filename):
            ext = file.filename.rsplit(".", 1)[1].lower()
            unique_name = f"{uuid.uuid4().hex}.{ext}"
            file.save(os.path.join(UPLOAD_FOLDER, unique_name))
            image_filename = f"uploads/{unique_name}"

        new_item = {
            "id": f"item-{uuid.uuid4().hex[:8]}",
            "name": name,
            "price": price,
            "category": category,
            "description": description,
            "seller": session["user"],
            "image": image_filename,
            "sold": False,
        }
        items.insert(0, new_item)
        flash("Item posted successfully! 🎊", "success")
        return redirect(url_for("index"))

    cart_count = len(carts.get(session["user"], []))
    return render_template("index.html", page="post", cart_count=cart_count, user=session["user"])


# ─────────────────────────────────────────
#  Item Detail
# ─────────────────────────────────────────

@app.route("/item/<item_id>")
def item_detail(item_id):
    if "user" not in session:
        return redirect(url_for("login"))

    item = get_item(item_id)
    if not item:
        flash("Item not found.", "error")
        return redirect(url_for("index"))

    item_chats = chats.get(item_id, [])
    user_cart = carts.get(session["user"], [])
    in_cart = item_id in user_cart
    cart_count = len(user_cart)

    return render_template(
        "index.html",
        page="detail",
        item=item,
        messages=item_chats,
        in_cart=in_cart,
        cart_count=cart_count,
        user=session["user"],
    )


# ─────────────────────────────────────────
#  Seller Actions
# ─────────────────────────────────────────

@app.route("/item/<item_id>/mark_sold", methods=["POST"])
def mark_sold(item_id):
    if "user" not in session:
        return redirect(url_for("login"))

    item = get_item(item_id)
    if item and item["seller"] == session["user"]:
        item["sold"] = True
        flash("Item marked as sold.", "success")

    return redirect(url_for("item_detail", item_id=item_id))


@app.route("/item/<item_id>/delete", methods=["POST"])
def delete_item(item_id):
    if "user" not in session:
        return redirect(url_for("login"))

    item = get_item(item_id)
    if item and item["seller"] == session["user"]:
        items.remove(item)
        # Clean up carts
        for uname in carts:
            if item_id in carts[uname]:
                carts[uname].remove(item_id)
        flash("Item deleted.", "info")

    return redirect(url_for("index"))


# ─────────────────────────────────────────
#  Cart
# ─────────────────────────────────────────

@app.route("/cart/add/<item_id>", methods=["POST"])
def add_to_cart(item_id):
    if "user" not in session:
        return redirect(url_for("login"))

    user = session["user"]
    item = get_item(item_id)

    if not item:
        flash("Item not found.", "error")
    elif item["sold"]:
        flash("This item is already sold.", "error")
    elif item["seller"] == user:
        flash("You can't add your own item to cart.", "error")
    else:
        if user not in carts:
            carts[user] = []
        if item_id not in carts[user]:
            carts[user].append(item_id)
            flash(f"'{item['name']}' added to cart! 🛒", "success")
        else:
            flash("Already in your cart.", "info")

    return redirect(url_for("item_detail", item_id=item_id))


@app.route("/cart/remove/<item_id>", methods=["POST"])
def remove_from_cart(item_id):
    if "user" not in session:
        return redirect(url_for("login"))

    user = session["user"]
    if user in carts and item_id in carts[user]:
        carts[user].remove(item_id)
        flash("Item removed from cart.", "info")

    return redirect(url_for("cart"))


@app.route("/cart")
def cart():
    if "user" not in session:
        return redirect(url_for("login"))

    user = session["user"]
    cart_items = get_cart_items(user)
    total = sum(i["price"] for i in cart_items if i and not i["sold"])
    cart_count = len(carts.get(user, []))

    return render_template(
        "index.html",
        page="cart",
        cart_items=cart_items,
        total=total,
        cart_count=cart_count,
        user=user,
    )


# ─────────────────────────────────────────
#  Chat
# ─────────────────────────────────────────

@app.route("/item/<item_id>/chat", methods=["POST"])
def send_message(item_id):
    if "user" not in session:
        return redirect(url_for("login"))

    message = request.form.get("message", "").strip()
    if not message:
        flash("Message cannot be empty.", "error")
        return redirect(url_for("item_detail", item_id=item_id))

    if item_id not in chats:
        chats[item_id] = []

    from datetime import datetime
    chats[item_id].append({
        "sender": session["user"],
        "message": message,
        "time": datetime.now().strftime("%I:%M %p"),
    })

    return redirect(url_for("item_detail", item_id=item_id) + "#chat")


# ─────────────────────────────────────────
#  Run App
# ─────────────────────────────────────────

if __name__ == "__main__":
    app.run()
