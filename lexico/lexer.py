"""
╔══════════════════════════════════════════════════════════╗
║           DiamondLang 💎 — Analizador Léxico            ║
║                      lexer.py                           ║
║  Curso: Teoría de Compiladores                          ║
║  Lenguaje fuente: DiamondLang (palabras clave español)  ║
║  Lenguaje destino: Julia                                ║
╚══════════════════════════════════════════════════════════╝

Uso:
    python lexer.py

Dependencias:
    pip install colorama tabulate
"""

import re
import sys

# ─────────────────────────────────────────────
#  Intentamos importar librerías opcionales
# ─────────────────────────────────────────────
try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
    COLOR_DISPONIBLE = True
except ImportError:
    COLOR_DISPONIBLE = False
    print("[AVISO] colorama no instalado. Ejecuta: pip install colorama")

try:
    from tabulate import tabulate
    TABULATE_DISPONIBLE = True
except ImportError:
    TABULATE_DISPONIBLE = False
    print("[AVISO] tabulate no instalado. Ejecuta: pip install tabulate")


# ══════════════════════════════════════════════
#  SECCIÓN 1 — DEFINICIÓN DE TOKENS
#  Aquí definimos todos los tipos de tokens
#  que puede tener DiamondLang
# ══════════════════════════════════════════════

# Palabras reservadas del lenguaje
KEYWORDS = {
    'funcion', 'fin_funcion', 'retornar',
    'si', 'entonces', 'sino', 'fin_si',
    'para', 'desde', 'hasta', 'paso', 'hacer', 'fin_para',
    'mientras', 'fin_mientras',
    'y', 'o', 'no',
    'clase', 'fin_clase', 'nuevo', 'este',
    'leer', 'escribir',
}

# Palabras que representan tipos de datos
TIPOS = {'entero', 'real', 'cadena', 'booleano', 'vacio'}

# Palabras que representan valores booleanos
BOOLEANOS = {'verdadero', 'falso'}

# ──────────────────────────────────────────────
#  Patrones de tokens en orden de prioridad
#  IMPORTANTE: el orden importa. Python prueba
#  cada patrón de arriba hacia abajo y usa
#  el primero que coincida.
# ──────────────────────────────────────────────
TOKEN_PATTERNS = [
    # Comentarios de línea  //  texto
    ('COMENTARIO',    r'//[^\n]*'),

    # Comentarios de bloque  /* texto */
    ('COMENTARIO',    r'/\*[\s\S]*?\*/'),

    # Número real ANTES que entero (3.14 antes que 3)
    ('REAL',          r'\d+\.\d+'),

    # Número entero
    ('ENTERO',        r'\d+'),

    # Cadena con comillas dobles  "texto"
    ('CADENA',        r'"(?:[^"\\]|\\.)*"'),

    # Cadena con comillas simples  'texto'
    ('CADENA',        r"'(?:[^'\\]|\\.)*'"),

    # Operadores de dos caracteres  ==  !=  <=  >=  <-  **
    ('OPERADOR',      r'==|!=|<=|>=|<-|\*\*|\+\+|--'),

    # Operadores de un carácter  + - * / ^ % < > =
    ('OPERADOR',      r'[+\-*/^%<>=!]'),

    # Símbolos de puntuación  ( ) { } [ ] , ; :
    ('SIMBOLO',       r'[(){}\[\],;:.]'),

    # Identificadores y palabras clave
    # Soporta tildes (á é í ó ú) y la letra ñ
    ('IDENTIFICADOR', r'[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ_][a-zA-ZáéíóúÁÉÍÓÚñÑüÜ_0-9]*'),

    # Espacios y tabulaciones (se ignoran, no generan token)
    ('__SKIP',        r'[ \t\r]+'),

    # Salto de línea (se usa solo para contar líneas)
    ('__NL',          r'\n'),
]

# Compilamos todos los patrones en un solo regex gigante
# Esto es más eficiente que probar uno por uno
MASTER_REGEX = re.compile(
    '|'.join(f'(?P<PAT{i}>{pat})' for i, (_, pat) in enumerate(TOKEN_PATTERNS)),
    re.UNICODE
)


# ══════════════════════════════════════════════
#  SECCIÓN 2 — CLASE TOKEN
#  Representa un token individual con toda
#  su información
# ══════════════════════════════════════════════

