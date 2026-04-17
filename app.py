from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "stockar_secret"

# ---------------- DB ----------------
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        rol TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        codigo TEXT,
        nombre TEXT,
        categoria TEXT,
        cantidad INTEGER,
        precio REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        nombre TEXT,
        precio REAL,
        fecha TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("SELECT id,rol FROM usuarios WHERE username=? AND password=?",
                       (request.form['username'], request.form['password']))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            session['rol'] = user[1]
            return redirect('/')
        else:
            return "Usuario incorrecto"

    return render_template("login.html")

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("INSERT INTO usuarios (username,password,rol) VALUES (?,?,?)",
                       (request.form['username'], request.form['password'], "admin"))

        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template("register.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ---------------- HOME ----------------
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect('/login')

    uid = session['user_id']

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT codigo,nombre,categoria,cantidad,precio FROM productos WHERE usuario_id=?", (uid,))
    productos = cursor.fetchall()

    cursor.execute("SELECT precio FROM ventas WHERE usuario_id=?", (uid,))
    ventas = cursor.fetchall()

    conn.close()

    productos_lista = [
        {"codigo": p[0], "nombre": p[1], "categoria": p[2], "cantidad": p[3], "precio": p[4]}
        for p in productos
    ]

    carrito = session.get("carrito", [])

    total = sum([v[0] for v in ventas])
    cantidad = len(ventas)
    promedio = round(total / cantidad, 2) if cantidad > 0 else 0

    return render_template("index.html",
                           productos=productos_lista,
                           carrito=carrito,
                           total_hoy=total,
                           cantidad_hoy=cantidad,
                           promedio=promedio)

# ---------------- PRODUCTOS ----------------
@app.route('/agregar', methods=['POST'])
def agregar():
    uid = session['user_id']

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO productos (usuario_id,codigo,nombre,categoria,cantidad,precio)
    VALUES (?,?,?,?,?,?)
    """, (
        uid,
        request.form['codigo'],
        request.form['nombre'],
        request.form['categoria'],
        int(request.form['cantidad']),
        float(request.form['precio'])
    ))

    conn.commit()
    conn.close()

    return redirect('/')

@app.route('/sumar/<codigo>')
def sumar(codigo):
    uid = session['user_id']
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE productos SET cantidad=cantidad+1 WHERE codigo=? AND usuario_id=?", (codigo,uid))
    conn.commit()
    conn.close()
    return redirect('/')

# ---------------- CARRITO ----------------
@app.route('/carrito/<codigo>')
def carrito_add(codigo):
    uid = session['user_id']

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT nombre,precio FROM productos WHERE codigo=? AND usuario_id=?", (codigo,uid))
    p = cursor.fetchone()

    conn.close()

    if p:
        carrito = session.get("carrito", [])
        carrito.append({"codigo":codigo,"nombre":p[0],"precio":p[1]})
        session["carrito"] = carrito

    return redirect('/')

@app.route('/scan/<codigo>')
def scan_add(codigo):
    return carrito_add(codigo)

# ---------------- FINALIZAR ----------------
@app.route('/finalizar')
def finalizar():
    uid = session['user_id']
    carrito = session.get("carrito", [])

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    total = 0
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

    for item in carrito:
        total += item["precio"]

        cursor.execute("INSERT INTO ventas (usuario_id,nombre,precio,fecha) VALUES (?,?,?,?)",
                       (uid,item["nombre"],item["precio"],fecha))

        cursor.execute("UPDATE productos SET cantidad=cantidad-1 WHERE codigo=? AND usuario_id=?",
                       (item["codigo"],uid))

    conn.commit()
    conn.close()

    session["carrito"] = []

    return render_template("ticket.html", carrito=carrito, total=total, fecha=fecha)

# ---------------- HISTORIAL ----------------
@app.route('/historial')
def historial():
    uid = session['user_id']

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT nombre,precio,fecha FROM ventas WHERE usuario_id=? ORDER BY id DESC",(uid,))
    ventas = cursor.fetchall()
    conn.close()

    return render_template("historial.html", ventas=ventas)

if __name__ == '__main__':
    app.run()