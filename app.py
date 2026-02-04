import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from streamlit_mic_recorder import mic_recorder
import os

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="PQM Assistant", page_icon="🥩", layout="centered")

# 2. CONFIGURACIÓN DE SEGURIDAD
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    GOOGLE_API_KEY = "TU_CLAVE_LOCAL"

genai.configure(api_key=GOOGLE_API_KEY)

# 3. FUNCIONES DE APOYO
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

# 4. INICIALIZACIÓN
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

if "inventario_texto" not in st.session_state:
    ruta_base = "data/precios.pdf"
    if os.path.exists(ruta_base):
        st.session_state.inventario_texto = leer_pdf(ruta_base)
        st.session_state.origen = "GitHub"
    else:
        st.session_state.inventario_texto = None
        st.session_state.origen = "Ninguno"

# 5. BARRA LATERAL
with st.sidebar:
    st.header("⚙️ Admin")
    password = st.text_input("Clave", type="password")
    if password == "PQM2026":
        archivo_nuevo = st.file_uploader("Actualizar Inventario", type="pdf")
        if archivo_nuevo:
            st.session_state.inventario_texto = leer_pdf(archivo_nuevo)
            st.success("¡Actualizado!")
    st.divider()
    if st.button("Borrar historial"):
        st.session_state.mensajes = []
        st.rerun()

# 6. INTERFAZ DE CHAT
st.title("🥩 PQM Assistant")

chat_container = st.container()
with chat_container:
    for m in st.session_state.mensajes:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

# 7. ÁREA FIJA INFERIOR (BOTÓN GRANDE Y ALINEADO)
st.write("---")
col_mic, col_info = st.columns([1.5, 4]) 

with col_mic:
    # Botón más grande para móvil
    audio_data = mic_recorder(
        start_prompt="🎤 HABLAR", 
        stop_prompt="🛑 DETENER", 
        key='recorder'
    )

with col_info:
    st.caption("Presiona 'Hablar' o escribe abajo ↓")

prompt_texto = st.chat_input("Escribe tu duda aquí...")

# 8. LÓGICA DE PROCESAMIENTO
if prompt_texto or audio_data:
    prompt_usuario = prompt_texto if prompt_texto else "🎤 [Consulta por voz]"
    
    st.session_state.mensajes.append({"role": "user", "content": prompt_usuario})
    with chat_container:
        with st.chat_message("user"):
            st.markdown(prompt_usuario)

    if st.session_state.inventario_texto:
        with chat_container:
            with st.chat_message("assistant"):
                with st.spinner("Consultando..."):
                    try:
                        # CAMBIO CLAVE: Nombre de modelo simplificado para evitar el 404
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        
                        instruccion = f"""
                        Eres el asistente de PQM. REGLAS: FS=Fresco, FZ=Congelado, #10=10lb, #22=22lb.
                        No muestres la lista completa. Si no encuentras algo, sugiere un sinónimo.
                        SINÓNIMOS: Top clod=Shoulder clod, Oxtail=Cola, Ground beef=Carne molida, Menudo=Scalded tripe.
                        Si solo dicen un producto (ej. "pechuga"), da marca, peso y precio de todas las opciones.
                        Responde en el idioma del usuario basándote en:
                        {st.session_state.inventario_texto}
                        """
                        
                        if audio_data:
                            contenido = [instruccion, {"mime_type": "audio/wav", "data": audio_data['bytes']}]
                        else:
                            contenido = [instruccion, prompt_texto]
                        
                        respuesta = model.generate_content(contenido)
                        st.markdown(respuesta.text)
                        st.session_state.mensajes.append({"role": "assistant", "content": respuesta.text})

                    except Exception as e:
                        error_msg = str(e)
                        if "429" in error_msg or "quota" in error_msg.lower():
                            st.warning("⚠️ Límite alcanzado. Espera 30 segundos.")
                        elif "404" in error_msg:
                            st.error("Error de modelo: Intenta de nuevo en un momento.")
                        else:
                            st.error(f"Error técnico: {error_msg}")
    else:
        st.warning("⚠️ Carga el inventario en la barra lateral.")