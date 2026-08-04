import streamlit as st
import json
import os
from agent_history_users import DynamicExecutor, run_refinement, run_story_writer

# Configuración de la página (Cumpliendo con mejores prácticas de Streamlit)
st.set_page_config(
    page_title="Generador de historias de usuario", 
    page_icon=":material/smart_toy:",
    layout="centered"
)

# Título y descripción (Cumpliendo con Sentence Case)
st.title("Generador de historias de usuario 🤖")
st.markdown(
    """
    **¡Bienvenido al refinador inteligente de historias de usuario!**  
    Aquí podrás definir tu necesidad, responder preguntas clave de refinamiento y obtener tu Historia de Usuario final de forma totalmente conversacional en un solo chat.
    
    Este agente utiliza los principios **INVEST**, desglosa los criterios de aceptación en formato **BDD** (*Dado que / Cuando / Entonces*) y **admite el análisis de mockups o imágenes de diseños** para complementar tus requerimientos de forma multimodal.
    """
)

# Inicializa el objeto de mensajes en la sesión
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "¡Hola! Soy tu asistente para la creación de Historias de Usuario. 🚀\n\nCuéntame, **¿cuál es la necesidad o funcionalidad de negocio que deseas desarrollar?** (Nota: Sube un diseño o mockup en la barra lateral *solo si dispones de uno*, esto es totalmente opcional. Puedes continuar usando únicamente texto si lo prefieres)."
        }
    ]

if "chat_step" not in st.session_state:
    st.session_state.chat_step = "need"  # Choices: "need", "answers", "done"

if "raw_input" not in st.session_state:
    st.session_state.raw_input = ""

# Menú lateral (Sidebar)
with st.sidebar:
    st.image("https://img.icons8.com/?size=100&id=103790&format=png&color=000000", width=100)
    st.subheader("Configuración de IA 🤖")
    
    # Selector de Proveedor
    provider = st.selectbox(
        "Proveedor de IA",
        ["Google Gemini", "OpenAI", "Anthropic Claude"],
        index=0
    )
    
    # Modelos y placeholders según el proveedor
    if provider == "Google Gemini":
        models = ["gemini-1.5-flash", "gemini-2.5-flash", "gemini-1.5-pro"]
        default_index = 0
        key_placeholder = "Escribe tu Google API Key..."
        key_url = "https://aistudio.google.com/"
        env_var_name = "GOOGLE_API_KEY"
    elif provider == "OpenAI":
        models = ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]
        default_index = 0
        key_placeholder = "Escribe tu OpenAI API Key..."
        key_url = "https://platform.openai.com/api-keys"
        env_var_name = "OPENAI_API_KEY"
    else:  # Anthropic Claude
        models = ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"]
        default_index = 0
        key_placeholder = "Escribe tu Anthropic API Key..."
        key_url = "https://console.anthropic.com/"
        env_var_name = "ANTHROPIC_API_KEY"
        
    model_name = st.selectbox("Modelo", models, index=default_index)
    
    # Intentar obtener la clave desde las variables de entorno como valor inicial
    default_key = os.environ.get(env_var_name, "")
    
    api_key = st.text_input(
        "Clave de API (API Key)",
        value=default_key,
        type="password",
        placeholder=key_placeholder,
        help=f"Puedes obtener tu clave de API aquí: {key_url}"
    )
    
    st.divider()
    
    st.subheader("📐 Entrada de Diseño / Imagen")
    
    # Selector de archivos de imagen (Mockup o captura)
    uploaded_file = st.file_uploader(
        "Sube una captura o mockup (opcional)",
        type=["png", "jpg", "jpeg"],
        help="Sube una captura de pantalla, bosquejo o diseño de la funcionalidad para que la IA la analice al generar la HU."
    )
    
    image_bytes = None
    image_type = None
    if uploaded_file is not None:
        image_bytes = uploaded_file.getvalue()
        image_type = uploaded_file.type
        # Mostrar preview del diseño subido en el sidebar
        st.image(uploaded_file, caption="Diseño adjunto listo para analizar 🖼️", use_container_width=True)
    
    st.divider()
    
    st.subheader("📄 Archivo de Apoyo (opcional)")
    
    # Selector de archivos de texto o código de apoyo
    uploaded_doc = st.file_uploader(
        "Sube un archivo de apoyo (.txt, .md, .html)",
        type=["txt", "md", "html"],
        help="Sube un archivo de texto, plantilla de markdown o código HTML que sirva de base o referencia para tu HU."
    )
    
    doc_content = None
    doc_name = None
    if uploaded_doc is not None:
        doc_name = uploaded_doc.name
        try:
            doc_content = uploaded_doc.getvalue().decode("utf-8")
            st.success(f"Archivo de apoyo cargado: `{doc_name}` 📄")
        except Exception as e:
            st.error(f"Error al leer el archivo de apoyo: {str(e)}")
            
    st.divider()
    
    # Mostrar el estado actual
    st.info(
        f"**Estado actual:**\n"
        f"Paso: {st.session_state.chat_step.upper()}\n\n"
        f"**Modelo activo:**\n"
        f"{model_name}"
    )
    
    # Advertencia si falta la API Key
    if not api_key:
        st.warning("⚠️ Ingresa tu API Key en la parte superior para habilitar el chat.")
    
    # Botón de reiniciar
    if st.button("Reiniciar conversación 🔄", use_container_width=True):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "¡Hola! Soy tu asistente para la creación de Historias de Usuario. 🚀\n\nCuéntame, **¿cuál es la necesidad o funcionalidad de negocio que deseas desarrollar?** (Nota: Sube un diseño o mockup en la barra lateral *solo si dispones de uno*, esto es totalmente opcional. Puedes continuar usando únicamente texto si lo prefieres)."
            }
        ]
        st.session_state.chat_step = "need"
        st.session_state.raw_input = ""
        st.rerun()

