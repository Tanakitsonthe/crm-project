from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
import os
import jwt
import datetime as dt
import hashlib
import hmac
import secrets
import urllib.parse as urlparse
from functools import wraps

app = Flask(__name__, static_folder="frontend")
CORS(app)
app.config["JSON_AS_ASCII"] = False

SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "").strip()


# -----------------------------
# Password helpers
# -----------------------------
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120000,
    ).hex()
    return f"{salt}${digest}"


def verify_password(stored_password: str, password: str) -> bool:
    if not stored_password:
        return False

    if "$" not in stored_password:
        return hmac.compare_digest(stored_password, password)

    salt, stored_digest = stored_password.split("$", 1)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120000,
    ).hex()
    return hmac.compare_digest(digest, stored_digest)


# -----------------------------
# Database
# -----------------------------
def _connect_from_url(url: str):
    parsed = urlparse.urlparse(url)
    dbname = parsed.path.lstrip("/")
    return mysql.connector.connect(
        host=parsed.hostname,
        user=parsed.username,
        password=parsed.password,
        database=dbname,
        port=parsed.port or 3306,
        connection_timeout=10,
    )


def get_db():
    try:
        for env_name in ("MYSQL_PUBLIC_URL", "DATABASE_URL"):
            url = os.getenv(env_name, "").strip()
            if url:
                return _connect_from_url(url)

        return mysql.connector.connect(
            host=os.getenv("MYSQLHOST", "localhost"),
            user=os.getenv("MYSQLUSER", "root"),
            password=os.getenv("MYSQLPASSWORD", ""),
            database=os.getenv("MYSQLDATABASE", "crm_db"),
            port=int(os.getenv("MYSQLPORT", 3306)),
            connection_timeout=10,
        )
    except Exception as exc:
        print("DB ERROR:", exc)
        return None


def column_exists(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(f"SHOW COLUMNS FROM `{table_name}` LIKE %s", (column_name,))
    return cursor.fetchone() is not None


def create_tables() -> bool:
    db = get_db()
    if not db:
        return False

    cursor = db.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) NOT NULL,
                password VARCHAR(255) NOT NULL,
                plan VARCHAR(20) NOT NULL DEFAULT 'free',
                role VARCHAR(20) NOT NULL DEFAULT 'user',
                UNIQUE KEY unique_username (username)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS customers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL DEFAULT 0,
                name VARCHAR(100) NOT NULL,
                phone VARCHAR(20) NOT NULL,
                tag VARCHAR(20) NOT NULL DEFAULT 'New'
            )
            """
        )

        if not column_exists(cursor, "users", "plan"):
            cursor.execute("ALTER TABLE users ADD COLUMN plan VARCHAR(20) NOT NULL DEFAULT 'free'")
        if not column_exists(cursor, "users", "role"):
            cursor.execute("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'")
        if not column_exists(cursor, "customers", "user_id"):
            cursor.execute("ALTER TABLE customers ADD COLUMN user_id INT NOT NULL DEFAULT 0")
        if not column_exists(cursor, "customers", "tag"):
            cursor.execute("ALTER TABLE customers ADD COLUMN tag VARCHAR(20) NOT NULL DEFAULT 'New'")

        db.commit()
        return True
    finally:
        cursor.close()
        db.close()


def close_db(db):
    if db:
        db.close()


# -----------------------------
# User helpers
# -----------------------------
def normalize_user(row):
    if not row:
        return None

    user = dict(row)
    if ADMIN_USERNAME and user.get("username") == ADMIN_USERNAME:
        user["role"] = "admin"
        user["plan"] = "pro"

    user["plan"] = (user.get("plan") or "free").lower()
    user["role"] = (user.get("role") or "user").lower()
    return user


def get_user_by_id(user_id: int):
    db = get_db()
    if not db:
        return None

    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT id, username, COALESCE(plan,'free') AS plan, COALESCE(role,'user') AS role
            FROM users
            WHERE id=%s
            LIMIT 1
            """,
            (user_id,),
        )
        return normalize_user(cursor.fetchone())
    finally:
        cursor.close()
        close_db(db)


