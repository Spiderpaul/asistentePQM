import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from streamlit_mic_recorder import mic_recorder
import os

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="PQM Assistant", page_icon="🥩", layout="centered")

# 2. CONFIGURACIÓN DE SEGURIDAD (API KEY DESDE SECRETS)
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    GOOGLE_API_KEY = "TU_CLAVE_LOCAL_TEMPORAL"

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
    except Exception as e:
        return None

# 4. INICIALIZACIÓN
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

# 5. BARRA LATERAL
with st.sidebar:
    st.header("⚙️ Configuración")
    password = st.text_input("Clave de Admin", type="password")
    if password == "PQM2026":
        archivo_nuevo = st.file_uploader("Actualizar Inventario", type="pdf")
        if archivo_nuevo:
            st.session_state.inventario_texto = leer_pdf(archivo_nuevo)
            st.session_state.origen = "Carga Manual"
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

# 7. ÁREA FIJA INFERIOR (CONTROLES MEJORADOS)
st.write("---")
# Usamos columnas para que el botón de micro sea más grande y esté junto al texto
col_mic, col_info = st.columns([1.2, 4]) # Ajustamos el ancho para que el botón quepa bien

with col_mic:
    # Botón de micrófono más grande agregando texto
    audio_data = mic_recorder(
        start_prompt="🎤 HABLAR", 
        stop_prompt="🛑 PARAR", 
        key='recorder'
    )

with col_info:
    st.caption("Usa el micro o escribe abajo ↓")

prompt_texto = st.chat_input("Escribe tu duda aquí...")

# LÓGICA DE PROCESAMIENTO
if prompt_texto or audio_data:
    prompt_usuario = prompt_texto if prompt_texto else "🎤 [Consulta por voz]"
    
    st.session_state.mensajes.append({"role": "user", "content": prompt_usuario})
    with chat_container:
        with st.chat_message("user"):
            st.markdown(prompt_usuario)

    if st.session_state.inventario_texto:
        with chat_container:
            with st.chat_message("assistant"):
                with st.spinner("Consultando inventario..."):
                    try:
                        # USAMOS EL MODELO 1.5-FLASH QUE ES EL MÁS ESTABLE
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        
                        instruccion = f"""
                        Eres el asistente experto de PQM. 
                        REGLAS: FS=Fresco, FZ=Congelado, #10=10lb, #22=22lb.
                        IMPORTANTE: No muestres la lista completa de precios, solo responde a la pregunta que se te hace. 
                        Si no encuentras un producto, sugiere intentar con un sinónimo.
                        Sinónimos comunes:
                        -Top clod es shoulder clod. 
                        -Oxtail es cola de res o colita.
                        -Ground beef es carne molida.
                        -Scalded tripe es menudo.
                        
                        Si el usuario solo dice el nombre del producto (ej. "pechuga"), muestra todas las opciones con marca, peso y precio.
                        Responde en el idioma que te hablen basándote en:
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
                            st.warning("⚠️ **PQM Assistant está tomando un respiro.** \n\nHemos alcanzado el límite de consultas. Por favor, **espera 30 segundos** y vuelve a intentarlo. 🥩")
                        elif "safety" in error_msg.lower():
                            st.error("No puedo responder a eso por políticas de seguridad.")
                        else:
                            st.error(f"Hubo un problema técnico: {error_msg}")
    else:
        st.warning("⚠️ No hay inventario cargado.")