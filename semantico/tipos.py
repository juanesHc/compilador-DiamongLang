"""
╔══════════════════════════════════════════════════════════╗
║   DiamondLang 💎 — Sistema de tipos                      ║
║                       tipos.py                          ║
║  Entrega 4 — Etapa 4.                                    ║
║                                                         ║
║  Inferencia de tipos sobre el sub-árbol de una           ║
║  `expresion` del CST. Es una función PURA: dado un nodo  ║
║  y la tabla de símbolos, sintetiza el tipo de la         ║
║  expresión recorriendo la jerarquía de precedencia       ║
║  (expr_or → expr_and → expr_rel → expr_add → expr_mul    ║
║  → expr_pot → expr_unaria → expr_primaria).              ║
║                                                         ║
║  NO implementa reglas semánticas nuevas: esta etapa      ║
║  sólo construye el motor de tipos que las Etapas 5, 6 y  ║
║  7 consultarán. No se invoca todavía desde semantico.py. ║
║                                                         ║
║  Tipos representados como strings (consistente con        ║
║  Simbolo.tipo): 'entero', 'real', 'cadena', 'booleano',  ║
║  'vacio', y el centinela 'ERROR'.                        ║
║                                                         ║
║  Agnóstico al parser: usa `etiqueta_normalizada` para    ║
║  funcionar con la salida del recursivo (primas con       ║
║  apóstrofo) y del predictivo (primas con `_prima`).      ║
╚══════════════════════════════════════════════════════════╝
"""

import re

from sintactico.arbol import (
    NodoArbol,
    etiqueta_normalizada,
    tiene_error_sintactico,
    primer_terminal,
)


# ══════════════════════════════════════════════
#  CONJUNTOS DE TIPOS
# ══════════════════════════════════════════════

TIPOS_NUMERICOS = {'entero', 'real'}
TIPOS_BASICOS   = {'entero', 'real', 'cadena', 'booleano'}

# Tipos que un nodo `tipo` puede derivar (incluye 'vacio', que sólo es
# válido como tipo de retorno — la validación de ese uso es de etapas
# posteriores; aquí sólo lo reconocemos como lexema legal).
TIPOS_DECLARABLES = {'entero', 'real', 'cadena', 'booleano', 'vacio'}

ERROR = 'ERROR'


# ══════════════════════════════════════════════
#  COMPATIBILIDAD DE TIPOS
# ══════════════════════════════════════════════

def compatible(destino: str, origen: str) -> bool:
    """
    ¿Un valor de tipo `origen` puede usarse donde se espera `destino`?

      - compatible(T, T)        = True   (para todo T)
      - compatible(real, entero)= True   (promoción entero→real)
      - compatible(entero, real)= False  (no hay truncamiento implícito)
      - compatible(T, 'ERROR')  = True   (suprime cascadas)
      - compatible('ERROR', T)  = True   (suprime cascadas)
      - cualquier otro par      = False
    """
    if destino == ERROR or origen == ERROR:
        return True
    if destino == origen:
        return True
    if destino == 'real' and origen == 'entero':
        return True
    return False


# ══════════════════════════════════════════════
#  UNIFICACIÓN POR FAMILIA DE OPERADORES
# ══════════════════════════════════════════════
#
# Cada `unificar_*` recibe los tipos de los operandos (ya sintetizados)
# y el operador, y devuelve el tipo del resultado o 'ERROR'. Son puras:
# nunca reportan. La cascada (un operando ya 'ERROR') se traduce siempre
# a 'ERROR' sin distinción especial — el QUIEN-reporta decide si calla.

def unificar_aritmetico(t1: str, t2: str, op: str) -> str:
    """
    Operadores aritméticos: +, -, *, /, %, ** (potencia).

      - numérico  ⊕ numérico → entero si ambos enteros, real si alguno real.
      - cadena    +  cadena  → cadena (concatenación; SÓLO con '+').
      - cualquier otra combinación → ERROR.
    """
    if t1 == ERROR or t2 == ERROR:
        return ERROR
    # Excepción de concatenación de cadenas (sólo el '+').
    if op == '+' and t1 == 'cadena' and t2 == 'cadena':
        return 'cadena'
    if t1 in TIPOS_NUMERICOS and t2 in TIPOS_NUMERICOS:
        if t1 == 'entero' and t2 == 'entero':
            return 'entero'
        return 'real'                      # promoción: al menos uno es real
    return ERROR


