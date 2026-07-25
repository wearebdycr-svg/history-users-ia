import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_core.tools import tool
from langchainhub import pull

import streamlit as st

if "GOOGLE_API_KEY" in st.secrets:
    os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]

with open("config.json", "r") as f:
    config = json.load(f)

llm = ChatGoogleGenerativeAI(model=config["model_name"], temperature=0.3)

# Carpeta base donde se permite inicializar proyectos (Supuesto de la HU: acceso a ~/Documents)
DOCUMENTS_DIR = Path.home() / "Documents"

# Variables de entorno para forzar modo no interactivo en las CLIs de scaffolding invocadas
SCAFFOLD_ENV_OVERRIDES = {
    "CI": "true",
    "NG_CLI_ANALYTICS": "false",
}

# --- Módulo de Discovery: árbol de decisión de stacks tecnológicos ---
# Cada stack es de tipo "cli" (se genera invocando la CLI oficial real, igual que se haría
# desde consola) o "manual" (no existe una CLI oficial no interactiva para ese caso, así que
# el agente escribe directamente los archivos mínimos necesarios).
STACK_TREE = {
    "web": [
        {
            "id": "react",
            "name": "React + Vite",
            "manager": "npm",
            "binaries": ["node", "npm"],
            "install_cmd": ["npm", "install"],
            "scaffold": "cli",
            "scaffold_cmd": ["npx", "--yes", "create-vite@latest", "{project_name}", "--template", "react"],
            "structure_summary": (
                "Generada por `create-vite` (plantilla React): src/, public/, index.html, "
                "vite.config.js y package.json listos para `npm run dev`."
            ),
        },
        {
            "id": "vue",
            "name": "Vue 3 + Vite",
            "manager": "npm",
            "binaries": ["node", "npm"],
            "install_cmd": ["npm", "install"],
            "scaffold": "cli",
            "scaffold_cmd": ["npx", "--yes", "create-vite@latest", "{project_name}", "--template", "vue"],
            "structure_summary": (
                "Generada por `create-vite` (plantilla Vue): src/, public/, index.html, "
                "vite.config.js y package.json listos para `npm run dev`."
            ),
        },
        {
            "id": "angular",
            "name": "Angular",
            "manager": "npm",
            "binaries": ["node", "npm"],
            "install_cmd": ["npm", "install"],
            "scaffold": "cli",
            "scaffold_cmd": [
                "npx", "--yes", "@angular/cli@latest", "new", "{project_name}",
                "--defaults", "--skip-git", "--package-manager=npm", "--skip-install",
            ],
            "structure_summary": (
                "Generada por `ng new` (Angular CLI): src/app estándar, configuración de "
                "routing/testing por defecto y angular.json."
            ),
        },
        {
            "id": "angular17",
            "name": "Angular 17+ (Standalone)",
            "manager": "npm",
            "binaries": ["node", "npm"],
            "install_cmd": ["npm", "install"],
            "scaffold": "cli",
            "scaffold_cmd": [
                "npx", "--yes", "@angular/cli@>=17.0.0", "new", "{project_name}",
                "--defaults", "--skip-git", "--package-manager=npm", "--skip-install",
            ],
            "structure_summary": (
                "Generada por `ng new` fijando Angular CLI ≥17: componentes standalone, "
                "signals y control flow nativo (@if/@for) por defecto, sin NgModules."
            ),
        },
        {
            "id": "next",
            "name": "Next.js",
            "manager": "npm",
            "binaries": ["node", "npm"],
            "install_cmd": ["npm", "install"],
            "scaffold": "cli",
            "scaffold_cmd": [
                "npx", "--yes", "create-next-app@latest", "{project_name}",
                "--ts", "--eslint", "--app", "--no-src-dir",
                "--import-alias", "@/*", "--use-npm", "--no-git", "--skip-install",
            ],
            "structure_summary": (
                "Generada por `create-next-app`: app router, TypeScript, ESLint y "
                "configuración de Next.js lista para `npm run dev`."
            ),
        },
    ],
    "mobile": [
        {
            "id": "flutter",
            "name": "Flutter",
            "manager": "flutter/pub",
            "binaries": ["flutter"],
            "install_cmd": ["flutter", "pub", "get"],
            "scaffold": "cli",
            "scaffold_cmd": [
                "flutter", "create", "--no-pub",
                "--project-name", "{flutter_project_name}", "{project_name}",
            ],
            "structure_summary": (
                "Generada por `flutter create`: lib/main.dart, carpeta test/ y configuración "
                "nativa android/ e ios/. El nombre de paquete Dart se deriva en snake_case a "
                "partir del nombre de carpeta."
            ),
        },
        {
            "id": "react_native",
            "name": "React Native",
            "manager": "npm",
            "binaries": ["node", "npm"],
            "install_cmd": ["npm", "install"],
            "scaffold": "cli",
            "scaffold_cmd": [
                "npx", "--yes", "@react-native-community/cli@latest", "init", "{rn_project_name}",
                "--directory", "{project_name}", "--skip-install",
            ],
            "structure_summary": (
                "Generada por `@react-native-community/cli init`: App.tsx, carpetas nativas "
                "android/ e ios/ y configuración de Metro. El nombre de proyecto nativo se "
                "deriva en PascalCase alfanumérico a partir del nombre de carpeta."
            ),
        },
        {
            "id": "native_ios",
            "name": "Nativo iOS (Swift) + CocoaPods",
            "manager": "pod",
            "binaries": ["pod"],
            "install_cmd": ["pod", "install"],
            "scaffold": "manual",
            "folders": [],
            "files": {
                "Podfile": "platform :ios, '13.0'\n\ntarget '{project_name}' do\n  use_frameworks!\nend\n",
                "Sources/AppDelegate.swift": (
                    "import UIKit\n\n"
                    "@main\n"
                    "class AppDelegate: UIResponder, UIApplicationDelegate {\n"
                    "    var window: UIWindow?\n"
                    "}\n"
                ),
                "Sources/ViewController.swift": (
                    "import UIKit\n\n"
                    "class ViewController: UIViewController {\n"
                    "    override func viewDidLoad() {\n"
                    "        super.viewDidLoad()\n"
                    "        let label = UILabel()\n"
                    "        label.text = \"{project_name}\"\n"
                    "        label.translatesAutoresizingMaskIntoConstraints = false\n"
                    "        view.addSubview(label)\n"
                    "        NSLayoutConstraint.activate([\n"
                    "            label.centerXAnchor.constraint(equalTo: view.centerXAnchor),\n"
                    "            label.centerYAnchor.constraint(equalTo: view.centerYAnchor),\n"
                    "        ])\n"
                    "    }\n"
                    "}\n"
                ),
            },
            "structure_summary": (
                "Estructura mínima escrita a mano (Podfile + Sources/): Xcode no ofrece una CLI "
                "oficial no interactiva para generar el .xcodeproj, así que deberás abrir el "
                "proyecto en Xcode para completarlo antes de compilarlo."
            ),
        },
        {
            "id": "ionic",
            "name": "Ionic + Capacitor",
            "manager": "npm",
            "binaries": ["node", "npm"],
            "install_cmd": ["npm", "install"],
            "scaffold": "cli",
            "scaffold_cmd": [
                "npx", "--yes", "@ionic/cli@latest", "start", "{project_name}", "blank",
                "--type=angular", "--capacitor", "--no-interactive", "--no-git", "--no-deps",
            ],
            "structure_summary": (
                "Generada por `ionic start` (blank + Angular + Capacitor): src/app, "
                "capacitor.config.ts y configuración lista para `ionic serve`."
            ),
        },
        {
            "id": "kotlin_android",
            "name": "Kotlin nativo (Android)",
            "manager": "gradle",
            "binaries": ["gradle"],
            "install_cmd": ["gradle", "build"],
            "scaffold": "manual",
            "folders": [],
            "files": {
                "settings.gradle.kts": "rootProject.name = \"{project_name}\"\ninclude(\":app\")\n",
                "build.gradle.kts": (
                    "plugins {\n"
                    "    id(\"com.android.application\") version \"8.5.0\" apply false\n"
                    "    id(\"org.jetbrains.kotlin.android\") version \"1.9.24\" apply false\n"
                    "}\n"
                ),
                "app/build.gradle.kts": (
                    "plugins {\n"
                    "    id(\"com.android.application\")\n"
                    "    id(\"org.jetbrains.kotlin.android\")\n"
                    "}\n\n"
                    "android {\n"
                    "    namespace = \"{package_name}\"\n"
                    "    compileSdk = 34\n\n"
                    "    defaultConfig {\n"
                    "        applicationId = \"{package_name}\"\n"
                    "        minSdk = 24\n"
                    "        targetSdk = 34\n"
                    "        versionCode = 1\n"
                    "        versionName = \"1.0\"\n"
                    "    }\n\n"
                    "    compileOptions {\n"
                    "        sourceCompatibility = JavaVersion.VERSION_1_8\n"
                    "        targetCompatibility = JavaVersion.VERSION_1_8\n"
                    "    }\n"
                    "    kotlinOptions {\n"
                    "        jvmTarget = \"1.8\"\n"
                    "    }\n"
                    "}\n\n"
                    "dependencies {\n"
                    "    implementation(\"androidx.core:core-ktx:1.13.1\")\n"
                    "    implementation(\"androidx.appcompat:appcompat:1.7.0\")\n"
                    "    implementation(\"com.google.android.material:material:1.12.0\")\n"
                    "}\n"
                ),
                "app/src/main/AndroidManifest.xml": (
                    "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n"
                    "<manifest xmlns:android=\"http://schemas.android.com/apk/res/android\">\n\n"
                    "    <application\n"
                    "        android:allowBackup=\"true\"\n"
                    "        android:label=\"{project_name}\"\n"
                    "        android:theme=\"@style/Theme.AppCompat.Light\">\n"
                    "        <activity\n"
                    "            android:name=\".MainActivity\"\n"
                    "            android:exported=\"true\">\n"
                    "            <intent-filter>\n"
                    "                <action android:name=\"android.intent.action.MAIN\" />\n"
                    "                <category android:name=\"android.intent.category.LAUNCHER\" />\n"
                    "            </intent-filter>\n"
                    "        </activity>\n"
                    "    </application>\n\n"
                    "</manifest>\n"
                ),
                "app/src/main/java/{package_path}/MainActivity.kt": (
                    "package {package_name}\n\n"
                    "import android.os.Bundle\n"
                    "import androidx.appcompat.app.AppCompatActivity\n\n"
                    "class MainActivity : AppCompatActivity() {\n"
                    "    override fun onCreate(savedInstanceState: Bundle?) {\n"
                    "        super.onCreate(savedInstanceState)\n"
                    "        setContentView(R.layout.activity_main)\n"
                    "    }\n"
                    "}\n"
                ),
                "app/src/main/res/layout/activity_main.xml": (
                    "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n"
                    "<LinearLayout xmlns:android=\"http://schemas.android.com/apk/res/android\"\n"
                    "    android:layout_width=\"match_parent\"\n"
                    "    android:layout_height=\"match_parent\"\n"
                    "    android:orientation=\"vertical\"\n"
                    "    android:gravity=\"center\">\n\n"
                    "    <TextView\n"
                    "        android:layout_width=\"wrap_content\"\n"
                    "        android:layout_height=\"wrap_content\"\n"
                    "        android:text=\"{project_name}\"\n"
                    "        android:textSize=\"24sp\" />\n\n"
                    "</LinearLayout>\n"
                ),
                "app/src/main/res/values/strings.xml": (
                    "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n"
                    "<resources>\n"
                    "    <string name=\"app_name\">{project_name}</string>\n"
                    "</resources>\n"
                ),
            },
            "structure_summary": (
                "Estructura mínima escrita a mano (build.gradle.kts, AndroidManifest.xml, "
                "MainActivity.kt): no existe una CLI oficial no interactiva fuera de Android "
                "Studio para generar un proyecto Android nativo."
            ),
        },
        {
            "id": "kmp",
            "name": "Kotlin Multiplatform (KMP)",
            "manager": "gradle",
            "binaries": ["gradle"],
            "install_cmd": ["gradle", "build"],
            "scaffold": "manual",
            "folders": [],
            "files": {
                "settings.gradle.kts": (
                    "pluginManagement {\n"
                    "    repositories {\n"
                    "        google()\n"
                    "        gradlePluginPortal()\n"
                    "        mavenCentral()\n"
                    "    }\n"
                    "}\n\n"
                    "dependencyResolutionManagement {\n"
                    "    repositories {\n"
                    "        google()\n"
                    "        mavenCentral()\n"
                    "    }\n"
                    "}\n\n"
                    "rootProject.name = \"{project_name}\"\n"
                    "include(\":androidApp\")\n"
                    "include(\":shared\")\n"
                ),
                "build.gradle.kts": (
                    "plugins {\n"
                    "    id(\"com.android.application\") version \"8.5.0\" apply false\n"
                    "    id(\"com.android.library\") version \"8.5.0\" apply false\n"
                    "    id(\"org.jetbrains.kotlin.android\") version \"1.9.24\" apply false\n"
                    "    id(\"org.jetbrains.kotlin.multiplatform\") version \"1.9.24\" apply false\n"
                    "}\n"
                ),
                "gradle.properties": (
                    "kotlin.code.style=official\n"
                    "android.useAndroidX=true\n"
                    "android.nonTransitiveRClass=true\n"
                ),
                "shared/build.gradle.kts": (
                    "plugins {\n"
                    "    id(\"org.jetbrains.kotlin.multiplatform\")\n"
                    "    id(\"com.android.library\")\n"
                    "}\n\n"
                    "kotlin {\n"
                    "    androidTarget()\n"
                    "    iosArm64()\n"
                    "    iosSimulatorArm64()\n\n"
                    "    sourceSets {\n"
                    "        val commonMain by getting\n"
                    "        val androidMain by getting\n"
                    "        val iosMain by creating {\n"
                    "            dependsOn(commonMain)\n"
                    "        }\n"
                    "        val iosArm64Main by getting { dependsOn(iosMain) }\n"
                    "        val iosSimulatorArm64Main by getting { dependsOn(iosMain) }\n"
                    "    }\n"
                    "}\n\n"
                    "android {\n"
                    "    namespace = \"{package_name}.shared\"\n"
                    "    compileSdk = 34\n"
                    "    defaultConfig {\n"
                    "        minSdk = 24\n"
                    "    }\n"
                    "    compileOptions {\n"
                    "        sourceCompatibility = JavaVersion.VERSION_1_8\n"
                    "        targetCompatibility = JavaVersion.VERSION_1_8\n"
                    "    }\n"
                    "}\n"
                ),
                "shared/src/commonMain/kotlin/{package_path}/Platform.kt": (
                    "package {package_name}\n\n"
                    "interface Platform {\n"
                    "    val name: String\n"
                    "}\n\n"
                    "expect fun getPlatform(): Platform\n"
                ),
                "shared/src/commonMain/kotlin/{package_path}/Greeting.kt": (
                    "package {package_name}\n\n"
                    "class Greeting {\n"
                    "    private val platform = getPlatform()\n\n"
                    "    fun greet(): String = \"Hola desde {project_name}, ejecutando en ${platform.name}!\"\n"
                    "}\n"
                ),
                "shared/src/androidMain/kotlin/{package_path}/Platform.android.kt": (
                    "package {package_name}\n\n"
                    "class AndroidPlatform : Platform {\n"
                    "    override val name: String = \"Android ${android.os.Build.VERSION.SDK_INT}\"\n"
                    "}\n\n"
                    "actual fun getPlatform(): Platform = AndroidPlatform()\n"
                ),
                "shared/src/iosMain/kotlin/{package_path}/Platform.ios.kt": (
                    "package {package_name}\n\n"
                    "import platform.UIKit.UIDevice\n\n"
                    "class IOSPlatform : Platform {\n"
                    "    override val name: String =\n"
                    "        UIDevice.currentDevice.systemName() + \" \" + UIDevice.currentDevice.systemVersion\n"
                    "}\n\n"
                    "actual fun getPlatform(): Platform = IOSPlatform()\n"
                ),
                "androidApp/build.gradle.kts": (
                    "plugins {\n"
                    "    id(\"com.android.application\")\n"
                    "    id(\"org.jetbrains.kotlin.android\")\n"
                    "}\n\n"
                    "android {\n"
                    "    namespace = \"{package_name}\"\n"
                    "    compileSdk = 34\n\n"
                    "    defaultConfig {\n"
                    "        applicationId = \"{package_name}\"\n"
                    "        minSdk = 24\n"
                    "        targetSdk = 34\n"
                    "        versionCode = 1\n"
                    "        versionName = \"1.0\"\n"
                    "    }\n\n"
                    "    compileOptions {\n"
                    "        sourceCompatibility = JavaVersion.VERSION_1_8\n"
                    "        targetCompatibility = JavaVersion.VERSION_1_8\n"
                    "    }\n"
                    "    kotlinOptions {\n"
                    "        jvmTarget = \"1.8\"\n"
                    "    }\n"
                    "}\n\n"
                    "dependencies {\n"
                    "    implementation(project(\":shared\"))\n"
                    "    implementation(\"androidx.core:core-ktx:1.13.1\")\n"
                    "    implementation(\"androidx.appcompat:appcompat:1.7.0\")\n"
                    "}\n"
                ),
                "androidApp/src/main/AndroidManifest.xml": (
                    "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n"
                    "<manifest xmlns:android=\"http://schemas.android.com/apk/res/android\">\n\n"
                    "    <application\n"
                    "        android:allowBackup=\"true\"\n"
                    "        android:label=\"{project_name}\"\n"
                    "        android:theme=\"@style/Theme.AppCompat.Light\">\n"
                    "        <activity\n"
                    "            android:name=\".MainActivity\"\n"
                    "            android:exported=\"true\">\n"
                    "            <intent-filter>\n"
                    "                <action android:name=\"android.intent.action.MAIN\" />\n"
                    "                <category android:name=\"android.intent.category.LAUNCHER\" />\n"
                    "            </intent-filter>\n"
                    "        </activity>\n"
                    "    </application>\n\n"
                    "</manifest>\n"
                ),
                "androidApp/src/main/java/{package_path}/MainActivity.kt": (
                    "package {package_name}\n\n"
                    "import android.os.Bundle\n"
                    "import android.widget.TextView\n"
                    "import androidx.appcompat.app.AppCompatActivity\n\n"
                    "class MainActivity : AppCompatActivity() {\n"
                    "    override fun onCreate(savedInstanceState: Bundle?) {\n"
                    "        super.onCreate(savedInstanceState)\n"
                    "        val textView = TextView(this)\n"
                    "        textView.text = Greeting().greet()\n"
                    "        setContentView(textView)\n"
                    "    }\n"
                    "}\n"
                ),
            },
            "structure_summary": (
                "Estructura mínima escrita a mano (Gradle multi-módulo: shared/ con "
                "commonMain·androidMain·iosMain + androidApp/): JetBrains no ofrece una CLI "
                "oficial no interactiva (el asistente kmp.jetbrains.com genera un zip vía "
                "navegador); la parte iOS requiere abrir Xcode para completar el target nativo."
            ),
        },
        {
            "id": "expo",
            "name": "Expo (React Native managed)",
            "manager": "npm",
            "binaries": ["node", "npm"],
            "install_cmd": ["npm", "install"],
            "scaffold": "cli",
            "scaffold_cmd": [
                "npx", "--yes", "create-expo-app@latest", "{project_name}",
                "--template", "blank", "--no-install",
            ],
            "structure_summary": (
                "Generada por `create-expo-app` (plantilla blank): App.js, app.json y "
                "configuración Expo lista para `npx expo start`."
            ),
        },
    ],
}


