from flask import Flask, render_template, jsonify
import json
import random

# Inicializar la aplicación Flask
app = Flask(__name__)

# --- Carga del Banco de Preguntas ---
def cargar_preguntas():
    """Abre y carga las preguntas desde el archivo JSON."""
    try:
        with open('preguntas.json', 'r', encoding='utf-8') as f:
            preguntas = json.load(f)
        return preguntas
    except FileNotFoundError:
        print("Error: El archivo 'preguntas.json' no se encontró.")
        return []
    except json.JSONDecodeError:
        print("Error: El archivo 'preguntas.json' tiene un formato incorrecto.")
        return []

# Cargamos las preguntas una sola vez al iniciar la aplicación
banco_preguntas = cargar_preguntas()
print(f"Se han cargado {len(banco_preguntas)} preguntas del banco.")


# --- Definición de Rutas (Páginas Web) ---

@app.route('/')
def pagina_inicio():
    """Renderiza la página de bienvenida."""
    return render_template('index.html')


# --- Punto de entrada para ejecutar la aplicación ---
if __name__ == '__main__':
    # El modo debug permite que los cambios se vean sin reiniciar el servidor manualmente
    app.run(debug=True)