def unificar_relacional(t1: str, t2: str, op: str) -> str:
    """
    Operadores relacionales: ==, !=, <, >, <=, >=.

      - numérico  ⊕ numérico → booleano (promoción entre entero/real).
      - cadena    ⊕ cadena   → booleano (comparación lexicográfica).
      - booleano  ⊕ booleano → booleano SÓLO con == y != ; con
                               <, >, <=, >= → ERROR.
      - cualquier otra combinación → ERROR.
    """
    if t1 == ERROR or t2 == ERROR:
        return ERROR
    if t1 in TIPOS_NUMERICOS and t2 in TIPOS_NUMERICOS:
        return 'booleano'
    if t1 == 'cadena' and t2 == 'cadena':
        return 'booleano'
    if t1 == 'booleano' and t2 == 'booleano':
        if op in ('==', '!='):
            return 'booleano'
        return ERROR                       # orden no definido sobre booleanos
    return ERROR


def unificar_logico(t1: str, t2: str) -> str:
    """
    Operadores lógicos binarios: y, o.

      - booleano ⊕ booleano → booleano.
      - cualquier otra combinación → ERROR.
    """
    if t1 == ERROR or t2 == ERROR:
        return ERROR
    if t1 == 'booleano' and t2 == 'booleano':
        return 'booleano'
    return ERROR


def unificar_unario(t: str, op: str) -> str:
    """
    Operadores unarios:
      - 'no' <expr>: expr debe ser booleano → booleano.
      - '-'  <expr>: expr debe ser numérico → mismo tipo (entero/real).
    """
    if t == ERROR:
        return ERROR
    if op == 'no':
        return 'booleano' if t == 'booleano' else ERROR
    if op == '-':
        return t if t in TIPOS_NUMERICOS else ERROR
    return ERROR


# ══════════════════════════════════════════════
#  LITERALES Y TIPOS DECLARADOS
# ══════════════════════════════════════════════

_RE_ENTERO = re.compile(r'\d+$')
_RE_REAL   = re.compile(r'\d+\.\d+$')


def tipo_de_literal(terminal_nodo: NodoArbol) -> str:
    """
    Tipo de un literal a partir del nodo terminal que lo representa.

    NOTA DE DISEÑO: el CST guarda el LEXEMA del token como `etiqueta`
    (no su categoría léxica ENTERO/REAL/CADENA — esa información se
    pierde al construir el árbol, ver §A.2 del plan). Por eso aquí el
    tipo léxico se re-deduce del propio lexema:
      - 'verdadero' / 'falso'         → booleano
      - lexema entre comillas " o '    → cadena
      - \\d+                           → entero
      - \\d+\\.\\d+                     → real
      - cualquier otra cosa            → ERROR
    """
    if terminal_nodo is None or not terminal_nodo.es_terminal:
        return ERROR
    lex = terminal_nodo.etiqueta
    if lex in ('verdadero', 'falso'):
        return 'booleano'
    if lex and lex[0] in ('"', "'"):
        return 'cadena'
    if _RE_ENTERO.match(lex):
        return 'entero'
    if _RE_REAL.match(lex):
        return 'real'
    return ERROR


def tipo_declarado(nodo_tipo: NodoArbol) -> str:
    """
    Tipo declarado a partir de un nodo `tipo`
    (producción `tipo → entero | real | cadena | booleano | vacio`).

    Devuelve la etiqueta del primer hijo terminal (el keyword del tipo),
    o 'ERROR' si el sub-árbol está mal formado.
    """
    if nodo_tipo is None:
        return ERROR
    for h in nodo_tipo.hijos:
        if h.es_terminal and not h.es_error and h.etiqueta != 'ε':
            return h.etiqueta
    return ERROR


# ══════════════════════════════════════════════
#  HELPERS DE NAVEGACIÓN DEL CST
# ══════════════════════════════════════════════

def _hijo_norm(nodo: NodoArbol, etq: str):
    """Primer hijo directo cuya etiqueta normalizada coincide, o None."""
    if nodo is None:
        return None
    for h in nodo.hijos:
        if etiqueta_normalizada(h.etiqueta) == etq:
            return h
    return None


