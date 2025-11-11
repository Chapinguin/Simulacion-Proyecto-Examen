from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
import json
import random
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64

# ==============================================================================
# --- CONFIGURACIÓN DE LA APLICACIÓN Y BASE DE DATOS ---
# ==============================================================================
app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui_super_segura'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///simulador.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ==============================================================================
# --- PARÁMETROS DE EVALUACIÓN ---
# ==============================================================================
PUNTOS_PRACTICA = 5.0
PUNTOS_FINAL = 2.5
PORCENTAJE_APROBACION = 75.0
NUM_PREGUNTAS_PRACTICA = 20
NUM_PREGUNTAS_FINAL = 40
LIMITE_INTENTOS_PRACTICA = 6
LIMITE_INTENTOS_FINAL = 3

# ==============================================================================
# --- MODELOS DE LA BASE DE DATOS ---
# ==============================================================================
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), nullable=False)
    apellido = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    fecha_nacimiento = db.Column(db.Date, nullable=False)
    es_admin = db.Column(db.Boolean, default=False)
    intentos = db.relationship('Intento', backref='usuario', lazy=True)

class Pregunta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    texto_pregunta = db.Column(db.Text, nullable=False)
    imagen_path = db.Column(db.String(100))
    explicacion = db.Column(db.Text)
    opciones = db.relationship('Opcion', backref='pregunta', lazy=True, cascade="all, delete-orphan")

class Opcion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pregunta_id = db.Column(db.Integer, db.ForeignKey('pregunta.id'), nullable=False)
    texto_opcion = db.Column(db.String(200), nullable=False)
    es_correcta = db.Column(db.Boolean, default=False, nullable=False)


