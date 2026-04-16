from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import jwt
import datetime

app = Flask(__name__)
CORS(app)

SECRET_KEY = "mysecretkey"

def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="1230",   # 👈 ของคุณ
        database="crm_db"
    )

# ================= REGISTER =================
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    conn = get_db()
    c = conn.cursor()

    c.execute(
        "INSERT INTO users (username, password) VALUES (%s, %s)",
        (data['username'], data['password'])
    )

    conn.commit()
    conn.close()
    return {"message": "registered"}

# ================= LOGIN =================
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    conn = get_db()
    c = conn.cursor()

    c.execute(
        "SELECT * FROM users WHERE username=%s AND password=%s",
        (data['username'], data['password'])
    )

    user = c.fetchone()
    conn.close()

    if user:
        token = jwt.encode({
            "user_id": user[0],
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)
        }, SECRET_KEY, algorithm="HS256")

        return {"token": token}

    return {"message": "login failed"}, 401

# ================= VERIFY TOKEN =================
def verify_token(token):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except:
        return None

# ================= ADD CUSTOMER =================
@app.route('/add_customer', methods=['POST'])
def add_customer():
    token = request.headers.get('Authorization')
    user = verify_token(token)

    if not user:
        return {"message": "unauthorized"}, 401

    data = request.json
    name = data['name']
    phone = data['phone']
    tag = data.get('tag', 'New')

    conn = get_db()
    c = conn.cursor()

    c.execute(
        "INSERT INTO customers (user_id, name, phone, tag) VALUES (%s, %s, %s, %s)",
        (user['user_id'], name, phone, tag)
    )

    conn.commit()
    conn.close()

    return {"message": "added"}

# ================= GET CUSTOMERS =================
@app.route('/customers', methods=['GET'])
def customers():
    token = request.headers.get('Authorization')
    user = verify_token(token)

    if not user:
        return {"message": "unauthorized"}, 401

    conn = get_db()
    c = conn.cursor()

    c.execute(
        "SELECT id, name, phone, tag FROM customers WHERE user_id=%s",
        (user['user_id'],)
    )

    data = c.fetchall()
    conn.close()

    return jsonify(data)

# ================= DASHBOARD =================
@app.route('/dashboard', methods=['GET'])
def dashboard():
    token = request.headers.get('Authorization')
    user = verify_token(token)

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        SELECT tag, COUNT(*) 
        FROM customers 
        WHERE user_id=%s 
        GROUP BY tag
    """, (user['user_id'],))

    data = c.fetchall()
    conn.close()

    return {"data": data}

# ================= AI =================
@app.route('/ai', methods=['GET'])
def ai():
    token = request.headers.get('Authorization')
    user = verify_token(token)

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT tag, COUNT(*) FROM customers WHERE user_id=%s GROUP BY tag", (user['user_id'],))
    data = dict(c.fetchall())

    conn.close()

    vip = data.get('VIP', 0)
    new = data.get('New', 0)

    if vip > 5:
        insight = "ลูกค้า VIP เยอะ ควรทำโปรพิเศษ"
    elif new > 5:
        insight = "ลูกค้าใหม่เยอะ รีบปิดการขาย"
    else:
        insight = "ควรเพิ่มลูกค้าใหม่"

    return {"insight": insight}

if __name__ == '__main__':
    app.run(debug=True)