def get_user_by_username(username: str, include_password: bool = False):
    db = get_db()
    if not db:
        return None

    cursor = db.cursor(dictionary=True)
    try:
        if include_password:
            cursor.execute(
                """
                SELECT id, username, password, COALESCE(plan,'free') AS plan, COALESCE(role,'user') AS role
                FROM users
                WHERE username=%s
                LIMIT 1
                """,
                (username,),
            )
        else:
            cursor.execute(
                """
                SELECT id, username, COALESCE(plan,'free') AS plan, COALESCE(role,'user') AS role
                FROM users
                WHERE username=%s
                LIMIT 1
                """,
                (username,),
            )
        return normalize_user(cursor.fetchone())
    finally:
        cursor.close()
        close_db(db)


def is_admin_user(user):
    if not user:
        return False
    return str(user.get("role", "user")).lower() == "admin"


def make_token(user_id: int, username: str):
    token = jwt.encode(
        {
            "user_id": user_id,
            "username": username,
            "exp": dt.datetime.utcnow() + dt.timedelta(hours=8),
        },
        SECRET_KEY,
        algorithm="HS256",
    )
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def token_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "No token"}), 401

        token = auth.split(" ", 1)[1].strip()
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            user_id = int(payload["user_id"])
        except Exception:
            return jsonify({"error": "Invalid token"}), 401

        return fn(user_id, *args, **kwargs)

    return wrapper


def require_admin(user_id):
    user = get_user_by_id(user_id)
    if not user or not is_admin_user(user):
        return None
    return user


# -----------------------------
# Routes
# -----------------------------
@app.route("/")
def home():
    return send_from_directory("frontend", "index.html")


