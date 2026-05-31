"""
╔══════════════════════════════════════════════════════════╗
║   DiamondLang 💎 — Modelo de error sintáctico            ║
║                  errores.py                             ║
║  Entrega 3: reporte detallado de errores con            ║
║  recuperación en modo pánico.                           ║
╚══════════════════════════════════════════════════════════╝

Cada error sintáctico se representa con un dataclass
`ErrorSintactico` que captura:
    - índice (1..N), fila y columna del fuente original
    - lexema y tipo del token encontrado
    - lista de tokens esperados según la gramática LL(1)
    - no-terminal en curso al fallar y producción intentada
    - sugerencia en español ("¿Quiso decir?") y su origen
"""

from dataclasses import dataclass, field, asdict


# ══════════════════════════════════════════════
#  DATACLASS PRINCIPAL
# ══════════════════════════════════════════════

@dataclass
class ErrorSintactico:
    """
    Representa un único error sintáctico detectado durante
    el análisis. Es serializable a dict para mandarse al
    frontend vía JSON.
    """
    indice: int
    fila: int
    columna: int
    lexema: str
    tipo_token: str
    tokens_esperados: list = field(default_factory=list)
    no_terminal: str = ""
    produccion_intentada: str = None
    sugerencia: str = ""
    fuente_sugerencia: str = "local"   # 'local' | 'ia' | 'fallback'

    def to_dict(self) -> dict:
        """Convierte a diccionario JSON-serializable."""
        d = asdict(self)
        # produccion_intentada puede ser None: lo dejamos como tal
        return d


# ══════════════════════════════════════════════
#  FORMATEADORES DE TEXTO
# ══════════════════════════════════════════════

def _normalizar_posicion(error: ErrorSintactico):
    """
    Devuelve (fila, columna) corregidos. EOF se reporta como
    'final del archivo' usando la última posición conocida (1,1)
    si el lexer envió -1.
    """
    fila = error.fila if error.fila > 0 else 0
    col  = error.columna if error.columna > 0 else 0
    return fila, col


def formatear_error(e: ErrorSintactico) -> str:
    """
    Genera el bloque de texto plano correspondiente a un error.

    Formato:
        Error sintáctico [N] — línea L, columna C
          Encontrado : lexema='...' tipo=...
          Esperado   : TOKEN_A | TOKEN_B | ...
          ¿Quiso decir? : ...
    """
    fila, col = _normalizar_posicion(e)

    if fila == 0:
        loc = "final del archivo"
    else:
        loc = f"línea {fila}, columna {col}"

    if e.lexema == '$' or e.tipo_token == '$':
        encontrado = "fin de archivo"
    else:
        encontrado = f"lexema='{e.lexema}' tipo={e.tipo_token}"

    if e.tokens_esperados:
        esperados = " | ".join(e.tokens_esperados)
    else:
        esperados = "(sin información)"

    sug = e.sugerencia.strip() or "(sin sugerencia)"

    return (
        f"Error sintáctico [{e.indice}] — {loc}\n"
        f"  Encontrado : {encontrado}\n"
        f"  Esperado   : {esperados}\n"
        f"  ¿Quiso decir? : {sug}"
    )


def formatear_lista(errores) -> str:
    """
    Formatea la lista completa de errores separados por línea
    en blanco. Si la lista está vacía devuelve un mensaje OK.
    """
    if not errores:
        return "✓ Sin errores sintácticos."
    return "\n\n".join(formatear_error(e) for e in errores)


# ══════════════════════════════════════════════
#  PRUEBAS BÁSICAS
# ══════════════════════════════════════════════

if __name__ == '__main__':
    e1 = ErrorSintactico(
        indice=1, fila=3, columna=12,
        lexema='hacer', tipo_token='KEYWORD',
        tokens_esperados=['entonces'],
        no_terminal='sent_si',
        produccion_intentada='si expresion entonces bloque rama_sino fin_si',
        sugerencia="Falta la palabra clave 'entonces' después de la condición del 'si'.",
    )
    e2 = ErrorSintactico(
        indice=2, fila=5, columna=1,
        lexema='$', tipo_token='$',
        tokens_esperados=['fin_si'],
        no_terminal='sent_si',
        sugerencia="Falta cerrar el bloque con 'fin_si'.",
    )
    print(formatear_lista([e1, e2]))
    print()
    print("Dict:", e1.to_dict())
