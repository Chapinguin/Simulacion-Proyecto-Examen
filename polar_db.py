# poblar_db.py
from app import app, db, Usuario, Pregunta, Opcion
from werkzeug.security import generate_password_hash
import json
from datetime import datetime

def poblar_datos():
    """
    Función para reiniciar y poblar la base de datos con datos iniciales.
    EJECUTAR ESTE SCRIPT UNA SOLA VEZ para configurar el sistema.
    """
    with app.app_context():
        # --- PASO 1: REINICIAR LA BASE DE DATOS ---
        # Advertencia: Esto borrará todos los datos existentes.
        print("Reiniciando la base de datos (borrando tablas antiguas)...")
        db.drop_all()
        print("Creando nuevas tablas...")
        db.create_all()

        # --- PASO 2: CREAR EL USUARIO ADMINISTRADOR ---
        try:
            admin_email = "admin@simulador.com"
            admin_password = "admin123"
            admin_pass_hash = generate_password_hash(admin_password)
            
            admin_user = Usuario(
                nombre="Admin",
                apellido="User",
                email=admin_email,
                password_hash=admin_pass_hash,
                fecha_nacimiento=datetime.strptime("2000-01-01", "%Y-%m-%d").date(),
                es_admin=True
            )
            db.session.add(admin_user)
            print(f"-> Usuario 'admin' preparado para ser insertado (email: {admin_email}, pass: {admin_password})")
        except Exception as e:
            print(f"Error creando el usuario admin: {e}")


        # --- PASO 3: POBLAR PREGUNTAS DESDE JSON ---
        try:
            with open('preguntas.json', 'r', encoding='utf-8') as f:
                banco_preguntas = json.load(f)
            
            if not banco_preguntas:
                print("Advertencia: El archivo 'preguntas.json' está vacío o no es una lista válida.")
                return

            for p_json in banco_preguntas:
                # Crear la nueva pregunta
                nueva_pregunta = Pregunta(
                    id=p_json['id'],
                    texto_pregunta=p_json['pregunta'],
                    imagen_path=p_json.get('imagen'),
                    explicacion=p_json.get('explicacion')
                )
                db.session.add(nueva_pregunta)

                # Crear sus opciones asociadas
                for letra_opcion, texto_opcion in p_json['opciones'].items():
                    es_correcta = (letra_opcion == p_json['respuesta_correcta'])
                    nueva_opcion = Opcion(
                        pregunta=nueva_pregunta, # Asocia la opción con la pregunta
                        texto_opcion=texto_opcion,
                        es_correcta=es_correcta
                    )
                    db.session.add(nueva_opcion)
            
            print(f"-> Se han preparado {len(banco_preguntas)} preguntas para ser insertadas.")

        except FileNotFoundError:
            print("Error fatal: No se encontró el archivo 'preguntas.json'. No se pueden poblar las preguntas.")
        except Exception as e:
            print(f"Error al leer o procesar preguntas.json: {e}")

        # --- PASO 4: GUARDAR TODOS LOS CAMBIOS ---
        try:
            db.session.commit()
            print("\n¡Base de datos poblada exitosamente!")
        except Exception as e:
            db.session.rollback() # Deshacer cambios si hay un error al guardar
            print(f"\nError al guardar los datos en la base de datos: {e}")

# Este bloque permite ejecutar el script directamente desde la terminal
if __name__ == '__main__':
    poblar_datos()