class Token:
    """
    Un token es la unidad mínima del lenguaje.
    Tiene:
      - lexema:  el texto exacto encontrado  (ej: "funcion")
      - tipo:    su categoría               (ej: "KEYWORD")
      - linea:   en qué línea apareció      (ej: 3)
      - columna: en qué columna apareció    (ej: 5)
    """
    def __init__(self, lexema: str, tipo: str, linea: int, columna: int):
        self.lexema  = lexema
        self.tipo    = tipo
        self.linea   = linea
        self.columna = columna

    def __repr__(self):
        return f"Token({self.tipo}, {self.lexema!r}, L{self.linea}:C{self.columna})"


# ══════════════════════════════════════════════
#  SECCIÓN 3 — CLASE LEXER
#  El corazón del analizador léxico.
#  Recibe el código fuente y produce tokens.
# ══════════════════════════════════════════════

class Lexer:
    """
    Analizador léxico de DiamondLang.

    Uso básico:
        lexer = Lexer("funcion hola() hacer fin_funcion")
        tokens, errores = lexer.tokenizar()
    """

    def __init__(self, codigo_fuente: str):
        self.fuente  = codigo_fuente
        self.tokens  = []          # lista de tokens encontrados
        self.errores = []          # lista de errores léxicos

    def tokenizar(self):
        """
        Recorre el código fuente carácter por carácter
        usando expresiones regulares y produce tokens.

        Retorna:
            (tokens, errores) — dos listas
        """
        linea   = 1
        col_ini = 0  # posición en el string donde empieza la línea actual

        pos = 0  # posición actual en el string

        while pos < len(self.fuente):

            # Intentamos hacer coincidir el patrón con lo que queda del string
            m = MASTER_REGEX.match(self.fuente, pos)

            if m:
                # ── Encontramos algo reconocible ──
                lexema = m.group()
                col    = m.start() - col_ini + 1

                # Identificamos cuál patrón coincidió
                for i, (tipo, _) in enumerate(TOKEN_PATTERNS):
                    if m.group(f'PAT{i}') is not None:
                        tipo_encontrado = tipo
                        break

                if tipo_encontrado == '__SKIP':
                    # Espacio o tabulación → ignorar
                    pass

                elif tipo_encontrado == '__NL':
                    # Salto de línea → actualizar contadores
                    linea   += 1
                    col_ini  = m.end()

                else:
                    # ── Clasificación especial para identificadores ──
                    # Un identificador puede ser keyword, tipo o booleano
                    if tipo_encontrado == 'IDENTIFICADOR':
                        if lexema in KEYWORDS:
                            tipo_encontrado = 'KEYWORD'
                        elif lexema in TIPOS:
                            tipo_encontrado = 'TIPO'
                        elif lexema in BOOLEANOS:
                            tipo_encontrado = 'BOOLEANO'

                    # Guardamos el token
                    tok = Token(lexema, tipo_encontrado, linea, col)
                    self.tokens.append(tok)

                pos = m.end()

            else:
                # ── No coincidió ningún patrón → ERROR LÉXICO ──
                caracter_invalido = self.fuente[pos]
                col = pos - col_ini + 1

                error_msg = (
                    f"Carácter inválido '{caracter_invalido}' "
                    f"en Línea {linea}, Columna {col}"
                )
                self.errores.append(error_msg)

                # Guardamos el token de error (no abortamos el análisis)
                tok_error = Token(caracter_invalido, 'ERROR', linea, col)
                self.tokens.append(tok_error)

                pos += 1  # avanzamos un carácter y continuamos

        return self.tokens, self.errores


# ══════════════════════════════════════════════
#  SECCIÓN 4 — VISUALIZACIÓN EN CONSOLA
#  Funciones para mostrar los resultados
#  con colores usando colorama
# ══════════════════════════════════════════════

# Colores asignados a cada tipo de token
COLORES_TOKEN = {
    'KEYWORD':      Fore.MAGENTA  + Style.BRIGHT if COLOR_DISPONIBLE else '',
    'TIPO':         Fore.CYAN     + Style.BRIGHT if COLOR_DISPONIBLE else '',
    'IDENTIFICADOR':Fore.WHITE                   if COLOR_DISPONIBLE else '',
    'ENTERO':       Fore.YELLOW   + Style.BRIGHT if COLOR_DISPONIBLE else '',
    'REAL':         Fore.YELLOW                  if COLOR_DISPONIBLE else '',
    'CADENA':       Fore.GREEN    + Style.BRIGHT if COLOR_DISPONIBLE else '',
    'OPERADOR':     Fore.RED      + Style.BRIGHT if COLOR_DISPONIBLE else '',
    'SIMBOLO':      Fore.LIGHTYELLOW_EX          if COLOR_DISPONIBLE else '',
    'BOOLEANO':     Fore.LIGHTMAGENTA_EX         if COLOR_DISPONIBLE else '',
    'COMENTARIO':   Fore.LIGHTBLACK_EX           if COLOR_DISPONIBLE else '',
    'ERROR':        Back.RED + Fore.WHITE + Style.BRIGHT if COLOR_DISPONIBLE else '',
}

