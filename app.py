import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from streamlit_mic_recorder import mic_recorder
import os

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="PQM Assistant", page_icon="🥩", layout="centered")

# 2. CONFIGURACIÓN DE SEGURIDAD (API KEY DESDE SECRETS)
# Cambiamos esto para que use los Secrets que configuramos en Streamlit Cloud
try:
    # Intenta leer la clave desde los "Secrets" de Streamlit Cloud
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    # Si falla (por ejemplo, cuando estás probando en tu PC local)
    # Aquí puedes poner tu clave temporalmente solo para pruebas locales
    # Pero asegúrate de no subirla a GitHub
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

# Contenedor para los mensajes (esto ayuda a que el scroll funcione mejor)
chat_container = st.container()

with chat_container:
    for m in st.session_state.mensajes:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

# 7. ENTRADA DE USUARIO (EL ORDEN ES CLAVE AQUÍ)
# Ponemos el micrófono arriba del input de texto
st.write("---")
audio_data = mic_recorder(start_prompt="🎤 Grabar pregunta", stop_prompt="🛑 Detener", key='recorder')

# El chat_input de Streamlit se va AUTOMÁTICAMENTE al fondo de la pantalla
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
                        model = genai.GenerativeModel('models/gemini-2.5-flash')
                        
                        instruccion = f"""
                        Eres el asistente experto de PQM. 
                        REGLAS: FS=Fresco, FZ=Congelado, #10=10lb, #22=22lb.
                        IMPORTANTE: No muestres la lista completa de precios, solo responde a la pregunta que se te hace. 
                        Si no encuentras un producto, puedes decir que no lo encontraste, que intenten con un sinónimo del producto.
                        Los productos pueden tener variaciones en sus nombres, por ejemplo:
                        -Top clod, es shoulder clod. 
                        -Oxtail, es cola de res o colita.
                        -Ground beef, es carne molida o molida de res.
                        -Scalded tripe, es menudo.
                        -Etc.
                        Tienes libertad para preguntar si se refieren a un producto u otro si no estás seguro de que producto es el que se busca.

                        Responde en el idioma que te hablen basándote en:
                        {st.session_state.inventario_texto}
                        """
                        
                        # Preparamos el contenido mezclando instrucción + audio/texto
                        if audio_data:
                            contenido = [instruccion, {"mime_type": "audio/wav", "data": audio_data['bytes']}]
                        else:
                            contenido = [instruccion, prompt_texto]
                        
                        respuesta = model.generate_content(contenido)
                        st.markdown(respuesta.text)
                        st.session_state.mensajes.append({"role": "assistant", "content": respuesta.text})
                    except Exception as e:
                        st.error(f"Error: {e}")
    else:
        st.warning("⚠️ No hay inventario cargado.")