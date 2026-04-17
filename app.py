from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3, json
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)
app.secret_key = "stockar_pro"

DB = "database.db"

# ---------------- DB ----------------
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

# ---------------- AUTH ----------------
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
    carrito = session.get("carrito", [])
    alertas = [p for p in productos if p[3] <= 3]

    return render_template("index.html",
        productos=productos,
        carrito=carrito,
        total=total,
        alertas=alertas
    )

# ---------------- PRODUCTOS ----------------
@app.route('/agregar', methods=['POST'])
def agregar():
    uid = session['user_id']

    conn = db()
    conn.execute("""
        INSERT INTO productos(usuario_id,codigo,nombre,categoria,cantidad,precio)
        VALUES (?,?,?,?,?,?)
    """, (uid,
          request.form['codigo'],
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

    # backup
    with open("backup.json","a") as f:
        f.write(json.dumps({"total":total,"fecha":fecha})+"\n")

    session["ultima"] = {"items":carrito,"total":total,"fecha":fecha}
    session["carrito"] = []

    return redirect('/ticket')

# ---------------- TICKET ----------------
@app.route('/ticket')
def ticket():
    return render_template("ticket.html", venta=session.get("ultima"))

# ---------------- PDF ----------------
@app.route('/pdf')
def pdf():
    venta = session.get("ultima")

    doc = SimpleDocTemplate("ticket.pdf")
    styles = getSampleStyleSheet()

    content = [Paragraph("stockAr", styles["Title"])]

    for i in venta["items"]:
        content.append(Paragraph(f'{i["nombre"]} - ${i["precio"]}', styles["Normal"]))

    content.append(Paragraph(f'Total: ${venta["total"]}', styles["Normal"]))
    doc.build(content)

    return send_file("ticket.pdf", as_attachment=True)

if __name__ == "__main__":
    app.run()