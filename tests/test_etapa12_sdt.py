"""
╔══════════════════════════════════════════════════════════╗
║   DiamondLang 💎 — Tests de la Fase B (SDT → Julia)      ║
║                 test_etapa12_sdt.py                      ║
║  Entrega Final — Etapa 12.                               ║
║                                                         ║
║  Ejecutable directo (sin pytest ni red):                ║
║      python test_etapa12_sdt.py                         ║
║                                                         ║
║  Cubre: unitarios por construcción, integración         ║
║  (factorial/fibonacci/elseif), detección de 'principal', ║
║  contrato del endpoint /traducir y no-regresión del      ║
║  pipeline /parsear existente.                            ║
╚══════════════════════════════════════════════════════════╝
"""

import sys

import os as _os, sys as _sys
_PROJ_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _PROJ_ROOT not in _sys.path:
    _sys.path.insert(0, _PROJ_ROOT)
from sintactico.parser_predictivo import ParserPredictivo
from sintactico.parser_recursivo import ParserRecursivo
from semantico.semantico import AnalizadorSemantico
from traduccion import sdt


# ── Mini-arnés de aserciones ──
_PASS = 0
_FAIL = 0


def check(nombre, cond, extra=''):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ✓ {nombre}")
    else:
        _FAIL += 1
        print(f"  ✗ {nombre}   {extra}")


def traducir_prog(prog, metodo='predictivo', con_header=False):
    """Pipeline completo lexer→parser→semántico→SDT. Falla si el programa no
    es válido (los tests de SDT solo traducen programas válidos)."""
    Parser = ParserPredictivo if metodo == 'predictivo' else ParserRecursivo
    p = Parser(prog)
    r = p.analizar()
    assert r['valido'], f"sintaxis inválida: {r.get('errores')}"
    sem = AnalizadorSemantico(p.arbol_raiz)
    rs = sem.analizar()
    assert rs['valido_semantico'], f"semántica inválida: {rs['errores_semanticos']}"
    return sdt.traducir(p.arbol_raiz, sem.tabla, con_header=con_header)


def _func(cuerpo, cabecera='funcion principal()'):
    """Envuelve un cuerpo en una función para tener un programa válido."""
    return f"{cabecera}\nhacer\n{cuerpo}\nfin_funcion"


