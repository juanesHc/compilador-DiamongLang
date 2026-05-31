"""
╔══════════════════════════════════════════════════════════╗
║   DiamondLang 💎 — Recuperación de errores (modo pánico) ║
║                  recuperacion.py                        ║
║  Define los conjuntos de sincronización por             ║
║  no-terminal y la función `sincronizar` usada por       ║
║  ambos parsers para continuar tras un error.            ║
╚══════════════════════════════════════════════════════════╝

Estrategia (Aho/Sethi/Ullman, Compilers §4.1.4):
    Ante un error en el no-terminal A, descartamos tokens
    hasta encontrar uno que esté en SIGUIENTE(A) o en un
    conjunto de "delimitadores fuertes" del lenguaje
    (cierres de bloque y la palabra 'sino'). Eso permite
    continuar el análisis en una posición coherente sin
    desestabilizar la estructura jerárquica del programa.

Garantía de terminación:
    El símbolo EOF '$' siempre pertenece al conjunto de
    sincronización, así que `sincronizar` siempre detiene.
"""


# ══════════════════════════════════════════════
#  CONJUNTOS BASE
# ══════════════════════════════════════════════

# Delimitadores fuertes del lenguaje: cierres de bloque y 'sino'.
# Nunca los descartamos durante una sincronización porque
# arruinaría la estructura del programa.
SYNC_GLOBAL = {
    'fin_funcion', 'fin_si', 'fin_mientras', 'fin_para', 'fin_clase',
    'sino', '$',
}

# Tokens con los que puede empezar una sentencia (inicios de
# `decl_variable`, `sentencia_id`, `sent_si`, `sent_mientras`,
# `sent_para`, `sent_retornar`, `sent_escribir`, `sent_leer`,
# `def_funcion`).
INICIOS_SENTENCIA = {
    'si', 'mientras', 'para', 'retornar', 'leer', 'escribir', 'funcion',
    'entero', 'real', 'cadena', 'booleano', 'vacio',
    'IDENTIFICADOR',
}

# Sincronización dentro de un bloque o programa: caer al inicio
# de la siguiente sentencia o a un cierre.
SYNC_SENTENCIA = SYNC_GLOBAL | INICIOS_SENTENCIA


def sync_expresion(siguiente):
    """
    Construye dinámicamente el conjunto de sincronización para
    expresiones a partir de SIGUIENTE(expresion). Esto evita
    drift si la gramática evoluciona.
    """
    base = set(siguiente.get('expresion', set()))
    # Añadir delimitadores fuertes para cortar a tiempo
    return base | SYNC_GLOBAL


# Mapa NO_TERMINAL → conjunto-tipo. Los no-terminales no listados
# usan SYNC_SENTENCIA como fallback, lo que cubre la mayoría de
# los casos en DiamondLang.
GRUPO_EXPRESION = {
    'expresion', 'expr_or', "expr_or'",
    'expr_and', "expr_and'",
    'expr_rel', "expr_rel'", 'op_rel',
    'expr_add', "expr_add'",
    'expr_mul', "expr_mul'",
    'expr_pot', "expr_pot'",
    'expr_unaria',
    'expr_primaria',
    'sufijo_id',
    'argumentos', 'arg_lista', "arg_lista'",
}


# ══════════════════════════════════════════════
#  SELECCIÓN DEL CONJUNTO POR NO-TERMINAL
# ══════════════════════════════════════════════

def conjunto_sync_para(no_terminal: str, siguiente: dict) -> set:
    """
    Devuelve el conjunto de sincronización adecuado para
    `no_terminal`, combinando SIGUIENTE(no_terminal) con
    los delimitadores fuertes (SYNC_GLOBAL).

    - Si el no-terminal pertenece al grupo de expresiones,
      añade el conjunto SYNC_EXPRESION (derivado de
      SIGUIENTE(expresion)).
    - En cualquier otro caso, usa SIGUIENTE(no_terminal)
      ∪ SYNC_GLOBAL.
    - Si el no-terminal no aparece en SIGUIENTE (ej: 'programa'),
      devuelve SYNC_SENTENCIA.
    """
    sig = set(siguiente.get(no_terminal, set()))

    if no_terminal in GRUPO_EXPRESION:
        return sync_expresion(siguiente) | sig | SYNC_GLOBAL

    if not sig:
        return SYNC_SENTENCIA

    return sig | SYNC_GLOBAL


# ══════════════════════════════════════════════
#  FUNCIÓN DE SINCRONIZACIÓN
# ══════════════════════════════════════════════

def _tipo_logico(tok):
    """
    Replica el método `tipo_actual` de los parsers:
    para keywords, tipos, booleanos, operadores y símbolos
    devuelve el lexema; para el resto devuelve el tipo.
    """
    if tok.tipo in ('KEYWORD', 'TIPO', 'BOOLEANO', 'OPERADOR', 'SIMBOLO'):
        return tok.lexema
    return tok.tipo


def sincronizar(tokens, indice: int, conjunto_sync: set):
    """
    Avanza `indice` descartando tokens hasta que el actual
    esté en `conjunto_sync` o se alcance EOF.

    No consume el token de sincronización: lo deja como tope
    para que el parser pueda decidir qué hacer (continuar o
    pop del no-terminal).

    Retorna:
        (nuevo_indice, descartados)
        - nuevo_indice: posición tras la sincronización
        - descartados: lista de lexemas descartados (para traza)
    """
    descartados = []
    while indice < len(tokens):
        tok = tokens[indice]
        ta = _tipo_logico(tok)
        if ta in conjunto_sync:
            return indice, descartados
        descartados.append(tok.lexema)
        indice += 1
    # Llegamos a EOF sin encontrar nada — devolvemos len(tokens)
    return indice, descartados


# ══════════════════════════════════════════════
#  PRUEBAS BÁSICAS
# ══════════════════════════════════════════════

if __name__ == '__main__':
    # Importar perezosamente para no obligar a tabla_ll si solo
    # quieres usar las constantes.
    from sintactico.tabla_ll import generar_tabla
    _, siguiente, _ = generar_tabla()

    print("SYNC_GLOBAL:", sorted(SYNC_GLOBAL))
    print()
    print("SYNC_SENTENCIA:", sorted(SYNC_SENTENCIA))
    print()
    print("conjunto_sync_para('expresion'):",
          sorted(conjunto_sync_para('expresion', siguiente)))
    print()
    print("conjunto_sync_para('sent_si'):",
          sorted(conjunto_sync_para('sent_si', siguiente)))
    print()
    print("conjunto_sync_para('decl_variable'):",
          sorted(conjunto_sync_para('decl_variable', siguiente)))
