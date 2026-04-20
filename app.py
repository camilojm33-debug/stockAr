from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3, time, qrcode, os
from datetime import datetime

from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
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
    carrito = session.get("carrito", [])

    return render_template("index.html",
        productos=productos,
        carrito=carrito,
        total=total
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
def productos_page():
    uid = session['user_id']
    conn = db()
    c = conn.cursor()

    c.execute("SELECT * FROM productos WHERE usuario_id=?", (uid,))
    productos = c.fetchall()

    conn.close()
    return render_template("productos.html", productos=productos)

@app.route('/qr_individual/<codigo>')
def qr_individual(codigo):
    img = qrcode.make(codigo)
    filename = f"{codigo}.png"
    img.save(filename)
    return send_file(filename, as_attachment=True)

# ---------------- QR MANUAL ----------------
@app.route('/qr_manual', methods=['GET','POST'])
def qr_manual():
    if request.method == 'POST':
        codigo = str(int(time.time()))
        nombre = request.form['nombre']
        precio = request.form['precio']

        data = f"{codigo}|{nombre}|{precio}"

        img = qrcode.make(data)
        filename = f"{codigo}.png"
        img.save(filename)

        return send_file(filename, as_attachment=True)

    return render_template("qr_manual.html")

# ---------------- QR CONFIG ----------------
@app.route('/qr_config')
def qr_config():
    uid = session['user_id']
    conn = db()
    c = conn.cursor()

    c.execute("SELECT * FROM productos WHERE usuario_id=?", (uid,))
    productos = c.fetchall()

    return render_template("qr_config.html", productos=productos)

# ---------------- QR GENERAR ----------------
@app.route('/qr_generar', methods=['POST'])
def qr_generar():
    try:
        total = int(request.form.get('total', 0))

        if total == 0:
            return "No hay productos para generar etiquetas"

        styles = getSampleStyleSheet()
        data = []
        fila = []
        archivos = []

        for i in range(1, total+1):
            codigo = request.form.get(f'codigo_{i}')
            precio = request.form.get(f'precio_{i}')
            nombre = request.form.get(f'nombre_{i}', 'Producto')

            if not codigo:
                continue

            img = qrcode.make(codigo)
            filename = f"{codigo}.png"
            img.save(filename)
            archivos.append(filename)

            celda = [
                Paragraph(f"<font size=14><b>${precio}</b></font>", styles["Normal"]),
                Image(filename, width=3.5*cm, height=3.5*cm),
                Paragraph(f"<font size=8>{nombre}</font>", styles["Normal"])
            ]

            fila.append(celda)

            if len(fila) == 4:
                data.append(fila)
                fila = []

        if fila:
            while len(fila) < 4:
                fila.append("")
            data.append(fila)

        doc = SimpleDocTemplate("etiquetas.pdf", pagesize=(21*cm, 29.7*cm))

        tabla = Table(data, colWidths=[5*cm]*4)
        tabla.setStyle(TableStyle([
            ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ]))

        doc.build([tabla])

        for f in archivos:
            os.remove(f)

        return send_file("etiquetas.pdf", as_attachment=True)

    except Exception as e:
        return f"Error generando PDF: {str(e)}"

# ---------------- CARRITO ----------------
@app.route('/carrito/<data>')
def carrito(data):
    uid = session['user_id']
    partes = data.split("|")

    conn = db()
    c = conn.cursor()

    if len(partes) == 3:
        codigo, nombre, precio = partes

        c.execute("SELECT nombre FROM productos WHERE codigo=? AND usuario_id=?", (codigo,uid))
        existe = c.fetchone()

        if not existe:
            c.execute("""
                INSERT INTO productos(usuario_id,codigo,nombre,categoria,cantidad,precio)
                VALUES (?,?,?,?,?,?)
            """, (uid, codigo, nombre, "QR", 1, precio))
            conn.commit()

        producto = (nombre, float(precio))

    else:
        c.execute("SELECT nombre,precio FROM productos WHERE codigo=? AND usuario_id=?", (data,uid))
        producto = c.fetchone()

    if producto:
        carrito = session.get("carrito", [])
        carrito.append({
            "codigo": partes[0],
            "nombre": producto[0],
            "precio": producto[1]
        })
        session["carrito"] = carrito

    return redirect('/')

# ---------------- VENTA DIRECTA (CAJA RÁPIDA) ----------------
@app.route('/vender/<data>')
def vender(data):
    uid = session['user_id']
    partes = data.split("|")

    conn = db()
    c = conn.cursor()

    if len(partes) == 3:
        codigo, nombre, precio = partes
        producto = (nombre, float(precio))
    else:
        c.execute("SELECT nombre,precio FROM productos WHERE codigo=? AND usuario_id=?", (data,uid))
        producto = c.fetchone()

    if not producto:
        return "Producto no encontrado"

    nombre, precio = producto
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

    c.execute("INSERT INTO ventas VALUES (NULL,?,?,?,?)",
              (uid, nombre, precio, fecha))

    c.execute("UPDATE productos SET cantidad=cantidad-1 WHERE codigo=? AND usuario_id=?",
              (partes[0], uid))

    conn.commit()
    conn.close()

    session["ultima"] = {
        "items": [{"nombre": nombre, "precio": precio}],
        "total": precio,
        "fecha": fecha
    }

    return redirect('/ticket')

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

    c.execute("SELECT nombre,precio,fecha FROM ventas WHERE usuario_id=?", (uid,))
    ventas = c.fetchall()

    conn.close()
    return render_template("historial.html", ventas=ventas)

# ---------------- SCANNER ----------------
@app.route('/scanner')
def scanner():
    return render_template("scanner.html")

# ---------------- TICKET ----------------
@app.route('/ticket')
def ticket():
    return render_template("ticket.html", venta=session.get("ultima"))

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)