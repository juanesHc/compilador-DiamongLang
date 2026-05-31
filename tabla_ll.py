"""
╔══════════════════════════════════════════════════════════╗
║     DiamondLang 💎 — Tabla LL(1)                        ║
║                  tabla_ll.py                            ║
║  Calcula automáticamente:                               ║
║    - Conjuntos PRIMERO de cada no-terminal              ║
║    - Conjuntos SIGUIENTE de cada no-terminal            ║
║    - Tabla de análisis LL(1)                            ║
╚══════════════════════════════════════════════════════════╝
"""

# ══════════════════════════════════════════════
#  GRAMÁTICA DE DIAMONDLANG
#  Representada como diccionario:
#    NO_TERMINAL -> [ [produccion1], [produccion2], ... ]
#  'ε' representa la producción vacía
#  Los terminales están en MAYÚSCULAS o son strings literales
# ══════════════════════════════════════════════

EPSILON = 'ε'
EOF     = '$'

# Símbolo inicial
START = 'programa'

# Terminales del lenguaje
TERMINALES = {
    # Keywords
    'funcion','fin_funcion','retornar',
    'si','entonces','sino','fin_si',
    'para','desde','hasta','paso','hacer','fin_para',
    'mientras','fin_mientras',
    'y','o','no',
    'leer','escribir',
    'verdadero','falso',
    'nuevo','este',
    # Tipos
    'entero','real','cadena','booleano','vacio',
    # Operadores
    '==','!=','<=','>=','<-','**',
    '+','-','*','/','%',
    '<','>',
    # Símbolos
    '(',')',',',';',':','.',
    # Literales (categorías del lexer)
    'ENTERO','REAL','CADENA','IDENTIFICADOR',
    # EOF
    '$',
}

# Gramática completa de DiamondLang
# Cada producción es una lista de símbolos
# Los no-terminales empiezan con minúscula y usan _
GRAMATICA = {
    # ── Programa ──
    'programa': [
        ['declaracion', 'programa'],
        [EPSILON],
    ],
    'declaracion': [
        ['def_funcion'],
        ['sentencia'],
    ],

    # ── Funciones ──
    'def_funcion': [
        ['funcion', 'IDENTIFICADOR', '(', 'parametros', ')', 'tipo_retorno_opt', 'hacer', 'bloque', 'fin_funcion'],
    ],
    'tipo_retorno_opt': [
        ['retornar', 'tipo'],
        [EPSILON],
    ],
    'parametros': [
        ['param_lista'],
        [EPSILON],
    ],
    'param_lista': [
        ['tipo', 'IDENTIFICADOR', 'param_lista_prima'],
    ],
    'param_lista_prima': [
        [',', 'tipo', 'IDENTIFICADOR', 'param_lista_prima'],
        [EPSILON],
    ],

    # ── Tipos ──
    'tipo': [
        ['entero'],
        ['real'],
        ['cadena'],
        ['booleano'],
        ['vacio'],
    ],

    # ── Bloque y sentencias ──
    'bloque': [
        ['sentencia', 'bloque_prima'],
    ],
    'bloque_prima': [
        ['sentencia', 'bloque_prima'],
        [EPSILON],
    ],
    'sentencia': [
        ['decl_variable'],
        ['sentencia_id'],
        ['sent_si'],
        ['sent_mientras'],
        ['sent_para'],
        ['sent_retornar'],
        ['sent_escribir'],
        ['sent_leer'],
    ],

    # ── Declaración con tipo ──
    'decl_variable': [
        ['tipo', 'IDENTIFICADOR', '<-', 'expresion'],
    ],

    # ── Factorizado: IDENTIFICADOR <- expr  |  IDENTIFICADOR(args) ──
    'sentencia_id': [
        ['IDENTIFICADOR', 'sentencia_id_cola'],
    ],
    'sentencia_id_cola': [
        ['<-', 'expresion'],
        ['(', 'argumentos', ')'],
    ],

    # ── Asignación (usada internamente por el parser) ──
    'asignacion': [
        ['IDENTIFICADOR', '<-', 'expresion'],
    ],

    # ── Sentencia de llamada (usada internamente) ──
    'llamada_sentencia': [
        ['IDENTIFICADOR', '(', 'argumentos', ')'],
    ],

    # ── Condicional ──
    'sent_si': [
        ['si', 'expresion', 'entonces', 'bloque', 'rama_sino', 'fin_si'],
    ],
    'rama_sino': [
        ['sino', 'bloque'],
        [EPSILON],
    ],

    # ── Mientras ──
    'sent_mientras': [
        ['mientras', 'expresion', 'hacer', 'bloque', 'fin_mientras'],
    ],

    # ── Para ──
    'sent_para': [
        ['para', 'IDENTIFICADOR', 'desde', 'expresion', 'hasta', 'expresion', 'paso_opt', 'hacer', 'bloque', 'fin_para'],
    ],
    'paso_opt': [
        ['paso', 'expresion'],
        [EPSILON],
    ],

    # ── Retorno, escribir, leer ──
    'sent_retornar': [
        ['retornar', 'expresion'],
    ],
    'sent_escribir': [
        ['escribir', '(', 'expresion', ')'],
    ],
    'sent_leer': [
        ['leer', '(', 'IDENTIFICADOR', ')'],
    ],

    # ── Expresiones (jerarquía de precedencia, sin recurs. izq.) ──
    'expresion': [
        ['expr_or'],
    ],
    'expr_or': [
        ['expr_and', 'expr_or_prima'],
    ],
    'expr_or_prima': [
        ['o', 'expr_and', 'expr_or_prima'],
        [EPSILON],
    ],
    'expr_and': [
        ['expr_rel', 'expr_and_prima'],
    ],
    'expr_and_prima': [
        ['y', 'expr_rel', 'expr_and_prima'],
        [EPSILON],
    ],
    'expr_rel': [
        ['expr_add', 'expr_rel_prima'],
    ],
    'expr_rel_prima': [
        ['op_rel', 'expr_add'],
        [EPSILON],
    ],
    'op_rel': [
        ['=='], ['!='], ['<'], ['>'], ['<='], ['>='],
    ],
    'expr_add': [
        ['expr_mul', 'expr_add_prima'],
    ],
    'expr_add_prima': [
        ['+', 'expr_mul', 'expr_add_prima'],
        ['-', 'expr_mul', 'expr_add_prima'],
        [EPSILON],
    ],
    'expr_mul': [
        ['expr_pot', 'expr_mul_prima'],
    ],
    'expr_mul_prima': [
        ['*', 'expr_pot', 'expr_mul_prima'],
        ['/', 'expr_pot', 'expr_mul_prima'],
        ['%', 'expr_pot', 'expr_mul_prima'],
        [EPSILON],
    ],
    'expr_pot': [
        ['expr_unaria', 'expr_pot_prima'],
    ],
    'expr_pot_prima': [
        ['**', 'expr_pot'],
        [EPSILON],
    ],
    'expr_unaria': [
        ['no', 'expr_unaria'],
        ['-', 'expr_unaria'],
        ['expr_primaria'],
    ],
    'expr_primaria': [
        ['ENTERO'],
        ['REAL'],
        ['CADENA'],
        ['verdadero'],
        ['falso'],
        ['IDENTIFICADOR', 'sufijo_id'],
        ['(', 'expresion', ')'],
    ],
    'sufijo_id': [
        ['(', 'argumentos', ')'],
        [EPSILON],
    ],

    # ── Argumentos ──
    'argumentos': [
        ['arg_lista'],
        [EPSILON],
    ],
    'arg_lista': [
        ['expresion', 'arg_lista_prima'],
    ],
    'arg_lista_prima': [
        [',', 'expresion', 'arg_lista_prima'],
        [EPSILON],
    ],
}