RESET = Style.RESET_ALL if COLOR_DISPONIBLE else ''


def colorear(texto: str, tipo: str) -> str:
    """Aplica el color correspondiente al tipo de token."""
    color = COLORES_TOKEN.get(tipo, '')
    return f"{color}{texto}{RESET}"


def mostrar_tokens_visual(tokens: list):
    """
    Muestra los tokens agrupados por línea,
    cada uno coloreado según su tipo.
    """
    print("\n" + "═" * 60)
    print("  💎 VISUALIZACIÓN DE TOKENS")
    print("═" * 60)

    # Agrupamos tokens por línea
    lineas = {}
    for tok in tokens:
        lineas.setdefault(tok.linea, []).append(tok)

    for num_linea in sorted(lineas):
        # Número de línea en gris
        prefijo = f"{Fore.LIGHTBLACK_EX if COLOR_DISPONIBLE else ''}{num_linea:3d} │{RESET} "
        toks_linea = lineas[num_linea]
        chips = "  ".join(
            colorear(f"[{tok.lexema}]", tok.tipo)
            for tok in toks_linea
        )
        print(prefijo + chips)

    print()


def mostrar_tabla_simbolos(tokens: list):
    """
    Muestra la tabla de símbolos léxicos con
    columnas: #, Lexema, TokenType, Línea, Columna
    """
    print("═" * 60)
    print("  📋 TABLA DE SÍMBOLOS LÉXICOS")
    print("═" * 60)

    filas = []
    for i, tok in enumerate(tokens, 1):
        tipo_coloreado = colorear(tok.tipo, tok.tipo)
        filas.append([i, tok.lexema, tipo_coloreado, tok.linea, tok.columna])

    encabezados = ["#", "Lexema", "TokenType", "Línea", "Columna"]

    if TABULATE_DISPONIBLE:
        print(tabulate(filas, headers=encabezados, tablefmt="rounded_outline"))
    else:
        # Tabla manual si no hay tabulate
        ancho = [6, 22, 20, 8, 9]
        sep = "+" + "+".join("-" * (a + 2) for a in ancho) + "+"
        def fila_str(vals):
            return "|" + "|".join(f" {str(v):<{ancho[i]}} " for i, v in enumerate(vals)) + "|"
        print(sep)
        print(fila_str(encabezados))
        print(sep)
        for f in filas:
            print(fila_str(f))
        print(sep)

    print()


def mostrar_errores(errores: list):
    """Muestra los errores léxicos encontrados."""
    if not errores:
        if COLOR_DISPONIBLE:
            print(Fore.GREEN + Style.BRIGHT + "  ✓ Sin errores léxicos." + RESET)
        else:
            print("  Sin errores léxicos.")
        return

    print("═" * 60)
    if COLOR_DISPONIBLE:
        print(Fore.RED + Style.BRIGHT + "  ⚠  ERRORES LÉXICOS" + RESET)
    else:
        print("  ERRORES LÉXICOS")
    print("═" * 60)
    for err in errores:
        prefijo = f"{Fore.RED + Style.BRIGHT if COLOR_DISPONIBLE else ''}ERROR{RESET}"
        print(f"  [{prefijo}] {err}")
    print()


def mostrar_estadisticas(tokens: list, errores: list):
    """Muestra un resumen estadístico del análisis."""
    print("═" * 60)
    print("  📊 ESTADÍSTICAS")
    print("═" * 60)

    conteo = {}
    for tok in tokens:
        conteo[tok.tipo] = conteo.get(tok.tipo, 0) + 1

    total = len(tokens)
    print(f"  Total de tokens    : {colorear(str(total), 'IDENTIFICADOR')}")
    for tipo, cant in sorted(conteo.items()):
        print(f"  {tipo:<18}: {colorear(str(cant), tipo)}")
    print(f"  Errores léxicos   : {colorear(str(len(errores)), 'ERROR') if errores else colorear('0', 'CADENA')}")
    print()


# ══════════════════════════════════════════════
#  SECCIÓN 5 — EJEMPLOS PREDEFINIDOS
#  Cadenas de código DiamondLang para probar
# ══════════════════════════════════════════════

