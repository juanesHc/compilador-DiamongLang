"""
╔══════════════════════════════════════════════════════════╗
║   DiamondLang 💎 — Sugerencias SEMÁNTICAS con IA         ║
║              sugerencias_ia_semantica.py                 ║
║  Bonus (Modalidad A): IA como CAPA ADICIONAL sobre los   ║
║  errores semánticos detectados por las reglas clásicas.  ║
║  Cada ErrorSemantico se envía a Claude junto al          ║
║  fragmento de código relevante; Claude devuelve una      ║
║  sugerencia enriquecida en lenguaje natural.             ║
║                                                         ║
║  Es 100% opcional: sin ANTHROPIC_API_KEY o sin la        ║
║  librería `anthropic`, `disponible()` es False y         ║
║  `sugerencia_ia_semantica()` devuelve None; el sistema   ║
║  cae a la sugerencia local (sugerencias_semanticas.py).  ║
║                                                         ║
║  Diseñado en PARALELO a `sugerencias_ia.py` (la versión  ║
║  sintáctica de la Entrega 3): mismo cliente, mismo       ║
║  modelo, misma política de caché/timeout/fallback. Ver   ║
║  la nota de "deuda futura" sobre compartir el helper de  ║
║  fragmento de código.                                    ║
╚══════════════════════════════════════════════════════════╝

Activación:
    export ANTHROPIC_API_KEY=...
    pip install anthropic
"""

import os
from pathlib import Path

# ── Carga portable del archivo .env (igual que sugerencias_ia.py) ──
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


# ── Configuración (paridad con sugerencias_ia.py) ──────────
# Modelo configurable por variable de entorno; por defecto el mismo
# Haiku 4.5 rápido/económico que usa la fase sintáctica.
MODELO_IA   = os.environ.get("DIAMOND_IA_SEMANTICA_MODELO", "claude-haiku-4-5")
MAX_TOKENS  = 250
TIMEOUT_SEG = 10

# Cache en memoria por (regla, mensaje, lexema). El módulo expone uno por
# defecto, pero `sugerencia_ia_semantica` también acepta un cache externo
# (el server.py mantiene el suyo vivo entre peticiones).
_cache: dict = {}


# ══════════════════════════════════════════════
#  DISPONIBILIDAD
# ══════════════════════════════════════════════

def disponible() -> bool:
    """True si está la librería `anthropic` y la variable de entorno."""
    return Anthropic is not None and bool(os.environ.get("ANTHROPIC_API_KEY"))


def info() -> dict:
    """Diagnóstico para el endpoint /ping_ia_semantica."""
    return {
        'libreria_instalada': Anthropic is not None,
        'api_key_presente':   bool(os.environ.get("ANTHROPIC_API_KEY")),
        'disponible':         disponible(),
        'modelo':             MODELO_IA,
        'ambito':             'semantica',
    }


# ══════════════════════════════════════════════
#  CONSTRUCCIÓN DEL PROMPT
# ══════════════════════════════════════════════

def _fragmento_codigo(codigo_fuente: str, fila: int, columna: int,
                      ventana: int = 2) -> str:
    """
    Genera un fragmento de código con 5 líneas (ventana=2 a cada lado de
    `fila`) y un marcador ↑ apuntando a la columna del error.

    NOTA (deuda futura): esta función es idéntica a la de
    `sugerencias_ia.py`. Se duplica a propósito para que los dos módulos
    de IA sean independientes (decisión de la Etapa 9). Una refactorización
    razonable sería extraer un módulo `ia_comun.py` con el cliente, el
    builder de fragmento y la política de caché compartidos.
    """
    if fila is None or fila <= 0:
        return "(sin posición en el código)"

    lineas = codigo_fuente.splitlines()
    if not lineas:
        return "(código vacío)"

    inicio = max(0, fila - 1 - ventana)
    fin    = min(len(lineas), fila + ventana)

    col = columna if (columna and columna > 0) else 1
    salida = []
    for idx in range(inicio, fin):
        prefijo = f"{idx + 1:>3} │ "
        salida.append(prefijo + lineas[idx])
        if (idx + 1) == fila:
            espacios = ' ' * (len(prefijo) + max(0, col - 1))
            salida.append(espacios + "↑")

    return "\n".join(salida)


def _contexto_legible(contexto: dict) -> str:
    """Serializa el dict `contexto` del error a 'k=v · k=v' (o '(sin datos)')."""
    if not contexto:
        return "(sin datos adicionales)"
    return " · ".join(f"{k}={v}" for k, v in contexto.items())


