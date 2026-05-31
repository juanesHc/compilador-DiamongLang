"""
╔══════════════════════════════════════════════════════════╗
║   DiamondLang 💎 — Sugerencias SINTÁCTICAS con IA        ║
║                  sugerencias_ia.py                       ║
║  Bonus: enriquece las sugerencias locales de errores      ║
║  SINTÁCTICOS con un modelo de lenguaje.                   ║
║                                                          ║
║  ▸ Fase 5b: MIGRADO de Anthropic (Claude) a Google        ║
║    (Gemini Flash) vía `cliente_gemini`. La fase IA         ║
║    SEMÁNTICA (sugerencias_ia_semantica.py) sigue usando    ║
║    Claude, sin cambios.                                   ║
║                                                          ║
║  El CONTRATO PÚBLICO se conserva intacto para no romper    ║
║  a server.py ni al frontend:                              ║
║    · disponible() -> bool                                 ║
║    · info() -> dict  (mismas claves; 'modelo' ahora Gemini)║
║    · sugerencia_ia(error, codigo_fuente, cache=None) -> str|None
║    · construir_prompt(error, codigo_fuente) -> str         ║
║    · limpiar_cache()                                      ║
║                                                          ║
║  Es 100% opcional: sin GOOGLE_API_KEY o sin google-genai, ║
║  `disponible()` es False y `sugerencia_ia()` devuelve None;║
║  el sistema cae a la sugerencia local.                    ║
╚══════════════════════════════════════════════════════════╝

Activación:
    export GOOGLE_API_KEY=...        # (o GEMINI_API_KEY)
    pip install google-genai
"""

# El cliente Gemini ya carga el .env (ruta absoluta) y hace la importación
# perezosa del SDK; reutilizamos ese módulo en vez de duplicar la lógica.
from ai import cliente_gemini


# ── Configuración ──────────────────────────────
# El modelo real lo decide cliente_gemini (MODELO_GEMINI). Aquí solo
# exponemos una etiqueta legible para info()/diagnóstico.
MODELO_IA   = "Gemini Flash"
TIMEOUT_SEG = 10

# Caché en memoria por (no_terminal, esperados, lexema): evita pedir dos
# veces la misma sugerencia dentro de un mismo análisis. Se conserva la
# MISMA clave y semántica que en la versión Claude.
_cache: dict = {}

# Instrucción de sistema (rol). En la versión Claude esto iba dentro del
# único prompt; con Gemini lo separamos como system_instruction y dejamos en
# el prompt solo los datos del caso.
SYSTEM_SINTACTICO = (
    "Eres un asistente que ayuda a estudiantes de programación con errores "
    "sintácticos en DiamondLang, un lenguaje educativo cuyas palabras clave "
    "están en español (funcion, fin_funcion, si, entonces, sino, fin_si, "
    "mientras, hacer, fin_mientras, para, desde, hasta, paso, fin_para, "
    "retornar, leer, escribir; operadores lógicos: y, o, no; asignación: "
    "'<-'). Da UNA sugerencia BREVE (máximo 2 frases), en español natural, "
    "como un compañero de clase. NO reproduzcas la gramática formal ni uses "
    "jerga compiladora. No uses markdown, listas ni encabezados; responde en "
    "texto plano, sin comillas ni prefijos como 'Sugerencia:'."
)


# ══════════════════════════════════════════════
#  DISPONIBILIDAD
# ══════════════════════════════════════════════

def disponible() -> bool:
    """True si Gemini está disponible (librería google-genai + API key)."""
    return cliente_gemini.disponible()


def info() -> dict:
    """
    Diagnóstico para el endpoint /ping_ia. Mantiene EXACTAMENTE las mismas
    claves que la versión Claude para no romper el frontend (pingIA() lee
    'disponible', 'modelo' y 'libreria_instalada'); solo cambia el proveedor.
    """
    base = cliente_gemini.info()
    return {
        'libreria_instalada': base['libreria_instalada'],
        'api_key_presente':   base['api_key_presente'],
        'disponible':         base['disponible'],
        'modelo':             MODELO_IA,          # "Gemini Flash"
        'proveedor':          'google',
    }


# ══════════════════════════════════════════════
#  CONSTRUCCIÓN DEL PROMPT
# ══════════════════════════════════════════════