NO_TERMINALES = set(GRAMATICA.keys())


# ══════════════════════════════════════════════
#  CÁLCULO DE CONJUNTOS PRIMERO
# ══════════════════════════════════════════════

def calcular_primero(gramatica):
    """
    Calcula PRIMERO(X) para todos los símbolos X.

    PRIMERO(X):
      - Si X es terminal: {X}
      - Si X -> ε: {ε}
      - Si X -> Y1 Y2 ... Yn:
          agrega PRIMERO(Y1) - {ε}
          si ε ∈ PRIMERO(Y1), agrega PRIMERO(Y2) - {ε}, etc.
          si ε ∈ PRIMERO(Yi) para todo i, agrega ε
    """
    primero = {nt: set() for nt in gramatica}

    # Para terminales, PRIMERO es él mismo
    def primero_simbolo(sym):
        if sym == EPSILON:
            return {EPSILON}
        if sym not in gramatica:          # es terminal
            return {sym}
        return primero[sym]

    # Iterar hasta punto fijo
    cambio = True
    while cambio:
        cambio = False
        for nt, producciones in gramatica.items():
            for prod in producciones:
                if prod == [EPSILON]:
                    if EPSILON not in primero[nt]:
                        primero[nt].add(EPSILON)
                        cambio = True
                    continue

                # Recorrer símbolo a símbolo
                todos_tienen_epsilon = True
                for sym in prod:
                    p = primero_simbolo(sym)
                    antes = len(primero[nt])
                    primero[nt] |= (p - {EPSILON})
                    if len(primero[nt]) > antes:
                        cambio = True
                    if EPSILON not in p:
                        todos_tienen_epsilon = False
                        break

                if todos_tienen_epsilon:
                    if EPSILON not in primero[nt]:
                        primero[nt].add(EPSILON)
                        cambio = True

    return primero


def primero_de_cadena(cadena, primero):
    """
    Calcula PRIMERO de una cadena de símbolos α = X1 X2 ... Xn.
    """
    resultado = set()
    for sym in cadena:
        if sym == EPSILON:
            resultado.add(EPSILON)
            break
        p = primero.get(sym, {sym})
        resultado |= (p - {EPSILON})
        if EPSILON not in p:
            break
    else:
        resultado.add(EPSILON)
    return resultado


