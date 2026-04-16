from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime

app = Flask(__name__)

# 🔥 CREAR DB SI NO EXISTE
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

# 🔥 HOME
@app.route('/')
def index():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT codigo, nombre, cantidad, precio FROM productos")
    productos = cursor.fetchall()

    conn.close()

    productos_lista = []
    for p in productos:
        productos_lista.append({
            "codigo": p[0],
            "nombre": p[1],
            "cantidad": p[2],
            "precio": p[3]
        })

    return render_template('index.html', productos=productos_lista)

# 🔥 AGREGAR
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

# 🔥 SUMAR
@app.route('/sumar/<codigo>')
def sumar(codigo):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("UPDATE productos SET cantidad = cantidad + 1 WHERE codigo=?", (codigo,))

    conn.commit()
    conn.close()

    return redirect('/')

# 🔥 RESTAR
@app.route('/restar/<codigo>')
def restar(codigo):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("UPDATE productos SET cantidad = cantidad - 1 WHERE codigo=? AND cantidad > 0", (codigo,))

    conn.commit()
    conn.close()

    return redirect('/')

# 🔥 VENDER + GUARDAR + TICKET
@app.route('/vender', methods=['POST'])
def vender():
    codigo = request.form['codigo']

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT nombre, precio, cantidad FROM productos WHERE codigo=?", (codigo,))
    p = cursor.fetchone()

    if p and p[2] > 0:
        nombre, precio, cantidad = p

        # descontar
        cursor.execute("UPDATE productos SET cantidad = cantidad - 1 WHERE codigo=?", (codigo,))

        # guardar venta
        fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
        cursor.execute("INSERT INTO ventas (nombre, precio, fecha) VALUES (?, ?, ?)", (nombre, precio, fecha))

        conn.commit()
        conn.close()

        return render_template("ticket.html", venta={
            "nombre": nombre,
            "precio": precio,
            "fecha": fecha
        })

    conn.close()
    return redirect('/')

@app.route('/logout')
def logout():
    return redirect('/')

if __name__ == '__main__':
    app.run()