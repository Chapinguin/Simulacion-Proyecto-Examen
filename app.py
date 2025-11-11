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

@app.route('/')
def pagina_inicio():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Consultamos el número de intentos
    intentos_practica = Intento.query.filter_by(usuario_id=user_id, tipo_examen='Práctica').count()
    intentos_final = Intento.query.filter_by(usuario_id=user_id, tipo_examen='Examen Final').count()
    
    # --- NUEVO: Consultamos si ya existe un intento aprobado ---
    practica_aprobada = Intento.query.filter_by(usuario_id=user_id, tipo_examen='Práctica', aprobado=True).first() is not None
    final_aprobado = Intento.query.filter_by(usuario_id=user_id, tipo_examen='Examen Final', aprobado=True).first() is not None
    
    # Guardamos este estado en la sesión para que sea fácil de acceder
    session['practica_aprobada'] = practica_aprobada
    session['final_aprobado'] = final_aprobado
    
    return render_template('index.html', 
                        intentos={'practica': intentos_practica, 'final': intentos_final},
                        limites={'practica': LIMITE_INTENTOS_PRACTICA, 'final': LIMITE_INTENTOS_FINAL})
# EN app.py

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
    if 'user_id' not in session: 
        return redirect(url_for('login'))

    respuestas_usuario = request.form
    tipo_examen = request.form.get('tipo_examen')
    user_id = session['user_id']

    # --- INICIO DE LA NUEVA LÓGICA DE CALIFICACIÓN ---
    
    # Obtenemos la lista completa de IDs de las preguntas del examen
    ids_str = request.form.get('todos_los_ids', '')
    preguntas_ids_en_examen = [int(id_str) for id_str in ids_str.split(',') if id_str.strip()]
    
    total_preguntas_en_examen = len(preguntas_ids_en_examen)
    respuestas_correctas = 0
    resultados_detallados = []

    # Iteramos directamente sobre los IDs de las preguntas que estaban en el examen
    for pregunta_id in preguntas_ids_en_examen:
        # Buscamos la pregunta en la base de datos
        pregunta = db.session.query(Pregunta).get(pregunta_id)
        if not pregunta:
            continue # Si por alguna razón no se encuentra, la saltamos

        # Obtenemos la respuesta del usuario para esta pregunta
        pregunta_id_form = f"pregunta-{pregunta_id}"
        opcion_elegida_id_str = respuestas_usuario.get(pregunta_id_form) # Puede ser None
        
        # Buscamos la opción correcta de la pregunta
        opcion_correcta_obj = db.session.query(Opcion).filter_by(pregunta_id=pregunta_id, es_correcta=True).first()
        
        es_correcta = False
        opcion_elegida_obj = None
        
        if opcion_elegida_id_str:
            opcion_elegida_obj = db.session.query(Opcion).get(int(opcion_elegida_id_str))
            if opcion_elegida_obj and opcion_elegida_obj.es_correcta:
                respuestas_correctas += 1
                es_correcta = True
        
        # Preparamos los datos para la plantilla de resultados
        resultados_detallados.append({
            'pregunta': pregunta.texto_pregunta,
            'opciones': {str(op.id): op.texto_opcion for op in pregunta.opciones},
            'respuesta_enviada_texto': opcion_elegida_obj.texto_opcion if opcion_elegida_obj else "No contestada",
            'respuesta_correcta_texto': opcion_correcta_obj.texto_opcion if opcion_correcta_obj else "N/A",
            'es_correcta': es_correcta,
            'explicacion': pregunta.explicacion
        })

    # --- Lógica de Calificación (basada en los parámetros globales) ---
    if tipo_examen == "Práctica":
        puntos_por_reactivo = PUNTOS_PRACTICA
        puntaje_maximo = total_preguntas_en_examen * PUNTOS_PRACTICA
    elif tipo_examen == "Examen Final":
        puntos_por_reactivo = PUNTOS_FINAL
        puntaje_maximo = total_preguntas_en_examen * PUNTOS_FINAL
    else:
        return "Tipo de examen no reconocido", 400

    puntaje = respuestas_correctas * puntos_por_reactivo
    puntaje_porcentual = (puntaje / puntaje_maximo) * 100 if puntaje_maximo > 0 else 0
    aprobado = puntaje_porcentual >= PORCENTAJE_APROBACION
    
    # --- Guardar el Intento en la Base de Datos ---
    nuevo_intento = Intento(
        usuario_id=user_id,
        tipo_examen=tipo_examen,
        puntaje_pct=puntaje_porcentual,
        aprobado=aprobado
    )
    db.session.add(nuevo_intento)
    db.session.commit()
    
    flash(f"Tu {tipo_examen} ha sido calificado.", "info")
    
    return render_template('resultado.html', 
                        puntaje=puntaje,
                        puntaje_maximo=puntaje_maximo,
                        puntaje_porcentual=puntaje_porcentual,
                        aprobado=aprobado,
                        resultados=resultados_detallados,
                        tipo_examen=tipo_examen,
                        respuestas_correctas=respuestas_correctas,
                        total_preguntas=total_preguntas_en_examen,
                        puntos_reactivo=puntos_por_reactivo,
                        porcentaje_aprobacion=PORCENTAJE_APROBACION)


# EN app.py (Reemplazar la función dashboard)

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