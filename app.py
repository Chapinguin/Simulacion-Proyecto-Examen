# Importamos 'session' y 'redirect' para el manejo de usuarios
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
import json
import random

app = Flask(__name__)
# Es necesario configurar una 'secret_key' para que las sesiones funcionen
app.secret_key = 'tu_clave_secreta_aqui' # Cambia esto por cualquier frase secreta

# --- Base de Datos Simulada (en memoria) ---
# En un proyecto real, esto estaría en una base de datos.
# Por simplicidad para el examen, usaremos diccionarios.
if 'usuarios' not in globals():
    usuarios = {"sebastian": "123", "gustavo": "456"} # Usuarios de ejemplo con sus contraseñas
if 'intentos_db' not in globals():
    intentos_db = {} # Ej: {'sebastian': {'practica': 2, 'final': 1}}

def cargar_preguntas():
    try:
        with open('preguntas.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

banco_preguntas = cargar_preguntas()
print(f"Se han cargado {len(banco_preguntas)} preguntas del banco.")

# --- Rutas de Autenticación y Usuarios ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Verificamos si el usuario y la contraseña son correctos
        if username in usuarios and usuarios[username] == password:
            session['username'] = username # Guardamos el usuario en la sesión
            if username not in intentos_db:
                intentos_db[username] = {'practica': 0, 'final': 0}
            return redirect(url_for('pagina_inicio'))
        else:
            return "Usuario o contraseña incorrectos", 401 # Mensaje de error
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None) # Eliminamos al usuario de la sesión
    return redirect(url_for('pagina_inicio'))


# --- Rutas de la Aplicación ---

@app.route('/')
def pagina_inicio():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    intentos = intentos_db.get(session['username'], {'practica': 0, 'final': 0})
    return render_template('index.html', intentos=intentos)

@app.route('/practica')
def modo_practica():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Requerimiento: Límite de 6 intentos de práctica
    username = session['username']
    if intentos_db[username]['practica'] >= 6:
        return "Has alcanzado el límite de 6 intentos de práctica."

    num_preguntas = 20
    preguntas_seleccionadas = random.sample(banco_preguntas, min(num_preguntas, len(banco_preguntas)))
    
    return render_template('test.html', preguntas=preguntas_seleccionadas, tipo_examen="Práctica")

# --- NUEVA RUTA PARA EL MODO EXAMEN FINAL ---
@app.route('/examen')
def modo_examen():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Requerimiento: Límite de 3 intentos de examen final
    username = session['username']
    if intentos_db[username]['final'] >= 3:
        return "Has alcanzado el límite de 3 intentos para el examen final."
        
    num_preguntas = 40
    preguntas_seleccionadas = random.sample(banco_preguntas, min(num_preguntas, len(banco_preguntas)))
    
    return render_template('test.html', preguntas=preguntas_seleccionadas, tipo_examen="Examen Final")


@app.route('/resultado', methods=['POST'])
def procesar_resultado():
    if 'username' not in session:
        return redirect(url_for('login'))

    respuestas_usuario = request.form
    tipo_examen = request.form.get('tipo_examen') # Obtenemos el tipo de examen del formulario
    username = session['username']

    respuestas_correctas = 0
    total_preguntas_enviadas = 0
    resultados_detallados = []
    
    for pregunta in banco_preguntas:
        pregunta_id_str = f"pregunta-{pregunta['id']}"
        if pregunta_id_str in respuestas_usuario:
            total_preguntas_enviadas += 1
            respuesta_enviada = respuestas_usuario[pregunta_id_str]
            es_correcta = (respuesta_enviada == pregunta['respuesta_correcta'])
            
            if es_correcta:
                respuestas_correctas += 1
            
            resultados_detallados.append({
                'pregunta': pregunta['pregunta'],
                'opciones': pregunta['opciones'],
                'respuesta_enviada': respuesta_enviada,
                'letra_correcta': pregunta['respuesta_correcta'],
                'respuesta_correcta_texto': pregunta['opciones'][pregunta['respuesta_correcta']],
                'es_correcta': es_correcta,
                'explicacion': pregunta.get('explicacion', 'No hay explicación disponible.')
            })
    
    # --- Lógica de Calificación Adaptada ---
    if tipo_examen == "Práctica":
        puntaje = respuestas_correctas * 5
        puntaje_maximo = total_preguntas_enviadas * 5
        intentos_db[username]['practica'] += 1 # Incrementamos el contador de intentos
    elif tipo_examen == "Examen Final":
        puntaje = respuestas_correctas * 2.5
        puntaje_maximo = total_preguntas_enviadas * 2.5
        intentos_db[username]['final'] += 1 # Incrementamos el contador de intentos
    else:
        return "Tipo de examen no reconocido", 400

    puntaje_porcentual = (puntaje / puntaje_maximo) * 100 if puntaje_maximo > 0 else 0
    aprobado = puntaje_porcentual >= 75
    
    return render_template('resultado.html', 
                        puntaje=puntaje,
                        puntaje_maximo=puntaje_maximo,
                        puntaje_porcentual=puntaje_porcentual,
                        aprobado=aprobado,
                        resultados=resultados_detallados,
                        tipo_examen=tipo_examen)


if __name__ == '__main__':
    app.run(debug=True)