import sqlite3
from tkinter import *
from tkinter import messagebox
from datetime import datetime
from openpyxl import Workbook

BG = "#121212"
CARD = "#1f1f2e"
TXT = "white"

usuario_actual = None
rol_actual = None

# =========================
# DB
# =========================
def crear_db():
    conn = sqlite3.connect("stock.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY,
        username TEXT,
        password TEXT,
        rol TEXT
    )
    """)

    cursor.execute("CREATE TABLE IF NOT EXISTS productos (id INTEGER PRIMARY KEY, nombre TEXT, precio REAL, stock INTEGER)")
    cursor.execute("CREATE TABLE IF NOT EXISTS ventas (id INTEGER PRIMARY KEY, producto_id INTEGER, cantidad INTEGER, fecha TEXT)")

    cursor.execute("SELECT * FROM usuarios WHERE username='admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO usuarios VALUES(NULL,'admin','1234','admin')")

    conn.commit()
    conn.close()

# =========================
# EXPORTAR A EXCEL
# =========================
def exportar_productos():
    wb = Workbook()
    ws = wb.active
    ws.title = "Productos"

    ws.append(["ID", "Nombre", "Precio", "Stock"])

    conn = sqlite3.connect("stock.db")
    cursor = conn.cursor()

    for p in cursor.execute("SELECT * FROM productos"):
        ws.append(p)

    conn.close()

    wb.save("productos.xlsx")
    messagebox.showinfo("Excel", "Productos exportados")

def exportar_ventas():
    wb = Workbook()
    ws = wb.active
    ws.title = "Ventas"

    ws.append(["ID", "Producto", "Cantidad", "Fecha"])

    conn = sqlite3.connect("stock.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT ventas.id, productos.nombre, ventas.cantidad, ventas.fecha
    FROM ventas JOIN productos ON ventas.producto_id = productos.id
    """)

    for v in cursor.fetchall():
        ws.append(v)

    conn.close()

    wb.save("ventas.xlsx")
    messagebox.showinfo("Excel", "Ventas exportadas")

# =========================
# LOGIN
# =========================
def login():
    global usuario_actual, rol_actual

    conn = sqlite3.connect("stock.db")
    cursor = conn.cursor()

    cursor.execute("SELECT username, rol FROM usuarios WHERE username=? AND password=?",
                   (entry_user.get(), entry_pass.get()))
    r = cursor.fetchone()

    conn.close()

    if r:
        usuario_actual, rol_actual = r
        ventana_login.destroy()
        abrir_sistema()
    else:
        messagebox.showerror("Error", "Datos incorrectos")

# =========================
# SISTEMA
# =========================
def abrir_sistema():
    global lista

    app = Tk()
    app.title("Stock PRO EMPRESARIAL")
    app.geometry("950x650")
    app.config(bg=BG)

    Label(app, text=f"Usuario: {usuario_actual} ({rol_actual})", bg=BG, fg="cyan").pack()

    # BOTONES EXCEL (solo admin)
    if rol_actual == "admin":
        frame_excel = Frame(app, bg=CARD)
        frame_excel.pack(pady=5)

        Button(frame_excel, text="Exportar Productos", command=exportar_productos).pack(side=LEFT, padx=5)
        Button(frame_excel, text="Exportar Ventas", command=exportar_ventas).pack(side=LEFT, padx=5)

    # PRODUCTOS
    frame = Frame(app, bg=CARD)
    frame.pack(pady=10)

    global e_nombre, e_precio, e_stock, e_cant

    e_nombre = Entry(frame)
    e_nombre.grid(row=0, column=1)
    Label(frame, text="Nombre", bg=CARD, fg=TXT).grid(row=0, column=0)

    e_precio = Entry(frame)
    e_precio.grid(row=1, column=1)
    Label(frame, text="Precio", bg=CARD, fg=TXT).grid(row=1, column=0)

    e_stock = Entry(frame)
    e_stock.grid(row=2, column=1)
    Label(frame, text="Stock", bg=CARD, fg=TXT).grid(row=2, column=0)

    if rol_actual == "admin":
        Button(frame, text="Agregar", command=agregar).grid(row=3, column=0)
        Button(frame, text="Eliminar", command=eliminar).grid(row=3, column=1)

    lista = Listbox(app, width=100)
    lista.pack(pady=10)

    e_cant = Entry(app)
    e_cant.pack()

    Button(app, text="Vender", command=vender).pack()

    actualizar()
    app.mainloop()

# =========================
# FUNCIONES
# =========================
def agregar():
    conn = sqlite3.connect("stock.db")
    cursor = conn.cursor()

    cursor.execute("INSERT INTO productos VALUES(NULL,?,?,?)",
                   (e_nombre.get(), float(e_precio.get()), int(e_stock.get())))

    conn.commit()
    conn.close()
    actualizar()

def eliminar():
    if not lista.get(ACTIVE): return

    pid = int(lista.get(ACTIVE).split("|")[0])

    conn = sqlite3.connect("stock.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM productos WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    actualizar()

def actualizar():
    lista.delete(0, END)

    conn = sqlite3.connect("stock.db")
    cursor = conn.cursor()

    for p in cursor.execute("SELECT * FROM productos"):
        lista.insert(END, f"{p[0]} | {p[1]} | ${p[2]} | Stock:{p[3]}")

    conn.close()

def vender():
    if not lista.get(ACTIVE): return

    pid = int(lista.get(ACTIVE).split("|")[0])
    cant = int(e_cant.get())

    conn = sqlite3.connect("stock.db")
    cursor = conn.cursor()

    cursor.execute("SELECT stock FROM productos WHERE id=?", (pid,))
    stock = cursor.fetchone()[0]

    if cant > stock:
        messagebox.showerror("Error", "Sin stock")
        return

    cursor.execute("UPDATE productos SET stock=? WHERE id=?", (stock-cant, pid))
    cursor.execute("INSERT INTO ventas VALUES(NULL,?,?,?)",
                   (pid, cant, datetime.now()))

    conn.commit()
    conn.close()
    actualizar()

# =========================
# LOGIN UI
# =========================
crear_db()

ventana_login = Tk()
ventana_login.title("Login")
ventana_login.geometry("300x200")
ventana_login.config(bg=BG)

Label(ventana_login, text="Usuario", bg=BG, fg="white").pack()
entry_user = Entry(ventana_login)
entry_user.pack()

Label(ventana_login, text="Contraseña", bg=BG, fg="white").pack()
entry_pass = Entry(ventana_login, show="*")
entry_pass.pack()

Button(ventana_login, text="Ingresar", command=login).pack(pady=10)

ventana_login.mainloop()