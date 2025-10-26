# poblar_db.py
from app import app, db, Usuario, Pregunta, Opcion, Intento
from werkzeug.security import generate_password_hash
import json
from datetime import datetime, timedelta
import random

def poblar_datos_simulados():
    """
    Función para reiniciar y poblar la base de datos con el admin, las preguntas
    y un conjunto de usuarios e intentos simulados.
    """
    with app.app_context():
        # --- PASO 1: REINICIAR LA BASE DE DATOS ---
        print("Reiniciando la base de datos...")
        db.drop_all()
        db.create_all()

        # --- PASO 2: CREAR USUARIO ADMIN Y PREGUNTAS ---
        # (Esta parte es la misma que antes)
        admin_email = "admin@simulador.com"
        admin_password = "admin123"
        admin_pass_hash = generate_password_hash(admin_password)
        admin_user = Usuario(nombre="Admin", apellido="User", email=admin_email, password_hash=admin_pass_hash, fecha_nacimiento=datetime(2000, 1, 1).date(), es_admin=True)
        db.session.add(admin_user)

        try:
            with open('preguntas.json', 'r', encoding='utf-8') as f:
                banco_preguntas = json.load(f)
            for p_json in banco_preguntas:
                nueva_pregunta = Pregunta(id=p_json['id'], texto_pregunta=p_json['pregunta'], imagen_path=p_json.get('imagen'), explicacion=p_json.get('explicacion'))
                db.session.add(nueva_pregunta)
                for letra, texto in p_json['opciones'].items():
                    es_correcta = (letra == p_json['respuesta_correcta'])
                    db.session.add(Opcion(pregunta=nueva_pregunta, texto_opcion=texto, es_correcta=es_correcta))
            print(f"-> Se insertaron {len(banco_preguntas)} preguntas.")
        except Exception as e:
            print(f"Error cargando preguntas: {e}")

        # --- PASO 3: GENERAR USUARIOS Y RESULTADOS DUMMY ---
        print("\nGenerando usuarios y resultados simulados...")
        num_usuarios_dummy = 20
        
        for i in range(num_usuarios_dummy):
            # Crear usuario ficticio
            email = f'usuario{i+1}@test.com'
            pass_hash = generate_password_hash('123')
            nuevo_usuario = Usuario(
                nombre=f'Usuario',
                apellido=f'{i+1}',
                email=email,
                password_hash=pass_hash,
                fecha_nacimiento=datetime(2002, 1, 1).date()
            )
            db.session.add(nuevo_usuario)
            db.session.flush() # Para obtener el ID del usuario antes del commit

            # Simular intentos de PRÁCTICA para este usuario
            num_practicas = random.randint(0, 6)
            puntaje_base_practica = 40.0 # Empiezan con un puntaje bajo
            for j in range(num_practicas):
                # Simular mejora: cada intento aumenta el puntaje un poco, con algo de aleatoriedad
                puntaje_practica = min(100, puntaje_base_practica + random.uniform(5, 15))
                puntaje_base_practica = puntaje_practica # Guardar el nuevo puntaje base
                intento_practica = Intento(
                    usuario_id=nuevo_usuario.id,
                    tipo_examen='Práctica',
                    puntaje_pct=puntaje_practica,
                    aprobado=(puntaje_practica >= 75.0)
                )
                db.session.add(intento_practica)

            # Simular intentos de EXAMEN FINAL para este usuario
            num_finales = random.randint(1, 3)
            for k in range(num_finales):
                # La probabilidad de aprobar depende de cuántas prácticas hizo
                # Puntaje base con un bonus por cada práctica realizada
                puntaje_base_final = 50.0 + (num_practicas * 7) 
                puntaje_final = min(100, puntaje_base_final + random.uniform(-10, 10)) # Añadir aleatoriedad
                
                intento_final = Intento(
                    usuario_id=nuevo_usuario.id,
                    tipo_examen='Examen Final',
                    puntaje_pct=puntaje_final,
                    aprobado=(puntaje_final >= 75.0)
                )
                db.session.add(intento_final)

        print(f"-> Se generaron {num_usuarios_dummy} usuarios ficticios con sus respectivos intentos.")

        # --- PASO 4: GUARDAR TODOS LOS CAMBIOS ---
        try:
            db.session.commit()
            print("\n¡Base de datos poblada con datos simulados exitosamente!")
        except Exception as e:
            db.session.rollback()
            print(f"\nError al guardar los datos simulados: {e}")

if __name__ == '__main__':
    poblar_datos_simulados()