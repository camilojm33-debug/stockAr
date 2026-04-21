import sqlite3
from tkinter import *
from tkinter import messagebox
from datetime import datetime

# =========================
# CONFIG
# =========================
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
# CREAR USUARIO
# =========================
def crear_usuario():
    user = entry_new_user.get()
    pwd = entry_new_pass.get()
    rol = var_rol.get()

    if user == "" or pwd == "":
        messagebox.showerror("Error", "Completar campos")
        return

    conn = sqlite3.connect("stock.db")
    cursor = conn.cursor()

    cursor.execute("INSERT INTO usuarios VALUES(NULL,?,?,?)", (user, pwd, rol))

    conn.commit()
    conn.close()

    messagebox.showinfo("Éxito", "Usuario creado")

# =========================
# SISTEMA
# =========================
def abrir_sistema():
    global lista

    app = Tk()
    app.title("stockAr PRO")
    app.geometry("950x650")
    app.config(bg=BG)

    Label(app, text=f"Usuario: {usuario_actual} ({rol_actual})", bg=BG, fg="cyan").pack()

    # PANEL ADMIN
    if rol_actual == "admin":
        frame_user = Frame(app, bg=CARD, padx=10, pady=10)
        frame_user.pack(pady=10)

        Label(frame_user, text="Crear Usuario", bg=CARD, fg="white").grid(row=0, columnspan=2)

        global entry_new_user, entry_new_pass, var_rol

        entry_new_user = Entry(frame_user)
        entry_new_user.grid(row=1, column=1)
        Label(frame_user, text="Usuario", bg=CARD, fg="white").grid(row=1, column=0)

        entry_new_pass = Entry(frame_user)
        entry_new_pass.grid(row=2, column=1)
        Label(frame_user, text="Password", bg=CARD, fg="white").grid(row=2, column=0)

        var_rol = StringVar(value="empleado")
        OptionMenu(frame_user, var_rol, "admin", "empleado").grid(row=3, columnspan=2)

        Button(frame_user, text="Crear Usuario", command=crear_usuario).grid(row=4, columnspan=2, pady=5)

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
    if e_nombre.get() == "" or e_precio.get() == "" or e_stock.get() == "":
        messagebox.showerror("Error", "Completar todos los campos")
        return

    try:
        precio = float(e_precio.get())
        stock = int(e_stock.get())
    except:
        messagebox.showerror("Error", "Datos inválidos")
        return

    conn = sqlite3.connect("stock.db")
    cursor = conn.cursor()

    cursor.execute("INSERT INTO productos VALUES(NULL,?,?,?)",
                   (e_nombre.get(), precio, stock))

    conn.commit()
    conn.close()
    actualizar()

def eliminar():
    seleccionado = lista.get(ACTIVE)

    if not seleccionado:
        return

    pid = int(seleccionado.split("|")[0].strip())

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
    seleccionado = lista.get(ACTIVE)

    if not seleccionado:
        messagebox.showerror("Error", "Seleccionar producto")
        return

    if e_cant.get() == "":
        messagebox.showerror("Error", "Ingresar cantidad")
        return

    try:
        cant = int(e_cant.get())
    except:
        messagebox.showerror("Error", "Cantidad inválida")
        return

    pid = int(seleccionado.split("|")[0].strip())

    conn = sqlite3.connect("stock.db")
    cursor = conn.cursor()

    cursor.execute("SELECT stock FROM productos WHERE id=?", (pid,))
    resultado = cursor.fetchone()

    if not resultado:
        return

    stock = resultado[0]

    if cant > stock:
        messagebox.showerror("Error", "Sin stock")
        return

    nuevo_stock = stock - cant

    cursor.execute("UPDATE productos SET stock=? WHERE id=?", (nuevo_stock, pid))

    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("INSERT INTO ventas VALUES(NULL,?,?,?)",
                   (pid, cant, fecha))

    conn.commit()
    conn.close()

    actualizar()

# =========================
# LOGIN UI
# =========================
crear_db()

ventana_login = Tk()
ventana_login.title("stockAr Login")
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