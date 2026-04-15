from flask import Flask, render_template, request, redirect, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "stockar_secret"

# DB
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT,
        nombre TEXT,
        cantidad INTEGER,
        user_id INTEGER
    )
    """)

    conn.close()

init_db()

# LOGIN
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM usuarios WHERE username=?",
            (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            return redirect("/")
        else:
            return "Login incorrecto"

    return render_template("login.html")

# REGISTER
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        password_hash = generate_password_hash(password)

        conn = get_db()
        conn.execute(
            "INSERT INTO usuarios (username,password) VALUES (?,?)",
            (username, password_hash)
        )
        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")

# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# HOME
@app.route("/")
def index():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    productos = conn.execute(
        "SELECT * FROM productos WHERE user_id=?",
        (session["user_id"],)
    ).fetchall()
    conn.close()

    return render_template("index.html", productos=productos)

# AGREGAR
@app.route("/agregar", methods=["POST"])
def agregar():
    codigo = request.form["codigo"]
    nombre = request.form["nombre"]
    cantidad = int(request.form["cantidad"])

    conn = get_db()

    existente = conn.execute(
        "SELECT * FROM productos WHERE codigo=? AND user_id=?",
        (codigo, session["user_id"])
    ).fetchone()

    if existente:
        conn.execute(
            "UPDATE productos SET cantidad = cantidad + ? WHERE codigo=? AND user_id=?",
            (cantidad, codigo, session["user_id"])
        )
    else:
        conn.execute(
            "INSERT INTO productos (codigo,nombre,cantidad,user_id) VALUES (?,?,?,?)",
            (codigo, nombre, cantidad, session["user_id"])
        )

    conn.commit()
    conn.close()

    return redirect("/")

# SUMAR
@app.route("/sumar/<codigo>")
def sumar(codigo):
    conn = get_db()
    conn.execute(
        "UPDATE productos SET cantidad = cantidad + 1 WHERE codigo=? AND user_id=?",
        (codigo, session["user_id"])
    )
    conn.commit()
    conn.close()
    return redirect("/")

# RESTAR
@app.route("/restar/<codigo>")
def restar(codigo):
    conn = get_db()
    conn.execute(
        "UPDATE productos SET cantidad = CASE WHEN cantidad > 0 THEN cantidad - 1 ELSE 0 END WHERE codigo=? AND user_id=?",
        (codigo, session["user_id"])
    )
    conn.commit()
    conn.close()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)