def _primer_terminal_significativo(nodo: NodoArbol):
    """
    Primer hijo directo terminal que no sea ε ni marcador de error.
    Sirve para extraer el operador de un nodo prima (`+`, `o`, `**`, …)
    y para extraer el terminal de un literal en `expr_primaria`.
    """
    if nodo is None:
        return None
    for h in nodo.hijos:
        if h.es_terminal and not h.es_error and h.etiqueta != 'ε':
            return h
    return None


def _tiene_terminal_directo(nodo: NodoArbol, lexema: str) -> bool:
    """True si `nodo` tiene un hijo directo terminal con ese lexema."""
    if nodo is None:
        return False
    for h in nodo.hijos:
        if h.es_terminal and not h.es_error and h.etiqueta == lexema:
            return True
    return False


# Configuración de los niveles binarios izquierda-asociativos cuyo patrón
# es idéntico: `nivel → operando prima`, `prima → op operando prima | ε`.
#   etiqueta_nivel : (etiqueta_operando, etiqueta_prima, familia)
_NIVELES_BINARIOS = {
    'expr_or':  ('expr_and', 'expr_or_prima',  'logico'),
    'expr_and': ('expr_rel', 'expr_and_prima', 'logico'),
    'expr_add': ('expr_mul', 'expr_add_prima', 'aritmetico'),
    'expr_mul': ('expr_pot', 'expr_mul_prima', 'aritmetico'),
}


# ══════════════════════════════════════════════
#  REPORTE (sólo lo usa la versión con_reporte)
# ══════════════════════════════════════════════

def _reportar_binario(reportar, op, op_node, t_izq, t_der):
    reportar(
        regla='TIPO_OPERADOR',
        mensaje=(f"El operador '{op}' no se puede aplicar a operandos de "
                 f"tipo '{t_izq}' y '{t_der}'."),
        nodo=op_node,
        lexema=op,
        contexto={
            'operador':       op,
            'tipo_izquierdo': t_izq,
            'tipo_derecho':   t_der,
        },
    )


def _reportar_unario(reportar, op, op_node, t):
    reportar(
        regla='TIPO_OPERADOR',
        mensaje=(f"El operador unario '{op}' no se puede aplicar a un "
                 f"operando de tipo '{t}'."),
        nodo=op_node,
        lexema=op,
        contexto={'operador': op, 'tipo_operando': t},
    )


# ══════════════════════════════════════════════
#  INFERENCIA — NÚCLEO RECURSIVO
# ══════════════════════════════════════════════
#
# `reportar` es None en la versión silenciosa, o `self._reportar` del
# AnalizadorSemantico en la versión con reporte. El criterio de cascada
# (decisión F.10) está centralizado en `_combinar`: sólo se reporta
# cuando AMBOS operandos son tipos válidos pero el operador los rechaza.

def _combinar(resultado, t_izq, t_der, op, op_node, reportar):
    """Reporta (si procede) un error de operador binario y devuelve el
    tipo resultante. No reporta en cascada: si algún operando ya era
    ERROR, calla."""
    if (resultado == ERROR and reportar is not None
            and t_izq != ERROR and t_der != ERROR):
        _reportar_binario(reportar, op, op_node, t_izq, t_der)
    return resultado


def _inferir(nodo: NodoArbol, tabla, reportar) -> str:
    if nodo is None or nodo.es_error:
        return ERROR

    # Un terminal suelto sólo puede ser un literal.
    if nodo.es_terminal:
        return tipo_de_literal(nodo)

    etq = etiqueta_normalizada(nodo.etiqueta)

    if etq == 'expresion':
        return _inferir(_hijo_norm(nodo, 'expr_or'), tabla, reportar)

    if etq in _NIVELES_BINARIOS:
        return _nivel_binario(nodo, etq, tabla, reportar)

    if etq == 'expr_rel':
        return _nivel_relacional(nodo, tabla, reportar)

    if etq == 'expr_pot':
        return _nivel_potencia(nodo, tabla, reportar)

    if etq == 'expr_unaria':
        return _nivel_unario(nodo, tabla, reportar)

    if etq == 'expr_primaria':
        return _primaria(nodo, tabla, reportar)

    # Nodo envoltorio inesperado: bajar por su primer no-terminal.
    for h in nodo.hijos:
        if not h.es_terminal:
            return _inferir(h, tabla, reportar)
    return ERROR