class Intento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    tipo_examen = db.Column(db.String(50), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    puntaje_pct = db.Column(db.Float, nullable=False)
    aprobado = db.Column(db.Boolean, nullable=False)
    respuestas = db.relationship('RespuestaUsuario', backref='intento', lazy=True, cascade="all, delete-orphan")


class RespuestaUsuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    intento_id = db.Column(db.Integer, db.ForeignKey('intento.id'), nullable=False)
    pregunta_id = db.Column(db.Integer, db.ForeignKey('pregunta.id'), nullable=False)
    opcion_elegida_id = db.Column(db.Integer, db.ForeignKey('opcion.id'), nullable=True) # Nullable para no contestadas
    es_correcta = db.Column(db.Boolean, nullable=False)

# ==============================================================================
# --- RUTAS DE AUTENTICACIÓN ---
# ==============================================================================
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        email = request.form['email']
        password = request.form['password']
        fecha_nacimiento_str = request.form['fecha_nacimiento']
        
        if not all([nombre, apellido, email, password, fecha_nacimiento_str]):
            flash("Todos los campos son obligatorios.", "danger")
            return redirect(url_for('signup'))
            
        fecha_nacimiento = datetime.strptime(fecha_nacimiento_str, '%Y-%m-%d').date()
        edad = (datetime.now().date() - fecha_nacimiento).days / 365.25
        if edad < 15.5:
            flash("Debes tener al menos 15 años y medio para registrarte.", "danger")
            return redirect(url_for('signup'))

        if Usuario.query.filter_by(email=email).first():
            flash("El correo electrónico ya está registrado.", "warning")
            return redirect(url_for('signup'))

        password_hash = generate_password_hash(password)
        
        nuevo_usuario = Usuario(nombre=nombre, apellido=apellido, email=email, 
                                password_hash=password_hash, fecha_nacimiento=fecha_nacimiento)
        
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        flash("¡Registro exitoso! Ahora puedes iniciar sesión.", "success")
        return redirect(url_for('login'))
        
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        folio_pago = request.form['folio_pago']
        
        if folio_pago != "001":
            flash("Folio de pago inválido.", "danger")
            return redirect(url_for('login'))
            
        usuario = Usuario.query.filter_by(email=email).first()
        
        if usuario and check_password_hash(usuario.password_hash, password):
            session['user_id'] = usuario.id
            session['username'] = usuario.nombre
            flash(f"Bienvenido de nuevo, {usuario.nombre}!", "success")
            return redirect(url_for('pagina_inicio'))
        else:
            flash("Correo o contraseña incorrectos.", "danger")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Has cerrado sesión exitosamente.", "info")
    return redirect(url_for('login'))


# ==============================================================================
# --- RUTAS PRINCIPALES DE LA APLICACIÓN ---
# ==============================================================================
# EN app.py
# EN app.py (Reemplazar la función pagina_inicio)

@app.route('/')
def pagina_inicio():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Consultas para contar intentos
    intentos_practica_count = Intento.query.filter_by(usuario_id=user_id, tipo_examen='Práctica').count()
    intentos_final_count = Intento.query.filter_by(usuario_id=user_id, tipo_examen='Examen Final').count()
    
    # --- NUEVO: Buscar el ID del último intento para cada tipo ---
    ultimo_intento_practica = Intento.query.filter_by(usuario_id=user_id, tipo_examen='Práctica').order_by(Intento.fecha.desc()).first()
    ultimo_intento_final = Intento.query.filter_by(usuario_id=user_id, tipo_examen='Examen Final').order_by(Intento.fecha.desc()).first()

    practica_aprobada = Intento.query.filter_by(usuario_id=user_id, tipo_examen='Práctica', aprobado=True).first() is not None
    final_aprobado = Intento.query.filter_by(usuario_id=user_id, tipo_examen='Examen Final', aprobado=True).first() is not None
    
    session['practica_aprobada'] = practica_aprobada
    session['final_aprobado'] = final_aprobado
    
    return render_template('index.html', 
                        intentos={'practica': intentos_practica_count, 'final': intentos_final_count},
                        limites={'practica': LIMITE_INTENTOS_PRACTICA, 'final': LIMITE_INTENTOS_FINAL},
                        ultimo_intento_practica_id=ultimo_intento_practica.id if ultimo_intento_practica else None,
                        ultimo_intento_final_id=ultimo_intento_final.id if ultimo_intento_final else None)

@app.route('/practica')
def modo_practica():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # --- NUEVA COMPROBACIÓN 1: Verificar si ya aprobó un examen de práctica ---
    intento_aprobado = Intento.query.filter_by(
        usuario_id=user_id, 
        tipo_examen='Práctica', 
        aprobado=True
    ).first()
    
    if intento_aprobado:
        flash("¡Felicidades! Ya has aprobado el examen de práctica.", "success")
        return redirect(url_for('pagina_inicio'))
    # --- FIN DE LA COMPROBACIÓN 1 ---

    # Comprobación del límite de intentos (se mantiene igual)
    intentos_usuario = Intento.query.filter_by(usuario_id=user_id, tipo_examen='Práctica').count()
    if intentos_usuario >= LIMITE_INTENTOS_PRACTICA:
        flash(f"Has alcanzado el límite de {LIMITE_INTENTOS_PRACTICA} intentos de práctica.", "warning")
        return redirect(url_for('pagina_inicio'))

    preguntas_seleccionadas = db.session.query(Pregunta).order_by(func.random()).limit(NUM_PREGUNTAS_PRACTICA).all()
    
    return render_template('test.html', 
                        preguntas=preguntas_seleccionadas, 
                        tipo_examen="Práctica", 
                        puntos_por_pregunta=PUNTOS_PRACTICA)


@app.route('/examen')
def modo_examen():
    if 'user_id' not in session: return redirect(url_for('login'))

    user_id = session['user_id']

    # --- NUEVA COMPROBACIÓN 2: Verificar si ya aprobó un examen final ---
    intento_aprobado = Intento.query.filter_by(
        usuario_id=user_id, 
        tipo_examen='Examen Final', 
        aprobado=True
    ).first()

    if intento_aprobado:
        flash("¡Felicidades! Ya has aprobado el examen final y estás listo para tu prueba práctica.", "success")
        return redirect(url_for('pagina_inicio'))
    # --- FIN DE LA COMPROBACIÓN 2 ---

    # Comprobación del límite de intentos (se mantiene igual)
    intentos_usuario = Intento.query.filter_by(usuario_id=user_id, tipo_examen='Examen Final').count()
    if intentos_usuario >= LIMITE_INTENTOS_FINAL:
        flash(f"Has alcanzado el límite de {LIMITE_INTENTOS_FINAL} intentos para el examen final.", "warning")
        return redirect(url_for('pagina_inicio'))
        
    preguntas_seleccionadas = db.session.query(Pregunta).order_by(func.random()).limit(NUM_PREGUNTAS_FINAL).all()
    
    return render_template('test.html', 
                        preguntas=preguntas_seleccionadas, 
                        tipo_examen="Examen Final",
                        puntos_por_pregunta=PUNTOS_FINAL)

# EN app.py (Reemplazar la función procesar_resultado)

@app.route('/resultado', methods=['POST'])
def procesar_resultado():
    if 'user_id' not in session: return redirect(url_for('login'))

    respuestas_usuario_form = request.form
    tipo_examen = request.form.get('tipo_examen')
    user_id = session['user_id']

    ids_str = request.form.get('todos_los_ids', '')
    preguntas_ids_en_examen = [int(id_str) for id_str in ids_str.split(',') if id_str.strip()]
    
    preguntas_del_examen = db.session.query(Pregunta).filter(Pregunta.id.in_(preguntas_ids_en_examen)).all()
    
    total_preguntas_en_examen = len(preguntas_del_examen)
    respuestas_correctas = 0
    
    # --- LÓGICA DE CALIFICACIÓN Y PREPARACIÓN DE DATOS ---
    respuestas_para_guardar = []
    resultados_detallados = []

    for pregunta in preguntas_del_examen:
        opcion_elegida_id_str = respuestas_usuario_form.get(f"pregunta-{pregunta.id}")
        opcion_elegida_id = int(opcion_elegida_id_str) if opcion_elegida_id_str else None
        
        opcion_correcta_obj = next((op for op in pregunta.opciones if op.es_correcta), None)
        es_correcta = (opcion_elegida_id == opcion_correcta_obj.id) if opcion_correcta_obj and opcion_elegida_id else False

        if es_correcta:
            respuestas_correctas += 1

        respuestas_para_guardar.append({
            'pregunta_id': pregunta.id,
            'opcion_elegida_id': opcion_elegida_id,
            'es_correcta': es_correcta
        })
        
        opcion_elegida_obj = next((op for op in pregunta.opciones if op.id == opcion_elegida_id), None)
        resultados_detallados.append({
            'pregunta': pregunta.texto_pregunta,
            'opciones': {str(op.id): op.texto_opcion for op in pregunta.opciones},
            'respuesta_enviada_texto': opcion_elegida_obj.texto_opcion if opcion_elegida_obj else "No contestada",
            'respuesta_correcta_texto': opcion_correcta_obj.texto_opcion if opcion_correcta_obj else "N/A",
            'es_correcta': es_correcta,
            'explicacion': pregunta.explicacion
        })

    # --- LÓGICA DE PUNTAJE Y GUARDADO EN BD ---
    puntos_por_reactivo = PUNTOS_PRACTICA if tipo_examen == "Práctica" else PUNTOS_FINAL
    puntaje = respuestas_correctas * puntos_por_reactivo
    puntaje_maximo = total_preguntas_en_examen * puntos_por_reactivo
    puntaje_porcentual = (puntaje / puntaje_maximo) * 100 if puntaje_maximo > 0 else 0
    aprobado = puntaje_porcentual >= PORCENTAJE_APROBACION
    
    # Crear el intento principal
    nuevo_intento = Intento(usuario_id=user_id, tipo_examen=tipo_examen, puntaje_pct=puntaje_porcentual, aprobado=aprobado)
    db.session.add(nuevo_intento)
    db.session.flush() # Para obtener el ID del nuevo intento antes de hacer commit

    # Guardar cada respuesta asociada a este nuevo intento
    for r in respuestas_para_guardar:
        nueva_respuesta = RespuestaUsuario(
            intento_id=nuevo_intento.id,
            pregunta_id=r['pregunta_id'],
            opcion_elegida_id=r['opcion_elegida_id'],
            es_correcta=r['es_correcta']
        )
        db.session.add(nueva_respuesta)

    db.session.commit() # Guardar todo en la base de datos
    
    flash("Tu examen ha sido calificado y guardado.", "info")
    
    return render_template('resultado.html', # ... (el resto de los argumentos se mantiene igual)
                        puntaje=puntaje, puntaje_maximo=puntaje_maximo,
                        puntaje_porcentual=puntaje_porcentual, aprobado=aprobado,
                        resultados=resultados_detallados, tipo_examen=tipo_examen,
                        respuestas_correctas=respuestas_correctas, total_preguntas=total_preguntas_en_examen,
                        puntos_reactivo=puntos_por_reactivo, porcentaje_aprobacion=PORCENTAJE_APROBACION)
    
    
# EN app.py (añadir esta nueva ruta)

@app.route('/revisar/<int:intento_id>')
def revisar_intento(intento_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Buscar el intento en la base de datos
    intento = Intento.query.get_or_404(intento_id)

    # Medida de seguridad: asegurarse de que el usuario solo pueda ver sus propios intentos
    if intento.usuario_id != session['user_id']:
        flash("No tienes permiso para ver este resultado.", "danger")
        return redirect(url_for('pagina_inicio'))

    # Reconstruir los datos para la plantilla resultado.html
    respuestas_guardadas = RespuestaUsuario.query.filter_by(intento_id=intento.id).all()
    
    resultados_detallados = []
    respuestas_correctas = 0
    
    for respuesta in respuestas_guardadas:
        pregunta = Pregunta.query.get(respuesta.pregunta_id)
        opcion_correcta_obj = next((op for op in pregunta.opciones if op.es_correcta), None)
        opcion_elegida_obj = Opcion.query.get(respuesta.opcion_elegida_id) if respuesta.opcion_elegida_id else None
        
        if respuesta.es_correcta:
            respuestas_correctas += 1

        resultados_detallados.append({
            'pregunta': pregunta.texto_pregunta,
            'opciones': {str(op.id): op.texto_opcion for op in pregunta.opciones},
            'respuesta_enviada_texto': opcion_elegida_obj.texto_opcion if opcion_elegida_obj else "No contestada",
            'respuesta_correcta_texto': opcion_correcta_obj.texto_opcion,
            'es_correcta': respuesta.es_correcta,
            'explicacion': pregunta.explicacion
        })

    # Recalcular puntaje para mostrar
    tipo_examen = intento.tipo_examen
    total_preguntas = len(resultados_detallados)
    puntos_por_reactivo = PUNTOS_PRACTICA if tipo_examen == "Práctica" else PUNTOS_FINAL
    puntaje = respuestas_correctas * puntos_por_reactivo
    puntaje_maximo = total_preguntas * puntos_por_reactivo

    return render_template('resultado.html',
                        puntaje=puntaje, puntaje_maximo=puntaje_maximo,
                        puntaje_porcentual=intento.puntaje_pct, aprobado=intento.aprobado,
                        resultados=resultados_detallados, tipo_examen=tipo_examen,
                        respuestas_correctas=respuestas_correctas, total_preguntas=total_preguntas,
                        puntos_reactivo=puntos_por_reactivo, porcentaje_aprobacion=PORCENTAJE_APROBACION)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # --- NUEVA LÓGICA: Consultar la base de datos ---
    # Obtenemos todos los intentos de todos los usuarios
    todos_los_intentos = Intento.query.all()
    
    # Si no hay ningún intento en la base de datos, mostramos el dashboard vacío
    if not todos_los_intentos:
        return render_template('dashboard.html', grafico_practica_url=None, grafico_final_url=None)

    # Convertimos la lista de objetos Intento a un DataFrame de Pandas para un análisis fácil
    datos_df = pd.DataFrame([{
        'usuario_id': i.usuario_id,
        'tipo_examen': i.tipo_examen,
        'puntaje': i.puntaje_pct,
        'aprobado': i.aprobado
    } for i in todos_los_intentos])

    # --- GRÁFICO 1: ANÁLISIS DE EXÁMENES DE PRÁCTICA ---
    df_practica = datos_df[datos_df['tipo_examen'] == 'Práctica'].copy()
    grafico_practica_url = None
    if not df_practica.empty:
        # Calcular el puntaje promedio por cada número de intento (1er intento, 2do, etc.)
        df_practica['num_intento'] = df_practica.groupby('usuario_id').cumcount() + 1
        progreso_practica = df_practica.groupby('num_intento')['puntaje'].mean().reset_index()

        fig1, ax1 = plt.subplots(figsize=(10, 6))
        ax1.plot(progreso_practica['num_intento'], progreso_practica['puntaje'], marker='o', linestyle='-', color='royalblue', label='Puntaje Promedio')
        ax1.axhline(y=PORCENTAJE_APROBACION, color='red', linestyle='--', label=f'Umbral de Aprobación ({PORCENTAJE_APROBACION}%)')
        ax1.set_title('Progreso del Puntaje Promedio en Exámenes de Práctica', fontsize=16)
        ax1.set_xlabel('Número de Intento de Práctica', fontsize=12)
        ax1.set_ylabel('Puntaje Promedio (%)', fontsize=12)
        ax1.set_ylim(0, 105)
        # Aseguramos que el eje X muestre todos los intentos posibles
        ax1.set_xticks(range(1, max(progreso_practica['num_intento'].max(), LIMITE_INTENTOS_PRACTICA) + 1))
        ax1.grid(axis='y', linestyle='--')
        ax1.legend()
        
        # Convertir el gráfico a imagen para el HTML
        buf1 = io.BytesIO()
        fig1.savefig(buf1, format='png')
        buf1.seek(0)
        grafico_practica_url = base64.b64encode(buf1.getvalue()).decode('utf8')
        plt.close(fig1)

    # --- GRÁFICO 2: ANÁLISIS DE EXÁMENES FINALES ---
    df_final = datos_df[datos_df['tipo_examen'] == 'Examen Final'].copy()
    grafico_final_url = None
    if not df_final.empty and not df_practica.empty: # Necesitamos ambos tipos de datos
        practicas_antes_del_final = []
        for user_id in df_final['usuario_id'].unique():
            num_practicas = df_practica[df_practica['usuario_id'] == user_id].shape[0]
            # Tomamos el resultado del primer examen final de este usuario
            primer_final = df_final[df_final['usuario_id'] == user_id].iloc[0]
            practicas_antes_del_final.append({'num_practicas': num_practicas, 'aprobado_final': primer_final['aprobado']})
        
        if practicas_antes_del_final:
            df_correlacion = pd.DataFrame(practicas_antes_del_final)
            tasa_aprobacion = df_correlacion.groupby('num_practicas')['aprobado_final'].mean().reset_index()
            tasa_aprobacion['aprobado_final'] *= 100

            fig2, ax2 = plt.subplots(figsize=(10, 6))
            ax2.bar(tasa_aprobacion['num_practicas'], tasa_aprobacion['aprobado_final'], color='coral', zorder=3)
            ax2.set_title('Impacto de la Práctica en la Tasa de Aprobación del Examen Final', fontsize=16)
            ax2.set_xlabel('Número de Prácticas Realizadas Antes del Examen Final', fontsize=12)
            ax2.set_ylabel('Tasa de Aprobación (%)', fontsize=12)
            ax2.set_ylim(0, 105)
            max_practicas_db = int(tasa_aprobacion['num_practicas'].max()) if not tasa_aprobacion.empty else 0
            ax2.set_xticks(range(max_practicas_db + 2))
            ax2.grid(axis='y', linestyle='--')
            
            buf2 = io.BytesIO()
            fig2.savefig(buf2, format='png')
            buf2.seek(0)
            grafico_final_url = base64.b64encode(buf2.getvalue()).decode('utf8')
            plt.close(fig2)

    return render_template('dashboard.html', 
                        grafico_practica_url=grafico_practica_url, 
                        grafico_final_url=grafico_final_url)

# ==============================================================================
# --- PUNTO DE ENTRADA ---
# ==============================================================================
if __name__ == '__main__':
    # Este bloque asegura que las tablas se creen si el archivo .db no existe
    with app.app_context():
        db.create_all()
    app.run(debug=True)