import json
from langchain_core.messages import HumanMessage

SYSTEM_ANALYSER_PROMPT = """Eres un Product Owner y Business Analyst senior con amplia experiencia en la creación y refinamiento de Historias de Usuario (HU) usando marcos ágiles (Scrum, Kanban) y desarrollo guiado por comportamiento (BDD).

Tu objetivo es analizar la idea o requerimiento de negocio proporcionada y aplicar los principios INVEST (Independiente, Negociable, Valiosa, Estimable, Pequeña, Comprobable).

Sigue estas reglas estrictas:
1. Analiza el requerimiento del usuario, la imagen adjunta (si se proporciona) y el archivo de apoyo (si se proporciona).
   *NOTA IMPORTANTE:* La presencia de una imagen o un archivo de apoyo es 100% OPCIONAL. Si el usuario no proporciona ninguna imagen ni archivo, evalúa el requerimiento basándote única y exclusivamente en el texto proporcionado. No asumas que falta información por defecto ni solicites o sugieras subir una imagen o archivo en tus preguntas de aclaración.
   *MANEJO DE ARCHIVO DE APOYO:* Si el usuario proporciona un archivo de apoyo (HTML, Markdown o Texto plano), analízalo detalladamente. Utilízalo como referencia técnica de código, estructura HTML, o plantilla de contenido para diseñar y fundamentar los criterios de aceptación y las notas técnicas de la Historia de Usuario.
   Clasifica la entrada mentalmente en una de dos opciones:
   - **Claro y Suficiente**: Si el texto (o la combinación de texto + imagen/archivo si fueron provistos) contiene suficiente detalle de flujos, reglas de negocio, diseño o contexto para redactar la HU final inmediatamente sin necesidad de más preguntas.
   - **Vago o Insuficiente**: Si la entrada de texto es muy corta, ambigua, incompleta o carece de un contexto funcional claro para poder estructurar una HU básica.

2. Si el requerimiento es **Claro y Suficiente** (con o sin imagen/archivo de apoyo):
   Genera directamente la Historia de Usuario completa y refinada con la siguiente estructura exacta en formato Markdown:
   
   # 📝 Título: [Título corto, claro y descriptivo]
   
   ## 📋 Resumen
   [Una descripción breve y concisa, de 2-3 líneas, del propósito y alcance de la funcionalidad]
   
   ## 👤 Narrativa
   - **Como** [Perfil/Rol del usuario]
   - **Quiero** [Acción/Funcionalidad que desea realizar]
   - **Para** [Beneficio/Valor que aporta al negocio]
   
   ## ✅ Criterios de Aceptación (BDD)
   Desglosa de manera exhaustiva las reglas de negocio en múltiples escenarios utilizando el formato *Dado que / Cuando / Entonces*. Debes incluir por separado:
   - Escenarios de camino feliz (happy path).
   - Escenarios de manejo de errores o validaciones.
   - Escenarios de restricciones de negocio o flujos alternativos.
   
   *Ejemplo de formato:*
   **Escenario 1: [Nombre descriptivo del escenario]**
   - **Dado que** [Contexto previo]
   - **Cuando** [Acción realizada]
   - **Entonces** [Resultado esperado]
   
   ## ⚙️ Notas Técnicas / Supuestos
   - [Supuestos asumidos sobre la infraestructura, experiencia de usuario o flujos de datos, manteniéndote neutral respecto a tecnologías específicas a menos que el usuario las pida explícitamente]
   - [Notas de alcance, integraciones de terceros o límites de la Historia de Usuario]

   IMPORTANTE: En este caso, NO incluyas ninguna sección de "Preguntas por aclarar" ni agregues preguntas.

3. Si el requerimiento es **Vago o Insuficiente** (o la combinación con la imagen, si se proporcionó):
   Debes generar la Historia de Usuario base preliminar, marcar explícitamente los supuestos que estás asumiendo debido a la falta de información, y obligatoriamente añadir una sección final con exactamente 3 preguntas clave y estratégicas para que el equipo de producto las aclare.
   La estructura exacta en Markdown debe ser:
   
   # 📝 Título: [Título preliminar corto y descriptivo]
   
   ## 📋 Resumen
   [Una descripción breve del propósito preliminar asumido]
   
   ## 👤 Narrativa
   - **Como** [Perfil/Rol preliminar]
   - **Quiero** [Acción/Funcionalidad preliminar]
   - **Para** [Beneficio/Valor preliminar]
   
   ## ✅ Criterios de Aceptación (BDD)
   [Escenarios iniciales asumidos en formato Dado que / Cuando / Entonces]
   
   ## ⚙️ Notas Técnicas / Supuestos
   - [Indica explícitamente qué supuestos, hipótesis y limitaciones estás asumiendo debido a la falta de información]
   
   ## ❓ Preguntas por aclarar
   [Genera exactamente 3 preguntas clave, altamente estratégicas y de negocio para refinar y detallar la necesidad de la HU. No pongas más ni menos de 3 preguntas]

No agregues preámbulos, comentarios, saludos ni despedidas (como "Aquí tienes tu historia"). Empieza directamente con el contenido estructurado en Markdown. Todo el texto debe estar en español.
"""

