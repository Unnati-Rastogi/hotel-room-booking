# ============================================================
#  Smart Hotel Booking System — Flask Backend
#  app.py  |  MySQL via mysql-connector-python
# ============================================================

import os
import time
import random
import threading
import mysql.connector
from mysql.connector import Error, errorcode
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime, date

# Serve index.html from the same directory as this script
app = Flask(__name__, static_folder=os.path.dirname(os.path.abspath(__file__)))
CORS(app)

# ──────────────────────────────────────────────────────────
#  DB CONFIG  — ⚠️  SET YOUR MYSQL PASSWORD BELOW
# ──────────────────────────────────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "@R00t123",
    "database": "hotel_booking",
    "autocommit": False,
    "connection_timeout": 10,
}


def get_connection():
    """Return a fresh MySQL connection (autocommit OFF)."""
    return mysql.connector.connect(**DB_CONFIG)


# ──────────────────────────────────────────────────────────
#  STARTUP: ensure reviews table exists + seed sample data
# ──────────────────────────────────────────────────────────
def ensure_reviews_table():
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                review_id     INT AUTO_INCREMENT PRIMARY KEY,
                customer_name VARCHAR(120) NOT NULL,
                rating        TINYINT NOT NULL,
                comment       TEXT,
                room_type     VARCHAR(30) DEFAULT '',
                view_type     VARCHAR(20) DEFAULT '',
                room_number   VARCHAR(20) DEFAULT '',
                review_date   DATETIME DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT chk_rating CHECK (rating BETWEEN 1 AND 5)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        # Add missing columns for existing installs
        for col_sql in [
            "ALTER TABLE reviews ADD COLUMN view_type VARCHAR(20) DEFAULT ''",
            "ALTER TABLE reviews ADD COLUMN room_number VARCHAR(20) DEFAULT ''",
        ]:
            try:
                cursor.execute(col_sql)
                conn.commit()
            except Error:
                pass  # column already exists
        conn.commit()

        # Seed sample reviews if table is empty
        cursor.execute("SELECT COUNT(*) FROM reviews")
        if cursor.fetchone()[0] == 0:
            sample = [
                ('Priya Sharma',  5, 'The sea-view suite was absolutely breathtaking. Waking up to the ocean every morning was magical!',  'suite',  'sea',    '2026-03-15 10:00:00'),
                ('Arjun Mehta',   4, 'Pool-view double room was spacious and the view was stunning. Fell asleep to the sound of the pool.', 'double', 'pool',   '2026-03-22 14:30:00'),
                ('Sneha Iyer',    5, 'The garden view room was so peaceful. Woke up to birds and greenery — felt like a private retreat.',   'double', 'garden', '2026-04-01 09:15:00'),
                ('Rahul Gupta',   4, 'City lights from the single room were gorgeous at night. Great for business travellers.',              'single', 'city',   '2026-04-08 16:45:00'),
                ('Ananya Kapoor', 5, 'Sea-view suite — every detail was perfect. The balcony sunset view alone is worth the price.',         'suite',  'sea',    '2026-04-10 11:00:00'),
                ('Vikram Nair',   3, 'Pool view was nice but a bit noisy in the evening. Room was clean and staff were helpful.',            'single', 'pool',   '2026-04-12 08:30:00'),
                ('Meera Joshi',   5, 'Garden-view double exceeded all expectations. Quiet, lush, and incredibly comfortable.',               'double', 'garden', '2026-04-14 09:00:00'),
                ('Kabir Singh',   4, 'City-view suite had a panoramic skyline — rooms are modern and the bed was extremely comfortable.',    'suite',  'city',   '2026-04-14 18:00:00'),
            ]
            cursor.executemany(
                "INSERT INTO reviews (customer_name, rating, comment, room_type, view_type, review_date) VALUES (%s,%s,%s,%s,%s,%s)",
                sample
            )
            conn.commit()
        print("Reviews table ready.")
    except Error as e:
        print(f"Warning: Could not set up reviews table: {e}")
    finally:
        try: cursor.close(); conn.close()
        except Exception: pass