def construir_prompt(error, codigo_fuente: str) -> str:
    """
    Arma el prompt en español que enviamos a Claude para un error
    SEMÁNTICO. Es instructivo (no abierto): pide explicar el porqué y
    proponer una corrección concreta, en máximo 2-3 frases.
    """
    fragmento = _fragmento_codigo(codigo_fuente, error.fila, error.columna)
    contexto  = _contexto_legible(error.contexto)
    lexema    = error.lexema if error.lexema not in (None, "") else "(no aplica)"

    return (
        "Eres un asistente de un compilador para DiamondLang, un lenguaje "
        "de programación educativo cuyas palabras clave están en español "
        "(funcion, fin_funcion, si, entonces, sino, fin_si, mientras, "
        "hacer, fin_mientras, para, retornar, leer, escribir; tipos: "
        "entero, real, cadena, booleano, vacio; asignación: '<-'; "
        "operadores lógicos: y, o, no).\n\n"
        "El análisis SEMÁNTICO (no el sintáctico) detectó este error:\n\n"
        f"Regla: {error.regla}\n"
        f"Mensaje: {error.mensaje}\n"
        f"Lexema: '{lexema}' en línea {error.fila}, columna {error.columna}\n"
        f"Contexto adicional: {contexto}\n"
        f"Sugerencia local (punto de partida; mejórala, no la contradigas): "
        f"{error.sugerencia}\n\n"
        "Código fuente alrededor del error (la línea con ↑ marca la "
        "columna):\n"
        "```\n"
        f"{fragmento}\n"
        "```\n\n"
        "Responde en español, en MÁXIMO 2-3 frases, como un compañero de "
        "clase (sin jerga de compiladores). Explica POR QUÉ ocurre el "
        "error, propón una CORRECCIÓN concreta y, si aplica, por qué el "
        "programador pudo cometerlo (orden de declaración, tipo "
        "equivocado, aridad, etc.). Devuelve solo la sugerencia, sin "
        "prefijos como 'Sugerencia:' ni comillas."
    )


# ══════════════════════════════════════════════
#  LLAMADA A LA API
# ══════════════════════════════════════════════

def sugerencia_ia_semantica(error, codigo_fuente: str, cache=None):
    """
    Devuelve una sugerencia enriquecida por Claude para el error
    semántico dado, o None si la IA no está disponible / falla / timeout.

    Parámetros:
        error:         ErrorSemantico (objeto, no dict).
        codigo_fuente: el programa completo, para extraer el fragmento.
        cache:         dict opcional. Si se pasa, se usa como caché
                       (clave (regla, mensaje, lexema)); si es None, se
                       usa el caché de módulo. El llamador (server.py)
                       pasa su propio dict para mantenerlo vivo entre
                       peticiones.

    Retorna:
        - str con la sugerencia mejorada si la API responde a tiempo.
        - None si la IA no está disponible, hay timeout, o cualquier
          fallo de red/API. El llamador debe conservar la sugerencia local.
    """
    if not disponible():
        return None

    almacen = cache if cache is not None else _cache
    clave_cache = (error.regla, error.mensaje, error.lexema)
    if clave_cache in almacen:
        return almacen[clave_cache]

    prompt = construir_prompt(error, codigo_fuente)

    try:
        client = Anthropic(timeout=TIMEOUT_SEG)
        resp = client.messages.create(
            model=MODELO_IA,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        if not resp.content:
            return None
        texto = resp.content[0].text.strip()

        if texto.startswith('"') and texto.endswith('"'):
            texto = texto[1:-1].strip()

        almacen[clave_cache] = texto
        return texto

    except Exception as e:
        # Cualquier fallo (red, timeout, API) → None y caemos a la local.
        print(f"[IA-semántica] {type(e).__name__}: {e}")
        return None


def limpiar_cache():
    """Vacía la cache de módulo (útil para tests)."""
    _cache.clear()


# ══════════════════════════════════════════════
#  PRUEBA RÁPIDA
# ══════════════════════════════════════════════

if __name__ == '__main__':
    print("Diagnóstico IA semántica:")
    for k, v in info().items():
        print(f"  {k}: {v}")
    print()

    if not disponible():
        print("IA no disponible. Define ANTHROPIC_API_KEY e instala anthropic.")
        print("(El sistema seguirá funcionando con sugerencias locales.)")
    else:
        from errores_semanticos import ErrorSemantico
        e = ErrorSemantico(
            indice=1, fila=3, columna=12,
            lexema='x', regla='TIPO_ASIGNACION',
            mensaje=("No se puede asignar un valor de tipo 'cadena' a una "
                     "variable de tipo 'entero'."),
            sugerencia=("No puedes asignar un valor de tipo 'cadena' a una "
                        "variable de tipo 'entero'."),
            contexto={'tipo_destino': 'entero', 'tipo_recibido': 'cadena',
                      'identificador': 'x'},
        )
        codigo = ("funcion principal() retornar entero\n"
                  "hacer\n"
                  "    entero x <- \"hola\"\n"
                  "    retornar 0\n"
                  "fin_funcion\n")
        print("Respuesta IA:", sugerencia_ia_semantica(e, codigo))