def validate_mandatory_answer(text: str) -> Optional[str]:
    """Valida que una respuesta obligatoria del flujo de discovery no esté vacía. Retorna un mensaje de error o None si es válida."""
    if text is None or not text.strip():
        return "⚠️ Esta pregunta es obligatoria y no puede omitirse ni quedar vacía. Por favor, respóndela para continuar."
    return None


def normalize_project_type(text: str) -> Optional[str]:
    """Normaliza la respuesta del usuario a 'web' o 'mobile'. Retorna None si no coincide con ninguna opción válida."""
    clean = text.strip().lower()
    if clean in ("web", "página web", "pagina web", "sitio web"):
        return "web"
    if clean in ("mobile", "móvil", "movil", "app móvil", "app movil"):
        return "mobile"
    return None


def get_recommended_stacks(project_type: str) -> list:
    """Retorna la lista de stacks recomendados por el árbol de decisión para un tipo de proyecto ('web' o 'mobile')."""
    return STACK_TREE.get(project_type, [])


def resolve_stack_choice(project_type: str, choice_text: str) -> Optional[dict]:
    """Resuelve la elección del usuario (por número o nombre) contra los stacks recomendados. Retorna None si no hay coincidencia."""
    stacks = get_recommended_stacks(project_type)
    clean = choice_text.strip().lower()

    if clean.isdigit():
        index = int(clean) - 1
        if 0 <= index < len(stacks):
            return stacks[index]
        return None

    for stack in stacks:
        if clean == stack["id"].lower() or clean in stack["name"].lower():
            return stack
    return None