def _nivel_binario(nodo, etq, tabla, reportar) -> str:
    """
    Niveles izquierda-asociativos (or / and / add / mul). Acumula de
    izquierda a derecha siguiendo la cadena de nodos prima.
    """
    operando_etq, prima_etq, familia = _NIVELES_BINARIOS[etq]

    tipo = _inferir(_hijo_norm(nodo, operando_etq), tabla, reportar)
    prima = _hijo_norm(nodo, prima_etq)

    while prima is not None:
        op_node = _primer_terminal_significativo(prima)
        if op_node is None:                       # prima → ε : fin de la cola
            break
        op = op_node.etiqueta
        tipo_der = _inferir(_hijo_norm(prima, operando_etq), tabla, reportar)

        if familia == 'logico':
            res = unificar_logico(tipo, tipo_der)
        else:
            res = unificar_aritmetico(tipo, tipo_der, op)

        tipo = _combinar(res, tipo, tipo_der, op, op_node, reportar)
        prima = _hijo_norm(prima, prima_etq)       # siguiente eslabón
    return tipo


def _nivel_relacional(nodo, tabla, reportar) -> str:
    """
    expr_rel → expr_add expr_rel_prima ;
    expr_rel_prima → op_rel expr_add | ε   (un solo operador, sin cadena).
    """
    tipo_izq = _inferir(_hijo_norm(nodo, 'expr_add'), tabla, reportar)
    prima = _hijo_norm(nodo, 'expr_rel_prima')
    if prima is None:
        return tipo_izq

    op_rel = _hijo_norm(prima, 'op_rel')
    if op_rel is None:                             # prima → ε
        return tipo_izq

    op_node = primer_terminal(op_rel)              # el <, >, ==, … real
    op = op_node.etiqueta if op_node is not None else '?'
    tipo_der = _inferir(_hijo_norm(prima, 'expr_add'), tabla, reportar)

    res = unificar_relacional(tipo_izq, tipo_der, op)
    return _combinar(res, tipo_izq, tipo_der, op, op_node, reportar)


def _nivel_potencia(nodo, tabla, reportar) -> str:
    """
    expr_pot → expr_unaria expr_pot_prima ;
    expr_pot_prima → ** expr_pot | ε       (derecha-asociativo).
    """
    tipo_izq = _inferir(_hijo_norm(nodo, 'expr_unaria'), tabla, reportar)
    prima = _hijo_norm(nodo, 'expr_pot_prima')
    if prima is None:
        return tipo_izq

    op_node = _primer_terminal_significativo(prima)
    if op_node is None:                            # prima → ε
        return tipo_izq

    op = op_node.etiqueta                           # '**'
    # El operando derecho es otro expr_pot (recursión por la derecha).
    tipo_der = _inferir(_hijo_norm(prima, 'expr_pot'), tabla, reportar)

    res = unificar_aritmetico(tipo_izq, tipo_der, op)
    return _combinar(res, tipo_izq, tipo_der, op, op_node, reportar)


def _nivel_unario(nodo, tabla, reportar) -> str:
    """
    expr_unaria → no expr_unaria | - expr_unaria | expr_primaria.
    """
    primer = nodo.hijos[0] if nodo.hijos else None
    if (primer is not None and primer.es_terminal and not primer.es_error
            and primer.etiqueta in ('no', '-')):
        op = primer.etiqueta
        tipo = _inferir(_hijo_norm(nodo, 'expr_unaria'), tabla, reportar)
        res = unificar_unario(tipo, op)
        if res == ERROR and reportar is not None and tipo != ERROR:
            _reportar_unario(reportar, op, primer, tipo)
        return res

    # Caso pass-through: expr_primaria.
    return _inferir(_hijo_norm(nodo, 'expr_primaria'), tabla, reportar)