def ensure_bookings_columns():
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        # Add columns for guests and breakfast if they don't exist
        columns = [
            ("adults", "INT NOT NULL DEFAULT 1"),
            ("children", "INT NOT NULL DEFAULT 0"),
            ("breakfast_opt", "BOOLEAN NOT NULL DEFAULT 0"),
            ("breakfast_days", "INT NOT NULL DEFAULT 0"),
        ]
        for col_name, col_def in columns:
            try:
                cursor.execute(f"ALTER TABLE bookings ADD COLUMN {col_name} {col_def}")
                conn.commit()
            except Error:
                pass  # column already exists
        print("Bookings table columns verified.")
    except Error as e:
        print(f"Warning: Could not update bookings table: {e}")
    finally:
        try: cursor.close(); conn.close()
        except Exception: pass


def ensure_customers_password():
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("ALTER TABLE customers ADD COLUMN password VARCHAR(255) NOT NULL DEFAULT 'pass123'")
            conn.commit()
            print("Customers table updated with password column.")
        except Error:
            pass  # column already exists
    except Error as e:
        print(f"Warning: Could not update customers table: {e}")
    finally:
        try: cursor.close(); conn.close()
        except Exception: pass


def ensure_sample_bookings():
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT COUNT(*) as count FROM bookings")
        if cursor.fetchone()["count"] < 10:  # Seed more if we have few
            print("Seeding more sample bookings...")
            cursor.execute("SELECT customer_id FROM customers LIMIT 1")
            cust = cursor.fetchone()
            if not cust:
                cursor.execute("INSERT INTO customers (name, email, phone, password) VALUES ('Sample Guest', 'guest@example.com', '9876543210', 'pass123')")
                conn.commit()
                cursor.execute("SELECT customer_id FROM customers WHERE email = 'guest@example.com'")
                cust = cursor.fetchone()
            
            customer_id = cust["customer_id"]
            
            # Get rooms that are marked as 'booked' but don't have active bookings
            cursor.execute("""
                SELECT r.room_id FROM rooms r
                LEFT JOIN bookings b ON b.room_id = r.room_id AND b.check_out >= CURDATE()
                WHERE r.status = 'booked' AND b.booking_id IS NULL
            """)
            rooms_to_book = cursor.fetchall()
            
            today = date.today()
            for r in rooms_to_book:
                # Random check-in in the past/near future
                cursor.execute("""
                    INSERT INTO bookings (customer_id, room_id, check_in, check_out, adults, children)
                    VALUES (%s, %s, %s, DATE_ADD(%s, INTERVAL 3 DAY), 1, 0)
                """, (customer_id, r["room_id"], today, today))
                
                cursor.execute("SELECT LAST_INSERT_ID() as id")
                bid = cursor.fetchone()["id"]
                cursor.execute("INSERT INTO payments (booking_id, amount, payment_status) VALUES (%s, 7500.00, 'success')", (bid,))
            
            conn.commit()
            print(f"Added {len(rooms_to_book)} more sample bookings.")
            
    except Error as e:
        print(f"Warning: Could not seed sample bookings: {e}")
    finally:
        try: cursor.close(); conn.close()
        except Exception: pass


# ══════════════════════════════════════════════════════════
#  PATCH /rooms/release-all
# ══════════════════════════════════════════════════════════
@app.route("/rooms/release-all", methods=["PATCH"])
def release_all_rooms():
    conn = cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        conn.start_transaction()
        # Must delete payments first (FK: payments.booking_id -> bookings.booking_id)
        cursor.execute("""
            DELETE p FROM payments p
            JOIN bookings b ON b.booking_id = p.booking_id
            WHERE b.check_out >= CURDATE()
        """)
        cursor.execute("DELETE FROM bookings WHERE check_out >= CURDATE()")
        cursor.execute("UPDATE rooms SET status = 'available'")
        conn.commit()
        return jsonify({"success": True, "message": "All rooms released successfully."}), 200
    except Error as e:
        if conn: conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        try: cursor.close(); conn.close()
        except Exception: pass


