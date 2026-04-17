from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "stockar_secret"

def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY,
        username TEXT,
        password TEXT,
        rol TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY,
        usuario_id INTEGER,
        codigo TEXT,
        nombre TEXT,
        categoria TEXT,
        cantidad INTEGER,
        precio REAL,
        updated_at TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY,
        usuario_id INTEGER,
        nombre TEXT,
        precio REAL,
        fecha TEXT
    )""")

    conn.commit()
    conn.close()

init_db()

# LOGIN
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT id FROM usuarios WHERE username=? AND password=?",
                  (request.form['username'], request.form['password']))
        user = c.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            return redirect('/')

    return render_template("login.html")

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("INSERT INTO usuarios (username,password,rol) VALUES (?,?,?)",
                  (request.form['username'], request.form['password'], "admin"))
        conn.commit()
        conn.close()
        return redirect('/login')

    return render_template("register.html")

# HOME
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect('/login')

    uid = session['user_id']

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT codigo,nombre,categoria,cantidad,precio FROM productos WHERE usuario_id=?", (uid,))
    productos = c.fetchall()

    conn.close()

    return render_template("index.html",
        productos=productos,
        carrito=session.get("carrito", [])
    )

# 🔥 RESUMEN (NUEVO)
@app.route('/resumen')
def resumen():
    uid = session['user_id']

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT nombre,precio,fecha FROM ventas WHERE usuario_id=?", (uid,))
    ventas = c.fetchall()

    conn.close()

    total = sum([v[1] for v in ventas])
    cantidad = len(ventas)

    # ventas por día
    ventas_por_dia = {}
    for v in ventas:
        dia = v[2].split(" ")[0]
        ventas_por_dia[dia] = ventas_por_dia.get(dia, 0) + v[1]

    dias = list(ventas_por_dia.keys())
    montos = list(ventas_por_dia.values())

    # top productos
    productos_count = {}
    for v in ventas:
        productos_count[v[0]] = productos_count.get(v[0], 0) + 1

    top_productos = sorted(productos_count.items(), key=lambda x: x[1], reverse=True)[:5]

    return render_template("resumen.html",
        total=total,
        cantidad=cantidad,
        dias=dias,
        montos=montos,
        top_productos=top_productos
    )

# PRODUCTOS
@app.route('/agregar', methods=['POST'])
def agregar():
    uid = session['user_id']
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""INSERT INTO productos 
    (usuario_id,codigo,nombre,categoria,cantidad,precio,updated_at)
    VALUES (?,?,?,?,?,?,?)""",
    (uid,
     request.form['codigo'],
     request.form['nombre'],
     request.form['categoria'],
     request.form['cantidad'],
     request.form['precio'],
     datetime.now().strftime("%Y-%m-%d %H:%M")))

    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/carrito/<codigo>')
def carrito_add(codigo):
    uid = session['user_id']
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT nombre,precio FROM productos WHERE codigo=? AND usuario_id=?", (codigo,uid))
    p = c.fetchone()
    conn.close()

    if p:
        carrito = session.get("carrito", [])
        carrito.append({"codigo":codigo,"nombre":p[0],"precio":p[1]})
        session["carrito"] = carrito

    return redirect('/')

@app.route('/finalizar')
def finalizar():
    uid = session['user_id']
    carrito = session.get("carrito", [])

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    total = 0
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

    for item in carrito:
        total += item["precio"]

        c.execute("INSERT INTO ventas (usuario_id,nombre,precio,fecha) VALUES (?,?,?,?)",
                  (uid,item["nombre"],item["precio"],fecha))

        c.execute("UPDATE productos SET cantidad=cantidad-1 WHERE codigo=? AND usuario_id=?",
                  (item["codigo"],uid))

    conn.commit()
    conn.close()

    session["carrito"] = []

    return render_template("ticket.html", carrito=carrito, total=total, fecha=fecha)