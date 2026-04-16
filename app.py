from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "stockar_secret"

# 🔥 DB
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT,
        nombre TEXT,
        cantidad INTEGER,
        precio REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        precio REAL,
        fecha TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT codigo, nombre, cantidad, precio FROM productos")
    productos = cursor.fetchall()

    conn.close()

    productos_lista = [
        {"codigo": p[0], "nombre": p[1], "cantidad": p[2], "precio": p[3]}
        for p in productos
    ]

    carrito = session.get("carrito", [])

    return render_template('index.html', productos=productos_lista, carrito=carrito)

@app.route('/agregar', methods=['POST'])
def agregar():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("INSERT INTO productos (codigo, nombre, cantidad, precio) VALUES (?, ?, ?, ?)", (
        request.form['codigo'],
        request.form['nombre'],
        int(request.form['cantidad']),
        float(request.form['precio'])
    ))

    conn.commit()
    conn.close()

    return redirect('/')

@app.route('/sumar/<codigo>')
def sumar(codigo):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE productos SET cantidad = cantidad + 1 WHERE codigo=?", (codigo,))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/restar/<codigo>')
def restar(codigo):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE productos SET cantidad = cantidad - 1 WHERE codigo=? AND cantidad > 0", (codigo,))
    conn.commit()
    conn.close()
    return redirect('/')

# 🛒 CARRITO
@app.route('/carrito/<codigo>')
def carrito_add(codigo):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT nombre, precio FROM productos WHERE codigo=?", (codigo,))
    p = cursor.fetchone()
    conn.close()

    if p:
        carrito = session.get("carrito", [])
        carrito.append({"nombre": p[0], "precio": p[1]})
        session["carrito"] = carrito

    return redirect('/')

# 🧾 FINALIZAR
@app.route('/finalizar')
def finalizar():
    carrito = session.get("carrito", [])

    if not carrito:
        return redirect('/')

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    total = 0
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

    for item in carrito:
        total += item["precio"]

        cursor.execute(
            "INSERT INTO ventas (nombre, precio, fecha) VALUES (?, ?, ?)",
            (item["nombre"], item["precio"], fecha)
        )

    conn.commit()
    conn.close()

    session["carrito"] = []

    return render_template("ticket.html", carrito=carrito, total=total, fecha=fecha)

# 📊 HISTORIAL
@app.route('/historial')
def historial():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT nombre, precio, fecha FROM ventas ORDER BY id DESC")
    ventas = cursor.fetchall()

    conn.close()

    return render_template("historial.html", ventas=ventas)

if __name__ == '__main__':
    app.run()