# ══════════════════════════════════════════════
#  A) UNITARIOS — una construcción por test
# ══════════════════════════════════════════════
def test_unitarios():
    print("\n── A) Unitarios por construcción ──")

    # función sin parámetros, sin retorno (vacio)
    j = traducir_prog(_func("    escribir(1)"))
    check("función sin params/retorno → function principal()",
          "function principal()" in j and "end" in j)

    # función con parámetros y retorno tipado
    j = traducir_prog("funcion sumar(entero a, entero b) retornar entero\nhacer\n    retornar a + b\nfin_funcion")
    check("params + retorno → function sumar(a::Int, b::Int)::Int",
          "function sumar(a::Int, b::Int)::Int" in j)

    # declaración de cada tipo
    j = traducir_prog(_func('    entero e <- 1\n    real r <- 1.5\n    cadena c <- "x"\n    booleano b <- verdadero'))
    check("decl entero → e::Int = 1", "e::Int = 1" in j)
    check("decl real → r::Float64 = 1.5", "r::Float64 = 1.5" in j)
    check('decl cadena → c::String = "x"', 'c::String = "x"' in j)
    check("decl booleano → b::Bool = true", "b::Bool = true" in j)

    # asignación
    j = traducir_prog(_func("    entero e <- 1\n    e <- e + 1"))
    check("asignación → e = e + 1", "e = e + 1" in j)

    # si simple
    j = traducir_prog(_func("    si 1 > 0 entonces\n        escribir(1)\n    fin_si"))
    check("si simple → if ... end", "if 1 > 0" in j and j.count("end") >= 1)

    # si/sino simple
    j = traducir_prog(_func("    si 1 > 0 entonces\n        escribir(1)\n    sino\n        escribir(2)\n    fin_si"))
    check("si/sino → if/else/end", "if 1 > 0" in j and "else" in j and "elseif" not in j)

    # si/sino con else-if → colapsa a elseif
    j = traducir_prog(_func(
        "    si 1 > 2 entonces\n        escribir(1)\n    sino\n        si 3 > 4 entonces\n            escribir(2)\n        sino\n            escribir(3)\n        fin_si\n    fin_si"))
    check("si/sino/si anidado único → COLAPSA a elseif",
          "    elseif 3 > 4" in j and j.count("    end") == 1, extra=repr(j))

    # si/sino anidado NO único → NO colapsa (else + bloque)
    j = traducir_prog(_func(
        "    si 1 > 2 entonces\n        escribir(1)\n    sino\n        si 3 > 4 entonces\n            escribir(2)\n        fin_si\n        escribir(9)\n    fin_si"))
    check("sino con MÁS que un si → NO colapsa (else)",
          "else" in j and "elseif" not in j, extra=repr(j))

    # mientras
    j = traducir_prog(_func("    entero i <- 0\n    mientras i < 3 hacer\n        i <- i + 1\n    fin_mientras"))
    check("mientras → while ... end", "while i < 3" in j)

    # para con paso → for in a:paso:b  (la var del 'para' debe pre-declararse:
    # el análisis semántico la trata como un USO, no como una declaración)
    j = traducir_prog(_func("    entero k <- 0\n    para k desde 1 hasta 10 paso 2 hacer\n        escribir(k)\n    fin_para"))
    check("para con paso → for k in 1:2:10", "for k in 1:2:10" in j)

    # para sin paso → for in a:b
    j = traducir_prog(_func("    entero k <- 0\n    para k desde 1 hasta 10 hacer\n        escribir(k)\n    fin_para"))
    check("para sin paso → for k in 1:10", "for k in 1:10" in j)

    # retornar con expresión
    j = traducir_prog("funcion f() retornar entero\nhacer\n    retornar 42\nfin_funcion")
    check("retornar → return 42", "return 42" in j)

    # escribir
    j = traducir_prog(_func("    escribir(7)"))
    check("escribir → println(7)", "println(7)" in j)

    # leer cada tipo
    j = traducir_prog(_func("    entero e <- 0\n    leer(e)"))
    check("leer entero → parse(Int, readline())", "e = parse(Int, readline())" in j)
    j = traducir_prog(_func("    real r <- 0.0\n    leer(r)"))
    check("leer real → parse(Float64, readline())", "r = parse(Float64, readline())" in j)
    j = traducir_prog(_func('    cadena c <- ""\n    leer(c)'))
    check("leer cadena → readline() (sin parse)", "c = readline()" in j)
    j = traducir_prog(_func("    booleano b <- verdadero\n    leer(b)"))
    check("leer booleano → parse(Bool, readline())", "b = parse(Bool, readline())" in j)

    # aritmética simple
    j = traducir_prog(_func("    entero e <- 2 + 3 * 4 - 1"))
    check("aritmética → 2 + 3 * 4 - 1", "2 + 3 * 4 - 1" in j)

    # división ENTERA → ÷
    j = traducir_prog(_func("    entero a <- 10\n    entero b <- 3\n    entero c <- a / b"))
    check("división entero/entero → ÷", "c::Int = a ÷ b" in j)

    # división REAL → /
    j = traducir_prog(_func("    real x <- 5.0\n    real z <- x / 2"))
    check("división con real → /", "z::Float64 = x / 2" in j)

    # potencia ** → ^
    j = traducir_prog(_func("    entero p <- 2 ** 8"))
    check("potencia ** → ^", "2 ^ 8" in j)

    # concatenación de cadenas + → *
    j = traducir_prog(_func('    cadena s <- "hola" + " mundo"'))
    check("concatenación + → *", '"hola" * " mundo"' in j)

    # lógicos
    j = traducir_prog(_func("    booleano b <- verdadero y falso o no verdadero"))
    check("lógicos y/o/no → &&/||/!", "true && false || !true" in j)

    # comparaciones
    j = traducir_prog(_func("    booleano b <- 1 <= 2"))
    check("comparación <= → <=", "1 <= 2" in j)

    # llamada como sentencia y como expresión
    j = traducir_prog(
        "funcion g(entero n) retornar entero\nhacer\n    retornar n\nfin_funcion\n"
        "funcion principal()\nhacer\n    entero r <- g(5)\n    g(7)\nfin_funcion")
    check("llamada como expresión → g(5)", "r::Int = g(5)" in j)
    check("llamada como sentencia → g(7)", "g(7)" in j)


# ══════════════════════════════════════════════
#  B) INTEGRACIÓN — programas completos
# ══════════════════════════════════════════════
FACTORIAL = """funcion factorial(entero n) retornar entero
hacer
    si n <= 1 entonces
        retornar 1
    sino
        retornar n * factorial(n - 1)
    fin_si
fin_funcion
funcion principal()
hacer
    escribir(factorial(5))
fin_funcion"""

FIBONACCI = """funcion fibonacci(entero n) retornar entero
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
fin_funcion"""

