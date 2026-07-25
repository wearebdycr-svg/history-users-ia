import streamlit as st

from agent_project_initializer import (
    DOCUMENTS_DIR,
    stack_advisor_executor,
    plan_summary_executor,
    validate_mandatory_answer,
    normalize_project_type,
    resolve_stack_choice,
    resolve_destination_path,
    check_missing_binaries,
    create_project_structure,
    install_dependencies,
)

# Configuración de la página
st.set_page_config(
    page_title="Agente Inicializador de Proyectos",
    page_icon="🛠️",
    layout="centered"
)

st.title("Agente Inicializador de Proyectos 🛠️")
st.markdown(
    """
    **¡Bienvenido al asistente de inicialización de proyectos!**
    Te guiaré por una fase de descubrimiento (tipo de proyecto y stack), confirmaremos la ruta de destino
    dentro de `~/Documents` y, antes de instalar cualquier dependencia, te pediré aprobación explícita
    (**Human-in-the-loop**).
    """
)

WELCOME_MESSAGE = (
    "¡Hola! Soy tu asistente para inicializar proyectos de software. 🚀\n\n"
    "Para empezar, cuéntame: **¿qué tipo de proyecto deseas iniciar? (Web / Mobile)**"
)

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": WELCOME_MESSAGE}]

if "chat_step" not in st.session_state:
    st.session_state.chat_step = "type"  # Choices: "type", "stack", "path", "review", "done"

if "project_type" not in st.session_state:
    st.session_state.project_type = None

if "stack" not in st.session_state:
    st.session_state.stack = None

if "destination_path" not in st.session_state:
    st.session_state.destination_path = None


def reset_conversation():
    st.session_state.messages = [{"role": "assistant", "content": WELCOME_MESSAGE}]
    st.session_state.chat_step = "type"
    st.session_state.project_type = None
    st.session_state.stack = None
    st.session_state.destination_path = None


# Menú lateral
with st.sidebar:
    st.image("https://img.icons8.com/?size=100&id=103790&format=png&color=000000", width=100)
    st.subheader("Configuración & Control")
    st.info(
        f"**Estado actual:**\nPaso: {st.session_state.chat_step.upper()}\n\n"
        f"**Directorio base:**\n`{DOCUMENTS_DIR}`"
    )

    if st.button("Reiniciar Conversación 🔄", use_container_width=True):
        reset_conversation()
        st.rerun()

# Muestra los mensajes
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Checkpoint de Human-in-the-loop: se muestra solo en el paso de revisión
if st.session_state.chat_step == "review":
    col1, col2 = st.columns(2)
    approve = col1.button("✅ Aprobar e instalar", use_container_width=True)
    reject = col2.button("🔄 Rechazar / Modificar", use_container_width=True)

    if approve:
        stack = st.session_state.stack
        dest_path = st.session_state.destination_path

        with st.spinner("Validando gestores de paquetes requeridos..."):
            missing = check_missing_binaries(stack["binaries"])

        if missing:
            error_msg = (
                f"❌ No se encontraron en el sistema las siguientes herramientas requeridas: "
                f"**{', '.join(missing)}**. Instálalas y presiona nuevamente 'Aprobar e instalar'."
            )
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
            st.rerun()
        else:
            with st.spinner(f"Creando estructura del proyecto en {dest_path}..."):
                structure_error = create_project_structure(dest_path, stack)

            if structure_error:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"{structure_error}\n\n**¿En qué carpeta dentro de 'Documents' deseas crear el proyecto?**"
                })
                st.session_state.chat_step = "path"
                st.rerun()
            else:
                with st.spinner(f"Instalando dependencias con {stack['manager']}..."):
                    success, output = install_dependencies(dest_path, stack)

                if success:
                    final_msg = (
                        f"✅ ¡Proyecto listo para ejecutarse! Se creó la estructura en `{dest_path}` "
                        f"y se instalaron las dependencias con `{' '.join(stack['install_cmd'])}`.\n\n"
                        f"```\n{output}\n```"
                    )
                else:
                    final_msg = (
                        f"⚠️ La estructura del proyecto se creó en `{dest_path}`, pero la instalación de "
                        f"dependencias falló:\n\n```\n{output}\n```"
                    )
                st.session_state.messages.append({"role": "assistant", "content": final_msg})
                st.session_state.chat_step = "done"
                st.rerun()

    if reject:
        st.session_state.messages.append({
            "role": "assistant",
            "content": (
                "Entendido, detengo el proceso de instalación. Cuéntame qué ajustes necesitas y "
                "empecemos de nuevo: **¿qué tipo de proyecto deseas iniciar? (Web / Mobile)**"
            )
        })
        st.session_state.project_type = None
        st.session_state.stack = None
        st.session_state.destination_path = None
        st.session_state.chat_step = "type"
        st.rerun()

