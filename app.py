from flask import Flask, render_template, jsonify, request, session, redirect, url_for
import json
import random
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)
app.secret_key = 'clave_super_secreta_para_el_examen' # Clave para las sesiones

# ==============================================================================
# --- CONFIGURACIÓN DE REQUISITOS DE EVALUACIÓN ---
# ==============================================================================
PUNTOS_PRACTICA = 5.0
PUNTOS_FINAL = 2.5
PORCENTAJE_APROBACION = 75.0
NUM_PREGUNTAS_PRACTICA = 20
NUM_PREGUNTAS_FINAL = 40
LIMITE_INTENTOS_PRACTICA = 6
LIMITE_INTENTOS_FINAL = 3
# ==============================================================================

# --- Base de Datos Simulada (en memoria) ---
if 'usuarios' not in globals():
    usuarios = {"sebastian": "123", "gustavo": "456"}
if 'intentos_db' not in globals():
    intentos_db = {}

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
        if username in usuarios and usuarios[username] == password:
            session['username'] = username
            if username not in intentos_db:
                intentos_db[username] = []
            return redirect(url_for('pagina_inicio'))
        else:
            return "Usuario o contraseña incorrectos", 401
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# --- Rutas de la Aplicación ---
@app.route('/')
def pagina_inicio():
    if 'username' not in session: return redirect(url_for('login'))
    
    username = session['username']
    intentos_usuario = intentos_db.get(username, [])
    num_practica = sum(1 for i in intentos_usuario if i['tipo'] == 'Práctica')
    num_final = sum(1 for i in intentos_usuario if i['tipo'] == 'Examen Final')
    
    return render_template('index.html', 
                        intentos={'practica': num_practica, 'final': num_final},
                        limites={'practica': LIMITE_INTENTOS_PRACTICA, 'final': LIMITE_INTENTOS_FINAL})


@app.route('/practica')
def modo_practica():
    if 'username' not in session: return redirect(url_for('login'))
    
    username = session['username']
    num_practica = sum(1 for i in intentos_db.get(username, []) if i['tipo'] == 'Práctica')
    if num_practica >= LIMITE_INTENTOS_PRACTICA:
        return f"Has alcanzado el límite de {LIMITE_INTENTOS_PRACTICA} intentos de práctica. <a href='/'>Volver</a>"

    preguntas_seleccionadas = random.sample(banco_preguntas, NUM_PREGUNTAS_PRACTICA)
    
    # --- CAMBIO AQUÍ: Añadimos los puntos por pregunta ---
    return render_template('test.html', 
                        preguntas=preguntas_seleccionadas, 
                        tipo_examen="Práctica", 
                        puntos_por_pregunta=PUNTOS_PRACTICA)

@app.route('/examen')
def modo_examen():
    if 'username' not in session: return redirect(url_for('login'))

    username = session['username']
    num_final = sum(1 for i in intentos_db.get(username, []) if i['tipo'] == 'Examen Final')
    if num_final >= LIMITE_INTENTOS_FINAL:
        return f"Has alcanzado el límite de {LIMITE_INTENTOS_FINAL} intentos para el examen final. <a href='/'>Volver</a>"
        
    preguntas_seleccionadas = random.sample(banco_preguntas, NUM_PREGUNTAS_FINAL)
    
    # --- CAMBIO AQUÍ: Añadimos los puntos por pregunta ---
    return render_template('test.html', 
                        preguntas=preguntas_seleccionadas, 
                        tipo_examen="Examen Final",
                        puntos_por_pregunta=PUNTOS_FINAL)

@app.route('/resultado', methods=['POST'])
def procesar_resultado():
    if 'username' not in session: return redirect(url_for('login'))

    respuestas_usuario = request.form
    tipo_examen = request.form.get('tipo_examen')
    username = session['username']

    if username not in intentos_db:
        intentos_db[username] = []
        
    respuestas_correctas = 0
    total_preguntas_enviadas = 0
    resultados_detallados = []
    
    preguntas_ids_en_examen = [key.split('-')[1] for key in respuestas_usuario if key.startswith('pregunta-')]

    for pregunta in banco_preguntas:
        if str(pregunta['id']) in preguntas_ids_en_examen:
            total_preguntas_enviadas += 1
            pregunta_id_str = f"pregunta-{pregunta['id']}"
            respuesta_enviada = respuestas_usuario.get(pregunta_id_str)
            es_correcta = (respuesta_enviada == pregunta['respuesta_correcta'])
            if es_correcta: respuestas_correctas += 1
            
            resultados_detallados.append({
                'pregunta': pregunta['pregunta'], 'opciones': pregunta['opciones'],
                'respuesta_enviada': respuesta_enviada, 'letra_correcta': pregunta['respuesta_correcta'],
                'respuesta_correcta_texto': pregunta['opciones'].get(pregunta['respuesta_correcta']),
                'es_correcta': es_correcta, 'explicacion': pregunta.get('explicacion', '')
            })

    if tipo_examen == "Práctica":
        puntos_por_reactivo = PUNTOS_PRACTICA
        puntaje_maximo = total_preguntas_enviadas * PUNTOS_PRACTICA
    elif tipo_examen == "Examen Final":
        puntos_por_reactivo = PUNTOS_FINAL
        puntaje_maximo = total_preguntas_enviadas * PUNTOS_FINAL
    else:
        return "Tipo de examen no reconocido", 400

    puntaje = respuestas_correctas * puntos_por_reactivo
    puntaje_porcentual = (puntaje / puntaje_maximo) * 100 if puntaje_maximo > 0 else 0
    aprobado = puntaje_porcentual >= PORCENTAJE_APROBACION
    
    intentos_db[username].append({'tipo': tipo_examen, 'puntaje_pct': puntaje_porcentual, 'aprobado': aprobado})
    
    return render_template('resultado.html', 
                           puntaje=puntaje, puntaje_maximo=puntaje_maximo,
                           puntaje_porcentual=puntaje_porcentual, aprobado=aprobado,
                           resultados=resultados_detallados, tipo_examen=tipo_examen,
                           respuestas_correctas=respuestas_correctas,
                           total_preguntas=total_preguntas_enviadas,
                           puntos_reactivo=puntos_por_reactivo,
                           porcentaje_aprobacion=PORCENTAJE_APROBACION)