def _fragmento_codigo(codigo_fuente: str, fila: int, columna: int,
                      ventana: int = 2) -> str:
    """
    Genera un fragmento de código con 5 líneas (ventana=2 a cada
    lado de `fila`) y un marcador ↑ apuntando a la columna del error.
    """
    if fila <= 0:
        return "(error al final del archivo)"

    lineas = codigo_fuente.splitlines()
    if not lineas:
        return "(código vacío)"

    inicio = max(0, fila - 1 - ventana)
    fin    = min(len(lineas), fila + ventana)

    salida = []
    for idx in range(inicio, fin):
        prefijo = f"{idx + 1:>3} │ "
        salida.append(prefijo + lineas[idx])
        if (idx + 1) == fila:
            # Marcador ↑ alineado con `columna`
            espacios = ' ' * (len(prefijo) + max(0, columna - 1))
            salida.append(espacios + "↑")

    return "\n".join(salida)


def construir_prompt(error, codigo_fuente: str) -> str:
    """
    Arma el contenido del usuario (datos del caso) que enviamos a Gemini.
    El rol/instrucciones van aparte, en SYSTEM_SINTACTICO.
    """
    fragmento = _fragmento_codigo(codigo_fuente, error.fila, error.columna)
    esperados = ", ".join(error.tokens_esperados) or "(sin información)"

    return (
        "Código alrededor del error (la línea con ↑ marca la columna):\n"
        "```\n"
        f"{fragmento}\n"
        "```\n\n"
        "Información del parser:\n"
        f"- No-terminal en curso: {error.no_terminal}\n"
        f"- Tokens esperados:     {esperados}\n"
        f"- Encontrado:           lexema='{error.lexema}' "
        f"tipo={error.tipo_token}\n"
        f"- Sugerencia local:     {error.sugerencia}\n\n"
        "Devuelve solo la sugerencia mejorada, en máximo 2 frases."
    )


# ══════════════════════════════════════════════
#  LLAMADA A LA API (vía cliente_gemini)
# ══════════════════════════════════════════════

def sugerencia_ia(error, codigo_fuente: str, cache=None):
    """
    Solicita a Gemini una sugerencia mejorada para el error sintáctico dado.

    Parámetros:
        error:         ErrorSintactico (objeto, no dict).
        codigo_fuente: el programa completo, para extraer el fragmento.
        cache:         dict opcional. Si se pasa, se usa como caché; si es
                       None se usa el caché de módulo. (Parámetro nuevo en
                       5b, OPCIONAL y retrocompatible: server.py sigue
                       llamando con 2 argumentos.)

    Retorna:
        - str con la sugerencia mejorada si la API responde a tiempo.
        - None si la IA no está disponible, hay timeout, o cualquier fallo.
          El llamador debe caer a la sugerencia local.
    """
    if not disponible():
        return None

    almacen = cache if cache is not None else _cache
    clave_cache = (
        error.no_terminal,
        tuple(error.tokens_esperados[:3]),
        error.lexema,
    )
    if clave_cache in almacen:
        return almacen[clave_cache]

    prompt = construir_prompt(error, codigo_fuente)

    # cliente_gemini.responder ya captura todas las excepciones y devuelve
    # None ante cualquier fallo; aun así protegemos por si acaso.
    try:
        texto = cliente_gemini.responder(
            prompt, system=SYSTEM_SINTACTICO, timeout=TIMEOUT_SEG,
        )
    except Exception as e:
        print(f"[IA-sintáctica] {type(e).__name__}: {e}")
        return None

    if texto:
        almacen[clave_cache] = texto
    return texto


def limpiar_cache():
    """Vacía la cache de sugerencias IA (útil para tests)."""
    _cache.clear()


# ══════════════════════════════════════════════
#  PRUEBA RÁPIDA
# ══════════════════════════════════════════════

if __name__ == '__main__':
    print("Diagnóstico IA (sintáctica, ahora Gemini):")
    for k, v in info().items():
        print(f"  {k}: {v}")
    print()

    if not disponible():
        print("IA no disponible. Define GOOGLE_API_KEY e instala google-genai.")
        print("(El sistema seguirá funcionando con sugerencias locales.)")
    else:
        from sintactico.errores import ErrorSintactico
        e = ErrorSintactico(
            indice=1, fila=3, columna=14,
            lexema='hacer', tipo_token='KEYWORD',
            tokens_esperados=['entonces'],
            no_terminal='sent_si',
            sugerencia="Falta 'entonces' después de la condición del 'si'.",
        )
        codigo = "funcion p() hacer\n  si x > 0 hacer\n    escribir(x)\n  fin_si\nfin_funcion"
        print("Respuesta IA:", sugerencia_ia(e, codigo))