def _primaria(nodo, tabla, reportar) -> str:
    """
    expr_primaria → ENTERO | REAL | CADENA | verdadero | falso
                  | IDENTIFICADOR sufijo_id
                  | ( expresion )
    """
    # ── IDENTIFICADOR (variable o llamada) ──
    sufijo = _hijo_norm(nodo, 'sufijo_id')
    if sufijo is not None and nodo.hijos:
        ident = nodo.hijos[0]
        if not (ident.es_terminal and not ident.es_error):
            return ERROR
        nombre = ident.etiqueta
        es_llamada = _tiene_terminal_directo(sufijo, '(')
        simbolo = tabla.buscar(nombre)
        if simbolo is None:
            # No declarado: ya lo reporta la Regla 2 (_visit_expr_primaria).
            return ERROR
        es_funcion = (simbolo.categoria == 'funcion'
                      or simbolo.tipo == 'funcion')
        if es_llamada:
            # Llamada f(...): el tipo es el tipo_retorno de la función.
            # No se valida aridad/tipos de argumentos (eso es Regla 5).
            if es_funcion:
                return simbolo.tipo_retorno or ERROR
            return ERROR                            # variable usada como función
        # Uso como variable.
        if es_funcion:
            return ERROR                            # función usada como variable
        return simbolo.tipo

    # ── ( expresion ) ──
    interna = _hijo_norm(nodo, 'expresion')
    if interna is not None:
        return _inferir(interna, tabla, reportar)

    # ── Literal ──
    return tipo_de_literal(_primer_terminal_significativo(nodo))


# ══════════════════════════════════════════════
#  API PÚBLICA
# ══════════════════════════════════════════════

def tipo_de_expresion(nodo: NodoArbol, tabla) -> str:
    """
    Tipo sintetizado de una expresión. Función PURA: nunca reporta.
    Devuelve uno de 'entero', 'real', 'cadena', 'booleano', 'vacio'
    (este último sólo vía tipo_retorno de funciones) o 'ERROR'.

    Si el sub-árbol contiene cualquier nodo con error sintáctico
    (`tiene_error_sintactico`), devuelve 'ERROR' sin analizar más.
    """
    if nodo is None or tiene_error_sintactico(nodo):
        return ERROR
    return _inferir(nodo, tabla, None)


def tipo_de_expresion_con_reporte(nodo: NodoArbol, tabla, reportar) -> str:
    """
    Igual que `tipo_de_expresion`, pero recibe el callable `reportar`
    (la función `self._reportar` del AnalizadorSemantico). Cuando un
    operador rechaza sus operandos, reporta con regla='TIPO_OPERADOR'
    apuntando al nodo del operador (línea/columna correctas) antes de
    devolver 'ERROR'.

    Cascada (decisión F.10): si CUALQUIER operando ya es 'ERROR', NO
    reporta — el operador se contagia en silencio. Sólo reporta cuando
    ambos operandos son tipos válidos pero incompatibles con el operador.

    Las Etapas 5, 6 y 7 usan esta versión.
    """
    if nodo is None or tiene_error_sintactico(nodo):
        return ERROR
    return _inferir(nodo, tabla, reportar)


# ══════════════════════════════════════════════
#  PRUEBA RÁPIDA
# ══════════════════════════════════════════════

if __name__ == '__main__':
    from sintactico.parser_recursivo import ParserRecursivo
    from semantico.tabla_simbolos import TablaSimbolos

    def _buscar(nodo, etq):
        if etiqueta_normalizada(nodo.etiqueta) == etq:
            return nodo
        for h in nodo.hijos:
            r = _buscar(h, etq)
            if r is not None:
                return r
        return None

    ejemplos = [
        ('entero',   '5 + 3'),
        ('real',     '5 + 3.14'),
        ('cadena',   '"hola" + "mundo"'),
        ('booleano', '5 < 10'),
        ('booleano', '5 < 10 y 3 == 3'),
        ('ERROR',    '5 + "hola"'),
    ]
    for esperado, expr in ejemplos:
        codigo = (f"funcion p()\nhacer\n    entero x <- {expr}\n"
                  f"fin_funcion\n")
        p = ParserRecursivo(codigo)
        p.analizar()
        decl = _buscar(p.arbol_raiz, 'decl_variable')
        nodo_expr = decl.hijos[3]
        t = tipo_de_expresion(nodo_expr, TablaSimbolos())
        marca = "✓" if t == esperado else "✗"
        print(f"  {marca} {expr:24s} → {t:9s} (esperado {esperado})")