@app.route("/landing")
def landing():
    return send_from_directory("frontend", "landing.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory("frontend", path)


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "กรุณากรอก username และ password"}), 400

    if not create_tables():
        return jsonify({"error": "database unavailable"}), 503

    db = get_db()
    if not db:
        return jsonify({"error": "database unavailable"}), 503

    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM users WHERE username=%s LIMIT 1", (username,))
        if cursor.fetchone():
            return jsonify({"error": "username already exists"}), 409

        hashed = hash_password(password)
        is_owner = bool(ADMIN_USERNAME and username == ADMIN_USERNAME)
        role = "admin" if is_owner else "user"
        plan = "pro" if is_owner else "free"

        cursor.execute(
            "INSERT INTO users (username, password, plan, role) VALUES (%s, %s, %s, %s)",
            (username, hashed, plan, role),
        )
        db.commit()
        return jsonify({"message": "registered"})
    finally:
        cursor.close()
        close_db(db)


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "กรุณากรอก username และ password"}), 400

    if not create_tables():
        return jsonify({"error": "database unavailable"}), 503

    db = get_db()
    if not db:
        return jsonify({"error": "database unavailable"}), 503

    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT id, username, password, COALESCE(plan,'free') AS plan, COALESCE(role,'user') AS role
            FROM users
            WHERE username=%s
            LIMIT 1
            """,
            (username,),
        )
        row = cursor.fetchone()
        if not row or not verify_password(row["password"], password):
            return jsonify({"error": "login failed"}), 401

        user = normalize_user(row)
        token = make_token(user["id"], user["username"])
        return jsonify({
            "token": token,
            "username": user["username"],
            "plan": user["plan"],
            "role": user["role"],
        })
    finally:
        cursor.close()
        close_db(db)


@app.route("/dashboard", methods=["GET"])
@token_required
def dashboard(user_id):
    if not create_tables():
        return jsonify({"error": "database unavailable"}), 503

    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404

    db = get_db()
    if not db:
        return jsonify({"error": "database unavailable"}), 503

    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT COUNT(*) AS total FROM customers WHERE user_id=%s", (user_id,))
        total = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) AS vip FROM customers WHERE user_id=%s AND tag='VIP'", (user_id,))
        vip = cursor.fetchone()["vip"]

        cursor.execute(
            """
            SELECT tag, COUNT(*) AS count
            FROM customers
            WHERE user_id=%s
            GROUP BY tag
            """,
            (user_id,),
        )
        counts = {"New": 0, "VIP": 0, "Regular": 0}
        for row in cursor.fetchall():
            tag = row.get("tag") or "New"
            counts[tag] = row.get("count", 0)

        remaining = None if user["plan"] == "pro" else max(0, 5 - total)
        return jsonify({
            "total": total,
            "vip": vip,
            "counts": counts,
            "plan": user["plan"],
            "role": user["role"],
            "remaining": remaining,
        })
    finally:
        cursor.close()
        close_db(db)


@app.route("/customers", methods=["GET"])
@token_required
def get_customers(user_id):
    if not create_tables():
        return jsonify({"error": "database unavailable"}), 503

    db = get_db()
    if not db:
        return jsonify({"error": "database unavailable"}), 503

    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, name, phone, tag FROM customers WHERE user_id=%s ORDER BY id DESC",
            (user_id,),
        )
        return jsonify(cursor.fetchall())
    finally:
        cursor.close()
        close_db(db)


@app.route("/customers", methods=["POST"])
@token_required
def add_customer(user_id):
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    tag = (data.get("tag") or "New").strip()

    if not name or not phone:
        return jsonify({"error": "กรุณากรอกชื่อและเบอร์"}), 400
    if tag not in {"New", "VIP", "Regular"}:
        tag = "New"

    if not create_tables():
        return jsonify({"error": "database unavailable"}), 503

    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404

    db = get_db()
    if not db:
        return jsonify({"error": "database unavailable"}), 503

    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT COUNT(*) AS total FROM customers WHERE user_id=%s", (user_id,))
        total = cursor.fetchone()["total"]
        if user["plan"] == "free" and total >= 5:
            return jsonify({"error": "upgrade required"}), 403

        cursor.execute(
            "INSERT INTO customers (user_id, name, phone, tag) VALUES (%s, %s, %s, %s)",
            (user_id, name, phone, tag),
        )
        db.commit()
        return jsonify({"message": "added"})
    finally:
        cursor.close()
        close_db(db)


@app.route("/customers/<int:customer_id>", methods=["PUT"])
@token_required
def update_customer(user_id, customer_id):
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    tag = (data.get("tag") or "New").strip()

    if not name or not phone:
        return jsonify({"error": "กรุณากรอกชื่อและเบอร์"}), 400
    if tag not in {"New", "VIP", "Regular"}:
        tag = "New"

    if not create_tables():
        return jsonify({"error": "database unavailable"}), 503

    db = get_db()
    if not db:
        return jsonify({"error": "database unavailable"}), 503

    cursor = db.cursor()
    try:
        cursor.execute(
            "UPDATE customers SET name=%s, phone=%s, tag=%s WHERE id=%s AND user_id=%s",
            (name, phone, tag, customer_id, user_id),
        )
        if cursor.rowcount == 0:
            return jsonify({"error": "customer not found"}), 404
        db.commit()
        return jsonify({"message": "updated"})
    finally:
        cursor.close()
        close_db(db)


@app.route("/customers/<int:customer_id>", methods=["DELETE"])
@token_required
def delete_customer(user_id, customer_id):
    if not create_tables():
        return jsonify({"error": "database unavailable"}), 503

    db = get_db()
    if not db:
        return jsonify({"error": "database unavailable"}), 503

    cursor = db.cursor()
    try:
        cursor.execute(
            "DELETE FROM customers WHERE id=%s AND user_id=%s",
            (customer_id, user_id),
        )
        db.commit()
        return jsonify({"message": "deleted"})
    finally:
        cursor.close()
        close_db(db)


@app.route("/upgrade", methods=["POST"])
@token_required
def upgrade(user_id):
    if not create_tables():
        return jsonify({"error": "database unavailable"}), 503

    db = get_db()
    if not db:
        return jsonify({"error": "database unavailable"}), 503

    cursor = db.cursor()
    try:
        cursor.execute("UPDATE users SET plan='pro' WHERE id=%s", (user_id,))
        db.commit()
        return jsonify({"message": "upgraded"})
    finally:
        cursor.close()
        close_db(db)


@app.route("/admin/users", methods=["GET"])
@token_required
def admin_users(user_id):
    admin = require_admin(user_id)
    if not admin:
        return jsonify({"error": "forbidden"}), 403

    if not create_tables():
        return jsonify({"error": "database unavailable"}), 503

    db = get_db()
    if not db:
        return jsonify({"error": "database unavailable"}), 503

    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT
              u.id,
              u.username,
              COALESCE(u.plan,'free') AS plan,
              COALESCE(u.role,'user') AS role,
              COUNT(c.id) AS customers
            FROM users u
            LEFT JOIN customers c ON c.user_id = u.id
            GROUP BY u.id, u.username, u.plan, u.role
            ORDER BY u.id DESC
            """
        )
        rows = [normalize_user(row) | {"customers": row.get("customers", 0)} for row in cursor.fetchall()]
        return jsonify(rows)
    finally:
        cursor.close()
        close_db(db)


