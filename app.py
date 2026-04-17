from flask import Flask, request, jsonify, send_from_directory
import mysql.connector
import os
from flask_cors import CORS

app = Flask(__name__, static_folder="static")
CORS(app)

# =============================
# 🔥 CONNECT DATABASE (Railway)
# =============================
def get_db():
    return mysql.connector.connect(
        host=os.getenv("MYSQLHOST"),
        user=os.getenv("MYSQLUSER"),
        password=os.getenv("MYSQLPASSWORD"),
        database=os.getenv("MYSQLDATABASE"),
        port=int(os.getenv("MYSQLPORT", 3306))
    )

# =============================
# 🔥 CREATE TABLE
# =============================
def create_tables():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(100),
        password VARCHAR(100)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100),
        phone VARCHAR(100),
        tag VARCHAR(100)
    )
    """)

    db.commit()
    db.close()

# =============================
# 🔥 ROUTES
# =============================

@app.route("/")
def home():
    return send_from_directory("static", "index.html")

@app.route("/register", methods=["POST"])
def register():
    data = request.json

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "INSERT INTO users (username, password) VALUES (%s, %s)",
        (data["username"], data["password"])
    )

    db.commit()
    db.close()

    return jsonify({"msg": "ok"})

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
    db.close()

    if user:
        return jsonify({"token": "fake-token", "username": user["username"]})
    return jsonify({"error": "login failed"}), 401


@app.route("/customers", methods=["GET"])
def get_customers():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM customers")
    data = cursor.fetchall()

    db.close()
    return jsonify(data)


@app.route("/customers", methods=["POST"])
def add_customer():
    data = request.json

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "INSERT INTO customers (name, phone, tag) VALUES (%s, %s, %s)",
        (data["name"], data["phone"], data["tag"])
    )

    db.commit()
    db.close()

    return jsonify({"msg": "added"})


@app.route("/customers/<int:id>", methods=["DELETE"])
def delete_customer(id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("DELETE FROM customers WHERE id=%s", (id,))
    db.commit()
    db.close()

    return jsonify({"msg": "deleted"})


@app.route("/dashboard")
def dashboard():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT COUNT(*) FROM customers")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM customers WHERE tag='VIP'")
    vip = cursor.fetchone()[0]

    db.close()

    return jsonify({
        "total": total,
        "vip": vip
    })


# =============================
# 🔥 IMPORTANT FIX (แก้ 502 ตรงนี้)
# =============================
if __name__ == "__main__":
    create_tables()

    port = int(os.environ.get("PORT", 8080))  # ✅ ห้ามใช้ 3306

    app.run(host="0.0.0.0", port=port)