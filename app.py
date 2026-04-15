from flask import Flask, render_template, request, redirect

app = Flask(__name__)

# Base simple en memoria
productos = []

@app.route("/")
def index():
    return render_template("index.html", productos=productos)

@app.route("/agregar", methods=["POST"])
def agregar():
    codigo = request.form["codigo"]
    nombre = request.form["nombre"]
    cantidad = int(request.form["cantidad"])

    # Verifica si ya existe
    for p in productos:
        if p["codigo"] == codigo:
            p["cantidad"] += cantidad
            return redirect("/")

    productos.append({
        "codigo": codigo,
        "nombre": nombre,
        "cantidad": cantidad
    })

    return redirect("/")

@app.route("/sumar/<codigo>")
def sumar(codigo):
    for p in productos:
        if p["codigo"] == codigo:
            p["cantidad"] += 1
    return redirect("/")

@app.route("/restar/<codigo>")
def restar(codigo):
    for p in productos:
        if p["codigo"] == codigo and p["cantidad"] > 0:
            p["cantidad"] -= 1
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)