CLASIFICAR = """funcion clasificar(real nota) retornar cadena
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
fin_funcion"""


def test_integracion():
    print("\n── B) Integración (programas completos) ──")

    j = traducir_prog(FACTORIAL)
    check("factorial: recursión + if/else",
          "function factorial(n::Int)::Int" in j and "factorial(n - 1)" in j and "return 1" in j)

    j = traducir_prog(FIBONACCI)
    check("fibonacci: while + acumuladores",
          "while i < n" in j and "temp::Int = a + b" in j and "return a" in j)

    j = traducir_prog(CLASIFICAR)
    check("clasificar: dos niveles → if/elseif/else",
          "if nota >= 9.0" in j and "elseif nota >= 7.0" in j and "else" in j)

    # Mismo programa, ambos parsers → misma salida (agnóstico al método)
    jp = traducir_prog(FACTORIAL, metodo='predictivo')
    jr = traducir_prog(FACTORIAL, metodo='recursivo')
    check("factorial: predictivo == recursivo (agnóstico al parser)", jp == jr,
          extra="las salidas difieren")


# ══════════════════════════════════════════════
#  C) DETECCIÓN DE 'principal'
# ══════════════════════════════════════════════
def test_principal():
    print("\n── C) Detección de 'principal' ──")

    j = traducir_prog(_func("    escribir(1)"))
    check("con principal() → invoca principal() al final",
          j.rstrip().endswith("principal()"))

    j = traducir_prog("funcion otra()\nhacer\n    escribir(1)\nfin_funcion")
    check("sin principal → NO hay invocación automática",
          "principal()" not in j)


# ══════════════════════════════════════════════
#  D) CONTRATO DEL ENDPOINT /traducir
# ══════════════════════════════════════════════
def test_endpoint():
    print("\n── D) Contrato del endpoint /traducir ──")
    import server
    c = server.app.test_client()

    r = c.post('/traducir', json={"codigo": _func("    escribir(21 * 2)"), "metodo": "predictivo"})
    d = r.get_json()
    check("válido → ok=True y julia no vacío", d.get('ok') is True and bool(d.get('julia')))
    check("válido → header presente", "DiamondLang Compiler v5.0" in (d.get('julia') or ""))

    r = c.post('/traducir', json={"codigo": "funcion f()\nhacer\n    si 1 > 0\n        escribir(1)\n    fin_si\nfin_funcion"})
    d = r.get_json()
    check("error sintáctico → ok=False, fase_fallida=sintactica",
          d.get('ok') is False and d.get('fase_fallida') == 'sintactica')

    r = c.post('/traducir', json={"codigo": _func("    escribir(noexiste)")})
    d = r.get_json()
    check("error semántico → ok=False, fase_fallida=semantica",
          d.get('ok') is False and d.get('fase_fallida') == 'semantica')

    r = c.post('/traducir', json={"codigo": _func("    entero x <- 3 @ 4")})
    d = r.get_json()
    check("error léxico → ok=False, fase_fallida=lexica",
          d.get('ok') is False and d.get('fase_fallida') == 'lexica')


# ══════════════════════════════════════════════
#  E) NO-REGRESIÓN del pipeline existente
#     (los tests 1-9 + etapa11 fueron borrados por el usuario;
#      esta es la verificación sustituta de que /parsear sigue intacto)
# ══════════════════════════════════════════════
def test_no_regresion():
    print("\n── E) No-regresión: /parsear sigue intacto ──")
    import server
    c = server.app.test_client()
    r = c.post('/parsear', json={"codigo": FACTORIAL, "metodo": "recursivo"})
    d = r.get_json()
    check("/parsear factorial → valido y valido_semantico",
          d.get('valido') is True and d.get('valido_semantico') is True)
    check("/parsear sigue devolviendo 'simbolos'", isinstance(d.get('simbolos'), list))


# ══════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════
if __name__ == '__main__':
    print("═" * 60)
    print("  💎 Tests Etapa 12 — SDT (DiamondLang → Julia)")
    print("═" * 60)

    test_unitarios()
    test_integracion()
    test_principal()
    test_endpoint()
    test_no_regresion()

    print("\n" + "═" * 60)
    print(f"  Resultado: {_PASS} ✓   {_FAIL} ✗")
    print("═" * 60)
    if _FAIL == 0:
        print("✓ Todos los tests de la Etapa 12 (SDT) pasaron.")
        sys.exit(0)
    else:
        print("✗ Hubo fallos en la Etapa 12.")
        sys.exit(1)