EJEMPLOS = {
    "1": {
        "nombre": "Hola Mundo",
        "codigo": '''\
// Hola Mundo en DiamondLang
funcion principal()
hacer
    cadena mensaje <- "¡Hola, Mundo!"
    escribir(mensaje)
fin_funcion'''
    },
    "2": {
        "nombre": "Factorial recursivo",
        "codigo": '''\
// Factorial recursivo
funcion factorial(entero n) retornar entero
hacer
    si n <= 1 entonces
        retornar 1
    sino
        retornar n * factorial(n - 1)
    fin_si
fin_funcion'''
    },
    "3": {
        "nombre": "Fibonacci iterativo",
        "codigo": '''\
// Fibonacci iterativo
funcion fibonacci(entero n) retornar entero
hacer
    entero a <- 0
    entero b <- 1
    entero i <- 0
    mientras i < n hacer
        entero temp <- a + b
        a <- b
        b <- temp
        i <- i + 1
    fin_mientras
    retornar a
fin_funcion'''
    },
    "4": {
        "nombre": "Condicional y bucles",
        "codigo": '''\
funcion clasificar(real nota) retornar cadena
hacer
    si nota >= 9.0 entonces
        retornar "Sobresaliente"
    sino
        si nota >= 7.0 entonces
            retornar "Aprobado"
        sino
            retornar "Reprobado"
        fin_si
    fin_si
fin_funcion'''
    },
    "5": {
        "nombre": "Con errores léxicos",
        "codigo": '''\
funcion prueba()
hacer
    entero x <- 10
    entero y <- x @ 3
    cadena s <- "sin cerrar
    real z <- 3.14#2
    escribir(x + y)
fin_funcion'''
    },
}


# ══════════════════════════════════════════════
#  SECCIÓN 6 — MENÚ PRINCIPAL
#  Punto de entrada del programa
# ══════════════════════════════════════════════

def ejecutar_analisis(codigo: str):
    """Ejecuta el análisis léxico completo sobre el código dado."""
    lexer = Lexer(codigo)
    tokens, errores = lexer.tokenizar()

    mostrar_tokens_visual(tokens)
    mostrar_tabla_simbolos(tokens)
    mostrar_errores(errores)
    mostrar_estadisticas(tokens, errores)


def menu():
    """Menú interactivo en consola."""

    banner = f"""
{'═' * 60}
{'  💎  DiamondLang — Analizador Léxico':^60}
{'  Lenguaje fuente → Julia':^60}
{'═' * 60}"""

    if COLOR_DISPONIBLE:
        print(Fore.MAGENTA + Style.BRIGHT + banner + RESET)
    else:
        print(banner)

    while True:
        print("\n  ¿Cómo deseas ingresar el código?\n")
        print("  [1] Escribir código manualmente")
        print("  [2] Seleccionar un ejemplo predefinido")
        print("  [0] Salir\n")

        opcion = input("  Opción: ").strip()

        if opcion == "0":
            print("\n  ¡Hasta luego! 💎\n")
            break

        elif opcion == "1":
            print("\n  Escribe tu código DiamondLang.")
            print("  Cuando termines, escribe una línea con solo '###' y presiona Enter.\n")
            lineas = []
            while True:
                linea = input()
                if linea.strip() == "###":
                    break
                lineas.append(linea)
            codigo = "\n".join(lineas)
            if codigo.strip():
                ejecutar_analisis(codigo)
            else:
                print("  [AVISO] No ingresaste código.")

        elif opcion == "2":
            print("\n  Ejemplos disponibles:\n")
            for k, v in EJEMPLOS.items():
                print(f"  [{k}] {v['nombre']}")
            print()
            sel = input("  Selecciona un ejemplo: ").strip()
            if sel in EJEMPLOS:
                ejemplo = EJEMPLOS[sel]
                print(f"\n  ── Código: {ejemplo['nombre']} ──")
                print()
                for linea in ejemplo['codigo'].splitlines():
                    print(f"  {Fore.LIGHTBLACK_EX if COLOR_DISPONIBLE else ''}{linea}{RESET}")
                ejecutar_analisis(ejemplo['codigo'])
            else:
                print("  [AVISO] Opción no válida.")

        else:
            print("  [AVISO] Opción no válida. Intenta de nuevo.")


# ══════════════════════════════════════════════
#  PUNTO DE ENTRADA
# ══════════════════════════════════════════════

if __name__ == "__main__":
    menu()