# ══════════════════════════════════════════════════════════
#  GET /rooms/auto-release
#  Trigger checkout-based auto-release from the frontend.
#  Called on page load so expired rooms are freed immediately.
# ══════════════════════════════════════════════════════════
@app.route("/rooms/auto-release", methods=["GET"])
def trigger_auto_release():
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT DISTINCT r.room_id, r.room_number
            FROM rooms r
            WHERE r.status = 'booked'
              AND NOT EXISTS (
                  SELECT 1 FROM bookings b
                  WHERE b.room_id  = r.room_id
                    AND b.check_out > CURDATE()
              )
        """)
        expired = cursor.fetchall()

        if expired:
            conn.start_transaction()
            ids = [r["room_id"] for r in expired]
            fmt = ",".join(["%s"] * len(ids))
            cursor.execute(
                f"UPDATE rooms SET status = 'available' WHERE room_id IN ({fmt})", ids
            )
            conn.commit()
            return jsonify({
                "success": True,
                "freed": len(ids),
                "rooms": [r["room_number"] for r in expired]
            }), 200
        else:
            return jsonify({"success": True, "freed": 0}), 200

    except Error as e:
        if conn:
            try: conn.rollback()
            except Exception: pass
        return jsonify({"error": str(e)}), 500
    finally:
        try: cursor.close(); conn.close()
        except Exception: pass


# ══════════════════════════════════════════════════════════
#  POST /register
# ══════════════════════════════════════════════════════════
@app.route("/register", methods=["POST"])
def register_user():
    data = request.get_json(force=True)
    name     = data.get("name", "").strip()
    email    = data.get("email", "").strip().lower()
    phone    = data.get("phone", "").strip()
    password = data.get("password", "").strip()

    if not name or not email or not password:
        return jsonify({"error": "Name, email and password are required."}), 400

    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO customers (name, email, phone, password)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE name=VALUES(name), phone=VALUES(phone), password=VALUES(password)
        """, (name, email, phone, password))
        conn.commit()
        return jsonify({"success": True, "message": "User registered successfully."}), 201
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try: cursor.close(); conn.close()
        except Exception: pass


# ══════════════════════════════════════════════════════════
#  POST /login
# ══════════════════════════════════════════════════════════
@app.route("/login", methods=["POST"])
def login_user():
    data = request.get_json(force=True)
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM customers WHERE email = %s AND password = %s", (email, password))
        user = cursor.fetchone()
        
        if user:
            return jsonify({
                "success": True,
                "user": {
                    "name": user["name"],
                    "email": user["email"],
                    "phone": user["phone"],
                    "role": "user"
                }
            }), 200
        else:
            return jsonify({"error": "Invalid email or password."}), 401
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try: cursor.close(); conn.close()
        except Exception: pass

# ══════════════════════════════════════════════════════════
#  SERVE FRONTEND  — http://127.0.0.1:5000
# ══════════════════════════════════════════════════════════
@app.route("/")
def serve_frontend():
    return send_from_directory(app.static_folder, "index.html")


# ══════════════════════════════════════════════════════════
#  GET /rooms
#  Optional query params: floor, view_type, max_price
# ══════════════════════════════════════════════════════════
@app.route("/rooms", methods=["GET"])
def get_rooms():
    floor     = request.args.get("floor")
    view_type = request.args.get("view_type")
    max_price = request.args.get("max_price")

    query  = "SELECT * FROM rooms WHERE 1=1"
    params = []
    if floor:     query += " AND floor_number = %s"; params.append(int(floor))
    if view_type: query += " AND view_type = %s";    params.append(view_type)
    if max_price: query += " AND price <= %s";       params.append(float(max_price))
    query += " ORDER BY floor_number ASC, room_number ASC"

    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params)
        rooms  = cursor.fetchall()
        for r in rooms:
            r["price"] = float(r["price"])
        return jsonify(rooms), 200
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try: cursor.close(); conn.close()
        except Exception: pass


