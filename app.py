from flask import Flask, render_template, request, redirect, jsonify
import sqlite3
import requests
import os

app = Flask(__name__)

DB_PATH = "database.db"


def get_db():
    return sqlite3.connect(DB_PATH)


def crear_tabla():
    conn = get_db()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT,
        nombre TEXT NOT NULL,
        cantidad INTEGER NOT NULL
    )
    """)
    conn.commit()
    conn.close()

crear_tabla()


def obtener_nombre_producto(codigo):
    try:
        url = f"https://world.openfoodfacts.org/api/v0/product/{codigo}.json"
        res = requests.get(url)
        if res.status_code == 200:
            data = res.json()
            if data.get("status") == 1:
                return data["product"].get("product_name", "Producto sin nombre")
    except:
        pass
    return "Producto desconocido"


@app.route("/", methods=["GET", "POST"])
def home():
    conn = get_db()

    if request.method == "POST":
        codigo = request.form.get("codigo")
        nombre = request.form.get("nombre")
        cantidad = int(request.form.get("cantidad"))

        producto = conn.execute(
            "SELECT * FROM productos WHERE codigo = ?",
            (codigo,)
        ).fetchone()

        if producto:
            conn.execute(
                "UPDATE productos SET cantidad = ? WHERE id = ?",
                (producto[3] + cantidad, producto[0])
            )
        else:
            conn.execute(
                "INSERT INTO productos (codigo, nombre, cantidad) VALUES (?, ?, ?)",
                (codigo, nombre, cantidad)
            )

        conn.commit()
        conn.close()
        return redirect("/")

    productos = conn.execute("SELECT * FROM productos").fetchall()
    total_productos = len(productos)
    total_stock = sum(p[3] for p in productos)

    conn.close()

    return render_template(
        "index.html",
        productos=productos,
        total_productos=total_productos,
        total_stock=total_stock
    )


@app.route("/scan", methods=["POST"])
def scan():
    data = request.get_json()
    codigo = data.get("codigo")

    conn = get_db()
    nombre = obtener_nombre_producto(codigo)

    producto = conn.execute(
        "SELECT * FROM productos WHERE codigo = ?",
        (codigo,)
    ).fetchone()

    if producto:
        conn.execute(
            "UPDATE productos SET cantidad = ? WHERE id = ?",
            (producto[3] + 1, producto[0])
        )
    else:
        conn.execute(
            "INSERT INTO productos (codigo, nombre, cantidad) VALUES (?, ?, ?)",
            (codigo, nombre, 1)
        )

    conn.commit()
    conn.close()

    return jsonify({"status": "ok"})


@app.route("/eliminar/<int:id>")
def eliminar(id):
    conn = get_db()
    conn.execute("DELETE FROM productos WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect("/")


@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    conn = get_db()

    if request.method == "POST":
        nombre = request.form["nombre"]
        cantidad = request.form["cantidad"]

        conn.execute(
            "UPDATE productos SET nombre = ?, cantidad = ? WHERE id = ?",
            (nombre, cantidad, id)
        )
        conn.commit()
        conn.close()
        return redirect("/")

    producto = conn.execute(
        "SELECT * FROM productos WHERE id = ?",
        (id,)
    ).fetchone()

    conn.close()

    return render_template("editar.html", producto=producto)


@app.route("/ticket")
def ticket():
    conn = get_db()
    productos = conn.execute("SELECT * FROM productos").fetchall()
    conn.close()
    return render_template("ticket.html", productos=productos)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)