def resolve_destination_path(raw_path: str) -> Path:
    """Resuelve la ruta de destino ingresada por el usuario, anclándola siempre dentro de ~/Documents."""
    clean = raw_path.strip().strip('"')
    candidate = Path(clean).expanduser()
    if candidate.is_absolute():
        return candidate
    return DOCUMENTS_DIR / candidate


def check_missing_binaries(binaries: list) -> list:
    """Verifica qué gestores de paquetes/herramientas requeridas no están disponibles en el sistema."""
    return [binary for binary in binaries if shutil.which(binary) is None]


def _derive_placeholders(project_name: str) -> dict:
    """Deriva los valores de reemplazo (nombre de proyecto, paquete Kotlin/Java, etc.) para los templates de archivos manuales."""
    safe_slug = re.sub(r"[^a-zA-Z0-9]", "", project_name).lower() or "app"
    if safe_slug[0].isdigit():
        safe_slug = f"app{safe_slug}"
    package_name = f"com.example.{safe_slug}"
    return {
        "{project_name}": project_name,
        "{package_name}": package_name,
        "{package_path}": package_name.replace(".", "/"),
    }


def _to_snake_case_identifier(name: str) -> str:
    """Deriva un identificador válido en snake_case (requerido por 'flutter create --project-name')."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()
    slug = re.sub(r"_+", "_", slug) or "app"
    if slug[0].isdigit():
        slug = f"app_{slug}"
    return slug


def _to_pascal_case_identifier(name: str) -> str:
    """Deriva un identificador alfanumérico en PascalCase (requerido por '@react-native-community/cli init')."""
    parts = [p for p in re.split(r"[^a-zA-Z0-9]+", name) if p]
    identifier = "".join(p.capitalize() for p in parts) or "App"
    if identifier[0].isdigit():
        identifier = f"App{identifier}"
    return identifier


def _scaffold_cmd_placeholders(project_path: Path) -> dict:
    """Valores de reemplazo exactos por token para los comandos de scaffolding CLI (scaffold_cmd)."""
    return {
        "{project_name}": project_path.name,
        "{flutter_project_name}": _to_snake_case_identifier(project_path.name),
        "{rn_project_name}": _to_pascal_case_identifier(project_path.name),
    }


def _render(template: str, replacements: dict) -> str:
    for placeholder, value in replacements.items():
        template = template.replace(placeholder, value)
    return template


def create_project_structure(project_path: Path, stack: dict) -> Optional[str]:
    """Crea el proyecto invocando la CLI oficial del stack (o, si no existe una no interactiva, escribiendo los archivos mínimos). Retorna un mensaje de error o None si fue exitoso."""
    try:
        if project_path.exists():
            raise FileExistsError

        if stack.get("scaffold") == "cli":
            project_path.parent.mkdir(parents=True, exist_ok=True)
            cmd_placeholders = _scaffold_cmd_placeholders(project_path)
            cmd = [cmd_placeholders.get(arg, arg) for arg in stack["scaffold_cmd"]]
            env = {**os.environ, **SCAFFOLD_ENV_OVERRIDES}
            result = subprocess.run(
                cmd,
                cwd=str(project_path.parent),
                capture_output=True,
                text=True,
                timeout=600,
                env=env,
            )
            if result.returncode != 0:
                shutil.rmtree(project_path, ignore_errors=True)
                error_output = result.stderr.strip() or result.stdout.strip() or "El comando no produjo salida."
                return f"❌ Error al generar el proyecto con {stack['name']}:\n\n```\n{error_output}\n```"
            return None

        project_path.mkdir(parents=True, exist_ok=False)
        replacements = _derive_placeholders(project_path.name)
        for folder in stack.get("folders", []):
            (project_path / folder).mkdir(parents=True, exist_ok=True)
        for rel_path_template, content_template in stack["files"].items():
            file_path = project_path / _render(rel_path_template, replacements)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(_render(content_template, replacements))
        return None
    except FileExistsError:
        return f"❌ Error: la carpeta '{project_path}' ya existe. Por favor indica una ruta o nombre de proyecto distinto."
    except PermissionError:
        return f"❌ Error de permisos: no tienes permisos de escritura en '{project_path.parent}'. Por favor indica una ruta alternativa válida dentro de tu carpeta de usuario."
    except FileNotFoundError:
        return f"❌ No se encontró el ejecutable necesario para generar el proyecto con {stack['name']}. Verifica que esté instalado."
    except subprocess.TimeoutExpired:
        return f"❌ La generación del proyecto con {stack['name']} excedió el tiempo máximo de espera."
    except OSError as e:
        return f"❌ Error al crear la estructura del proyecto: {str(e)}"


def install_dependencies(project_path: Path, stack: dict) -> tuple:
    """Ejecuta el comando de instalación de dependencias del stack dentro del directorio del proyecto. Retorna (éxito, mensaje)."""
    try:
        result = subprocess.run(
            stack["install_cmd"],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            return True, result.stdout.strip() or "Instalación completada."
        return False, result.stderr.strip() or "El gestor de paquetes retornó un error."
    except FileNotFoundError:
        return False, f"No se encontró el ejecutable '{stack['install_cmd'][0]}' en el sistema."
    except subprocess.TimeoutExpired:
        return False, "La instalación de dependencias excedió el tiempo máximo de espera."


SYSTEM_STACK_ADVISOR_PROMPT = """Eres un arquitecto de software senior que asesora a desarrolladores en la elección de un stack tecnológico para un nuevo proyecto.

