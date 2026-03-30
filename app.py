import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from streamlit_mic_recorder import mic_recorder
from openai import OpenAI
import streamlit as st
from PIL import Image
import os
import tempfile
import subprocess
import streamlit as st
import base64

# =======================
# CONFIGURACIÓN GENERAL
# =======================

# Guardar el documento PDF
preciosURL = "data/PQM_033026.pdf"


# Cargar la imagen del logo
try:
    img_logo = Image.open("assets/PQMLogo.png")
except:
    img_logo = "🥩"

st.set_page_config(
    page_title="PQM Assistant",
    page_icon=img_logo,
    layout="centered"
)

# Ocultar marca de Streamlit
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY")
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY")

genai.configure(api_key=GOOGLE_API_KEY)

# Flag para debug (déjalo en False en producción)
DEBUG_AUDIO = False


# =======================
# FUNCIONES
# =======================

def leer_pdf(archivo):
    """Lee un PDF y devuelve todo el texto"""
    try:
        lector = PdfReader(archivo)
        texto = "\n".join(
            pagina.extract_text()
            for pagina in lector.pages
            if pagina.extract_text()
        )
        return texto
    except Exception as e:
        st.error(f"❌ Error al leer PDF: {e}")
        return None


def convertir_a_wav(audio_bytes):
    """
    Convierte audio WebM a WAV 16kHz mono (ideal para Whisper)
    Requiere ffmpeg instalado en el sistema
    """
    webm_file = tempfile.NamedTemporaryFile(delete=False, suffix=".webm")
    wav_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")

    webm_file.write(audio_bytes)
    webm_file.close()

    command = [
        "ffmpeg",
        "-y",
        "-i", webm_file.name,
        "-ac", "1",
        "-ar", "16000",
        wav_file.name
    ]

    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    os.unlink(webm_file.name)
    return wav_file.name


def transcribir_audio(audio_bytes):
    """Transcribe audio usando Whisper (OpenAI)"""
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)

        wav_path = convertir_a_wav(audio_bytes)

        if DEBUG_AUDIO:
            st.info(f"Audio convertido a WAV: {wav_path}")

        with open(wav_path, "rb") as audio_file:
            result = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="es"
            )

        os.unlink(wav_path)

        texto = result.text.strip()

        if not texto:
            return None

        return texto

    except Exception as e:
        st.error(f"❌ Error en Whisper: {e}")
        return None


