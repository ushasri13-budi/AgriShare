from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = "agrishare_secret_key"


def create_tables():
    conn = sqlite3.connect("agrishare.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            category TEXT,
            description TEXT,
            price INTEGER,
            location TEXT,
            owner_email TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_id INTEGER,
            farmer_name TEXT,
            booking_date TEXT,
            status TEXT DEFAULT 'Pending',
            farmer_email TEXT
        )
    """)

    conn.commit()
    conn.close()


create_tables()


# ---------------- HOME ----------------

@app.route("/")
def home():
    return render_template("index.html")


# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("agrishare.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, password)
        )

        user = cursor.fetchone()

        conn.close()

        if user:

            role = user[5]

            # Store logged-in user's details in session
            session["email"] = user[2]
            session["fullname"] = user[1]
            session["role"] = role

            if role == "farmer":
                return redirect("/farmer_dashboard")

            elif role == "owner":
                return redirect("/owner_dashboard")

            else:
                return "Invalid role"

        else:
            return "Invalid email or password"

    return render_template("login.html")


# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        fullname = request.form["fullname"]
        email = request.form["email"]
        phone = request.form["phone"]
        role = request.form["role"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            return "Passwords do not match!"

        conn = sqlite3.connect("agrishare.db")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO users(fullname, email, phone, password, role)
            VALUES (?, ?, ?, ?, ?)
        """, (fullname, email, phone, password, role))

        conn.commit()
        conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")


# ---------------- ADD EQUIPMENT ----------------

@app.route("/add_equipment", methods=["GET", "POST"])
def add_equipment():

    if "email" not in session or session.get("role") != "owner":
        return redirect("/login")

    if request.method == "POST":

        name = request.form["name"]
        category = request.form["category"]
        description = request.form["description"]
        price = request.form["price"]
        location = request.form["location"]

        owner_email = session["email"]

        conn = sqlite3.connect("agrishare.db")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO equipment(
                name,
                category,
                description,
                price,
                location,
                owner_email
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            category,
            description,
            price,
            location,
            owner_email
        ))

        conn.commit()
        conn.close()

        return redirect("/dashboard")

    return render_template("add_equipment.html")


# ---------------- EQUIPMENT DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():

    conn = sqlite3.connect("agrishare.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM equipment")
    equipment = cursor.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        equipment=equipment
    )


# ---------------- RENT / SEND REQUEST ----------------

@app.route("/rent/<int:id>", methods=["GET", "POST"])
def rent(id):

    if "email" not in session or session.get("role") != "farmer":
        return redirect("/login")

    conn = sqlite3.connect("agrishare.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM equipment WHERE id=?",
        (id,)
    )

    equipment = cursor.fetchone()

    if equipment is None:
        conn.close()
        return "Equipment not found"

    if request.method == "POST":

        farmer_name = request.form["farmer_name"]
        booking_date = request.form["booking_date"]
        farmer_email = session["email"]

        cursor.execute("""
            INSERT INTO bookings(
                equipment_id,
                farmer_name,
                booking_date,
                status,
                farmer_email
            )
            VALUES (?, ?, ?, 'Pending', ?)
        """,
        (
            id,
            farmer_name,
            booking_date,
            farmer_email
        ))

        conn.commit()
        conn.close()

        return "Rental Request Sent Successfully! ⏳"

    conn.close()

    return render_template(
        "rent.html",
        equipment=equipment
    )


# ---------------- FARMER BOOKINGS ----------------

@app.route("/bookings")
def bookings():

    if "email" not in session:
        return redirect("/login")

    conn = sqlite3.connect("agrishare.db")
    cursor = conn.cursor()

    # Farmer sees only their own requests
    if session.get("role") == "farmer":

        cursor.execute("""
            SELECT equipment.name,
                   bookings.farmer_name,
                   bookings.booking_date,
                   bookings.status
            FROM bookings
            JOIN equipment
            ON bookings.equipment_id = equipment.id
            WHERE bookings.farmer_email=?
        """,
        (session["email"],))

    else:

        # Owner sees bookings related to their equipment
        cursor.execute("""
            SELECT equipment.name,
                   bookings.farmer_name,
                   bookings.booking_date,
                   bookings.status
            FROM bookings
            JOIN equipment
            ON bookings.equipment_id = equipment.id
            WHERE equipment.owner_email=?
        """,
        (session["email"],))

    bookings = cursor.fetchall()

    conn.close()

    return render_template(
        "bookings.html",
        bookings=bookings
    )


# ---------------- OWNER RENTAL REQUESTS ----------------

@app.route("/owner_requests")
def owner_requests():

    if "email" not in session or session.get("role") != "owner":
        return redirect("/login")

    conn = sqlite3.connect("agrishare.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT bookings.id,
               equipment.name,
               bookings.farmer_name,
               bookings.booking_date,
               bookings.status
        FROM bookings
        JOIN equipment
        ON bookings.equipment_id = equipment.id
        WHERE equipment.owner_email=?
    """,
    (session["email"],))

    requests = cursor.fetchall()

    conn.close()

    return render_template(
        "owner_requests.html",
        requests=requests
    )


# ---------------- ACCEPT REQUEST ----------------

@app.route("/accept_request/<int:booking_id>")
def accept_request(booking_id):

    if "email" not in session or session.get("role") != "owner":
        return redirect("/login")

    conn = sqlite3.connect("agrishare.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE bookings
        SET status='Accepted'
        WHERE id=?
        AND equipment_id IN (
            SELECT id
            FROM equipment
            WHERE owner_email=?
        )
    """,
    (booking_id, session["email"]))

    conn.commit()
    conn.close()

    return redirect("/owner_requests")


# ---------------- REJECT REQUEST ----------------

@app.route("/reject_request/<int:booking_id>")
def reject_request(booking_id):

    if "email" not in session or session.get("role") != "owner":
        return redirect("/login")

    conn = sqlite3.connect("agrishare.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE bookings
        SET status='Rejected'
        WHERE id=?
        AND equipment_id IN (
            SELECT id
            FROM equipment
            WHERE owner_email=?
        )
    """,
    (booking_id, session["email"]))

    conn.commit()
    conn.close()

    return redirect("/owner_requests")


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# ---------------- FARMER DASHBOARD ----------------

@app.route("/farmer_dashboard")
def farmer_dashboard():

    if "email" not in session or session.get("role") != "farmer":
        return redirect("/login")

    return render_template(
        "farmer_dashboard.html"
    )


# ---------------- OWNER DASHBOARD ----------------

@app.route("/owner_dashboard")
def owner_dashboard():

    if "email" not in session or session.get("role") != "owner":
        return redirect("/login")

    return render_template(
        "owner_dashboard.html"
    )


@app.route("/equipment/<name>")
def equipment_details(name):

    conn = sqlite3.connect("agrishare.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM equipment WHERE LOWER(name) = LOWER(?)",
        (name,)
    )

    equipment = cursor.fetchone()

    conn.close()

    return render_template(
        "equipment_details.html",
        equipment=equipment
    )

# ---------------- RUN APPLICATION ----------------

if __name__ == "__main__":
    app.run(debug=True)