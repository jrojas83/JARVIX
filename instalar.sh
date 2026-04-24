#!/bin/bash
# instalar.sh — Jarvis v5 | Linux Mint / Ubuntu / Debian
# Instala dependencias, crea entorno virtual, configura .env y Ollama.

VERDE='\033[0;32m'; AMARILLO='\033[1;33m'; ROJO='\033[0;31m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
ok()    { echo -e "${VERDE}  ✅ $1${NC}"; }
info()  { echo -e "${AMARILLO}  ℹ️  $1${NC}"; }
err()   { echo -e "${ROJO}  ❌ $1${NC}"; }
titulo(){ echo -e "\n${CYAN}${BOLD}$1${NC}"; }

JARVIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$JARVIS_DIR/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"
ENV_FILE="$JARVIS_DIR/.env"

clear
echo -e "${CYAN}${BOLD}"
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║       🤖 JARVIS v5 — Instalador completo        ║"
echo "  ║              Linux Mint / Ubuntu                 ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo -e "${NC}"
echo "  Directorio: $JARVIS_DIR"

# ── 1. Paquetes del sistema ────────────────────────────────────
titulo "[ 1/8 ] Instalando paquetes del sistema..."
sudo apt update -qq
sudo apt install -y python3 python3-pip python3-venv python3-full python3-dev \
    espeak libnotify-bin xclip xdotool portaudio19-dev libportaudio2 \
    libasound2-dev firefox curl wget network-manager rfkill blueman 2>/dev/null || true
ok "Dependencias del sistema instaladas"

# ── 2. Entorno virtual Python ─────────────────────────────────
titulo "[ 2/8 ] Creando entorno virtual Python (.venv)..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    ok "Entorno virtual creado en $VENV_DIR"
else
    ok "Entorno virtual ya existe"
fi
source "$VENV_DIR/bin/activate"
"$VENV_PIP" install --upgrade pip --quiet
ok "venv activo — pip $("$VENV_PIP" --version | cut -d' ' -f2)"

# ── 3. Dependencias Python (requirements.txt) ─────────────────
titulo "[ 3/8 ] Instalando dependencias Python..."
if [ -f "$JARVIS_DIR/requirements.txt" ]; then
    "$VENV_PIP" install -r "$JARVIS_DIR/requirements.txt" --quiet && ok "requirements.txt instalado" || err "Fallo en requirements.txt"
else
    # Fallback si no existe requirements.txt
    for pkg in requests python-dotenv SpeechRecognition pyttsx3 psutil pyaudio selenium webdriver-manager groq google-generativeai google-genai anthropic; do
        "$VENV_PIP" install --quiet "$pkg" && ok "$pkg" || err "$pkg"
    done
fi

# ── 4. Archivo .env ───────────────────────────────────────────
titulo "[ 4/8 ] Configurando API keys (.env)..."

if [ ! -f "$ENV_FILE" ]; then
    cp "$JARVIS_DIR/.env.example" "$ENV_FILE"
    ok ".env creado desde .env.example"
else
    ok ".env ya existe"
fi

echo ""
echo -e "  ${BOLD}IAs en línea disponibles:${NC}"
echo "  🟢 GROQ      — GRATIS (14.400 req/día) → console.groq.com"
echo "  🟡 GEMINI    — GRATIS (1M tokens/mes)  → aistudio.google.com/app/apikey"
echo "  🔵 ANTHROPIC — \$5 créditos iniciales   → console.anthropic.com"
echo "  🌤 OPENWEATHER — Clima gratis          → openweathermap.org/api"
echo ""
echo -e "  ${AMARILLO}Las claves se guardan en .env (nunca en Git)${NC}"
echo ""

set_env() {
    local var="$1" val="$2"
    if grep -q "^$var=" "$ENV_FILE" 2>/dev/null; then
        sed -i "s|^$var=.*|$var=$val|" "$ENV_FILE"
    else
        echo "$var=$val" >> "$ENV_FILE"
    fi
}

get_env() {
    grep "^$1=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2
}

