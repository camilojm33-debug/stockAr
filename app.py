from flask import Flask, render_template, request, redirect

app = Flask(__name__)

productos = []
ventas = []

@app.route('/')
def index():
    return render_template('index.html', productos=productos)

@app.route('/agregar', methods=['POST'])
def agregar():
    codigo = request.form['codigo']
    nombre = request.form['nombre']
    cantidad = int(request.form['cantidad'])
    precio = float(request.form['precio'])

    producto = {
        "codigo": codigo,
        "nombre": nombre,
        "cantidad": cantidad,
        "precio": precio
    }

    productos.append(producto)

    return redirect('/')

@app.route('/sumar/<codigo>')
def sumar(codigo):
    for p in productos:
        if p["codigo"] == codigo:
            p["cantidad"] += 1
    return redirect('/')

@app.route('/restar/<codigo>')
def restar(codigo):
    for p in productos:
        if p["codigo"] == codigo and p["cantidad"] > 0:
            p["cantidad"] -= 1
    return redirect('/')

# 🔥 VENDER + TICKET
@app.route('/vender', methods=['POST'])
def vender_producto():
    codigo = request.form['codigo']

    for p in productos:
        if p["codigo"] == codigo and p["cantidad"] > 0:
            p["cantidad"] -= 1

            venta = {
                "nombre": p["nombre"],
                "precio": p["precio"]
            }

            ventas.append(venta)

            return render_template("ticket.html", venta=venta)

    return redirect('/')

@app.route('/logout')
def logout():
    return redirect('/')

if __name__ == '__main__':
    app.run()