Reglas estrictas:
- SOLO puedes recomendar y describir las opciones de stack que se te entregan explícitamente a continuación. NO inventes frameworks, herramientas ni gestores de paquetes adicionales.
- Presenta cada opción numerada, con su nombre y una justificación breve (1-2 líneas) de cuándo conviene elegirla.
- Cierra preguntando explícitamente al usuario cuál de las opciones numeradas desea seleccionar.
- Responde siempre en español, en formato Markdown, sin saludos ni despedidas.
"""

SYSTEM_PLAN_SUMMARY_PROMPT = """Eres un asistente de DevOps que presenta un plan de instalación de proyecto para revisión humana (Human-in-the-loop) antes de ejecutarlo.

Reglas estrictas:
- Resume ÚNICAMENTE la información entregada (tipo de proyecto, stack, ruta destino, carpetas a crear y comando de instalación). NO agregues pasos, carpetas ni comandos que no estén en los datos proporcionados.
- El formato debe ser un resumen claro en Markdown con las secciones: "📦 Tipo de proyecto", "🛠️ Stack seleccionado", "📁 Ruta de destino", "🗂️ Estructura a crear" y "⚙️ Comando de instalación".
- Finaliza SIEMPRE con la línea exacta: "**¿Apruebas la instalación?** Usa los botones de confirmación para continuar."
- Responde siempre en español, sin saludos ni despedidas.
"""


@tool(return_direct=True)
def recommend_stack(project_type: str) -> str:
    """Recomienda, mediante el árbol de decisión, los stacks tecnológicos disponibles para un tipo de proyecto ('web' o 'mobile')."""
    stacks = get_recommended_stacks(project_type.strip().lower())
    if not stacks:
        return "⚠️ Tipo de proyecto no reconocido. Por favor indica 'Web' o 'Mobile'."

    options_text = "\n".join(
        f"{i}. {s['name']} (gestor: {s['manager']})" for i, s in enumerate(stacks, start=1)
    )
    prompt = f"""{SYSTEM_STACK_ADVISOR_PROMPT}

Tipo de proyecto: {project_type}
Opciones disponibles:
{options_text}
"""
    return llm.invoke(prompt).content


@tool(return_direct=True)
def summarize_installation_plan(plan_data: str) -> str:
    """Genera el resumen del plan de instalación para presentarlo al usuario en el checkpoint de Human-in-the-loop."""
    prompt = f"""{SYSTEM_PLAN_SUMMARY_PROMPT}

Datos del plan:
{plan_data}
"""
    return llm.invoke(prompt).content


react_prompt = pull("hwchase17/react")

stack_advisor_agent = create_react_agent(llm, [recommend_stack], react_prompt)
stack_advisor_executor = AgentExecutor(agent=stack_advisor_agent, tools=[recommend_stack], verbose=True)

plan_summary_agent = create_react_agent(llm, [summarize_installation_plan], react_prompt)
plan_summary_executor = AgentExecutor(agent=plan_summary_agent, tools=[summarize_installation_plan], verbose=True)
