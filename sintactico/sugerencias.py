"""
╔══════════════════════════════════════════════════════════╗
║   DiamondLang 💎 — Sugerencias contextuales              ║
║                  sugerencias.py                         ║
║  Genera mensajes "¿Quiso decir?" en español natural,    ║
║  específicos al no-terminal en curso y al token         ║
║  esperado. Solo lógica local, sin red.                  ║
╚══════════════════════════════════════════════════════════╝
"""


# ══════════════════════════════════════════════
#  HUMANIZACIÓN DE TOKENS
# ══════════════════════════════════════════════
# Texto amigable para mostrar al usuario en lugar
# del nombre interno del token.
TOKEN_A_TEXTO = {
    # Categorías léxicas
    'IDENTIFICADOR': "un nombre de variable o función",
    'ENTERO':        "un número entero",
    'REAL':          "un número real (con punto decimal)",
    'CADENA':        "una cadena de texto entre comillas",
    'BOOLEANO':      "un valor booleano (verdadero/falso)",
    '$':             "el final del archivo",

    # Operadores y símbolos
    '<-': "el operador de asignación '<-'",
    '==': "el operador de igualdad '=='",
    '!=': "el operador de desigualdad '!='",
    '<=': "el operador 'menor o igual' '<='",
    '>=': "el operador 'mayor o igual' '>='",
    '<':  "el operador 'menor que' '<'",
    '>':  "el operador 'mayor que' '>'",
    '+':  "el operador '+'",
    '-':  "el operador '-'",
    '*':  "el operador '*'",
    '/':  "el operador '/'",
    '%':  "el operador '%'",
    '**': "el operador de potencia '**'",
    '(':  "un paréntesis de apertura '('",
    ')':  "un paréntesis de cierre ')'",
    ',':  "una coma ','",
    ';':  "un punto y coma ';'",
    ':':  "dos puntos ':'",
    '.':  "un punto '.'",

    # Tipos
    'entero':   "el tipo 'entero'",
    'real':     "el tipo 'real'",
    'cadena':   "el tipo 'cadena'",
    'booleano': "el tipo 'booleano'",
    'vacio':    "el tipo 'vacio'",

    # Keywords (las más importantes)
    'funcion':      "la palabra clave 'funcion'",
    'fin_funcion':  "la palabra clave 'fin_funcion'",
    'si':           "la palabra clave 'si'",
    'entonces':     "la palabra clave 'entonces'",
    'sino':         "la palabra clave 'sino'",
    'fin_si':       "la palabra clave 'fin_si'",
    'mientras':     "la palabra clave 'mientras'",
    'hacer':        "la palabra clave 'hacer'",
    'fin_mientras': "la palabra clave 'fin_mientras'",
    'para':         "la palabra clave 'para'",
    'desde':        "la palabra clave 'desde'",
    'hasta':        "la palabra clave 'hasta'",
    'paso':         "la palabra clave 'paso'",
    'fin_para':     "la palabra clave 'fin_para'",
    'retornar':     "la palabra clave 'retornar'",
    'leer':         "la palabra clave 'leer'",
    'escribir':     "la palabra clave 'escribir'",
    'verdadero':    "el valor 'verdadero'",
    'falso':        "el valor 'falso'",
    'y':            "el operador lógico 'y'",
    'o':            "el operador lógico 'o'",
    'no':           "el operador lógico 'no'",
}


def humanizar(token: str) -> str:
    """Devuelve la descripción amigable del token."""
    return TOKEN_A_TEXTO.get(token, f"'{token}'")


# ══════════════════════════════════════════════
#  REGLAS LOCALES — (no_terminal, esperado) → frase
# ══════════════════════════════════════════════
# Usamos '*' como comodín cuando la sugerencia depende
# solo del no-terminal y no del token específico.

