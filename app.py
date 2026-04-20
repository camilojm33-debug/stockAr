from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3, json, time, qrcode, os
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Spacer
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)
app.secret_key = "stockar_pro"

DB = "database.db"

def db():
    return sqlite3.connect(DB)

def init_db():
    conn = db()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS usuarios(
        id INTEGER PRIMARY KEY,
        username TEXT,
        password TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS productos(
        id INTEGER PRIMARY KEY,
        usuario_id INTEGER,
        codigo TEXT,
        nombre TEXT,
        categoria TEXT,
        cantidad INTEGER,
        precio REAL)""")

    c.execute("""CREATE TABLE IF NOT EXISTS ventas(
        id INTEGER PRIMARY KEY,
        usuario_id INTEGER,
        nombre TEXT,
        precio REAL,
        fecha TEXT)""")

    conn.commit()
    conn.close()

init_db()

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        c = db().cursor()
        c.execute("SELECT id FROM usuarios WHERE username=? AND password=?",
                  (request.form['username'], request.form['password']))
        user = c.fetchone()

        if user:
            session['user_id'] = user[0]
            return redirect('/')

    return render_template("login.html")

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        conn = db()
        conn.execute("INSERT INTO usuarios(username,password) VALUES (?,?)",
                     (request.form['username'], request.form['password']))
        conn.commit()
        conn.close()
        return redirect('/login')

    return render_template("register.html")

# ---------------- HOME ----------------
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect('/login')

    uid = session['user_id']
    conn = db()
    c = conn.cursor()

    c.execute("SELECT codigo,nombre,categoria,cantidad,precio FROM productos WHERE usuario_id=?", (uid,))
    productos = c.fetchall()

    c.execute("SELECT precio FROM ventas WHERE usuario_id=?", (uid,))
    ventas = c.fetchall()

    conn.close()

    total = sum([v[0] for v in ventas])
    cantidad_ventas = len(ventas)
    carrito = session.get("carrito", [])

    alertas = [p for p in productos if p[3] <= 3]

    return render_template("index.html",
        productos=productos,
        carrito=carrito,
        total=total,
        cantidad_ventas=cantidad_ventas,
        alertas=alertas
    )

# ---------------- AGREGAR ----------------
@app.route('/agregar', methods=['POST'])
def agregar():
    uid = session['user_id']
    codigo = str(int(time.time()))

    conn = db()
    conn.execute("""
        INSERT INTO productos(usuario_id,codigo,nombre,categoria,cantidad,precio)
        VALUES (?,?,?,?,?,?)
    """, (uid,
          codigo,
          request.form['nombre'],
          request.form['categoria'],
          request.form['cantidad'],
          request.form['precio']))
    conn.commit()
    conn.close()

    return redirect('/')

# ---------------- CARRITO ----------------
@app.route('/carrito/<codigo>')
def carrito(codigo):
    uid = session['user_id']
    c = db().cursor()

    c.execute("SELECT nombre,precio FROM productos WHERE codigo=? AND usuario_id=?", (codigo,uid))
    p = c.fetchone()

    if p:
        carrito = session.get("carrito", [])
        carrito.append({"codigo":codigo,"nombre":p[0],"precio":p[1]})
        session["carrito"] = carrito

    return redirect('/')

# ---------------- FINALIZAR ----------------
@app.route('/finalizar')
def finalizar():
    uid = session['user_id']
    carrito = session.get("carrito", [])

    conn = db()
    c = conn.cursor()

    total = 0
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

    for item in carrito:
        total += item["precio"]

        c.execute("INSERT INTO ventas VALUES (NULL,?,?,?,?)",
                  (uid,item["nombre"],item["precio"],fecha))

        c.execute("UPDATE productos SET cantidad=cantidad-1 WHERE codigo=? AND usuario_id=?",
                  (item["codigo"],uid))

    conn.commit()
    conn.close()

    session["ultima"] = {"items":carrito,"total":total,"fecha":fecha}
    session["carrito"] = []

    return redirect('/ticket')

# ---------------- HISTORIAL ----------------
@app.route('/historial')
def historial():
    uid = session['user_id']
    conn = db()
    c = conn.cursor()

    c.execute("SELECT nombre,precio,fecha FROM ventas WHERE usuario_id=? ORDER BY id DESC", (uid,))
    ventas = c.fetchall()

    conn.close()

    return render_template("historial.html", ventas=ventas)

# ---------------- SCANNER ----------------
@app.route('/scanner')
def scanner():
    return render_template("scanner.html")

# ---------------- QR A4 ----------------
@app.route('/qr')
def qr():
    uid = session['user_id']
    conn = db()
    c = conn.cursor()

    c.execute("SELECT codigo,nombre,precio FROM productos WHERE usuario_id=?", (uid,))
    productos = c.fetchall()

    doc = SimpleDocTemplate("qr_etiquetas.pdf")
    content = []
    styles = getSampleStyleSheet()

    archivos = []

    for p in productos:
        data = p[0]

        img = qrcode.make(data)
        filename = f"{p[0]}.png"
        img.save(filename)
        archivos.append(filename)

        # etiqueta tipo producto
        content.append(Paragraph(f"<b>{p[1]}</b>", styles["Normal"]))
        content.append(Paragraph(f"Precio: ${p[2]}", styles["Normal"]))
        content.append(Image(filename, width=140, height=140))
        content.append(Spacer(1,20))

    doc.build(content)

    for f in archivos:
        os.remove(f)

    return send_file("qr_etiquetas.pdf", as_attachment=True)

# ---------------- TICKET ----------------
@app.route('/ticket')
def ticket():
    return render_template("ticket.html", venta=session.get("ultima"))

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)