# ══════════════════════════════════════════════════════════
#  POST /book
#  Full ACID transaction + payment simulation
#  Body: name, email, phone, room_id, check_in, check_out,
#        card_last4  (last 4 digits for simulation)
# ══════════════════════════════════════════════════════════
@app.route("/book", methods=["POST"])
def book_room():
    data = request.get_json(force=True)
    required = ["name", "email", "room_id", "check_in", "check_out"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"Missing field: {field}"}), 400

    name           = data["name"].strip()
    email          = data["email"].strip().lower()
    phone          = data.get("phone", "").strip()
    room_id        = int(data["room_id"])
    check_in       = data["check_in"]
    check_out      = data["check_out"]
    adults         = int(data.get("adults", 1))
    children       = int(data.get("children", 0))
    breakfast_opt  = bool(data.get("breakfast_opt", False))
    breakfast_days = int(data.get("breakfast_days", 0))
    card_last4     = str(data.get("card_last4", "0000"))[-4:]
    payment_method = data.get("payment_method", "full_card")  # full_card | advance_card | cash

    # ── Payment Simulation (skip for cash) ───────────────
    if payment_method in ("full_card", "advance_card"):
        payment_ok = True
        if not payment_ok:
            return jsonify({
                "error": f"Payment declined for card ending ····{card_last4}. "
                         f"Please check your card details or try a different card.",
                "code":  "PAYMENT_FAILED"
            }), 402

    # ── Date validation ────────────────────────────────────
    try:
        ci = datetime.strptime(check_in,  "%Y-%m-%d").date()
        co = datetime.strptime(check_out, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400
    if co <= ci:
        return jsonify({"error": "Check-out must be after check-in."}), 400
    if ci < date.today():
        return jsonify({"error": "Check-in cannot be in the past."}), 400

    conn = cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. BEGIN
        conn.start_transaction(isolation_level="READ COMMITTED")

        # 2. Row-level lock
        cursor.execute("SELECT * FROM rooms WHERE room_id = %s FOR UPDATE", (room_id,))
        room = cursor.fetchone()
        if not room:
            conn.rollback(); return jsonify({"error": "Room not found."}), 404

        # 3. Status check
        if room["status"] == "booked":
            conn.rollback(); return jsonify({"error": "Room is already booked."}), 409

        # 4. Date overlap check
        cursor.execute("""
            SELECT booking_id FROM bookings
            WHERE room_id = %s AND check_in < %s AND check_out > %s
        """, (room_id, check_out, check_in))
        if cursor.fetchone():
            conn.rollback(); return jsonify({"error": "Room is already booked for selected dates."}), 409

        # 5. Upsert customer (handle password gracefully)
        password = data.get("password", "").strip()
        if password:
            cursor.execute("""
                INSERT INTO customers (name, email, phone, password) VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE name = VALUES(name), phone = VALUES(phone), password = VALUES(password)
            """, (name, email, phone, password))
        else:
            cursor.execute("""
                INSERT INTO customers (name, email, phone, password) VALUES (%s, %s, %s, 'pass123')
                ON DUPLICATE KEY UPDATE name = VALUES(name), phone = VALUES(phone)
            """, (name, email, phone))
        cursor.execute("SELECT customer_id FROM customers WHERE email = %s", (email,))
        customer_id = cursor.fetchone()["customer_id"]

        # 6. Insert booking
        cursor.execute("""
            INSERT INTO bookings (customer_id, room_id, check_in, check_out, adults, children, breakfast_opt, breakfast_days)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (customer_id, room_id, check_in, check_out, adults, children, 1 if breakfast_opt else 0, breakfast_days))
        booking_id = cursor.lastrowid

        # 7. Insert payment based on method
        nights     = (co - ci).days
        room_total = float(room["price"]) * nights
        breakfast_total = 0
        if breakfast_opt:
            breakfast_total = 500 * (adults + children) * breakfast_days
        
        full_amount = room_total + breakfast_total
        if payment_method == "advance_card":
            paid_amount    = round(full_amount * 0.30, 2)
            payment_status = "advance"
        elif payment_method == "cash":
            paid_amount    = 0.0
            payment_status = "cash"
        else:
            paid_amount    = full_amount
            payment_status = "success"

        cursor.execute("""
            INSERT INTO payments (booking_id, amount, payment_status)
            VALUES (%s, %s, %s)
        """, (booking_id, paid_amount, payment_status))

        # 8. COMMIT
        conn.commit()

        return jsonify({
            "success":        True,
            "booking_id":     booking_id,
            "room":           room["room_number"],
            "floor":          room["floor_number"],
            "room_type":      room["room_type"],
            "view_type":      room["view_type"],
            "customer":       name,
            "nights":         nights,
            "amount":         paid_amount,
            "full_amount":    full_amount,
            "payment_method": payment_method,
            "check_in":       check_in,
            "check_out":      check_out,
            "card_last4":     card_last4,
        }), 201

    except Error as e:
        if conn: conn.rollback()
        if e.errno == errorcode.ER_LOCK_DEADLOCK:
            return jsonify({"error": "A deadlock occurred. Please try again.", "code": "DEADLOCK"}), 503
        if e.errno == errorcode.ER_LOCK_WAIT_TIMEOUT:
            return jsonify({"error": "Server busy. Please retry.", "code": "LOCK_TIMEOUT"}), 503
        return jsonify({"error": str(e)}), 500
    finally:
        try: cursor.close(); conn.close()
        except Exception: pass


# ══════════════════════════════════════════════════════════
#  GET /bookings
# ══════════════════════════════════════════════════════════
@app.route("/bookings", methods=["GET"])
def get_bookings():
    show_all = request.args.get("all", "0") == "1"
    where = "" if show_all else "WHERE b.check_out >= CURDATE()"
    query = f"""
        SELECT b.booking_id, b.check_in, b.check_out, b.booking_date,
               b.adults, b.children, b.breakfast_opt, b.breakfast_days,
               c.name AS customer_name, c.email AS customer_email, c.phone AS customer_phone,
               r.room_id, r.room_number, r.floor_number, r.room_type, r.price, r.view_type,
               p.amount, p.payment_status
        FROM bookings b
        JOIN customers c ON c.customer_id = b.customer_id
        JOIN rooms     r ON r.room_id     = b.room_id
        LEFT JOIN payments p ON p.booking_id = b.booking_id
        {where}
        ORDER BY b.check_in ASC
    """
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query)
        rows = cursor.fetchall()
        for row in rows:
            for k, v in row.items():
                if isinstance(v, (date, datetime)):
                    row[k] = str(v)
                elif hasattr(v, "__class__") and v.__class__.__name__ == "Decimal":
                    row[k] = float(v)
        return jsonify(rows), 200
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try: cursor.close(); conn.close()
        except Exception: pass


# ══════════════════════════════════════════════════════════
#  GET /reviews — fetch all guest reviews
# ══════════════════════════════════════════════════════════
@app.route("/reviews", methods=["GET"])
def get_reviews():
    room_type = request.args.get("room_type", "").strip()
    view_type = request.args.get("view_type", "").strip()
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        if room_type and view_type:
            # Exact match: same room_type AND view_type (most relevant)
            cursor.execute("""
                SELECT * FROM reviews
                WHERE room_type = %s AND view_type = %s
                ORDER BY review_date DESC LIMIT 10
            """, (room_type, view_type))
        elif view_type:
            # Same view (e.g. all sea-view rooms)
            cursor.execute("""
                SELECT * FROM reviews
                WHERE view_type = %s
                ORDER BY review_date DESC LIMIT 10
            """, (view_type,))
        elif room_type:
            cursor.execute("""
                SELECT * FROM reviews
                WHERE room_type = %s
                ORDER BY review_date DESC LIMIT 10
            """, (room_type,))
        else:
            cursor.execute("SELECT * FROM reviews ORDER BY review_date DESC LIMIT 30")
        rows = cursor.fetchall()
        for r in rows:
            if isinstance(r.get("review_date"), (date, datetime)):
                r["review_date"] = str(r["review_date"])
        return jsonify(rows), 200
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try: cursor.close(); conn.close()
        except Exception: pass


# ══════════════════════════════════════════════════════════
#  POST /review — submit a guest review
#  Body: customer_name, rating (1-5), comment, room_type
# ══════════════════════════════════════════════════════════
@app.route("/review", methods=["POST"])
def post_review():
    data        = request.get_json(force=True)
    name        = data.get("customer_name", "").strip()
    comment     = data.get("comment", "").strip()
    room_type   = data.get("room_type", "").strip()
    view_type   = data.get("view_type", "").strip()
    room_number = data.get("room_number", "").strip()
    try:
        rating = int(data.get("rating", 5))
    except (ValueError, TypeError):
        rating = 5

    if not name or not comment:
        return jsonify({"error": "Name and comment are required."}), 400
    if not (1 <= rating <= 5):
        return jsonify({"error": "Rating must be between 1 and 5."}), 400

    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO reviews (customer_name, rating, comment, room_type, view_type, room_number)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, rating, comment, room_type, view_type, room_number))
        conn.commit()
        return jsonify({"success": True, "review_id": cursor.lastrowid}), 201
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try: cursor.close(); conn.close()
        except Exception: pass


# ══════════════════════════════════════════════════════════
#  POST /simulate-deadlock  (DBMS demo)
# ══════════════════════════════════════════════════════════
@app.route("/simulate-deadlock", methods=["POST"])
def simulate_deadlock():
    results = {"thread_a": None, "thread_b": None}

    def transaction_a():
        try:
            conn = get_connection(); cursor = conn.cursor()
            conn.start_transaction()
            cursor.execute("SELECT room_id FROM rooms WHERE room_id = 1 FOR UPDATE")
            time.sleep(1.5)
            cursor.execute("SELECT room_id FROM rooms WHERE room_id = 2 FOR UPDATE")
            conn.rollback()
            results["thread_a"] = "completed without deadlock"
        except Error as e:
            try: conn.rollback()
            except Exception: pass
            results["thread_a"] = f"error: {e}"
        finally:
            try: cursor.close(); conn.close()
            except Exception: pass

    def transaction_b():
        try:
            conn = get_connection(); cursor = conn.cursor()
            conn.start_transaction()
            time.sleep(0.3)
            cursor.execute("SELECT room_id FROM rooms WHERE room_id = 2 FOR UPDATE")
            time.sleep(1.5)
            cursor.execute("SELECT room_id FROM rooms WHERE room_id = 1 FOR UPDATE")
            conn.rollback()
            results["thread_b"] = "completed without deadlock"
        except Error as e:
            try: conn.rollback()
            except Exception: pass
            results["thread_b"] = f"error: {e}"
        finally:
            try: cursor.close(); conn.close()
            except Exception: pass

    ta = threading.Thread(target=transaction_a)
    tb = threading.Thread(target=transaction_b)
    ta.start(); tb.start()
    ta.join();  tb.join()

    detected = any("deadlock" in str(v).lower() for v in results.values())
    return jsonify({
        "simulation": "deadlock", "deadlock_detected": detected,
        "thread_a_result": results["thread_a"],
        "thread_b_result": results["thread_b"],
        "explanation": "InnoDB's deadlock detector killed one transaction (victim), allowing the other to proceed.",
    }), 200


# ══════════════════════════════════════════════════════════
#  PATCH /rooms/<room_id>/release  (Admin: release a room)
#  Marks the room status back to 'available' and removes
#  any future bookings for that room.
# ══════════════════════════════════════════════════════════
@app.route("/rooms/<int:room_id>/release", methods=["PATCH"])
def release_room(room_id):
    conn = cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        conn.start_transaction()

        # Check room exists
        cursor.execute("SELECT * FROM rooms WHERE room_id = %s FOR UPDATE", (room_id,))
        room = cursor.fetchone()
        if not room:
            conn.rollback()
            return jsonify({"error": "Room not found."}), 404

        # Get booking IDs for this room first
        cursor.execute("""
            SELECT booking_id FROM bookings
            WHERE room_id = %s AND check_out >= CURDATE()
        """, (room_id,))
        booking_ids = [r["booking_id"] for r in cursor.fetchall()]

        if booking_ids:
            # Delete payments first (FK constraint)
            fmt_ids = ",".join(["%s"] * len(booking_ids))
            cursor.execute(f"DELETE FROM payments WHERE booking_id IN ({fmt_ids})", booking_ids)
            # Then delete bookings
            cursor.execute(f"DELETE FROM bookings WHERE booking_id IN ({fmt_ids})", booking_ids)

        # Mark room as available
        cursor.execute(
            "UPDATE rooms SET status = 'available' WHERE room_id = %s",
            (room_id,)
        )
        conn.commit()
        return jsonify({"success": True, "room_id": room_id, "status": "available"}), 200

    except Error as e:
        if conn: conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        try: cursor.close(); conn.close()
        except Exception: pass


# ══════════════════════════════════════════════════════════
#  GET /bookings/user/<email>  — bookings for one customer
# ══════════════════════════════════════════════════════════
@app.route("/bookings/user/<path:email>", methods=["GET"])
def get_user_bookings(email):
    query = """
        SELECT b.booking_id, b.check_in, b.check_out, b.booking_date,
               c.name AS customer_name, c.email AS customer_email, c.phone AS customer_phone,
               r.room_id, r.room_number, r.floor_number, r.room_type, r.price, r.view_type,
               p.amount, p.payment_status
        FROM bookings b
        JOIN customers c ON c.customer_id = b.customer_id
        JOIN rooms     r ON r.room_id     = b.room_id
        LEFT JOIN payments p ON p.booking_id = b.booking_id
        WHERE LOWER(c.email) = LOWER(%s)
        ORDER BY b.booking_date DESC
    """
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, (email.strip(),))
        rows = cursor.fetchall()
        for row in rows:
            for k, v in row.items():
                if isinstance(v, (date, datetime)):
                    row[k] = str(v)
                elif hasattr(v, "__class__") and v.__class__.__name__ == "Decimal":
                    row[k] = float(v)
        return jsonify(rows), 200
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try: cursor.close(); conn.close()
        except Exception: pass

# ══════════════════════════════════════════════════════════
#  REVIEW UTILITIES  (merged from reviews.py)
#  Admin/seeding helpers — not exposed as API routes.
# ══════════════════════════════════════════════════════════
import math as _math

def insert_reviews(reviews_data):
    """Insert reviews, auto-filling room_type & view_type from room_number.
    reviews_data: list of (room_number, customer_name, comment, rating)
    """
    conn = cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        for room_num, name, comment, rating in reviews_data:
            cursor.execute("SELECT room_type, view_type FROM rooms WHERE room_number = %s", (room_num,))
            room  = cursor.fetchone()
            rtype = room["room_type"] if room else ""
            vtype = room["view_type"] if room else ""
            r_int = int(_math.ceil(rating))
            cursor.execute("""
                INSERT INTO reviews (customer_name, rating, comment, room_type, view_type, room_number)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (name, r_int, comment, rtype, vtype, room_num))
        conn.commit()
        print(f"Inserted {len(reviews_data)} reviews.")
    except Error as e:
        print(f"Error inserting reviews: {e}")
        if conn: conn.rollback()
    finally:
        try: cursor.close(); conn.close()
        except Exception: pass


def delete_reviews_not_in(names_to_keep):
    """Delete reviews whose customer_name is NOT in the provided list."""
    conn = cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        fmt    = ",".join(["%s"] * len(names_to_keep))
        cursor.execute(f"DELETE FROM reviews WHERE customer_name NOT IN ({fmt})", tuple(names_to_keep))
        conn.commit()
        print(f"Deleted {cursor.rowcount} old reviews.")
    except Error as e:
        print(f"Error deleting reviews: {e}")
    finally:
        try: cursor.close(); conn.close()
        except Exception: pass


def sync_reviews_with_rooms():
    """Update reviews.room_type/view_type to match the rooms table (backfill)."""
    conn = cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE reviews rev
            JOIN rooms rm ON rev.room_number = rm.room_number
            SET rev.room_type = rm.room_type, rev.view_type = rm.view_type
            WHERE rev.room_number != '' AND rev.room_number IS NOT NULL
        """)
        conn.commit()
        print("Synced review types with rooms table.")
    except Error as e:
        print(f"Error syncing reviews: {e}")
    finally:
        try: cursor.close(); conn.close()
        except Exception: pass


# ══════════════════════════════════════════════════════════
#  AUTO-RELEASE SCHEDULER
#  Runs in a daemon background thread every hour.
#  Sets rooms to 'available' once their check_out date has passed.
# ══════════════════════════════════════════════════════════

def auto_release_rooms():
    """Free any room whose latest booking check_out < today."""
    conn = cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        conn.start_transaction()

        # Rooms still marked 'booked' but with NO future/active booking
        cursor.execute("""
            SELECT DISTINCT r.room_id, r.room_number
            FROM rooms r
            WHERE r.status = 'booked'
              AND NOT EXISTS (
                  SELECT 1 FROM bookings b
                  WHERE b.room_id  = r.room_id
                    AND b.check_out > CURDATE()
              )
        """)
        expired = cursor.fetchall()

        if expired:
            ids  = [r["room_id"]     for r in expired]
            nums = [r["room_number"] for r in expired]
            fmt  = ",".join(["%s"] * len(ids))
            cursor.execute(
                f"UPDATE rooms SET status = 'available' WHERE room_id IN ({fmt})",
                ids
            )
            conn.commit()
            print(f"[AutoRelease] {date.today()} — freed {len(ids)} room(s): {', '.join(nums)}")
        else:
            conn.rollback()

    except Error as e:
        print(f"[AutoRelease] Error: {e}")
        if conn:
            try: conn.rollback()
            except Exception: pass
    finally:
        try: cursor.close(); conn.close()
        except Exception: pass


def _run_scheduler(interval=3600):
    """Loop forever: release expired rooms, then sleep for interval seconds."""
    while True:
        auto_release_rooms()
        time.sleep(interval)


# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    ensure_reviews_table()
    ensure_bookings_columns()
    ensure_customers_password()
    ensure_sample_bookings()

    # Immediately release any rooms that already passed checkout
    auto_release_rooms()

    # Background thread: re-checks every hour (daemon exits with server)
    t = threading.Thread(target=_run_scheduler, kwargs={"interval": 3600},
                         daemon=True, name="AutoRelease")
    t.start()
    print("[AutoRelease] Scheduler started — checks every 1 hour.")

    app.run(debug=True, port=5000)