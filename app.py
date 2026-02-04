import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from streamlit_mic_recorder import mic_recorder
import os

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="PQM Assistant", page_icon="🥩", layout="centered")

# 2. CONFIGURACIÓN DE SEGURIDAD (API KEY)
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    GOOGLE_API_KEY = "TU_API_KEY_LOCAL" 

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
    except Exception:
        return None

# 4. INICIALIZACIÓN DE ESTADOS
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

# 5. BARRA LATERAL (ADMIN)
with st.sidebar:
    st.header("⚙️ Admin")
    password = st.text_input("Contraseña", type="password")
    if password == "PQM2026":
        archivo_nuevo = st.file_uploader("Subir PDF", type="pdf")
        if archivo_nuevo:
            st.session_state.inventario_texto = leer_pdf(archivo_nuevo)
            st.session_state.origen = "Manual"
            st.success("Inventario actualizado")
    st.divider()
    if st.button("Limpiar Chat"):
        st.session_state.mensajes = []
        st.rerun()

# 6. INTERFAZ DE CHAT
st.title("🥩 PQM Assistant")

# Contenedor de mensajes con scroll
chat_container = st.container()
with chat_container:
    for m in st.session_state.mensajes:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

# 7. ENTRADA FIJA (MICRO Y TEXTO)
st.write("---")
# Usamos columnas para que el micro esté junto al texto
c1, c2 = st.columns([1, 4])

with c1:
    # Botón más grande con texto para mejor agarre en móvil
    audio_data = mic_recorder(
        start_prompt="🎤 HABLAR", 
        stop_prompt="🛑 PARAR", 
        key='recorder'
    )

with c2:
    # El chat_input siempre se ancla al fondo
    prompt_texto = st.chat_input("Escribe tu duda aquí...")

# 8. LÓGICA DE PROCESAMIENTO
if prompt_texto or audio_data:
    prompt_visible = prompt_texto if prompt_texto else "🎤 [Consulta por voz]"
    
    st.session_state.mensajes.append({"role": "user", "content": prompt_visible})
    with chat_container:
        with st.chat_message("user"):
            st.markdown(prompt_visible)

    if st.session_state.inventario_texto:
        with chat_container:
            with st.chat_message("assistant"):
                with st.spinner("Buscando en inventario..."):
                    try:
                        # REGRESAMOS AL MODELO QUE TE FUNCIONABA
                        model = genai.GenerativeModel('models/gemini-2.0-flash')
                        
                        instruccion = f"""
                        Eres el asistente experto de PQM. 
                        REGLAS: FS=Fresco, FZ=Congelado, #10=10lb, #22=22lb.
                        SINOPSIS/SINÓNIMOS:
                        - Top clod = Shoulder clod.
                        - Oxtail = Cola de res o colita.
                        - Ground beef = Carne molida.
                        - Scalded tripe = Menudo.
                        
                        Si solo dicen un producto (ej. "pechuga"), da TODA la info: marca, peso y precio.
                        Si no encuentras algo, sugiere un sinónimo o pregunta para aclarar.
                        Responde en el idioma que te hablen basándote en este inventario:
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
                            st.warning("⚠️ **Límite de velocidad.** Espera unos segundos y vuelve a intentar. 🥩")
                        else:
                            st.error(f"Error técnico: {error_msg}")
    else:
        st.warning("⚠️ No hay inventario cargado.")