"""
╔══════════════════════════════════════════════════════════╗
║   DiamondLang 💎 — Nodo del árbol sintáctico unificado   ║
║                       arbol.py                          ║
║  Definición común para ambos parsers (recursivo y       ║
║  predictivo). Misma forma pública que en E3, más dos    ║
║  campos opcionales `linea` y `columna` que la Etapa 1   ║
║  del análisis semántico necesita para reportar errores  ║
║  con posición.                                          ║
╚══════════════════════════════════════════════════════════╝
"""

import uuid


class NodoArbol:
    """
    Representa un nodo del árbol sintáctico.
      - etiqueta:    nombre del no-terminal o lexema del terminal
      - es_terminal: True si es hoja (token o ε)
      - es_error:    True si es un marcador sintético del modo pánico
      - hijos:       lista de NodoArbol
      - id:          identificador único corto para dibujar el árbol
      - linea:       línea original del token (None si no aplica)
      - columna:     columna original del token (None si no aplica)
    """

    def __init__(self, etiqueta: str, es_terminal: bool = False,
                 es_error: bool = False,
                 linea: int = None, columna: int = None):
        self.etiqueta    = etiqueta
        self.es_terminal = es_terminal
        self.es_error    = es_error
        self.hijos       = []
        self.id          = str(uuid.uuid4())[:8]
        self.linea       = linea
        self.columna     = columna

    def agregar_hijo(self, nodo):
        self.hijos.append(nodo)
        return nodo


def propagar_posicion_terminales(raiz: NodoArbol) -> None:
    """
    Recorre el árbol en post-orden y, para cada nodo no terminal cuya
    posición (linea/columna) siga en None, copia la del primer
    descendiente terminal con posición no nula.

    No toca nodos terminales — su posición ya viene del Token original
    (o se queda en None si el terminal es sintético: ε o ERROR<...>
    insertado sin token).
    """
    _propagar(raiz)


def _propagar(nodo: NodoArbol):
    """Helper recursivo. Devuelve la posición del nodo (puede seguir None)."""
    if not nodo.hijos:
        return nodo.linea, nodo.columna

    primer_pos = None
    for hijo in nodo.hijos:
        pos_hijo = _propagar(hijo)
        if primer_pos is None and pos_hijo[0] is not None:
            primer_pos = pos_hijo

    if nodo.linea is None and primer_pos is not None:
        nodo.linea, nodo.columna = primer_pos

    return nodo.linea, nodo.columna


# ══════════════════════════════════════════════
#  HELPERS DE NAVEGACIÓN (Etapa 2 — semántica)
# ══════════════════════════════════════════════
#
# Estas funciones son utilidades que el analizador semántico usa para
# recorrer el CST de manera declarativa, sin escribir bucles crudos en
# cada `_visit_*`. NO modifican el árbol.

def hijos_por_etiqueta(nodo: NodoArbol, etiqueta: str):
    """Devuelve la lista de hijos DIRECTOS cuya `etiqueta` coincide."""
    return [h for h in nodo.hijos if h.etiqueta == etiqueta]


def hijo_por_etiqueta(nodo: NodoArbol, etiqueta: str):
    """Primer hijo directo con esa etiqueta, o None."""
    for h in nodo.hijos:
        if h.etiqueta == etiqueta:
            return h
    return None


def primer_terminal(nodo: NodoArbol):
    """
    Recorre el sub-árbol en pre-orden y devuelve el primer descendiente
    con `es_terminal=True` y `es_error=False`. Útil para localizar la
    posición de una construcción cuando el nodo no-terminal no la
    tiene (caso de los nodos puramente ε).
    """
    if nodo.es_terminal and not nodo.es_error:
        return nodo
    for h in nodo.hijos:
        encontrado = primer_terminal(h)
        if encontrado is not None:
            return encontrado
    return None


def recolectar_terminales(nodo: NodoArbol):
    """Lista de TODOS los terminales del sub-árbol en pre-orden."""
    salida = []
    _recolectar_terminales(nodo, salida)
    return salida