def procesar_consulta(consulta, inventario_texto):
    """Consulta el inventario usando Gemini"""
    try:
        model = genai.GenerativeModel(
            model_name="models/gemini-2.0-flash"
        )

        prompt = f"""
Eres un asistente experto en consultar el inventario de Portland Quality Meats.

INVENTARIO:
{inventario_texto}

INSTRUCCIONES:
- Busca TODOS los productos relacionados con la consulta
- Muestra FZ o FS (si existe), nombre, marca (Si existe), peso (Si existe), costo y precio al cliente, poniendo siempre el signo $ antes de los números
- FZ significa congelado.
- FS significa fresco.
- Si no existe marca, no es necesario escrir nada, solo el nombre del producto
- Algunos productos son de peso fijo y tienen el peso en libras justo en frente del nombre, por ejemplo "Sausage Party 10 lb" en esos casos es importante mostrar el peso
- Algunos pesos en vez de decir "10 lb", dicen "10#" o "#10", por ejemplo "Bacon Economy #10" que es de 10 lb
- Si en vez de precio o costo ves un espacio vació, o que dice DP o Fernando, escribe N/A 
- Si en vez de precio o costo ves que dice OUT, escribe OUT
- Si ves que un producto tiene un precio muy elevado en comparación con otros similares, posiblemente porque faltó poner un punto o algún error de captura, sugiere al cliente que revise ese precio porque podría ser un error
- Si hay varias opciones, muéstralas todas
- Si no existe exacto, sugiere similares
- Los camarones Easy Peel White (EZ Peel) son de peso fijo y pesan 20 lb
- El resto de camarones indican el peso junto la descripción, por ejemplo "HEAD ON  24 lb", "PDT ON and COOKED 10 lb", etc.
- El queso Jack, Cheeddar, Mozzarella, 80/10/10/, Mix o (50/50), feather o fancy, cuestan regulamente lo mismo y pesan lo mismo "20 lb la caja de 4 piezas o bolsas de 5 lb"
- Cualquier queso en block o bloque, no tienen peso fijo y suelen tener un precio menor
- La lista contiene errores de captura, por ejemplo "scaladed" en vez de "scalded", toma en cuenta esos pequeños errores e interpretalos correctamente
- Solo muestra al usuario la columna que dice "Costumer Price" como precio al cliente, no muestres la columna "This Week Price" porque ese es el precio de compra, no de venta.
- Si el usuario te pide específicamente que muestres el costo del producto, entonces si puedes mostrar la cantidad que se encuentra en la columna "This Week Price"

Importante: 
Te comparto productos que no están en el PDF pero que se están manejando:
- Sazonador Adobo: $66.99
- Contenedor #1: $24.99
- Roma Tomato (tomate): 59.99
- Tomatillo Peeled (flesh): $59.99
- Cilantro: 25.99
- Cilantro en pieza: $0.69
- Jalapeño fresco: %66.99
- Mexican onion: $19.99
- White Onion: $31.99
- Red Onion: $14.99
- Yellow Onion: $11.99
- Purple Onion: $14.99
- Avocado: $49.99
- Radish (rábano): $34.99
- Carrot: $24.99
- Bell Pepper Green: $54.99
- Bell Pepper Red: $45.99
- Serrano pepper: 66.99
- Limes/Lemon: $94.99
- Lettuce: $39.99
- Cucumber (pepino): $65.99
- Nopal: $38.99
- Potatoe: $14.99
- Habanero: 6.99
- Orange: $28.99
- Canela: $8.79
- Chile Serrano: $44.99
- Calabaza mexicana_ 24.99
- Chayote: $39.99
- Sangria: $8.79
- Queso Cotija por pieza: $6.55
- Queso fresco por pieza: $39.99
- Salsa Enchilada Victoria: $52.99


Importante: Ignora el precio del octopus 6/8 que aparece en el documento PDF, su precio ha subido, te comparto el nuevo precio.
- Octopus 6/8: $4.59 




FORMATO DE RESPUESTA:
Al mostrar precios, usa este formato:
* FZ o FS, **Producto** marca: Precio: **X.XX**
Si el usuario te pide que especifiques el costo del producto, puedes agregarlo así:
* FZ o FS, **Producto** marca: Costo: X.XX Precio: **X.XX**
(NO uses backticks ` ni comillas simples/dobles alrededor de los números)


IMPORTANTE: 
- El usuario puede solo mencionar el nombre del producto sin decir nada más, por ejemplo "Chuck Roll". En ese caso, busca y muestra TODOS los precios y presentaciones disponibles para ese producto.
- El usuario muchas veces mencionará el producto de forma imprecisa o de forma coloquial, por ejemplo "Diezmillo" en lugar de "Diezmillo". Asegúrate de entender a qué producto se refiere y muéstrale todas las opciones disponibles.
- Intenta ser directo, claro y breve en tus respuestas si las preguntas son simples y claras, pero si tienes dudas sobre lo que intenta pedir el usuario, puedes preguntar o dar información extra al usuario.  

DICCIONARIO: (El usuario puede usar palabras en inglés o en español, coloquiales o muy imprecisas, aquí te pongo algunos ejemplos)
- Chuck roll = Diezmillo, chuck, fajitas de res
- Cheek = cachete, chek
- Feet Cut = pata SK, pata Su Karne, pata cortada
- Ground beef patty = molida, hamburguesa, amburguesa, ground party o ground beef party
- Knuckle Peeled = peel knucles, peel nucles, knuckles, etc.
- Marrow gut = tripa suelta, tripa
- Oxtail = cola de res, colita
- Shank cut = caldo cut, caldo, shank cortado
- shank = Foreshank, chamberete, chamorro
- Shank SW (Swift) = shank 5 star
- Top clod = shoulder clod, shoulder cloud
- Honeycomb = panal
- Honeycomb A & A = honeycomb azul
- Honeycomb IBP = honeycomb chico
- Omassum = librillo
- Scalded IBP = menudo regular 
- Scalded A & A = menudo verde
- Cornish hen = godorniz, codorniz
- Drumstiks = piernitas de pollo, piernitas
- Diced pork butt = puerco picado
- Bacon 14-16 #1 = bacon #1, tocino #1
- Bacon Economy #10 = bacon #2, tocino #2
- Bacon diced cooked = bacon cocido, tocino cocido, bacon cook, tocino cook, bycon, baicon
- Ham 4x6 = jamón, jamon, ham, jam
- Links (Pork) = sausage, pork links, sausage pork
- Sausage party = sausage patties, salchichas party, sausage patty
- T-Fillet 3-5 IVF = filete 3-5 individual
- Thigh meat boneless fresh (pollo) = x fresh, t meat fresh, tmeat fresh, x fresco, t meat fresco, tmeat fresco
- Thigh meat boneless frozen (pollo) = x (a veces el usuario escribe solo una x), tmeat, t meat, x frozen, t meat frozen, tmeat frozen
- Breast meat boneless fresh (pollo) = fresca, pechuga fresca
- Thigh Meat Boneles Wayne Wayne = wayne, tmeat wayne, thigh wayne
- thigh meat boneless P170 = p170, wayne p170, tmeat p170
- Gizzards = molleja, grizzarrds (tiene peso fijo de 30lb)
- Flap Meat = flap, ranchera, arrachera
- Shoulder clod = Top clod, clod, espaldilla
- Bottom Round flat = palomilla
- Willota = Guilota
- Cod Battered 3 Oz16/24 = pescado empanizado
- Tortilla taco #4 blanca y am = Tortilla chip, tortilla chip amarilla
- Margarine = margarina, mantequilla
- Dish Detergent = soap, jabón, detergente, dish
- 26/30 broke = 26/30 PDT ON Cooked
- Boneless stew = Beef for stew
- Chuletón = Chuck bone in
- Towel Roll Natural 8" = Papel para manos
- Towel Centerpull 2ply = Papel para dispensador
- Toilet Tissue 9” 2ply = Papel para baño



(Los usuarios pueden usar palabras muy confusas a veces, puedes preguntarles si se refieren a algún producto que te parezca que coincida) 

CONSULTA:
{consulta}

Responde claro y directo.
"""

        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        if "429" in str(e):
            return "⏳ Límite de API alcanzado. Intenta en un minuto."
        return f"❌ Error: {e}"