for var_name in GROQ_API_KEY GEMINI_API_KEY ANTHROPIC_API_KEY OPENWEATHER_API_KEY; do
    current=$(get_env "$var_name")
    if [ -n "$current" ] && [ "$current" != "TU_API_KEY_AQUI" ]; then
        ok "$var_name ya configurada"
    else
        read -rp "  $var_name (Enter para saltar): " new_val
        if [ -n "$new_val" ]; then
            set_env "$var_name" "$new_val"
            ok "$var_name guardada en .env"
        else
            info "$var_name saltada"
        fi
    fi
done

# Ciudad por defecto
echo ""
read -rp "  Ciudad por defecto para clima [Cali,CO]: " ciudad
ciudad="${ciudad:-Cali,CO}"
set_env "CIUDAD_DEFAULT" "$ciudad"
ok "Ciudad: $ciudad"

# ── 5. Ollama ─────────────────────────────────────────────────
titulo "[ 5/8 ] Configurando Ollama (IA local)..."
if ! command -v ollama &>/dev/null; then
    info "Instalando Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
fi
if ! pgrep -x ollama &>/dev/null; then
    ollama serve &>/dev/null & sleep 3
fi
ok "Ollama listo"

echo ""
echo -e "  ${BOLD}Modelos Ollama disponibles:${NC}"
echo -e "  ${AMARILLO}Para Intel N100 / 8 GB RAM: opciones 1-5 recomendadas${NC}"
echo "  ── LIGEROS (usar con < 3 GB RAM libre) ──"
echo "  [1] qwen2.5:1.5b        ~1.0 GB | Más liviano viable"
echo "  [2] smollm2:1.7b        ~1.1 GB | Diseñado para hardware limitado"
echo "  [3] gemma2:2b           ~1.6 GB | Buen español"
echo "  [4] deepseek-coder:1.3b ~0.8 GB | Solo código, ultra-eficiente"
echo "  ── BALANCEADOS (3-5 GB RAM libre) ⭐ ──"
echo "  [5] qwen2.5:3b          ~1.9 GB | Balance recomendado para N100"
echo "  [6] phi3:mini           ~2.3 GB | Excelente calidad (Microsoft)"
echo "  [7] phi3.5:mini         ~2.4 GB | phi3 mejorado"
echo "  [8] llama3.2:3b         ~2.0 GB | Buen español (Meta)"
echo "  ── POTENTES (> 5 GB RAM libre) ──"
echo "  [9] mistral:7b          ~4.1 GB | Mejor calidad general"
echo "  [10] qwen2.5:7b         ~4.7 GB | Excelente para código"
echo "  [0] Saltar (ya tienes un modelo o usarás solo IA online)"
read -rp "  Modelo a descargar [5]: " mop; mop="${mop:-5}"

dm(){ ollama list 2>/dev/null | grep -q "$1" && ok "$1 ya descargado" || { info "Descargando $1..."; ollama pull "$1" && ok "$1 OK" || err "$1 falló"; }; }
case "$mop" in
    1) dm "qwen2.5:1.5b" ;;
    2) dm "smollm2:1.7b" ;;
    3) dm "gemma2:2b" ;;
    4) dm "deepseek-coder:1.3b" ;;
    5) dm "qwen2.5:3b" ;;
    6) dm "phi3:mini" ;;
    7) dm "phi3.5:mini" ;;
    8) dm "llama3.2:3b" ;;
    9) dm "mistral:7b" ;;
    10) dm "qwen2.5:7b" ;;
    0) info "Saltando modelos" ;;
    *) dm "qwen2.5:3b" ;;
esac

# Guardar modelo elegido en .env
MODELO_ELEGIDO=$(ollama list 2>/dev/null | tail -n +2 | head -1 | awk '{print $1}')
[ -n "$MODELO_ELEGIDO" ] && set_env "MODELO_OLLAMA" "$MODELO_ELEGIDO"

# ── 6. Scripts de arranque ────────────────────────────────────
titulo "[ 6/8 ] Creando scripts de arranque..."