# ══════════════════════════════════════════════
#  CÁLCULO DE CONJUNTOS SIGUIENTE
# ══════════════════════════════════════════════

def calcular_siguiente(gramatica, primero):
    """
    Calcula SIGUIENTE(A) para todos los no-terminales A.

    Reglas:
      1. $ ∈ SIGUIENTE(S)  (S = símbolo inicial)
      2. Si A -> α B β:
           SIGUIENTE(B) ⊇ PRIMERO(β) - {ε}
      3. Si A -> α B  o  A -> α B β  con ε ∈ PRIMERO(β):
           SIGUIENTE(B) ⊇ SIGUIENTE(A)
    """
    siguiente = {nt: set() for nt in gramatica}
    siguiente[START].add(EOF)

    cambio = True
    while cambio:
        cambio = False
        for nt, producciones in gramatica.items():
            for prod in producciones:
                if prod == [EPSILON]:
                    continue
                for i, sym in enumerate(prod):
                    if sym not in gramatica:   # terminal, saltar
                        continue
                    beta = prod[i+1:]          # lo que viene después de sym

                    # Regla 2
                    p_beta = primero_de_cadena(beta, primero) if beta else {EPSILON}
                    antes = len(siguiente[sym])
                    siguiente[sym] |= (p_beta - {EPSILON})
                    if len(siguiente[sym]) > antes:
                        cambio = True

                    # Regla 3
                    if EPSILON in p_beta or not beta:
                        antes = len(siguiente[sym])
                        siguiente[sym] |= siguiente[nt]
                        if len(siguiente[sym]) > antes:
                            cambio = True

    return siguiente


# ══════════════════════════════════════════════
#  CONSTRUCCIÓN DE LA TABLA LL(1)
# ══════════════════════════════════════════════

def construir_tabla_ll(gramatica, primero, siguiente):
    """
    Construye la tabla M[A, a] donde:
      M[A, a] = producción  si a ∈ PRIMERO(α) o (ε ∈ PRIMERO(α) y a ∈ SIGUIENTE(A))
      M[A, a] = 'error'     en cualquier otro caso
    """
    tabla = {}   # (no_terminal, terminal) -> produccion o 'error'

    for nt, producciones in gramatica.items():
        for prod in producciones:
            if prod == [EPSILON]:
                p_alpha = {EPSILON}
            else:
                p_alpha = primero_de_cadena(prod, primero)

            for terminal in (p_alpha - {EPSILON}):
                clave = (nt, terminal)
                if clave in tabla:
                    # Conflicto — gramática no es LL(1) en este punto
                    tabla[clave] = f"CONFLICTO: {tabla[clave]} | {prod}"
                else:
                    tabla[clave] = prod

            if EPSILON in p_alpha:
                for terminal in siguiente[nt]:
                    clave = (nt, terminal)
                    if clave in tabla:
                        tabla[clave] = f"CONFLICTO: {tabla[clave]} | {prod}"
                    else:
                        tabla[clave] = prod

    return tabla


# ══════════════════════════════════════════════
#  FUNCIÓN PRINCIPAL — genera todo
# ══════════════════════════════════════════════

def generar_tabla():
    """
    Retorna (primero, siguiente, tabla_ll) para la gramática de DiamondLang.
    """
    primero   = calcular_primero(GRAMATICA)
    siguiente = calcular_siguiente(GRAMATICA, primero)
    tabla     = construir_tabla_ll(GRAMATICA, primero, siguiente)
    return primero, siguiente, tabla


def tabla_a_dict_serializable(tabla):
    """Convierte la tabla LL(1) a un dict JSON-serializable."""
    resultado = {}
    for (nt, term), prod in tabla.items():
        if nt not in resultado:
            resultado[nt] = {}
        if isinstance(prod, list):
            resultado[nt][term] = ' '.join(prod) if prod != [EPSILON] else 'ε'
        else:
            resultado[nt][term] = str(prod)
    return resultado


def sets_a_dict_serializable(sets_dict):
    """Convierte PRIMERO/SIGUIENTE a dict JSON-serializable."""
    return {k: sorted(list(v)) for k, v in sets_dict.items()}


# ── Prueba rápida ──
if __name__ == '__main__':
    primero, siguiente, tabla = generar_tabla()
    print(f"\n{'='*50}")
    print("  CONJUNTOS PRIMERO (muestra)")
    print('='*50)
    for nt in list(NO_TERMINALES)[:8]:
        print(f"  PRIMERO({nt:30s}) = {sorted(primero[nt])}")

    print(f"\n{'='*50}")
    print("  CONJUNTOS SIGUIENTE (muestra)")
    print('='*50)
    for nt in list(NO_TERMINALES)[:8]:
        print(f"  SIGUIENTE({nt:29s}) = {sorted(siguiente[nt])}")

    conflictos = [(k,v) for k,v in tabla.items() if isinstance(v,str) and 'CONFLICTO' in v]
    print(f"\n  Total entradas tabla LL(1): {len(tabla)}")
    print(f"  Conflictos detectados: {len(conflictos)}")
    if conflictos:
        for k, v in conflictos:
            print(f"    {k}: {v}")