# =======================
# ESTADO
# =======================

if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

if "inventario_texto" not in st.session_state:
    ruta = preciosURL
    if os.path.exists(ruta):
        st.session_state.inventario_texto = leer_pdf(ruta)
    else:
        st.session_state.inventario_texto = None

if "audio_procesado" not in st.session_state:
    st.session_state.audio_procesado = None


# =======================
# SIDEBAR
# =======================

with st.sidebar:
    st.header("⚙️ Configuración")

    password = st.text_input("Clave Admin", type="password")

    if password == "PQM2026":
        archivo = st.file_uploader(
            "Actualizar Inventario",
            type="pdf"
        )
        if archivo:
            st.session_state.inventario_texto = leer_pdf(archivo)
            st.success("✅ Inventario actualizado")

    st.divider()

    st.info(
        "🎤 Habla claro\n"
        "Ejemplos:\n"
        "- Precio del ribeye\n"
        "- Cuánto cuesta el diezmillo"
    )

    if st.button("🗑️ Borrar historial"):
        st.session_state.mensajes.clear()
        st.session_state.audio_procesado = None
        st.rerun()


# =======================
# INTERFAZ
# =======================

st.title("PQM Assistant")
st.caption("Consulta precios del inventario")

for msg in st.session_state.mensajes:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

st.write("---")

col1, col2 = st.columns([1, 2])

with col1:
    audio_data = mic_recorder(
        start_prompt="Hablar",
        stop_prompt="Parar",
        key="recorder"
    )

with col2:
    texto_input = st.chat_input("Escribe tu consulta...")


# =======================
# VALIDACIÓN INVENTARIO
# =======================

if not st.session_state.inventario_texto:
    st.warning("⚠️ No hay inventario cargado.")
    st.stop()


# =======================
# TEXTO
# =======================

if texto_input:
    st.session_state.mensajes.append({
        "role": "user",
        "content": texto_input
    })

    with st.spinner("🔍 Buscando..."):
        respuesta = procesar_consulta(
            texto_input,
            st.session_state.inventario_texto
        )

    st.session_state.mensajes.append({
        "role": "assistant",
        "content": respuesta
    })

    st.rerun()


# =======================
# VOZ
# =======================

if audio_data:
    audio_id = hash(audio_data["bytes"])

    if st.session_state.audio_procesado != audio_id:
        st.session_state.audio_procesado = audio_id

        if len(audio_data["bytes"]) < 5000:
            st.warning("⚠️ Audio muy corto")
        else:
            with st.spinner("🎧 Transcribiendo..."):
                texto = transcribir_audio(audio_data["bytes"])

            if not texto:
                st.error("❌ No se pudo entender el audio")
            else:
                st.session_state.mensajes.append({
                    "role": "user",
                    "content": f"🎤 **Dijiste:** \"{texto}\""
                })

                with st.spinner("🔍 Buscando..."):
                    respuesta = procesar_consulta(
                        texto,
                        st.session_state.inventario_texto
                    )

                st.session_state.mensajes.append({
                    "role": "assistant",
                    "content": respuesta
                })

                st.rerun()
