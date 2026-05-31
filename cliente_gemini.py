"""
╔══════════════════════════════════════════════════════════╗
║   DiamondLang 💎 — Cliente Google Gemini (Fase 5b)       ║
║                  cliente_gemini.py                       ║
║  Wrapper autocontenido sobre el SDK moderno `google-genai`║
║  (paquete `google.genai`). Lo usan:                       ║
║    · el endpoint /chat   (cuando el usuario elige Gemini) ║
║    · sugerencias_ia.py   (sugerencias SINTÁCTICAS, que    ║
║                           migraron de Claude a Gemini)    ║
║                                                          ║
║  Es 100% opcional: si la librería no está instalada o no  ║
║  hay GOOGLE_API_KEY (o GEMINI_API_KEY), `disponible()`    ║
║  es False y `responder()` devuelve None. El llamador cae  ║
║  a su comportamiento local (sugerencia local / placeholder).║
╚══════════════════════════════════════════════════════════╝

Activación:
    export GOOGLE_API_KEY=...        # (o GEMINI_API_KEY)
    pip install google-genai

Patrón calcado de sugerencias_ia*.py: importación perezosa, carga
portable del .env con ruta absoluta, caché en memoria, timeout y
fallback a None ante cualquier fallo.
"""

import os
from pathlib import Path

# ── Carga portable del archivo .env (mismo patrón que sugerencias_ia*.py) ──
_RAIZ_PROYECTO = Path(__file__).resolve().parent
_RUTA_ENV      = _RAIZ_PROYECTO / ".env"

try:
    from dotenv import load_dotenv
    if _RUTA_ENV.is_file():
        load_dotenv(dotenv_path=_RUTA_ENV, override=False)
except ImportError:
    pass

# Importación perezosa del SDK de Google. Si no está instalado, la app
# arranca igual y `disponible()` reporta False.
try:
    from google import genai as _genai
    from google.genai import types as _genai_types
except ImportError:
    _genai = None
    _genai_types = None


# ── Configuración ──────────────────────────────
# Flash más reciente: rápido y económico, ideal para mensajes cortos en
# español. Configurable por variable de entorno en una línea.
MODELO_GEMINI = os.environ.get("DIAMOND_GEMINI_MODELO", "gemini-2.5-flash")
MAX_TOKENS    = 600          # margen amplio: con thinking desactivado sobra
TIMEOUT_SEG   = 15.0

# Caché en memoria por (system, prompt). El módulo expone uno por defecto;
# `responder()` también acepta un dict externo (mismo patrón que la fase IA).
_cache: dict = {}


def _api_key():
    """La key de Google: acepta GOOGLE_API_KEY o GEMINI_API_KEY (alias común)."""
    return os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")


# ══════════════════════════════════════════════
#  DISPONIBILIDAD
# ══════════════════════════════════════════════

def disponible() -> bool:
    """True si está la librería `google-genai` y hay API key en el entorno."""
    return _genai is not None and bool(_api_key())


def info() -> dict:
    """Diagnóstico (mismo schema que info() de sugerencias_ia*.py)."""
    return {
        'libreria_instalada': _genai is not None,
        'api_key_presente':   bool(_api_key()),
        'disponible':         disponible(),
        'modelo':             MODELO_GEMINI,
    }


# ══════════════════════════════════════════════
#  LLAMADA A LA API
# ══════════════════════════════════════════════

def responder(prompt: str, system: str | None = None,
              timeout: float = TIMEOUT_SEG, cache=None):
    """
    Envía `prompt` a Gemini Flash y devuelve la respuesta en texto.

    Parámetros:
        prompt:  el contenido del usuario (puede incluir contexto/historial).
        system:  instrucción de sistema opcional (rol del asistente).
        timeout: segundos máximos de espera (se traduce a ms para el SDK).
        cache:   dict opcional para cachear por (system, prompt); si es None
                 se usa el caché de módulo.

    Retorna:
        - str con la respuesta si la API responde a tiempo.
        - None si Gemini no está disponible, hay timeout o cualquier fallo.
    """
    if not disponible():
        return None

    almacen = cache if cache is not None else _cache
    clave = (system or '', prompt)
    if clave in almacen:
        return almacen[clave]

    try:
        client = _genai.Client(
            api_key=_api_key(),
            http_options=_genai_types.HttpOptions(timeout=int(timeout * 1000)),
        )
        # Desactivamos el "thinking" del 2.5-flash: para respuestas cortas
        # no aporta y, con un max_output_tokens bajo, podría consumir todo el
        # presupuesto y devolver texto vacío.
        cfg_kwargs = {
            'max_output_tokens': MAX_TOKENS,
            'thinking_config': _genai_types.ThinkingConfig(thinking_budget=0),
        }
        if system:
            cfg_kwargs['system_instruction'] = system
        config = _genai_types.GenerateContentConfig(**cfg_kwargs)

        resp = client.models.generate_content(
            model=MODELO_GEMINI,
            contents=prompt,
            config=config,
        )
        texto = (getattr(resp, 'text', None) or '').strip()
        if not texto:
            return None

        # Limpieza ligera: quita comillas envolventes si las hubiera.
        if texto.startswith('"') and texto.endswith('"'):
            texto = texto[1:-1].strip()

        almacen[clave] = texto
        return texto

    except Exception as e:
        # Cualquier fallo (red, timeout, API, cuota) → None y el llamador
        # cae a su comportamiento local.
        print(f"[Gemini] {type(e).__name__}: {e}")
        return None


def limpiar_cache():
    """Vacía la caché de módulo (útil para tests)."""
    _cache.clear()


# ══════════════════════════════════════════════
#  PRUEBA RÁPIDA
# ══════════════════════════════════════════════

if __name__ == '__main__':
    print("Diagnóstico Gemini:")
    for k, v in info().items():
        print(f"  {k}: {v}")
    print()

    if not disponible():
        print("Gemini no disponible. Define GOOGLE_API_KEY e instala google-genai.")
    else:
        r = responder(
            "¿Qué es DiamondLang en una frase?",
            system="Eres un asistente conciso. Responde en español, una sola frase.",
        )
        print("Respuesta Gemini:", r)
