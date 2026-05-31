"""
╔══════════════════════════════════════════════════════════╗
║   DiamondLang 💎 — Cliente Anthropic Claude (Fase 5b)    ║
║                 cliente_anthropic.py                     ║
║  Wrapper autocontenido sobre el SDK `anthropic`, paralelo ║
║  a cliente_gemini.py. Lo usa el endpoint /chat cuando el  ║
║  usuario elige Claude Haiku.                              ║
║                                                          ║
║  NOTA: las sugerencias SEMÁNTICAS siguen usando su propio ║
║  módulo (sugerencias_ia_semantica.py) sin cambios. Este   ║
║  cliente genérico existe para el chatbot multi-modelo, de ║
║  modo que /chat trate a Claude y a Gemini de forma        ║
║  simétrica (mismo contrato `disponible()` / `responder()`).║
╚══════════════════════════════════════════════════════════╝

Activación:
    export ANTHROPIC_API_KEY=...
    pip install anthropic
"""

import os
from pathlib import Path

# ── Carga portable del archivo .env (igual patrón que el resto) ──
_RAIZ_PROYECTO = Path(__file__).resolve().parent
_RUTA_ENV      = _RAIZ_PROYECTO / ".env"

try:
    from dotenv import load_dotenv
    if _RUTA_ENV.is_file():
        load_dotenv(dotenv_path=_RUTA_ENV, override=False)
except ImportError:
    pass

# Importación perezosa de la librería oficial de Anthropic.
try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None


# ── Configuración ──────────────────────────────
MODELO_CLAUDE = os.environ.get("DIAMOND_CLAUDE_MODELO", "claude-haiku-4-5")
MAX_TOKENS    = 600
TIMEOUT_SEG   = 15.0

_cache: dict = {}


# ══════════════════════════════════════════════
#  DISPONIBILIDAD
# ══════════════════════════════════════════════

def disponible() -> bool:
    """True si está la librería `anthropic` y la variable de entorno."""
    return Anthropic is not None and bool(os.environ.get("ANTHROPIC_API_KEY"))


def info() -> dict:
    """Diagnóstico (mismo schema que info() de sugerencias_ia*.py)."""
    return {
        'libreria_instalada': Anthropic is not None,
        'api_key_presente':   bool(os.environ.get("ANTHROPIC_API_KEY")),
        'disponible':         disponible(),
        'modelo':             MODELO_CLAUDE,
    }


# ══════════════════════════════════════════════
#  LLAMADA A LA API
# ══════════════════════════════════════════════

def responder(prompt: str, system: str | None = None,
              timeout: float = TIMEOUT_SEG, cache=None,
              max_tokens: int | None = None):
    """
    Envía `prompt` a Claude y devuelve la respuesta en texto.
    Mismo contrato que cliente_gemini.responder() para que /chat sea
    simétrico. Devuelve None ante cualquier fallo (red, timeout, API).

    `max_tokens` es opcional: si no se pasa, se usa el default MAX_TOKENS
    (suficiente para el chat). El endpoint /validar_julia (Fase D, bonus IA)
    pide un tope mayor porque la auditoría devuelve un JSON estructurado más
    largo que una respuesta de chat.
    """
    if not disponible():
        return None

    almacen = cache if cache is not None else _cache
    clave = (system or '', prompt)
    if clave in almacen:
        return almacen[clave]

    try:
        client = Anthropic(timeout=timeout)
        kwargs = {
            'model':      MODELO_CLAUDE,
            'max_tokens': max_tokens or MAX_TOKENS,
            'messages':   [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs['system'] = system
        resp = client.messages.create(**kwargs)
        if not resp.content:
            return None
        texto = resp.content[0].text.strip()

        if texto.startswith('"') and texto.endswith('"'):
            texto = texto[1:-1].strip()

        almacen[clave] = texto
        return texto

    except Exception as e:
        print(f"[Claude-chat] {type(e).__name__}: {e}")
        return None


def limpiar_cache():
    """Vacía la caché de módulo (útil para tests)."""
    _cache.clear()


if __name__ == '__main__':
    print("Diagnóstico Claude (chat):")
    for k, v in info().items():
        print(f"  {k}: {v}")
    if disponible():
        print("Respuesta:", responder(
            "¿Qué es DiamondLang en una frase?",
            system="Eres un asistente conciso. Responde en español, una sola frase.",
        ))