def _recolectar_terminales(nodo: NodoArbol, acumulador: list) -> None:
    if nodo.es_terminal:
        acumulador.append(nodo)
        return
    for h in nodo.hijos:
        _recolectar_terminales(h, acumulador)


def tiene_error_sintactico(nodo: NodoArbol) -> bool:
    """
    True si en cualquier punto del sub-árbol hay un nodo con
    `es_error=True`. La fase semántica usa esto para SALTAR sub-árboles
    dañados por el modo pánico (decisión F.11: corremos semántica
    incluso con errores sintácticos, pero ignoramos lo que esté roto).
    """
    if nodo.es_error:
        return True
    for h in nodo.hijos:
        if tiene_error_sintactico(h):
            return True
    return False


def etiqueta_normalizada(etiqueta: str) -> str:
    """
    Normaliza las etiquetas de no-terminales auxiliares para que el
    visitor sea agnóstico al método de parseo.

    El parser recursivo usa nombres con apóstrofo: `bloque'`,
    `expr_or'`, `param_lista'`, `arg_lista'`, etc.
    El parser predictivo usa el sufijo `_prima`: `bloque_prima`,
    `expr_or_prima`, `param_lista_prima`, etc.

    Forma canónica elegida: `_prima` (es un identificador Python
    válido y permite que los métodos del visitor tengan nombres
    legales: `_visit_bloque_prima` en lugar de `_visit_bloque'`).

    Ejemplos:
        "bloque'"        -> "bloque_prima"
        "bloque_prima"   -> "bloque_prima"
        "expr_or'"       -> "expr_or_prima"
        "programa"       -> "programa"
        "ε"              -> "ε"            (sin cambio)
    """
    if etiqueta.endswith("'"):
        return etiqueta[:-1] + "_prima"
    return etiqueta


def raiz_logica(nodo: NodoArbol) -> NodoArbol:
    """
    Workaround del HALLAZGO 2 de la Etapa 1: el parser recursivo crea
    un nodo `programa` envoltorio que contiene a su vez un único hijo
    `programa` (la "raíz real"); el parser predictivo crea solo uno.

    Si la raíz tiene exactamente un hijo con su misma etiqueta,
    devuelve ese hijo. En cualquier otro caso devuelve `nodo` tal cual.
    """
    if (nodo is not None and len(nodo.hijos) == 1 and
            nodo.hijos[0].etiqueta == nodo.etiqueta):
        return nodo.hijos[0]
    return nodo


def extraer_expresiones_de_argumentos(nodo_argumentos: NodoArbol):
    """
    (Etapa 7 — Regla 5) Devuelve la lista PLANA de nodos `expresion` que
    cuelgan de un nodo `argumentos`, en el orden en que aparecen.

    La producción de argumentos es:
        argumentos      → arg_lista | ε
        arg_lista       → expresion arg_lista_prima
        arg_lista_prima → , expresion arg_lista_prima | ε

    Se recorren recursivamente los nodos `argumentos`, `arg_lista` y
    `arg_lista_prima`, recolectando sus hijos directos `expresion`. Se usa
    `etiqueta_normalizada`, así que funciona tanto con la salida del parser
    recursivo (`arg_lista'`) como con la del predictivo (`arg_lista_prima`).

    NO se desciende DENTRO de una `expresion`: así los argumentos de una
    llamada anidada (p.ej. el `x` de `f(g(x), y)`) no se confunden con los
    argumentos del nivel actual (que son `g(x)` e `y`).

    Si `nodo_argumentos` es None o deriva a ε (sin argumentos), devuelve [].
    """
    salida = []
    if nodo_argumentos is not None:
        _recolectar_expresiones_arg(nodo_argumentos, salida)
    return salida


def _recolectar_expresiones_arg(nodo: NodoArbol, salida: list) -> None:
    """Helper recursivo de `extraer_expresiones_de_argumentos`."""
    for h in nodo.hijos:
        etq = etiqueta_normalizada(h.etiqueta)
        if etq == 'expresion':
            salida.append(h)
        elif etq in ('argumentos', 'arg_lista', 'arg_lista_prima'):
            _recolectar_expresiones_arg(h, salida)