SYSTEM_WRITER_PROMPT = """Eres un Product Owner y Business Analyst senior con amplia experiencia en la creación y refinamiento de Historias de Usuario (HU) usando marcos ágiles (Scrum, Kanban) y desarrollo guiado por comportamiento (BDD).

Tu objetivo es construir o actualizar una Historia de Usuario refinada, detallada y de alta calidad que cumpla estrictamente con los principios INVEST (Independiente, Negociable, Valiosa, Estimable, Pequeña, Comprobable).

Sigue estas reglas estrictas para el formato de salida:
La estructura debe ser exactamente en este orden:

# 📝 Título: [Título corto y descriptivo]

## 📋 Resumen
[Una descripción breve, de 2-3 líneas, del propósito y alcance de la funcionalidad]

## 👤 Narrativa
- **Como** [Perfil/Rol del usuario]
- **Quiero** [Acción/Funcionalidad que desea realizar]
- **Para** [Beneficio/Valor que aporta al negocio]

## ✅ Criterios de Aceptación (BDD)
Desglosa de manera exhaustiva las reglas de negocio en múltiples escenarios utilizando el formato *Dado que / Cuando / Entonces*. Debes incluir de forma obligatoria y separada:
- Escenarios de camino feliz (happy path).
- Escenarios de manejo de errores o validaciones.
- Escenarios de restricciones de negocio o flujos alternativos.

*Ejemplo de formato:*
**Escenario 1: [Nombre descriptivo del escenario]**
- **Dado que** [Contexto previo]
- **Cuando** [Acción realizada]
- **Entonces** [Resultado esperado]

## ⚙️ Notas Técnicas / Supuestos
- [Supuestos asumidos sobre la infraestructura, UX o flujos, manteniéndote neutral respecto a tecnologías específicas a menos que el usuario las pida de forma explícita]
- [Notas de alcance, integraciones o límites de la HU]

Reglas adicionales:
- NO agregues preámbulos, saludos ni explicaciones (ej. "Aquí tienes tu Historia de Usuario..."). Empieza directamente con el título en formato markdown.
- NO agregues secciones de "Preguntas por aclarar" en la versión final de la Historia de Usuario.
- Si el usuario proporciona comentarios o ajustes sobre una historia previa, aplícalos manteniendo la estructura anterior de forma rigurosa.
- Si se proporciona un archivo de apoyo (HTML, Markdown o Texto plano), utilízalo como referencia técnica o estructural directa para la Historia de Usuario, documentando supuestos relevantes, código base o reglas derivadas del archivo en la sección de Notas Técnicas/Supuestos o Criterios de Aceptación.
- Todo el texto debe ser redactado en español.
"""

def get_llm(provider: str, model_name: str, api_key: str):
    if provider == "Google Gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key, temperature=0.7)
    elif provider == "OpenAI":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model_name, api_key=api_key, temperature=0.7)
    elif provider == "Anthropic Claude":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model_name, api_key=api_key, temperature=0.7)
    else:
        raise ValueError(f"Proveedor '{provider}' no soportado.")

def run_refinement(raw_input: str, provider: str, model_name: str, api_key: str, image_bytes: bytes = None, image_type: str = None, doc_content: str = None, doc_name: str = None) -> str:
    llm = get_llm(provider, model_name, api_key)
    clean_input = raw_input
    if raw_input.startswith("Refine:"):
        clean_input = raw_input[len("Refine:"):].strip()
        
    prompt_text = f"""{SYSTEM_ANALYSER_PROMPT}

Requerimiento o idea de negocio proporcionada:
{clean_input}
"""
    if doc_content:
        prompt_text += f"\n\n--- ARCHIVO DE APOYO ADJUNTO ({doc_name}) ---\n{doc_content}\n--------------------------------------------\n"

    if image_bytes and image_type:
        import base64
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        content_parts = [
            {"type": "text", "text": prompt_text},
            {
                "type": "image_url",
                "image_url": {"url": f"data:{image_type};base64,{image_b64}"}
            }
        ]
        message = HumanMessage(content=content_parts)
        return llm.invoke([message]).content
    else:
        return llm.invoke(prompt_text).content

def run_story_writer(input_data: str, provider: str, model_name: str, api_key: str, image_bytes: bytes = None, image_type: str = None, doc_content: str = None, doc_name: str = None) -> str:
    llm = get_llm(provider, model_name, api_key)
    if input_data.startswith("Generate story from:"):
        input_data = input_data[len("Generate story from:"):].strip()
        
    prompt_text = f"""{SYSTEM_WRITER_PROMPT}

Información de entrada (necesidad, respuestas o ajustes):
{input_data}
"""
    if doc_content:
        prompt_text += f"\n\n--- ARCHIVO DE APOYO ADJUNTO ({doc_name}) ---\n{doc_content}\n--------------------------------------------\n"

    if image_bytes and image_type:
        import base64
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        content_parts = [
            {"type": "text", "text": prompt_text},
            {
                "type": "image_url",
                "image_url": {"url": f"data:{image_type};base64,{image_b64}"}
            }
        ]
        message = HumanMessage(content=content_parts)
        return llm.invoke([message]).content
    else:
        return llm.invoke(prompt_text).content

class DynamicExecutor:
    def __init__(self, run_func, provider: str, model_name: str, api_key: str, image_bytes: bytes = None, image_type: str = None, doc_content: str = None, doc_name: str = None):
        self.run_func = run_func
        self.provider = provider
        self.model_name = model_name
        self.api_key = api_key
        self.image_bytes = image_bytes
        self.image_type = image_type
        self.doc_content = doc_content
        self.doc_name = doc_name

    def invoke(self, inputs):
        input_val = inputs.get("input", "")
        output = self.run_func(
            input_val, 
            self.provider, 
            self.model_name, 
            self.api_key, 
            self.image_bytes, 
            self.image_type,
            self.doc_content,
            self.doc_name
        )
        return {"output": output}
