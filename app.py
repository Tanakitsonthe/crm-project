from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
import jwt
import datetime

app = Flask(__name__)
CORS(app)

SECRET_KEY = "secret123"

# ======================
# 🔌 CONNECT DATABASE
# ======================
def get_db():
    return mysql.connector.connect(
        host="YOUR_HOST",
        user="YOUR_USER",
        password="YOUR_PASSWORD",
        database="crm_db"
    )

# ======================
# 🏠 SERVE FRONTEND
# ======================
@app.route("/")
def home():
    return send_from_directory("frontend", "index.html")

# ======================
# 👤 REGISTER
# ======================
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data["username"]
    password = data["password"]

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "INSERT INTO users (username, password) VALUES (%s, %s)",
        (username, password)
    )

    db.commit()
    cursor.close()
    db.close()

    return jsonify({"message": "registered"})


# ======================
# 🔐 LOGIN
# ======================
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data["username"]
    password = data["password"]

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM users WHERE username=%s AND password=%s",
        (username, password)
    )
    user = cursor.fetchone()

    cursor.close()
    db.close()

    if user:
        token = jwt.encode({
            "user_id": user["id"],
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=5)
        }, SECRET_KEY, algorithm="HS256")

        return jsonify({"token": token})

    return jsonify({"message": "login failed"}), 401


# ======================
# ➕ ADD CUSTOMER
# ======================
@app.route("/add_customer", methods=["POST"])
def add_customer():
    token = request.headers.get("Authorization")

    if not token:
        return jsonify({"message": "no token"}), 403

    try:
        data_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = data_token["user_id"]
    except:
        return jsonify({"message": "invalid token"}), 403

    data = request.json
    name = data["name"]
    phone = data["phone"]

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "INSERT INTO customers (user_id, name, phone) VALUES (%s, %s, %s)",
        (user_id, name, phone)
    )

    db.commit()
    cursor.close()
    db.close()

    return jsonify({"message": "added"})


# ======================
# 📋 GET CUSTOMERS
# ======================
@app.route("/customers", methods=["GET"])
def get_customers():
    token = request.headers.get("Authorization")

    if not token:
        return jsonify([])

    try:
        data_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = data_token["user_id"]
    except:
        return jsonify([])

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM customers WHERE user_id=%s",
        (user_id,)
    )
    customers = cursor.fetchall()

    cursor.close()
    db.close()

    return jsonify(customers)


# ======================
# 📊 DASHBOARD
# ======================
@app.route("/dashboard", methods=["GET"])
def dashboard():
    token = request.headers.get("Authorization")

    try:
        data_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = data_token["user_id"]
    except:
        return jsonify({"count": 0})

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM customers WHERE user_id=%s",
        (user_id,)
    )
    count = cursor.fetchone()[0]

    cursor.close()
    db.close()

    return jsonify({"count": count})


# ======================
# 🤖 AI ANALYSIS
# ======================
@app.route("/ai", methods=["GET"])
def ai():
    token = request.headers.get("Authorization")

    try:
        data_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = data_token["user_id"]
    except:
        return jsonify({"insight": "no data"})

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM customers WHERE user_id=%s",
        (user_id,)
    )
    count = cursor.fetchone()[0]

    cursor.close()
    db.close()

    if count == 0:
        msg = "ยังไม่มีลูกค้า"
    elif count < 5:
        msg = "ลูกค้ายังน้อย ควรเพิ่มการตลาด"
    else:
        msg = "ลูกค้าดีแล้ว รักษาความสัมพันธ์ไว้"

    return jsonify({"insight": msg})


# ======================
# 🚀 RUN
# ======================
if __name__ == "__main__":
    app.run(debug=True)