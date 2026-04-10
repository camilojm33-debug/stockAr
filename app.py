from flask import Flask, render_template, request, redirect
import sqlite3
import os
import requests

app = Flask(__name__)

# 📦 Ruta DB (IMPORTANTE PARA RENDER)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")


def get_db():
    return sqlite3.connect(DB_PATH)


# 🔥 CREAR DB AUTOMÁTICAMENTE
def crear_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT,
            nombre TEXT,
            cantidad INTEGER
        )
    """)
    conn.commit()
    conn.close()


crear_db()


# 🔍 API código de barras
def obtener_producto(codigo):
    try:
        url = f"https://world.openfoodfacts.org/api/v0/product/{codigo}.json"
        res = requests.get(url)
        data = res.json()

        if data["status"] == 1:
            return data["product"]["product_name"]
        else:
            return ""
    except:
        return ""


# 🏠 HOME
@app.route("/", methods=["GET", "POST"])
def home():
    conn = get_db()

    if request.method == "POST":
        codigo = request.form.get("codigo")
        nombre = request.form.get("nombre")
        cantidad = request.form.get("cantidad")

        if codigo and not nombre:
            nombre = obtener_producto(codigo)

        conn.execute(
            "INSERT INTO productos (codigo, nombre, cantidad) VALUES (?, ?, ?)",
            (codigo, nombre, cantidad)
        )
        conn.commit()
        conn.close()
        return redirect("/")

    productos = conn.execute("SELECT * FROM productos").fetchall()
    conn.close()

    return render_template("index.html", productos=productos)


# ❌ ELIMINAR
@app.route("/eliminar/<int:id>")
def eliminar(id):
    conn = get_db()
    conn.execute("DELETE FROM productos WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect("/")


# ✏️ EDITAR
@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    conn = get_db()

    if request.method == "POST":
        nombre = request.form.get("nombre")
        cantidad = request.form.get("cantidad")

        conn.execute(
            "UPDATE productos SET nombre = ?, cantidad = ? WHERE id = ?",
            (nombre, cantidad, id)
        )
        conn.commit()
        conn.close()
        return redirect("/")

    producto = conn.execute(
        "SELECT * FROM productos WHERE id = ?", (id,)
    ).fetchone()

    conn.close()
    return render_template("editar.html", producto=producto)


# 🧾 TICKET
@app.route("/ticket")
def ticket():
    conn = get_db()
    productos = conn.execute("SELECT * FROM productos").fetchall()
    conn.close()
    return render_template("ticket.html", productos=productos)


# 🚀 RUN
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)