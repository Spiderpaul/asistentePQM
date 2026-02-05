import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from streamlit_mic_recorder import mic_recorder
import os

# 1. CONFIGURACIÓN
st.set_page_config(page_title="PQM Assistant", page_icon="🥩", layout="centered")

GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY", "TU_CLAVE_HERE")
genai.configure(api_key=GOOGLE_API_KEY)

# 2. FUNCIONES
def leer_pdf(archivo):
    try:
        lector = PdfReader(archivo)
        texto = "\n".join(pagina.extract_text() for pagina in lector.pages if pagina.extract_text())
        return texto
    except Exception as e:
        st.error(f"Error al leer el PDF: {e}")
        return None

def procesar_consulta(user_input, inventario_texto, es_audio=False, audio_bytes=None):
    """Procesa la consulta del usuario usando Gemini"""
    try:
        model = genai.GenerativeModel(model_name='models/gemini-2.0-flash')
        
        # Instrucción MÁS ESPECÍFICA para audio
        if es_audio:
            instruccion = f"""Eres un asistente experto en productos cárnicos. El usuario te está haciendo una consulta POR VOZ.

IMPORTANTE: 
- Primero TRANSCRIBE exactamente lo que el usuario dice
- Luego busca en el inventario basándote en esa transcripción
- Si el usuario pregunta por un producto específico, muestra TODAS las opciones disponibles
- Si el usuario solo pone el nombre del producto, por ejemplo "diezmillo", busca y muestra TODOS los precios y presentaciones disponibles

INVENTARIO:
{inventario_texto}

FORMATO DE RESPUESTA:
1. "Escuché: [transcripción de lo que dijo el usuario]"
2. [Respuesta con los productos y precios encontrados]

Si no logras entender el audio, di: "No pude escuchar bien, ¿podrías repetir o escribir tu consulta?"
"""
        else:
            instruccion = f"""Eres un asistente experto en consultar inventarios y precios de productos cárnicos.

INVENTARIO DISPONIBLE:
{inventario_texto}

INSTRUCCIONES:
- Si te preguntan por un producto, busca TODOS los relacionados
- Muestra TODOS los precios y presentaciones disponibles
- Sé específico y claro

Usuario pregunta:
"""
        
        if es_audio and audio_bytes:
            contenido = [
                instruccion,
                {
                    "mime_type": "audio/webm",
                    "data": audio_bytes
                }
            ]
        else:
            contenido = [instruccion + f"\n{user_input}"]
        
        response = model.generate_content(contenido)
        return response.text
    
    except Exception as e:
        error_str = str(e)
        if "429" in error_str:
            return "⏳ Límite alcanzado. Espera 1 minuto o escribe tu consulta."
        return f"❌ Error: {error_str}"

# 3. ESTADOS
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

if "inventario_texto" not in st.session_state:
    ruta_base = "data/precios.pdf"
    if os.path.exists(ruta_base):
        st.session_state.inventario_texto = leer_pdf(ruta_base)
    else:
        st.session_state.inventario_texto = None

if "audio_procesado" not in st.session_state:
    st.session_state.audio_procesado = None

# 4. SIDEBAR
with st.sidebar:
    st.header("⚙️ Configuración")
    password = st.text_input("Clave de Admin", type="password")
    if password == "PQM2026":
        archivo_nuevo = st.file_uploader("Actualizar Inventario", type="pdf")
        if archivo_nuevo:
            st.session_state.inventario_texto = leer_pdf(archivo_nuevo)
            st.success("¡Inventario actualizado!")
    
    st.divider()
    st.subheader("💡 Consejos para usar el micrófono:")
    st.info("""
    1. Mantén presionado el botón mientras hablas
    2. Habla claro y cerca del micrófono
    3. Espera 1 segundo antes de soltar
    4. Di frases cortas y específicas
    
    Ejemplo: "Cuánto cuesta el diezmillo"
    """)
    
    if st.button("🗑️ Borrar historial"):
        st.session_state.mensajes.clear()
        st.session_state.audio_procesado = None
        st.rerun()

# 5. INTERFAZ
st.title("🥩 PQM Assistant")
st.caption("Consulta precios y productos del inventario")

# Mostrar historial
for m in st.session_state.mensajes:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# 6. ENTRADA
st.write("---")

# MEJORAR LA UI DEL MICRÓFONO
#col1, col2 = st.columns([2, 3])

#with col1:
#    st.markdown("### 🎤 Consulta por voz")
#    audio_data = mic_recorder(
#       start_prompt="▶️ Mantén presionado y habla", 
#        stop_prompt="⏹️ Suelta para enviar",
#        just_once=False,
#        use_container_width=True,
#        key='recorder'
#    )

#with col2:
#    st.markdown("### ✍️ O escribe aquí")
#    st.caption("El texto suele ser más preciso")

# Interfaz simplificada solo texto
st.markdown("### ✍️ Escribe tu consulta")

prompt_texto = st.chat_input("Escribe tu consulta (ej: precio del diezmillo)...")

# 7. VALIDACIÓN
if not st.session_state.inventario_texto:
    st.warning("⚠️ No hay inventario cargado.")
    st.stop()

# 8. PROCESAMIENTO DE TEXTO
if prompt_texto:
    st.session_state.mensajes.append({
        "role": "user", 
        "content": prompt_texto
    })
    
    with st.spinner("🔍 Buscando..."):
        respuesta = procesar_consulta(
            prompt_texto, 
            st.session_state.inventario_texto,
            es_audio=False
        )
    
    st.session_state.mensajes.append({
        "role": "assistant", 
        "content": respuesta
    })
    
    st.rerun()

# 9. PROCESAMIENTO DE VOZ
#if audio_data:
#    audio_id = hash(audio_data['bytes'])
#    
#    if st.session_state.audio_procesado != audio_id:
#        st.session_state.audio_procesado = audio_id
#        
#        # Validación mejorada
#        tamaño = len(audio_data['bytes'])
#        
#        if tamaño < 5000:  # Menos de 5KB probablemente está vacío
#            st.warning("⚠️ Audio muy corto. Mantén presionado el botón mientras hablas y suéltalo al terminar.")
#        elif tamaño > 5000000:  # Más de 5MB es sospechoso
#            st.warning("⚠️ Audio muy largo. Intenta hacer consultas más cortas.")
#        else:
#            st.session_state.mensajes.append({
#                "role": "user", 
#                "content": f"🎤 *[Consulta por voz - {tamaño/1000:.1f}KB]*"
#            })
#            
#            with st.spinner("🎧 Transcribiendo y buscando..."):
#                respuesta = procesar_consulta(
#                    None, 
#                    st.session_state.inventario_texto,
#                    es_audio=True,
#                    audio_bytes=audio_data['bytes']
#                )
#            
#            st.session_state.mensajes.append({
#                "role": "assistant", 
#                "content": respuesta
#            })
#           
#            st.rerun()