# 🚘 Simulador de Examen Teórico de Manejo

![Estado](https://img.shields.io/badge/estado-en%20desarrollo-yellow)

---

### **Índice**
1. [Descripción del Proyecto](#1-descripción-del-proyecto)
2. [Objetivo](#2-objetivo)
3. [Características Principales](#3-características-principales)
4. [Stack Tecnológico](#4-stack-tecnológico)
5. [Estructura del Proyecto](#5-estructura-del-proyecto)
6. [Desarrolladores](#6-desarrolladores)

---

### **1. Descripción del Proyecto**
Este proyecto consiste en el desarrollo de una aplicación web interactiva para simular el examen teórico necesario para obtener una licencia de manejo. El objetivo es proporcionar a los usuarios una herramienta de estudio y evaluación basada en el **Manual del Conductor de California**.

La aplicación utilizará un banco de preguntas (reactivos) extraídas y adaptadas del manual oficial, con un fuerte énfasis en el uso de **imágenes y elementos visuales** para mejorar la comprensión de señales de tráfico y situaciones de manejo.

### **2. Objetivo**
El objetivo principal es crear un simulador funcional que permita a los aspirantes a conductores:
- **Practicar** sus conocimientos en un entorno sin presión.
- **Evaluar** su preparación a través de un examen final cronometrado.
- **Identificar** áreas de oportunidad mediante la revisión de respuestas incorrectas y sus explicaciones.

### **3. Características Principales**
La aplicación contará con dos modos de operación principales:

#### **🚗 Modo Práctica (Test Simulador)**
- **Preguntas Aleatorias:** Selección de un subconjunto de preguntas al azar del banco principal.
- **Retroalimentación Inmediata:** Después de cada respuesta, el sistema indicará si fue correcta o incorrecta y mostrará la explicación correspondiente.
- **Sin Límite de Tiempo:** Ideal para el estudio y aprendizaje a un ritmo propio.

#### **🏁 Modo Examen Final**
- **Simulación Realista:** Selección de un número fijo de preguntas (ej. 40) de manera aleatoria, simulando la estructura de un examen oficial.
- **Cronometrado:** Se implementará un límite de tiempo para completar la prueba.
- **Resultados al Final:** El usuario no recibirá retroalimentación hasta que termine el examen, momento en el que se le mostrará su puntuación final, si aprobó o no, y la opción de revisar sus respuestas.

### **4. Stack Tecnológico**
- **Backend:** Python con el micro-framework **Flask**.
- **Frontend:** HTML, CSS y JavaScript.
- **Formato de Datos:** Las preguntas y respuestas se almacenarán en un archivo **JSON** para facilitar su manejo y escalabilidad.

### **5. Estructura del Proyecto**
El proyecto se organizará con la siguiente estructura de carpetas y archivos:
/simulador_examen/
|
|-- app.py # Lógica principal de la aplicación Flask
|-- preguntas.json # Banco de todas las preguntas y respuestas
|
|-- /static/
| |-- /css/
| | |-- style.css # Archivo de estilos para el frontend
| |-- /images/
| | |-- no_u_turn.png # Ejemplo de imagen para una pregunta
| | |-- ... # Resto de imágenes
|
|-- /templates/
|-- index.html # Página de inicio
|-- test.html # Plantilla para mostrar las preguntas
|-- resultado.html # Página para mostrar los resultados

### **6. Desarrolladores**
- Sebastian Chapa
- Gustavo Cortes