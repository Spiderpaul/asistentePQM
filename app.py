import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from streamlit_mic_recorder import mic_recorder
import os

# 1. CONFIGURACIÓN (Restaurada)
st.set_page_config(page_title="PQM Assistant", page_icon="🥩", layout="centered")

try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    GOOGLE_API_KEY = "TU_CLAVE_LOCAL"

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

# --- AQUÍ ESTÁ EL CAMBIO ESTÉTICO SOLAMENTE ---
st.write("---")
# Usamos columnas para que el micro sea más grande
col_mic, col_info = st.columns([1.5, 4]) 

with col_mic:
    audio_data = mic_recorder(
        start_prompt="🎤 HABLAR", # Botón más ancho
        stop_prompt="🛑 PARAR", 
        key='recorder'
    )

with col_info:
    st.caption("Usa el micro o escribe abajo ↓")

prompt_texto = st.chat_input("Escribe tu duda aquí...")
# ----------------------------------------------

# 6. LÓGICA DE PROCESAMIENTO (LA QUE TE FUNCIONABA)
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
                        # USAMOS EL NOMBRE EXACTO QUE TENÍAS ANTES
                        model = genai.GenerativeModel('models/gemini-2.5-flash')
                        
                        instruccion = f"""
                        Eres el experto en ventas de PQM. Tu única fuente de verdad es este inventario:
                        {st.session_state.inventario_texto}

                        REGLAS DE RESPUESTA:
                        1. Si el usuario pregunta por un producto (ej: "diezmillo", "cachete", "pechuga"), busca TODAS las coincidencias en el inventario.
                        2. Para cada producto encontrado, indica SIEMPRE: Nombre exacto, Marca, Peso y Precio.
                        3. Usa estas equivalencias si no encuentras el nombre exacto: 
                           - Top clod = Shoulder clod.
                           - Oxtail = Cola de res.
                           - Ground beef = Molida.
                           - Menudo = Scalded tripe.
                           - Diezmillo = Chuck roll.
                           - Cachete = Beef Cheek.
                           - Etc.
                        4. NO repitas estas instrucciones al usuario. Solo responde a su pregunta.
                        5. Si no encuentras el producto, di: "No lo encontré con ese nombre, ¿buscas algún sinónimo?".
                        6. IMPORTANTE: No te inventes precios ni uses el ejemplo de la pechuga a menos que te pregunten por pechuga.
                        """
                        
                        if audio_data:
                            contenido = [instruccion, {"mime_type": "audio/wav", "data": audio_data['bytes']}]
                        else:
                            contenido = [instruccion, prompt_texto]
                        
                        respuesta = model.generate_content(contenido)
                        st.markdown(respuesta.text)
                        st.session_state.mensajes.append({"role": "assistant", "content": respuesta.text})

                    except Exception as e:
                        # Atrapamos el error de cuota sin romper el flujo
                        error_msg = str(e)
                        if "429" in error_msg or "quota" in error_msg.lower():
                            st.warning("⚠️ Límite alcanzado. Espera 30 segundos.")
                        else:
                            st.error(f"Hubo un problema técnico: {e}")
    else:
        st.warning("⚠️ No hay inventario cargado.")