# Entrada conversacional del usuario
if prompt := st.chat_input("Escribe tu respuesta aquí..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    if st.session_state.chat_step == "type":
        error = validate_mandatory_answer(prompt)
        project_type = None
        if not error:
            project_type = normalize_project_type(prompt)
            if project_type is None:
                error = "⚠️ Por favor responde 'Web' o 'Mobile' para continuar."

        with st.chat_message("assistant"):
            if error:
                st.markdown(error)
                st.session_state.messages.append({"role": "assistant", "content": error})
            else:
                st.session_state.project_type = project_type
                with st.spinner("Consultando árbol de decisión de stacks tecnológicos..."):
                    try:
                        res = stack_advisor_executor.invoke(
                            {"input": f"Recomienda los stacks disponibles para un proyecto de tipo: {project_type}"}
                        )
                        response_text = res["output"]
                    except Exception as e:
                        response_text = f"❌ Ocurrió un error al recomendar el stack:\n\n`{str(e)}`\n\nPor favor, intenta de nuevo."

                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                st.session_state.chat_step = "stack"
            st.rerun()

    elif st.session_state.chat_step == "stack":
        error = validate_mandatory_answer(prompt)
        stack = None
        if not error:
            stack = resolve_stack_choice(st.session_state.project_type, prompt)
            if stack is None:
                error = "⚠️ Esa opción no es válida. Por favor selecciona uno de los stacks numerados anteriormente."

        with st.chat_message("assistant"):
            if error:
                st.markdown(error)
                st.session_state.messages.append({"role": "assistant", "content": error})
            else:
                st.session_state.stack = stack
                response_text = (
                    f"Elegiste **{stack['name']}**. Ahora, ¿en qué carpeta dentro de tu directorio "
                    f"**'Documents'** deseas crear el proyecto? (ej. `mi-proyecto`)"
                )
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                st.session_state.chat_step = "path"
            st.rerun()

    elif st.session_state.chat_step == "path":
        error = validate_mandatory_answer(prompt)

        with st.chat_message("assistant"):
            if error:
                st.markdown(error)
                st.session_state.messages.append({"role": "assistant", "content": error})
            else:
                dest_path = resolve_destination_path(prompt)
                st.session_state.destination_path = dest_path
                stack = st.session_state.stack

                plan_data = (
                    f"Tipo de proyecto: {st.session_state.project_type}\n"
                    f"Stack: {stack['name']} (gestor: {stack['manager']})\n"
                    f"Ruta destino: {dest_path}\n"
                    f"Estructura a crear: {stack['structure_summary']}\n"
                    f"Comando de instalación: {' '.join(stack['install_cmd'])}"
                )

                with st.spinner("Preparando plan de instalación para tu revisión..."):
                    try:
                        res = plan_summary_executor.invoke({"input": plan_data})
                        response_text = res["output"]
                    except Exception as e:
                        response_text = f"❌ Ocurrió un error al preparar el plan de instalación:\n\n`{str(e)}`\n\nPor favor, intenta de nuevo."

                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                st.session_state.chat_step = "review"
            st.rerun()

    elif st.session_state.chat_step == "review":
        with st.chat_message("assistant"):
            reminder = "Por favor utiliza los botones de aprobación que aparecen arriba para continuar (✅ Aprobar / 🔄 Rechazar)."
            st.markdown(reminder)
            st.session_state.messages.append({"role": "assistant", "content": reminder})

    elif st.session_state.chat_step == "done":
        with st.chat_message("assistant"):
            info_msg = "El proyecto ya fue inicializado. Usa 'Reiniciar Conversación' en la barra lateral para crear otro proyecto."
            st.markdown(info_msg)
            st.session_state.messages.append({"role": "assistant", "content": info_msg})