# Muestra el historial de mensajes en pantalla
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Capturar y actuar ante la acción del usuario
if prompt := st.chat_input("Escribe tu respuesta aquí..."):
    if not api_key:
        st.error("⚠️ Para poder interactuar con el asistente, primero debes ingresar tu API Key en la barra lateral izquierda.")
        st.stop()
        
    # Muestra el mensaje del usuario en el chat
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Guarda el mensaje en el historial
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Instanciación dinámica de los ejecutores con la clave, modelo, imagen y archivo de apoyo seleccionados
    refinement_executor = DynamicExecutor(
        run_refinement, 
        provider, 
        model_name, 
        api_key, 
        image_bytes=image_bytes, 
        image_type=image_type,
        doc_content=doc_content,
        doc_name=doc_name
    )
    story_writer_executor = DynamicExecutor(
        run_story_writer, 
        provider, 
        model_name, 
        api_key, 
        image_bytes=image_bytes, 
        image_type=image_type,
        doc_content=doc_content,
        doc_name=doc_name
    )
    
    # Procesa basado en el paso de conversación (step)
    if st.session_state.chat_step == "need":
        st.session_state.raw_input = prompt
        
        with st.chat_message("assistant"):
            spinner_msg = "Analizando requerimientos"
            if uploaded_file and uploaded_doc:
                spinner_msg += f" (con imagen y archivo {doc_name})"
            elif uploaded_file:
                spinner_msg += " (con imagen)"
            elif uploaded_doc:
                spinner_msg += f" (con archivo {doc_name})"
            spinner_msg += " para preparar preguntas de refinamiento..."
            with st.spinner(spinner_msg):
                try:
                    res = refinement_executor.invoke({"input": f"Refine: {prompt}"})
                    response_text = res["output"]
                except Exception as e:
                    response_text = f"❌ Ocurrió un error al procesar tu necesidad:\n\n`{str(e)}`\n\nPor favor, verifica tu API Key o intenta de nuevo."
            
            st.markdown(response_text)
            st.session_state.messages.append({"role": "assistant", "content": response_text})
            
            # Decisión inteligente de transición de paso
            if "preguntas por aclarar" in response_text.lower():
                st.session_state.chat_step = "answers"
            else:
                st.session_state.chat_step = "done"
            st.rerun()
            
    elif st.session_state.chat_step == "answers":
        with st.chat_message("assistant"):
            spinner_msg = "Generando Historia de Usuario"
            if uploaded_file and uploaded_doc:
                spinner_msg += f" (basada en tus respuestas, imagen y archivo {doc_name})..."
            elif uploaded_file:
                spinner_msg += " (basada en tus respuestas e imagen)..."
            elif uploaded_doc:
                spinner_msg += f" (basada en tus respuestas y archivo {doc_name})..."
            else:
                spinner_msg += " (basada en tus respuestas)..."
            with st.spinner(spinner_msg):
                try:
                    data = f"Need: {st.session_state.raw_input}. Answers: {prompt}"
                    res = story_writer_executor.invoke({"input": f"Generate story from: {data}"})
                    response_text = res["output"]
                except Exception as e:
                    response_text = f"❌ Ocurrió un error al generar la Historia de Usuario:\n\n`{str(e)}`\n\nPor favor, verifica tu API Key o intenta de nuevo."
            
            st.markdown(response_text)
            st.session_state.messages.append({"role": "assistant", "content": response_text})
            st.session_state.chat_step = "done"
            st.rerun()
            
    elif st.session_state.chat_step == "done":
        # Encuentra el último mensaje del asistente (El cual contiene la historia previa)
        last_story = ""
        for msg in reversed(st.session_state.messages[:-1]):  # Excluye el último mensaje del usuario
            if msg["role"] == "assistant":
                last_story = msg["content"]
                break
                
        with st.chat_message("assistant"):
            spinner_msg = "Actualizando Historia de Usuario"
            if uploaded_file and uploaded_doc:
                spinner_msg += f" (según tus comentarios, imagen y archivo {doc_name})..."
            elif uploaded_file:
                spinner_msg += " (según tus comentarios e imagen)..."
            elif uploaded_doc:
                spinner_msg += f" (según tus comentarios y archivo {doc_name})..."
            else:
                spinner_msg += " (según tus comentarios)..."
            with st.spinner(spinner_msg):
                try:
                    data = f"Original Story:\n{last_story}\n\nUser request for updates/adjustments:\n{prompt}"
                    res = story_writer_executor.invoke({"input": f"Generate story from: {data}"})
                    response_text = res["output"]
                except Exception as e:
                    response_text = f"❌ Ocurrió un error al actualizar la Historia de Usuario:\n\n`{str(e)}`\n\nPor favor, verifica tu API Key o intenta de nuevo."
            
            st.markdown(response_text)
            st.session_state.messages.append({"role": "assistant", "content": response_text})
            st.rerun()
