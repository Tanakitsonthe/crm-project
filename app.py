from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
import jwt
import datetime
import os
from functools import wraps

app = Flask(__name__, static_folder="frontend")
CORS(app)

SECRET = os.getenv("SECRET_KEY", "supersecret123")

# ================= DB =================
def get_db():
    return mysql.connector.connect(
        host=os.getenv("MYSQLHOST"),
        user=os.getenv("MYSQLUSER"),
        password=os.getenv("MYSQLPASSWORD"),
        database=os.getenv("MYSQLDATABASE"),
        port=int(os.getenv("MYSQLPORT"))
    )

# ================= CREATE TABLE =================
def create_tables():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(100),
        password VARCHAR(100),
        plan VARCHAR(20)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT,
        name VARCHAR(100),
        phone VARCHAR(20),
        tag VARCHAR(20)
    )
    """)

    db.commit()

# ================= TOKEN =================
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")

        if not token:
            return jsonify({"error": "No token"}), 401

        try:
            token = token.split(" ")[1]
            data = jwt.decode(token, SECRET, algorithms=["HS256"])
            user_id = data["user_id"]
        except:
            return jsonify({"error": "Invalid token"}), 401

        return f(user_id, *args, **kwargs)

    return decorated

# ================= FRONT =================
@app.route("/")
def home():
    return send_from_directory("frontend", "index.html")

@app.route("/landing")
def landing():
    return send_from_directory("frontend", "landing.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory("frontend", path)

# ================= AUTH =================
@app.route("/register", methods=["POST"])
def register():
    data = request.json

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "INSERT INTO users (username, password, plan) VALUES (%s, %s, 'free')",
        (data["username"], data["password"])
    )
    db.commit()

    return jsonify({"message": "registered"})

@app.route("/login", methods=["POST"])
def login():
    data = request.json

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM users WHERE username=%s AND password=%s",
        (data["username"], data["password"])
    )

    user = cursor.fetchone()

    if user:
        token = jwt.encode({
            "user_id": user["id"],
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=5)
        }, SECRET, algorithm="HS256")

        return jsonify({
            "token": token,
            "username": user["username"]
        })

    return jsonify({"error": "login failed"}), 401

# ================= CUSTOMER =================
@app.route("/customers", methods=["POST"])
@token_required
def add_customer(user_id):
    data = request.json

    db = get_db()
    cursor = db.cursor()

    # 🔥 LIMIT FREE PLAN
    cursor.execute("SELECT COUNT(*) FROM customers WHERE user_id=%s", (user_id,))
    count = cursor.fetchone()[0]

    cursor.execute("SELECT plan FROM users WHERE id=%s", (user_id,))
    plan = cursor.fetchone()[0]

    if plan == "free" and count >= 5:
        return jsonify({"error": "upgrade required"}), 403

    cursor.execute(
        "INSERT INTO customers (user_id, name, phone, tag) VALUES (%s, %s, %s, %s)",
        (user_id, data["name"], data["phone"], data["tag"])
    )
    db.commit()

    return jsonify({"message": "added"})

@app.route("/customers", methods=["GET"])
@token_required
def get_customers(user_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM customers WHERE user_id=%s",
        (user_id,)
    )

    return jsonify(cursor.fetchall())

@app.route("/customers/<int:id>", methods=["DELETE"])
@token_required
def delete_customer(user_id, id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "DELETE FROM customers WHERE id=%s AND user_id=%s",
        (id, user_id)
    )
    db.commit()

    return jsonify({"message": "deleted"})

# ================= UPGRADE =================
@app.route("/upgrade", methods=["POST"])
@token_required
def upgrade(user_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("UPDATE users SET plan='pro' WHERE id=%s", (user_id,))
    db.commit()

    return jsonify({"message": "upgraded"})

# ================= RUN =================
if __name__ == "__main__":
    create_tables()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))