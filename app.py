from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
import os
import jwt
import datetime
import hashlib
import hmac
import secrets
import urllib.parse as urlparse
from functools import wraps

app = Flask(__name__, static_folder="frontend")
CORS(app)
app.config["JSON_AS_ASCII"] = False

SECRET = os.getenv("SECRET_KEY", "change-this-secret")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "").strip()

# =========================
# Password helpers
# =========================
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

    # รองรับ password เก่าแบบ plaintext เพื่อไม่ให้ user เดิมล็อกอินไม่ได้
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


# =========================
# DB
# =========================
def get_db():
    try:
        public_url = os.getenv("MYSQL_PUBLIC_URL")
        if public_url:
            parsed = urlparse.urlparse(public_url)
            return mysql.connector.connect(
                host=parsed.hostname,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path.lstrip("/"),
                port=parsed.port or 3306,
                connection_timeout=10,
            )

        return mysql.connector.connect(
            host=os.getenv("MYSQLHOST"),
            user=os.getenv("MYSQLUSER"),
            password=os.getenv("MYSQLPASSWORD"),
            database=os.getenv("MYSQLDATABASE"),
            port=int(os.getenv("MYSQLPORT", 3306)),
            connection_timeout=10,
        )
    except Exception as e:
        print("DB ERROR:", e)
        return None


def column_exists(cursor, table_name, column_name):
    cursor.execute(f"SHOW COLUMNS FROM `{table_name}` LIKE %s", (column_name,))
    return cursor.fetchone() is not None


def create_tables():
    db = get_db()
    if not db:
        return False

    cursor = db.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(100) NOT NULL,
        password VARCHAR(255) NOT NULL,
        plan VARCHAR(20) NOT NULL DEFAULT 'free',
        role VARCHAR(20) NOT NULL DEFAULT 'user'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL DEFAULT 0,
        name VARCHAR(100) NOT NULL,
        phone VARCHAR(20) NOT NULL,
        tag VARCHAR(20) NOT NULL DEFAULT 'New'
    )
    """)

    if not column_exists(cursor, "users", "plan"):
        cursor.execute("ALTER TABLE users ADD COLUMN plan VARCHAR(20) NOT NULL DEFAULT 'free'")

    if not column_exists(cursor, "users", "role"):
        cursor.execute("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'")

    if not column_exists(cursor, "customers", "user_id"):
        cursor.execute("ALTER TABLE customers ADD COLUMN user_id INT NOT NULL DEFAULT 0")

    if not column_exists(cursor, "customers", "tag"):
        cursor.execute("ALTER TABLE customers ADD COLUMN tag VARCHAR(20) NOT NULL DEFAULT 'New'")

    db.commit()
    cursor.close()
    db.close()
    return True


# =========================
# Auth
# =========================
def token_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "No token"}), 401

        token = auth.split(" ", 1)[1].strip()
        try:
            payload = jwt.decode(token, SECRET, algorithms=["HS256"])
            user_id = int(payload["user_id"])
        except Exception:
            return jsonify({"error": "Invalid token"}), 401

        return fn(user_id, *args, **kwargs)

    return wrapper


# =========================
# Frontend
# =========================
@app.route("/")
def home():
    return send_from_directory("frontend", "index.html")


@app.route("/landing")
def landing():
    return send_from_directory("frontend", "landing.html")


@app.route("/<path:path>")
def frontend_files(path):
    return send_from_directory("frontend", path)


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


# =========================
# Auth routes
# =========================
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

        stored_password = hash_password(password)
        role = "admin" if ADMIN_USERNAME and username == ADMIN_USERNAME else "user"

        cursor.execute(
            "INSERT INTO users (username, password, plan, role) VALUES (%s, %s, 'free', %s)",
            (username, stored_password, role)
        )
        db.commit()
        return jsonify({"message": "registered"})
    finally:
        cursor.close()
        db.close()


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
            "SELECT id, username, password, COALESCE(plan,'free') AS plan, COALESCE(role,'user') AS role "
            "FROM users WHERE username=%s LIMIT 1",
            (username,)
        )
        user = cursor.fetchone()

        if not user or not verify_password(user["password"], password):
            return jsonify({"error": "login failed"}), 401

        token = jwt.encode(
            {
                "user_id": user["id"],
                "username": user["username"],
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=8),
            },
            SECRET,
            algorithm="HS256",
        )

        return jsonify({
            "token": token,
            "username": user["username"],
            "plan": user["plan"],
            "role": user["role"]
        })
    finally:
        cursor.close()
        db.close()


# =========================
# Customer routes
# =========================
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
            (user_id,)
        )
        return jsonify(cursor.fetchall())
    finally:
        cursor.close()
        db.close()


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

    db = get_db()
    if not db:
        return jsonify({"error": "database unavailable"}), 503

    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT COALESCE(plan,'free') AS plan FROM users WHERE id=%s LIMIT 1", (user_id,))
        user = cursor.fetchone()
        plan = (user or {}).get("plan", "free")

        cursor.execute("SELECT COUNT(*) AS total FROM customers WHERE user_id=%s", (user_id,))
        total = cursor.fetchone()["total"]

        if plan == "free" and total >= 5:
            return jsonify({"error": "upgrade required"}), 403

        cursor.execute(
            "INSERT INTO customers (user_id, name, phone, tag) VALUES (%s, %s, %s, %s)",
            (user_id, name, phone, tag)
        )
        db.commit()
        return jsonify({"message": "added"})
    finally:
        cursor.close()
        db.close()


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
            (name, phone, tag, customer_id, user_id)
        )
        if cursor.rowcount == 0:
            return jsonify({"error": "customer not found"}), 404
        db.commit()
        return jsonify({"message": "updated"})
    finally:
        cursor.close()
        db.close()


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
            (customer_id, user_id)
        )
        db.commit()
        return jsonify({"message": "deleted"})
    finally:
        cursor.close()
        db.close()


@app.route("/dashboard", methods=["GET"])
@token_required
def dashboard(user_id):
    if not create_tables():
        return jsonify({"error": "database unavailable"}), 503

    db = get_db()
    if not db:
        return jsonify({"error": "database unavailable"}), 503

    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT COALESCE(plan,'free') AS plan, COALESCE(role,'user') AS role FROM users WHERE id=%s LIMIT 1",
            (user_id,)
        )
        user = cursor.fetchone() or {"plan": "free", "role": "user"}
        plan = user["plan"]
        role = user["role"]

        cursor.execute("SELECT COUNT(*) AS total FROM customers WHERE user_id=%s", (user_id,))
        total = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) AS vip FROM customers WHERE user_id=%s AND tag='VIP'", (user_id,))
        vip = cursor.fetchone()["vip"]

        remaining = None if plan == "pro" else max(0, 5 - total)

        return jsonify({
            "total": total,
            "vip": vip,
            "plan": plan,
            "role": role,
            "remaining": remaining
        })
    finally:
        cursor.close()
        db.close()


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
        db.close()


if __name__ == "__main__":
    try:
        create_tables()
    except Exception as e:
        print("DB init skipped:", e)

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))