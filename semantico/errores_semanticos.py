"""
╔══════════════════════════════════════════════════════════╗
║   DiamondLang 💎 — Modelo de error semántico             ║
║                errores_semanticos.py                     ║
║  Entrega 4 — Etapa 2: infraestructura.                   ║
║                                                         ║
║  Paralelo a `errores.py` (ErrorSintactico) pero          ║
║  pensado para el análisis semántico:                     ║
║    - reporta por REGLA (decl duplicada, uso no           ║
║      declarado, incompatibilidad de tipos, …),           ║
║    - distingue lexema vs no aplica (None),               ║
║    - incluye un campo `contexto: dict` libre para        ║
║      acompañar datos auxiliares (útil para el            ║
║      bonus IA y para diagnósticos finos).                ║
╚══════════════════════════════════════════════════════════╝
"""

from dataclasses import dataclass, field, asdict


# ══════════════════════════════════════════════
#  DATACLASS PRINCIPAL
# ══════════════════════════════════════════════

@dataclass
class ErrorSemantico:
    """
    Un único error semántico detectado durante el análisis. Es
    serializable a `dict` para incluirse en la respuesta JSON.
    """
    indice: int
    fila: int = None                          # None si la posición no aplica
    columna: int = None
    lexema: str = None                        # token ofensor (None si N/A)
    regla: str = ""                           # ej. "DECL_DUPLICADA"
    mensaje: str = ""                         # texto en español
    sugerencia: str = None                    # estilo "¿quiso decir?"; opt.
    fuente_sugerencia: str = "local"          # 'local' | 'ia'
    contexto: dict = field(default_factory=dict)


def como_dict(error: ErrorSemantico) -> dict:
    """
    Serializa un `ErrorSemantico` a un `dict` JSON-friendly.
    Todas las claves quedan en snake_case (mismo nombre que el campo).
    """
    return asdict(error)


# ══════════════════════════════════════════════
#  FORMATEADORES DE TEXTO (estilo errores.py)
# ══════════════════════════════════════════════

def _ubicacion(e: ErrorSemantico) -> str:
    if e.fila is None or e.fila <= 0:
        return "ubicación no disponible"
    if e.columna is None or e.columna <= 0:
        return f"línea {e.fila}"
    return f"línea {e.fila}, columna {e.columna}"


def formatear_error(e: ErrorSemantico) -> str:
    """
    Formato visual paralelo al de `errores.formatear_error`:

        Error semántico [N] — línea L, columna C   (REGLA)
          Mensaje      : ...
          Lexema       : '...'        (opcional)
          Contexto     : k=v · k=v    (opcional)
          ¿Quiso decir? : ...         (opcional)
    """
    loc = _ubicacion(e)
    cabecera = f"Error semántico [{e.indice}] — {loc}"
    if e.regla:
        cabecera += f"   ({e.regla})"

    lineas = [cabecera, f"  Mensaje      : {e.mensaje}"]

    if e.lexema is not None and e.lexema != "":
        lineas.append(f"  Lexema       : '{e.lexema}'")

    if e.contexto:
        pares = " · ".join(f"{k}={v!r}" for k, v in e.contexto.items())
        lineas.append(f"  Contexto     : {pares}")

    if e.sugerencia:
        lineas.append(f"  ¿Quiso decir? : {e.sugerencia.strip()}")

    return "\n".join(lineas)


def formatear_lista(errores) -> str:
    """
    Texto plano con todos los errores semánticos separados por línea
    en blanco. Mensaje afirmativo si la lista está vacía.
    """
    if not errores:
        return "✓ Sin errores semánticos."
    return "\n\n".join(formatear_error(e) for e in errores)


# ══════════════════════════════════════════════
#  PRUEBAS BÁSICAS
# ══════════════════════════════════════════════

if __name__ == '__main__':
    e1 = ErrorSemantico(
        indice=1, fila=3, columna=12,
        lexema='x', regla='DECL_DUPLICADA',
        mensaje="La variable 'x' ya está declarada en el ámbito 'principal'.",
        sugerencia="Renómbrala o reutiliza la declaración existente.",
        contexto={'declaracion_previa': 'línea 2'},
    )
    e2 = ErrorSemantico(
        indice=2, fila=5, columna=1,
        regla='TIPO_CONDICION',
        mensaje="La condición de 'si' debe ser booleana; se encontró 'entero'.",
        contexto={'tipo_recibido': 'entero', 'tipo_esperado': 'booleano'},
    )
    print(formatear_lista([e1, e2]))
    print()
    print("Dict:", como_dict(e1))