# --- RUTA DEL DASHBOARD REFINADA ---
@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    datos_intentos = []
    for user, attempts in intentos_db.items():
        for attempt in attempts:
            datos_intentos.append({
                'usuario': user,
                'tipo_examen': attempt['tipo'],
                'puntaje': attempt['puntaje_pct'],
                'aprobado': attempt['aprobado']
            })
    
    if not datos_intentos:
        return render_template('dashboard.html', grafico_practica_url=None, grafico_final_url=None)

    df = pd.DataFrame(datos_intentos)
    
    # --- GRÁFICO 1: ANÁLISIS DE EXÁMENES DE PRÁCTICA ---
    df_practica = df[df['tipo_examen'] == 'Práctica'].copy()
    grafico_practica_url = None
    if not df_practica.empty:
        # Calcular el puntaje promedio por cada intento de práctica
        df_practica['num_intento'] = df_practica.groupby('usuario').cumcount() + 1
        progreso_practica = df_practica.groupby('num_intento')['puntaje'].mean().reset_index()

        fig1, ax1 = plt.subplots(figsize=(10, 6))
        ax1.plot(progreso_practica['num_intento'], progreso_practica['puntaje'], marker='o', linestyle='-', color='royalblue', label='Puntaje Promedio')
        ax1.axhline(y=75, color='red', linestyle='--', label='Umbral de Aprobación (75%)')
        ax1.set_title('Progreso del Puntaje Promedio en Exámenes de Práctica', fontsize=16)
        ax1.set_xlabel('Número de Intento de Práctica', fontsize=12)
        ax1.set_ylabel('Puntaje Promedio (%)', fontsize=12)
        ax1.set_ylim(0, 100)
        ax1.set_xticks(range(1, progreso_practica['num_intento'].max() + 1))
        ax1.grid(axis='y', linestyle='--')
        ax1.legend()
        
        buf1 = io.BytesIO()
        fig1.savefig(buf1, format='png')
        buf1.seek(0)
        grafico_practica_url = base64.b64encode(buf1.getvalue()).decode('utf8')
        plt.close(fig1)

    # --- GRÁFICO 2: ANÁLISIS DE EXÁMENES FINALES ---
    df_final = df[df['tipo_examen'] == 'Examen Final'].copy()
    grafico_final_url = None
    if not df_final.empty:
        practicas_antes_del_final = []
        for user in df_final['usuario'].unique():
            num_practicas = df_practica[df_practica['usuario'] == user].shape[0]
            primer_final_aprobado = df_final[df_final['usuario'] == user].iloc[0]['aprobado']
            practicas_antes_del_final.append({'num_practicas': num_practicas, 'aprobado_final': primer_final_aprobado})
        
        if practicas_antes_del_final:
            df_correlacion = pd.DataFrame(practicas_antes_del_final)
            tasa_aprobacion = df_correlacion.groupby('num_practicas')['aprobado_final'].mean().reset_index()
            tasa_aprobacion['aprobado_final'] *= 100

            fig2, ax2 = plt.subplots(figsize=(10, 6))
            ax2.bar(tasa_aprobacion['num_practicas'], tasa_aprobacion['aprobado_final'], color='coral')
            ax2.set_title('Impacto de la Práctica en la Tasa de Aprobación del Examen Final', fontsize=16)
            ax2.set_xlabel('Número de Prácticas Realizadas Antes del Examen Final', fontsize=12)
            ax2.set_ylabel('Tasa de Aprobación (%)', fontsize=12)
            ax2.set_ylim(0, 100)
            max_practicas = int(tasa_aprobacion['num_practicas'].max()) if not tasa_aprobacion.empty else 0
            ax2.set_xticks(range(max_practicas + 2))
            ax2.grid(axis='y', linestyle='--')
            
            buf2 = io.BytesIO()
            fig2.savefig(buf2, format='png')
            buf2.seek(0)
            grafico_final_url = base64.b64encode(buf2.getvalue()).decode('utf8')
            plt.close(fig2)

    return render_template('dashboard.html', 
                        grafico_practica_url=grafico_practica_url, 
                        grafico_final_url=grafico_final_url)

if __name__ == '__main__':
    app.run(debug=True)