REGLAS_LOCALES = {
    # ── Estructura de funciones ──
    ('def_funcion', 'funcion'):
        "Una definición de función comienza con la palabra clave 'funcion'.",
    ('def_funcion', 'IDENTIFICADOR'):
        "Falta el nombre de la función después de 'funcion'. "
        "Ejemplo: funcion mi_funcion(...) hacer ... fin_funcion",
    ('def_funcion', '('):
        "Falta el paréntesis '(' que inicia la lista de parámetros.",
    ('def_funcion', ')'):
        "Falta el paréntesis ')' que cierra la lista de parámetros.",
    ('def_funcion', 'hacer'):
        "Falta 'hacer' antes del cuerpo de la función.",
    ('def_funcion', 'fin_funcion'):
        "Falta cerrar la función con 'fin_funcion'.",

    # ── Condicional ──
    ('sent_si', 'si'):
        "Una sentencia condicional comienza con 'si'.",
    ('sent_si', 'entonces'):
        "Falta la palabra clave 'entonces' después de la condición del 'si'.",
    ('sent_si', 'fin_si'):
        "Falta cerrar el bloque condicional con 'fin_si'.",
    ('rama_sino', 'sino'):
        "La rama alternativa de un 'si' se introduce con 'sino'.",

    # ── Mientras ──
    ('sent_mientras', 'mientras'):
        "Un bucle 'mientras' comienza con la palabra clave 'mientras'.",
    ('sent_mientras', 'hacer'):
        "Falta 'hacer' después de la condición del 'mientras'.",
    ('sent_mientras', 'fin_mientras'):
        "Falta cerrar el bucle con 'fin_mientras'.",

    # ── Para ──
    ('sent_para', 'para'):
        "Un bucle iterativo comienza con 'para'.",
    ('sent_para', 'IDENTIFICADOR'):
        "Falta el nombre de la variable de iteración después de 'para'.",
    ('sent_para', 'desde'):
        "Falta 'desde' con el valor inicial del bucle 'para'.",
    ('sent_para', 'hasta'):
        "Falta 'hasta' con el valor final del bucle 'para'.",
    ('sent_para', 'hacer'):
        "Falta 'hacer' antes del cuerpo del bucle 'para'.",
    ('sent_para', 'fin_para'):
        "Falta cerrar el bucle con 'fin_para'.",
    ('paso_opt', 'paso'):
        "Si quieres un paso distinto a 1, usa 'paso <expresion>' antes de 'hacer'.",

    # ── Declaración de variable ──
    ('decl_variable', 'IDENTIFICADOR'):
        "Falta el nombre de la variable después del tipo. "
        "Ejemplo: entero contador <- 0",
    ('decl_variable', '<-'):
        "¿Olvidó la asignación '<-' después de declarar la variable? "
        "Ejemplo: entero x <- 10",
    ('decl_variable', '*'):
        "Una declaración de variable tiene la forma: <tipo> <nombre> <- <expresion>.",

    # ── Sentencias con identificador (asignación o llamada) ──
    ('sentencia_id', 'IDENTIFICADOR'):
        "Una sentencia que comienza con un identificador es una asignación o una llamada.",
    ('sentencia_id_cola', '<-'):
        "Después de un identificador se espera '<-' para asignar "
        "o '(' para llamar a una función.",
    ('sentencia_id_cola', '('):
        "Después de un identificador se espera '<-' para asignar "
        "o '(' para llamar a una función.",
    ('sentencia_id_cola', '*'):
        "Después de un identificador se espera '<-' para asignar "
        "o '(' para llamar a una función.",

    # ── Retorno ──
    ('sent_retornar', 'retornar'):
        "Una sentencia de retorno comienza con 'retornar'.",
    ('sent_retornar', '*'):
        "Después de 'retornar' se espera una expresión a devolver.",

    # ── Escribir / leer ──
    ('sent_escribir', 'escribir'):
        "Una sentencia de salida comienza con 'escribir'.",
    ('sent_escribir', '('):
        "Sintaxis: escribir(<expresion>). Falta el paréntesis de apertura.",
    ('sent_escribir', ')'):
        "Falta el paréntesis ')' que cierra la llamada a 'escribir'.",
    ('sent_leer', 'leer'):
        "Una sentencia de entrada comienza con 'leer'.",
    ('sent_leer', '('):
        "Sintaxis: leer(<nombre_variable>). Falta el paréntesis de apertura.",
    ('sent_leer', 'IDENTIFICADOR'):
        "'leer' espera el nombre de una variable: leer(nombre_variable).",
    ('sent_leer', ')'):
        "Falta el paréntesis ')' que cierra la llamada a 'leer'.",

    # ── Tipos ──
    ('tipo', '*'):
        "Se esperaba un tipo: 'entero', 'real', 'cadena', 'booleano' o 'vacio'.",
    ('parametros', '*'):
        "Cada parámetro se declara como <tipo> <nombre>, separados por comas.",
    ('param_lista', '*'):
        "Cada parámetro se declara como <tipo> <nombre>, separados por comas.",

    # ── Expresiones ──
    ('expr_primaria', '*'):
        "Se esperaba un valor (número, cadena, verdadero/falso), una variable, "
        "o una expresión entre paréntesis.",
    ('expresion', '*'):
        "Se esperaba una expresión válida.",
    ('op_rel', '*'):
        "Se esperaba un operador relacional: '==', '!=', '<', '>', '<=' o '>='.",
    ('argumentos', ')'):
        "Falta cerrar el paréntesis ')' de la lista de argumentos.",
    ('arg_lista', '*'):
        "Los argumentos se separan por comas. Cada uno es una expresión.",
    ("arg_lista'", ')'):
        "Falta cerrar el paréntesis ')' de la lista de argumentos.",
    ('sufijo_id', ')'):
        "Falta cerrar el paréntesis ')' de la llamada a función.",

    # ── Sentencia genérica ──
    ('sentencia', '*'):
        "Se esperaba el inicio de una sentencia: una declaración con tipo, "
        "una asignación, una llamada, o una palabra clave (si/mientras/para/"
        "retornar/leer/escribir).",
    ('declaracion', '*'):
        "Se esperaba una declaración: una función ('funcion ...') "
        "o una sentencia.",
    ('bloque', '*'):
        "Un bloque debe contener al menos una sentencia.",
}


