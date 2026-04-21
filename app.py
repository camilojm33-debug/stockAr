from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3, time, qrcode, os
from datetime import datetime

from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm

app = Flask(__name__)
app.secret_key = "stockar_pro"

DB = "database.db"

def db():
    return sqlite3.connect(DB)

def init_db():
    conn = db()
    c = conn.cursor()

    c.execute("CREATE TABLE IF NOT EXISTS usuarios(id INTEGER PRIMARY KEY, username TEXT, password TEXT)")

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

    c.execute("SELECT * FROM productos WHERE usuario_id=?", (uid,))
    productos = c.fetchall()

    c.execute("SELECT precio FROM ventas WHERE usuario_id=?", (uid,))
    ventas = c.fetchall()

    conn.close()

    total = sum([v[0] for v in ventas])
    cantidad_ventas = len(ventas)
    alertas = [p for p in productos if p[5] <= 5]

    return render_template("index.html",
        productos=productos,
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

# ---------------- PRODUCTOS ----------------
@app.route('/productos')
def productos():
    uid = session['user_id']
    conn = db()
    productos = conn.execute("SELECT * FROM productos WHERE usuario_id=?", (uid,)).fetchall()
    conn.close()
    return render_template("productos.html", productos=productos)

@app.route('/eliminar/<int:id>')
def eliminar(id):
    uid = session['user_id']
    conn = db()
    conn.execute("DELETE FROM productos WHERE id=? AND usuario_id=?", (id, uid))
    conn.commit()
    conn.close()
    return redirect('/productos')

# ---------------- QR ----------------
@app.route('/qr_individual/<codigo>')
def qr_individual(codigo):
    img = qrcode.make(codigo)
    filename = f"{codigo}.png"
    img.save(filename)
    return send_file(filename, as_attachment=True)

@app.route('/qr_manual', methods=['GET','POST'])
def qr_manual():
    if request.method == 'POST':
        codigo = str(int(time.time()))
        data = f"{codigo}|{request.form['nombre']}|{request.form['precio']}"
        img = qrcode.make(data)
        filename = f"{codigo}.png"
        img.save(filename)
        return send_file(filename, as_attachment=True)

    return render_template("qr_manual.html")

@app.route('/qr_config')
def qr_config():
    uid = session['user_id']
    conn = db()
    productos = conn.execute("SELECT * FROM productos WHERE usuario_id=?", (uid,)).fetchall()
    conn.close()
    return render_template("qr_config.html", productos=productos)

@app.route('/qr_generar', methods=['POST'])
def qr_generar():
    styles = getSampleStyleSheet()
    data = []
    fila = []

    total = int(request.form.get("total", 0))

    for i in range(1, total+1):
        codigo = request.form.get(f'codigo_{i}')
        precio = request.form.get(f'precio_{i}')
        nombre = request.form.get(f'nombre_{i}')

        img = qrcode.make(codigo)
        filename = f"{codigo}.png"
        img.save(filename)

        celda = [
            Paragraph(f"<b>${precio}</b>", styles["Normal"]),
            Image(filename, width=3*cm, height=3*cm),
            Paragraph(nombre, styles["Normal"])
        ]

        fila.append(celda)

        if len(fila) == 4:
            data.append(fila)
            fila = []

    if fila:
        data.append(fila)

    doc = SimpleDocTemplate("etiquetas.pdf")
    doc.build([Table(data)])

    return send_file("etiquetas.pdf", as_attachment=True)

# ---------------- VENTA ----------------
@app.route('/vender/<codigo>')
def vender(codigo):
    uid = session['user_id']
    conn = db()
    c = conn.cursor()

    c.execute("SELECT nombre,precio FROM productos WHERE codigo=? AND usuario_id=?", (codigo,uid))
    producto = c.fetchone()

    if not producto:
        return "No existe"

    nombre, precio = producto
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

    c.execute("INSERT INTO ventas VALUES (NULL,?,?,?,?)", (uid,nombre,precio,fecha))

    c.execute("""
    UPDATE productos 
    SET cantidad = CASE WHEN cantidad > 0 THEN cantidad-1 ELSE 0 END
    WHERE codigo=? AND usuario_id=?
    """,(codigo,uid))

    conn.commit()
    conn.close()

    session["ultima"] = {"items":[{"nombre":nombre,"precio":precio}],"total":precio}

    return redirect('/ticket')

# ---------------- HISTORIAL ----------------
@app.route('/historial')
def historial():
    uid = session['user_id']
    conn = db()
    ventas = conn.execute("SELECT nombre,precio,fecha FROM ventas WHERE usuario_id=?", (uid,)).fetchall()
    conn.close()
    return render_template("historial.html", ventas=ventas)

# ---------------- TICKET ----------------
@app.route('/ticket')
def ticket():
    return render_template("ticket.html", venta=session.get("ultima"))

if __name__ == "__main__":
    app.run(debug=True)