@app.route("/admin/users/<int:target_user_id>/plan", methods=["PUT"])
@token_required
def admin_set_plan(user_id, target_user_id):
    admin = require_admin(user_id)
    if not admin:
        return jsonify({"error": "forbidden"}), 403

    data = request.get_json(silent=True) or {}
    plan = (data.get("plan") or "").strip().lower()
    if plan not in {"free", "pro"}:
        return jsonify({"error": "invalid plan"}), 400

    target = get_user_by_id(target_user_id)
    if not target:
        return jsonify({"error": "user not found"}), 404
    if ADMIN_USERNAME and target["username"] == ADMIN_USERNAME and plan != "pro":
        return jsonify({"error": "admin must stay pro"}), 400

    db = get_db()
    if not db:
        return jsonify({"error": "database unavailable"}), 503

    cursor = db.cursor()
    try:
        cursor.execute("UPDATE users SET plan=%s WHERE id=%s", (plan, target_user_id))
        db.commit()
        return jsonify({"message": "updated", "plan": plan})
    finally:
        cursor.close()
        close_db(db)


@app.route("/admin/users/<int:target_user_id>/role", methods=["PUT"])
@token_required
def admin_set_role(user_id, target_user_id):
    admin = require_admin(user_id)
    if not admin:
        return jsonify({"error": "forbidden"}), 403

    data = request.get_json(silent=True) or {}
    role = (data.get("role") or "").strip().lower()
    if role not in {"user", "admin"}:
        return jsonify({"error": "invalid role"}), 400

    target = get_user_by_id(target_user_id)
    if not target:
        return jsonify({"error": "user not found"}), 404
    if ADMIN_USERNAME and target["username"] == ADMIN_USERNAME and role != "admin":
        return jsonify({"error": "owner admin cannot be downgraded"}), 400

    db = get_db()
    if not db:
        return jsonify({"error": "database unavailable"}), 503

    cursor = db.cursor()
    try:
        cursor.execute("UPDATE users SET role=%s WHERE id=%s", (role, target_user_id))
        db.commit()
        return jsonify({"message": "updated", "role": role})
    finally:
        cursor.close()
        close_db(db)


@app.route("/admin/impersonate/<int:target_user_id>", methods=["POST"])
@token_required
def admin_impersonate(user_id, target_user_id):
    admin = require_admin(user_id)
    if not admin:
        return jsonify({"error": "forbidden"}), 403

    target = get_user_by_id(target_user_id)
    if not target:
        return jsonify({"error": "user not found"}), 404

    token = make_token(target["id"], target["username"])
    return jsonify({
        "token": token,
        "username": target["username"],
        "plan": target["plan"],
        "role": target["role"],
    })


if __name__ == "__main__":
    create_tables()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
