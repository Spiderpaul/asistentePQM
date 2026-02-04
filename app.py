import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from streamlit_mic_recorder import mic_recorder
import os

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="PQM Intelligent Assistant", page_icon="🥩", layout="centered")

# 2. CONFIGURACIÓN DE SEGURIDAD (API KEY)
# Para probar localmente pon tu clave entre las comillas. 
# Al subir a Streamlit Cloud, usaremos st.secrets para mayor seguridad.
GOOGLE_API_KEY = "AIzaSyCpi-NnSjBZIKM8Fh029wmAD1nE_g8IaSo" 
genai.configure(api_key=GOOGLE_API_KEY)

# 3. FUNCIONES DE APOYO
def leer_pdf(archivo):
    try:
        lector = PdfReader(archivo)
        texto = ""
        for pagina in lector.pages:
            texto_extraido = pagina.extract_text()
            if texto_extraido:
                texto += texto_extraido + "\n"
        return texto
    except Exception as e:
        st.error(f"Error al leer el PDF: {e}")
        return None

# 4. INICIALIZACIÓN DE LA MEMORIA (Session State)
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

if "inventario_texto" not in st.session_state:
    ruta_base = "data/precios.pdf"
    if os.path.exists(ruta_base):
        st.session_state.inventario_texto = leer_pdf(ruta_base)
        st.session_state.origen = "Servidor (GitHub)"
    else:
        st.session_state.inventario_texto = None
        st.session_state.origen = "Ninguno"

# 5. BARRA LATERAL (ADMINISTRACIÓN)
with st.sidebar:
    st.header("⚙️ Configuración")
    password = st.text_input("Clave de Admin", type="password")
    
    if password == "PQM2026": # Puedes cambiar esta clave
        st.subheader("Actualizar Inventario")
        archivo_nuevo = st.file_uploader("Subir nuevo PDF", type="pdf")
        if archivo_nuevo:
            texto = leer_pdf(archivo_nuevo)
            if texto:
                st.session_state.inventario_texto = texto
                st.session_state.origen = "Carga Manual (Nueva)"
                st.success("Inventario actualizado.")
    
    st.divider()
    st.caption(f"Inventario actual: {st.session_state.origen}")
    if st.button("Borrar historial de chat"):
        st.session_state.mensajes = []
        st.rerun()

# 6. INTERFAZ PRINCIPAL
st.title("🥩 PQM Assistant")
st.markdown("Consulta precios por texto o voz (Español/English)")

# Mostrar mensajes previos
for m in st.session_state.mensajes:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# 7. ENTRADA DE USUARIO (MICROFONO Y TEXTO)
st.write("---")
col_mic, col_txt = st.columns([1, 5])

with col_mic:
    # Componente de grabación
    audio_data = mic_recorder(
        start_prompt="🎤",
        stop_prompt="🛑",
        key='recorder'
    )

with col_txt:
    prompt_texto = st.chat_input("Escribe tu duda aquí...")

# LÓGICA DE PROCESAMIENTO
if prompt_texto or audio_data:
    # Identificamos si es texto o voz
    if audio_data:
        prompt_usuario = "🎤 [Consulta por voz]"
        datos_para_gemini = [
            {"mime_type": "audio/wav", "data": audio_data['bytes']},
            "Analiza este audio y responde la duda sobre el inventario."
        ]
    else:
        prompt_usuario = prompt_texto
        datos_para_gemini = [prompt_texto]

    # Guardar y mostrar mensaje del usuario
    st.session_state.mensajes.append({"role": "user", "content": prompt_usuario})
    with st.chat_message("user"):
        st.markdown(prompt_usuario)

    # Respuesta de la IA
    if st.session_state.inventario_texto:
        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                try:
                    model = genai.GenerativeModel('models/gemini-2.5-flash')
                    
                    # Instrucción maestra con tus reglas de negocio
                    instruccion_maestra = f"""
                    Eres el asistente experto de Portland Quality Meats. 
                    REGLAS DE INTERPRETACIÓN:
                    - FS = Fresco (Fresh), FZ = Congelado (Frozen).
                    - #10 = 10 libras, #22 = 22 libras, 40lb = 40 libras.
                    - Si no hay marca en la línea del producto, di 'Sin marca'.
                    - Responde en el idioma en que recibas la pregunta (Español o Inglés).
                    - Sé preciso con los precios y marcas.

                    A tomar en cuenta, los nombres de los productos pueden variar, por ejemplo:
                    - Shoulder clod, puede estar escrito como top clod. 
                    - Shank puede estar escrito como foreshank.
                    - Etc.


                    INVENTARIO ACTUAL:
                    {st.session_state.inventario_texto}
                    """
                    
                    # Combinamos la instrucción con el contenido (texto o audio)
                    respuesta = model.generate_content([instruccion_maestra] + datos_para_gemini)
                    
                    texto_ia = respuesta.text
                    st.markdown(texto_ia)
                    st.session_state.mensajes.append({"role": "assistant", "content": texto_ia})
                    
                except Exception as e:
                    st.error(f"Error de conexión: {e}")
    else:
        st.warning("⚠️ No hay inventario cargado. Usa la barra lateral.")