cat > "$JARVIS_DIR/jarvis_run.sh" << RUNEOF
#!/bin/bash
cd "$JARVIS_DIR"
source "$VENV_DIR/bin/activate"
if ! pgrep -x ollama >/dev/null 2>&1; then
    ollama serve >/dev/null 2>&1 &
    sleep 2
fi
python jarvis.py "\$@"
RUNEOF
chmod +x "$JARVIS_DIR/jarvis_run.sh"
ok "jarvis_run.sh creado"

# Aliases
for line in \
    "alias jarvis='bash $JARVIS_DIR/jarvis_run.sh'" \
    "alias jarvis-voz='bash $JARVIS_DIR/jarvis_run.sh --voz'" \
    "alias jarvis-espera='bash $JARVIS_DIR/jarvis_run.sh --espera'"; do
    grep -qF "$line" ~/.bashrc || echo "$line" >> ~/.bashrc
done
ok "Aliases jarvis / jarvis-voz / jarvis-espera en ~/.bashrc"

# Acceso directo escritorio
if [ -d "$HOME/Escritorio" ]; then
    cat > "$HOME/Escritorio/Jarvis.desktop" << DESKEOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Jarvis
Comment=Asistente de escritorio con IA
Exec=bash -c 'cd $JARVIS_DIR && source $VENV_DIR/bin/activate && python jarvis.py; read -p "Presiona Enter para cerrar..."'
Icon=applications-system
Terminal=true
Categories=Utility;
DESKEOF
    chmod +x "$HOME/Escritorio/Jarvis.desktop"
    ok "Acceso directo en el Escritorio"
fi

# ── 7. Permisos ───────────────────────────────────────────────
titulo "[ 7/8 ] Permisos para WiFi y Bluetooth..."
sudo usermod -aG netdev "$USER" 2>/dev/null || true
ok "Usuario agregado al grupo netdev"

# ── 8. Verificación final ─────────────────────────────────────
titulo "[ 8/8 ] Verificación final..."
"$VENV_PYTHON" - << 'PYEOF'
import sys
print(f"  Python: {sys.version.split()[0]}")
paquetes = [
    ("requests",          "requests"),
    ("dotenv",            "python-dotenv"),
    ("speech_recognition","SpeechRecognition"),
    ("pyttsx3",           "pyttsx3"),
    ("psutil",            "psutil"),
    ("selenium",          "selenium"),
    ("groq",              "groq"),
    ("google.generativeai","google-generativeai"),
    ("anthropic",         "anthropic"),
]
for mod, nom in paquetes:
    try:
        __import__(mod); print(f"  ✅ {nom}")
    except ImportError:
        print(f"  ❌ {nom}")
import subprocess
for cmd in ["espeak","notify-send","xclip","xdotool","nmcli","rfkill","ollama"]:
    r = subprocess.run(["which", cmd], capture_output=True)
    print(f"  {'✅' if r.returncode==0 else '⚠️ '} {cmd}")
PYEOF

# Verificar que .env existe y no está vacío
if [ -f "$ENV_FILE" ] && [ -s "$ENV_FILE" ]; then
    ok ".env configurado"
else
    err ".env no encontrado o vacío"
fi

echo ""
echo -e "${VERDE}${BOLD}"
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║            ✅ ¡Instalación completa!             ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo -e "${NC}"
echo "  Formas de iniciar Jarvis:"
echo ""
echo "    bash jarvis_run.sh              → modo texto"
echo "    bash jarvis_run.sh --voz        → modo voz continua"
echo "    bash jarvis_run.sh --espera     → modo espera (di 'jarvis')"
echo ""
echo "    O abre terminal nueva y escribe:"
echo "    jarvis  /  jarvis-voz  /  jarvis-espera"
echo ""
echo -e "  ${AMARILLO}⚠️  Abre una terminal NUEVA para que los alias funcionen${NC}"
echo ""
echo -e "  ${CYAN}Logs en: ~/.jarvis.log${NC}"
echo -e "  ${CYAN}Datos en: ~/.jarvis.db${NC}"
echo ""
