from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

# 📦 CONEXION DB
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

# 🧠 CREAR TABLA SI NO EXISTE
def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE,
            nombre TEXT,
            cantidad INTEGER
        )
    """)
    conn.close()

init_db()

# 🏠 HOME
@app.route("/")
def index():
    conn = get_db()
    productos = conn.execute("SELECT * FROM productos").fetchall()
    conn.close()
    return render_template("index.html", productos=productos)

# ➕ AGREGAR
@app.route("/agregar", methods=["POST"])
def agregar():
    codigo = request.form["codigo"]
    nombre = request.form["nombre"]
    cantidad = int(request.form["cantidad"])

    conn = get_db()

    existente = conn.execute(
        "SELECT * FROM productos WHERE codigo = ?",
        (codigo,)
    ).fetchone()

    if existente:
        conn.execute(
            "UPDATE productos SET cantidad = cantidad + ? WHERE codigo = ?",
            (cantidad, codigo)
        )
    else:
        conn.execute(
            "INSERT INTO productos (codigo, nombre, cantidad) VALUES (?, ?, ?)",
            (codigo, nombre, cantidad)
        )

    conn.commit()
    conn.close()

    return redirect("/")

# ➕ SUMAR
@app.route("/sumar/<codigo>")
def sumar(codigo):
    conn = get_db()
    conn.execute(
        "UPDATE productos SET cantidad = cantidad + 1 WHERE codigo = ?",
        (codigo,)
    )
    conn.commit()
    conn.close()
    return redirect("/")

# ➖ RESTAR (VENTA)
@app.route("/restar/<codigo>")
def restar(codigo):
    conn = get_db()
    conn.execute(
        "UPDATE productos SET cantidad = CASE WHEN cantidad > 0 THEN cantidad - 1 ELSE 0 END WHERE codigo = ?",
        (codigo,)
    )
    conn.commit()
    conn.close()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)