# ══════════════════════════════════════════════
#  FUNCIÓN PRINCIPAL
# ══════════════════════════════════════════════

def sugerencia_local(no_terminal: str,
                     esperados,
                     lexema: str,
                     tipo_token: str = "") -> str:
    """
    Genera una sugerencia en español a partir del estado del parser.

    Estrategia:
      1. Buscar (no_terminal, esperado_principal) exacto.
      2. Buscar (no_terminal, '*') como fallback por contexto.
      3. Generar mensaje genérico humanizando los tokens esperados.

    `esperados` puede ser una lista o un set. Se toma el primer
    elemento "más informativo" (preferimos palabras clave sobre
    categorías léxicas).
    """
    esperados_lst = _ordenar_esperados(esperados)

    # 1. Regla específica
    for esp in esperados_lst:
        clave = (no_terminal, esp)
        if clave in REGLAS_LOCALES:
            return REGLAS_LOCALES[clave]

    # 2. Regla por no-terminal (comodín)
    clave_wild = (no_terminal, '*')
    if clave_wild in REGLAS_LOCALES:
        return REGLAS_LOCALES[clave_wild]

    # 3. Fallback genérico
    if not esperados_lst:
        return (f"No se esperaba '{lexema}' en este punto del programa.")

    if len(esperados_lst) == 1:
        return (f"Se esperaba {humanizar(esperados_lst[0])}, "
                f"pero se encontró '{lexema}'.")

    principales = esperados_lst[:3]
    partes = [humanizar(t) for t in principales]
    extra = ""
    if len(esperados_lst) > 3:
        extra = f" (y {len(esperados_lst) - 3} opciones más)"
    return ("Se esperaba uno de: " + ", ".join(partes) +
            f"{extra}, pero se encontró '{lexema}'.")


def _ordenar_esperados(esperados):
    """
    Ordena los esperados poniendo primero las palabras clave/símbolos
    'fuertes' (lo que el programador escribiría literalmente) y al
    final las categorías léxicas genéricas. Esto hace que las
    sugerencias sean más útiles.
    """
    if not esperados:
        return []

    lista = list(esperados)
    categoria_lexica = {'IDENTIFICADOR', 'ENTERO', 'REAL', 'CADENA',
                        'BOOLEANO', '$'}

    def prioridad(t):
        # Más bajo = más prioritario
        if t in categoria_lexica:
            return 2
        if len(t) == 1 and not t.isalpha():   # símbolo de un carácter
            return 1
        return 0   # keyword / operador multichar

    return sorted(lista, key=prioridad)


# ══════════════════════════════════════════════
#  PRUEBAS BÁSICAS
# ══════════════════════════════════════════════

if __name__ == '__main__':
    casos = [
        ('sent_si', ['entonces'], 'hacer'),
        ('sent_si', ['fin_si'], '$'),
        ('decl_variable', ['<-'], '5'),
        ('sent_para', ['hasta'], 'hacer'),
        ('expr_primaria', ['ENTERO', 'REAL', 'IDENTIFICADOR', '('], '+'),
        ('sentencia_id_cola', ['<-', '('], '+'),
        ('sentencia', ['si', 'mientras', 'IDENTIFICADOR'], '@'),
    ]
    for nt, esp, lex in casos:
        s = sugerencia_local(nt, esp, lex)
        print(f"  [{nt}] esperado={esp} lex='{lex}'")
        print(f"     → {s}")
        print()
