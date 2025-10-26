# Importamos 'request' para poder acceder a los datos del formulario
from flask import Flask, render_template, jsonify, request
import json
import random

app = Flask(__name__)

def cargar_preguntas():
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

banco_preguntas = cargar_preguntas()
print(f"Se han cargado {len(banco_preguntas)} preguntas del banco.")

# --- Rutas de la Aplicación ---

@app.route('/')
def pagina_inicio():
    return render_template('index.html')

@app.route('/practica')
def modo_practica():
    num_preguntas_practica = 20
    if len(banco_preguntas) < num_preguntas_practica:
        num_preguntas_a_seleccionar = len(banco_preguntas)
    else:
        num_preguntas_a_seleccionar = num_preguntas_practica
        
    preguntas_seleccionadas = random.sample(banco_preguntas, num_preguntas_a_seleccionar)
    return render_template('test.html', preguntas=preguntas_seleccionadas, tipo_examen="Práctica")

# --- NUEVA RUTA PARA PROCESAR RESULTADOS ---
@app.route('/resultado', methods=['POST'])
def procesar_resultado():
    # Obtenemos las respuestas enviadas por el usuario desde el formulario
    respuestas_usuario = request.form
    
    # Variables para la calificación
    respuestas_correctas = 0
    total_preguntas = 0
    resultados_detallados = []
    
    # Iteramos sobre nuestro banco de preguntas para verificar las respuestas
    for pregunta in banco_preguntas:
        pregunta_id_str = f"pregunta-{pregunta['id']}"
        
        # Verificamos si la pregunta fue enviada en el formulario
        if pregunta_id_str in respuestas_usuario:
            total_preguntas += 1
            respuesta_enviada = respuestas_usuario[pregunta_id_str]
            es_correcta = (respuesta_enviada == pregunta['respuesta_correcta'])
            
            if es_correcta:
                respuestas_correctas += 1
            
            # Guardamos los detalles para la revisión final
            resultados_detallados.append({
                'pregunta': pregunta['pregunta'],
                'opciones': pregunta['opciones'],
                'respuesta_enviada': respuesta_enviada,
                'letra_correcta': pregunta['respuesta_correcta'],
                'respuesta_correcta_texto': pregunta['opciones'][pregunta['respuesta_correcta']],
                'es_correcta': es_correcta,
                'explicacion': pregunta.get('explicacion', 'No hay explicación disponible.')
            })
    
    # --- Lógica de Calificación ---
    # Requerimiento: En práctica, cada reactivo vale 5 puntos.
    puntaje = respuestas_correctas * 5
    puntaje_maximo = total_preguntas * 5
    
    # Requerimiento: Aprobar con 75% o más.
    puntaje_porcentual = (puntaje / puntaje_maximo) * 100 if puntaje_maximo > 0 else 0
    aprobado = puntaje_porcentual >= 75
    
    # Renderizamos la plantilla de resultados y le pasamos toda la información
    return render_template('resultado.html', 
                        puntaje=puntaje,
                        puntaje_maximo=puntaje_maximo,
                        puntaje_porcentual=puntaje_porcentual,
                        aprobado=aprobado,
                        resultados=resultados_detallados)


if __name__ == '__main__':
    app.run(debug=True)