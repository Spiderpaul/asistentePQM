import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from streamlit_mic_recorder import mic_recorder
import os

# 1. CONFIGURACIÓN
st.set_page_config(page_title="PQM Assistant", page_icon="🥩", layout="centered")

try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    GOOGLE_API_KEY = "TU_CLAVE_HERE" # Reemplaza con tu nueva Key si es necesario

genai.configure(api_key=GOOGLE_API_KEY)

# 2. FUNCIONES
def leer_pdf(archivo):
    try:
        lector = PdfReader(archivo)
        texto = ""
        for pagina in lector.pages:
            t = pagina.extract_text()
            if t: texto += t + "\n"
        return texto
    except:
        return None

# 3. ESTADOS
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

if "inventario_texto" not in st.session_state:
    ruta_base = "data/precios.pdf"
    if os.path.exists(ruta_base):
        st.session_state.inventario_texto = leer_pdf(ruta_base)
    else:
        st.session_state.inventario_texto = None

# 4. SIDEBAR
with st.sidebar:
    st.header("⚙️ Configuración")
    password = st.text_input("Clave de Admin", type="password")
    if password == "PQM2026":
        archivo_nuevo = st.file_uploader("Actualizar Inventario", type="pdf")
        if archivo_nuevo:
            st.session_state.inventario_texto = leer_pdf(archivo_nuevo)
            st.success("¡Actualizado!")
    st.divider()
    if st.button("Borrar historial"):
        st.session_state.mensajes = []
        st.rerun()

# 5. INTERFAZ
st.title("🥩 PQM Assistant")

chat_container = st.container()

with chat_container:
    for m in st.session_state.mensajes:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

st.write("---")
col_mic, col_info = st.columns([1.5, 4]) 

with col_mic:
    audio_data = mic_recorder(
        start_prompt="🎤 HABLAR", 
        stop_prompt="🛑 PARAR", 
        key='recorder'
    )

with col_info:
    st.caption("Usa el micro o escribe abajo ↓")

prompt_texto = st.chat_input("Escribe tu duda aquí...")

# 6. LÓGICA DE PROCESAMIENTO
if prompt_texto or audio_data:
    # 1. Determinar el prompt
    prompt_usuario = prompt_texto if prompt_texto else "🎤 [Consulta por voz]"
    
    # 2. Guardar y mostrar lo que tú dijiste/escribiste
    st.session_state.mensajes.append({"role": "user", "content": prompt_usuario})
    
    # 3. PROCESAR CON LA IA
    if st.session_state.inventario_texto:
        with st.chat_message("assistant"): # Quitamos el container externo para probar
            with st.spinner("Buscando en inventario..."):
                try:
                    # Configuración del modelo 2.5 Flash
                    model = genai.GenerativeModel(model_name='models/gemini-2.5-flash')
                    
                    # (Tus instrucciones de carnicería aquí...)
                    instruccion = f"ERES UN BUSCADOR DE PRECIOS. INVENTARIO: {st.session_state.inventario_texto}"
                    
                    if audio_data:
                        contenido = [instruccion, {"mime_type": "audio/wav", "data": audio_data['bytes']}]
                    else:
                        contenido = [instruccion, prompt_texto]
                    
                    # Generar respuesta
                    respuesta = model.generate_content(contenido)
                    
                    # MOSTRAR Y GUARDAR RESPUESTA
                    st.markdown(respuesta.text)
                    st.session_state.mensajes.append({"role": "assistant", "content": respuesta.text})
                    
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        st.warning("No hay inventario cargado.")