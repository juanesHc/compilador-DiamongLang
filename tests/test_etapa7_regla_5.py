"""
Tests de la regla semántica 5 — Etapa 7
(Aridad y tipos de argumentos en llamadas a función deben coincidir con
la firma declarada).

La regla 5 se dispara en dos lugares:
  - expr_primaria → IDENTIFICADOR sufijo_id   (llamada como expresión),
    cuando sufijo_id → ( argumentos );
  - sentencia_id  → IDENTIFICADOR sentencia_id_cola (llamada como
    sentencia), cuando sentencia_id_cola → ( argumentos ).

Sub-validaciones (todas verificadas aquí):
  - LLAMADA_ARIDAD     : nº de argumentos ≠ nº de parámetros. Se reporta
                         INCLUSO si algún argumento es ERROR (aridad y
                         tipos son chequeos independientes).
  - LLAMADA_TIPO       : argumento i incompatible con parámetro i. Un
                         argumento de tipo ERROR se salta (cascada F.10).
                         Promoción entero→real permitida.
  - LLAMADA_NO_FUNCION : el símbolo existe pero no es función (x(5) con x
                         variable). No se valida aridad ni tipos.
  - NO EXISTE          : USO_NO_DECLARADO ya lo reportó la Etapa 3; la
                         regla 5 no añade nada.

Para cada ejemplo nuevo en `ejemplos_semanticos/` (16–22):
  - se parsea con el parser RECURSIVO y con el PREDICTIVO,
  - se ejecuta el analizador semántico,
  - se verifica número exacto de errores, regla, posición, lexema y
    (cuando aplica) un fragmento del mensaje y el contexto.

Adicionales:
  - Unit test del helper `extraer_expresiones_de_argumentos` (TAREA 1):
    0, 1, 2, 3 argumentos + caso anidado.
  - No-regresión: factorial recursivo completo (ejemplo 22), 0 errores.
  - Combinado: reglas 1 + 2 + 3 + 4 + 5 en un mismo programa; las cinco
    deben reportarse sin abortar.
  - Smoke tests de cierre (los tres descritos en la TAREA 5).

Ejecutar con:
    python3 test_etapa7_regla_5.py
"""

import os as _os, sys as _sys
_PROJ_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _PROJ_ROOT not in _sys.path:
    _sys.path.insert(0, _PROJ_ROOT)
from sintactico.parser_recursivo import ParserRecursivo
from sintactico.parser_predictivo import ParserPredictivo
from semantico.semantico import AnalizadorSemantico
from sintactico.arbol import (raiz_logica, etiqueta_normalizada,
                               extraer_expresiones_de_argumentos)


PARSERS = [("recursivo", ParserRecursivo), ("predictivo", ParserPredictivo)]


# ══════════════════════════════════════════════
#  HELPERS DE EJECUCIÓN
# ══════════════════════════════════════════════

def _analizar(parser_clase, codigo):
    p = parser_clase(codigo)
    p.analizar()
    r = AnalizadorSemantico(p.arbol_raiz).analizar()
    return p, r


def _buscar_argumentos(nodo):
    """Primer nodo cuya etiqueta normalizada sea 'argumentos' (pre-orden)."""
    if etiqueta_normalizada(nodo.etiqueta) == 'argumentos':
        return nodo
    for h in nodo.hijos:
        encontrado = _buscar_argumentos(h)
        if encontrado is not None:
            return encontrado
    return None


def _check_primer_error(errs, esperado, nombre_parser):
    assert len(errs) >= 1, (
        f"[{nombre_parser}] no se reportó ningún error semántico, "
        f"esperaba al menos uno: {esperado!r}"
    )
    e = errs[0]
    for clave, valor_esperado in esperado.items():
        valor_actual = e[clave]
        assert valor_actual == valor_esperado, (
            f"[{nombre_parser}] error #1: campo {clave!r} "
            f"esperaba {valor_esperado!r}, obtuvo {valor_actual!r}"
        )


def _check_contexto(errs, esperado, nombre_parser):
    contexto = errs[0].get("contexto", {})
    for clave, valor_esperado in esperado.items():
        valor_actual = contexto.get(clave)
        assert valor_actual == valor_esperado, (
            f"[{nombre_parser}] contexto[{clave!r}]: "
            f"esperaba {valor_esperado!r}, obtuvo {valor_actual!r}"
        )


# ══════════════════════════════════════════════
#  TAREA 1 — UNIT TEST DEL HELPER DE ARGUMENTOS
# ══════════════════════════════════════════════

# La llamada vive dentro de `principal`; `f` toma 1 parámetro (irrelevante
# para el helper, que sólo cuenta expresiones en la lista de argumentos).
_PLANTILLA_ARGS = (
    "funcion f(entero a) retornar entero\n"
    "hacer\n"
    "    retornar a\n"
    "fin_funcion\n"
    "\n"
    "funcion principal() retornar entero\n"
    "hacer\n"
    "    entero r <- f(%s)\n"
    "    retornar r\n"
    "fin_funcion\n"
)


def test_helper_extraer_argumentos():
    """El helper devuelve la lista plana correcta para 0, 1, 2 y 3
    argumentos, en ambos parsers."""
    casos = {0: "", 1: "1", 2: "1, 2", 3: "1, 2, 3"}
    for n_esperado, args in casos.items():
        codigo = _PLANTILLA_ARGS % args
        for nombre_parser, ParserClase in PARSERS:
            p = ParserClase(codigo)
            p.analizar()
            assert len(p.errores) == 0, (
                f"[{nombre_parser}] la plantilla con {n_esperado} arg(s) "
                f"debería ser sintácticamente válida; errores={p.errores}"
            )
            raiz = raiz_logica(p.arbol_raiz)
            nodo_args = _buscar_argumentos(raiz)
            exprs = extraer_expresiones_de_argumentos(nodo_args)
            assert len(exprs) == n_esperado, (
                f"[{nombre_parser}] f({args!r}): el helper devolvió "
                f"{len(exprs)} expresiones, esperaba {n_esperado}"
            )
            # Todos los nodos devueltos deben ser 'expresion'.
            for x in exprs:
                assert etiqueta_normalizada(x.etiqueta) == 'expresion', (
                    f"[{nombre_parser}] el helper devolvió un nodo no-expresión: "
                    f"{x.etiqueta!r}"
                )
        print(f"  ✓ helper con {n_esperado} argumento(s): {n_esperado} expresiones")

    # Caso anidado: f(g(x), z) → 2 argumentos de NIVEL SUPERIOR (no se
    # desciende dentro de la expresión g(x)).
    codigo_anidado = (
        "funcion g(entero a) retornar entero\n"
        "hacer\n"
        "    retornar a\n"
        "fin_funcion\n"
        "\n"
        "funcion f(entero a, entero b) retornar entero\n"
        "hacer\n"
        "    retornar a + b\n"
        "fin_funcion\n"
        "\n"
        "funcion principal() retornar entero\n"
        "hacer\n"
        "    entero x <- 3\n"
        "    entero z <- 4\n"
        "    entero r <- f(g(x), z)\n"
        "    retornar r\n"
        "fin_funcion\n"
    )
    for nombre_parser, ParserClase in PARSERS:
        p = ParserClase(codigo_anidado)
        p.analizar()
        assert len(p.errores) == 0, p.errores
        raiz = raiz_logica(p.arbol_raiz)
        nodo_args = _buscar_argumentos(raiz)   # el primero en pre-orden = f(...)
        exprs = extraer_expresiones_de_argumentos(nodo_args)
        assert len(exprs) == 2, (
            f"[{nombre_parser}] f(g(x), z): esperaba 2 argumentos de nivel "
            f"superior, obtuvo {len(exprs)}"
        )
        print(f"  ✓ [{nombre_parser}] f(g(x), z) -> 2 argumentos de nivel superior")


# ══════════════════════════════════════════════
#  ESPECIFICACIÓN DE LOS EJEMPLOS 16–22
# ══════════════════════════════════════════════

# Un `n_errores` de 0 indica un ejemplo VÁLIDO.
# Claves opcionales por ejemplo:
#   primer_error          : campos a verificar en errs[0]
#   contexto_primer_error : claves del contexto de errs[0]
#   mensaje_contiene      : fragmento que debe estar en errs[0]["mensaje"]
#   reglas                : lista EXACTA y ORDENADA de las reglas de todos
#                           los errores (para ejemplos multi-error)
#   reglas_ausentes       : reglas que NO deben aparecer
ESPECIFICACION = [
    {
        "ruta":      "ejemplos_semanticos/16_llamada_aridad_mas.dml",
        "n_errores": 1,
        "primer_error": {
            "regla":   "LLAMADA_ARIDAD",
            "fila":    9,
            "columna": 17,
            "lexema":  "sumar",
        },
        "contexto_primer_error": {
            "aridad_esperada": 2,
            "aridad_recibida": 3,
        },
        "mensaje_contiene": "espera 2 argumentos, recibió 3",
    },
    {
        "ruta":      "ejemplos_semanticos/17_llamada_aridad_menos.dml",
        "n_errores": 1,
        "primer_error": {
            "regla":   "LLAMADA_ARIDAD",
            "fila":    9,
            "columna": 17,
            "lexema":  "sumar",
        },
        "contexto_primer_error": {
            "aridad_esperada": 2,
            "aridad_recibida": 1,
        },
        "mensaje_contiene": "espera 2 argumentos, recibió 1",
    },
    {
        "ruta":      "ejemplos_semanticos/18_llamada_tipo_incompatible.dml",
        "n_errores": 1,
        "primer_error": {
            "regla":   "LLAMADA_TIPO",
            "fila":    10,
            "columna": 13,
            "lexema":  "42",
        },
        "contexto_primer_error": {
            "funcion":             "saludar",
            "posicion_argumento":  1,
            "tipo_esperado":       "cadena",
            "tipo_recibido":       "entero",
        },
        "mensaje_contiene": "el argumento 1 de 'saludar' debe ser 'cadena'",
    },
    {
        "ruta":      "ejemplos_semanticos/19_llamada_promocion_ok.dml",
        "n_errores": 0,                       # VÁLIDO: 5 (entero) → real
    },
    {
        "ruta":      "ejemplos_semanticos/20_llamada_no_funcion.dml",
        "n_errores": 1,
        "primer_error": {
            "regla":   "LLAMADA_NO_FUNCION",
            "fila":    7,
            "columna": 17,
            "lexema":  "x",
        },
        "contexto_primer_error": {
            "categoria": "variable",
        },
        "mensaje_contiene": "no es una función",
    },
    {
        "ruta":      "ejemplos_semanticos/21_llamada_cascada.dml",
        "n_errores": 2,
        # El argumento '1 + "hola"' infiere ERROR (TIPO_OPERADOR); la
        # cascada suprime LLAMADA_TIPO sobre él, pero la aridad sí falla.
        "primer_error": {
            "regla":   "TIPO_OPERADOR",
            "fila":    11,
            "columna": 25,
            "lexema":  "+",
        },
        "reglas":          ["TIPO_OPERADOR", "LLAMADA_ARIDAD"],
        "reglas_ausentes": ["LLAMADA_TIPO"],
    },
    {
        "ruta":      "ejemplos_semanticos/22_llamada_recursiva_ok.dml",
        "n_errores": 0,                       # VÁLIDO: recursión correcta
    },
]


# ══════════════════════════════════════════════
#  TESTS DE CADA EJEMPLO
# ══════════════════════════════════════════════

def test_ejemplos_dml():
    for spec in ESPECIFICACION:
        ruta = spec["ruta"]
        print(f"  ── {ruta} ──")
        with open(_os.path.join(_PROJ_ROOT, ruta), encoding='utf-8') as f:
            codigo = f.read()

        for nombre_parser, ParserClase in PARSERS:
            p, r = _analizar(ParserClase, codigo)

            # Los .dml están sintácticamente bien formados.
            assert len(p.errores) == 0, (
                f"[{nombre_parser}] el ejemplo {ruta} debería ser "
                f"sintácticamente válido; reportó {len(p.errores)} errores: "
                f"{p.errores}"
            )

            errs = r["errores_semanticos"]
            assert len(errs) == spec["n_errores"], (
                f"[{nombre_parser}] {ruta}: esperaba {spec['n_errores']} "
                f"errores semánticos, obtuvo {len(errs)}: {errs}"
            )

            if spec["n_errores"] == 0:
                assert r["valido_semantico"] is True, (
                    f"[{nombre_parser}] {ruta}: valido_semantico debería "
                    f"ser True; errores={errs}"
                )
                assert errs == [], errs
                print(f"    ✓ [{nombre_parser}] válido, sin errores semánticos")
                continue

            assert r["valido_semantico"] is False, (
                f"[{nombre_parser}] {ruta}: valido_semantico debería ser False"
            )

            if "primer_error" in spec:
                _check_primer_error(errs, spec["primer_error"], nombre_parser)
            if "contexto_primer_error" in spec:
                _check_contexto(errs, spec["contexto_primer_error"],
                                nombre_parser)
            if "mensaje_contiene" in spec:
                frag = spec["mensaje_contiene"]
                assert frag in errs[0]["mensaje"], (
                    f"[{nombre_parser}] {ruta}: el mensaje debería contener "
                    f"{frag!r}; mensaje='{errs[0]['mensaje']}'"
                )
            if "reglas" in spec:
                reglas = [e["regla"] for e in errs]
                assert reglas == spec["reglas"], (
                    f"[{nombre_parser}] {ruta}: esperaba reglas "
                    f"{spec['reglas']}, obtuvo {reglas}"
                )
            if "reglas_ausentes" in spec:
                reglas = {e["regla"] for e in errs}
                for ausente in spec["reglas_ausentes"]:
                    assert ausente not in reglas, (
                        f"[{nombre_parser}] {ruta}: la regla {ausente!r} NO "
                        f"debería aparecer (cascada); errores={errs}"
                    )
            print(f"    ✓ [{nombre_parser}] {len(errs)} error(es) "
                  f"esperados, verificación OK")


# ══════════════════════════════════════════════
#  NO-REGRESIÓN: FACTORIAL RECURSIVO (ejemplo 22)
# ══════════════════════════════════════════════

def test_factorial_no_regresion():
    """El factorial recursivo completo no debe reportar ningún error
    semántico: la función está registrada antes de abrir su ámbito, así
    que la llamada recursiva `factorial(n - 1)` resuelve con aridad 1 y
    tipo entero correctos."""
    with open(_os.path.join(_PROJ_ROOT, "ejemplos_semanticos/22_llamada_recursiva_ok.dml"),
              encoding='utf-8') as f:
        codigo = f.read()
    for nombre_parser, ParserClase in PARSERS:
        p, r = _analizar(ParserClase, codigo)
        assert len(p.errores) == 0, (
            f"[{nombre_parser}] el factorial no debería tener errores "
            f"sintácticos; obtuvo {len(p.errores)}: {p.errores}"
        )
        assert r["valido_semantico"] is True, r["errores_semanticos"]
        assert r["errores_semanticos"] == [], r["errores_semanticos"]
        print(f"  ✓ [{nombre_parser}] factorial recursivo: sin errores")


# ══════════════════════════════════════════════
#  COMBINADO: REGLAS 1 + 2 + 3 + 4 + 5 NO ABORTAN
# ══════════════════════════════════════════════

# - 'entero a' duplicada            -> DECL_DUPLICADA   (regla 1)
# - 'b' no declarada en asignación  -> USO_NO_DECLARADO (regla 2)
# - 'entero c <- "texto"'           -> TIPO_ASIGNACION  (regla 3)
# - 'si a entonces' con a:entero    -> TIPO_CONDICION   (regla 4)
# - 'sumar(1)' espera 2, recibe 1   -> LLAMADA_ARIDAD   (regla 5)
CODIGO_COMBINADO = (
    "funcion sumar(entero a, entero b) retornar entero\n"
    "hacer\n"
    "    retornar a + b\n"
    "fin_funcion\n"
    "\n"
    "funcion principal() retornar entero\n"
    "hacer\n"
    "    entero a <- 10\n"
    "    entero a <- 20\n"
    "    b <- 5\n"
    "    entero c <- \"texto\"\n"
    "    si a entonces\n"
    "        escribir(\"x\")\n"
    "    fin_si\n"
    "    entero s <- sumar(1)\n"
    "    retornar a\n"
    "fin_funcion\n"
)


def test_cinco_reglas_combinadas():
    for nombre_parser, ParserClase in PARSERS:
        p, r = _analizar(ParserClase, CODIGO_COMBINADO)
        assert len(p.errores) == 0, (
            f"[{nombre_parser}] el código combinado no debería tener errores "
            f"sintácticos; obtuvo {len(p.errores)}"
        )
        errs = r["errores_semanticos"]
        reglas = sorted({e["regla"] for e in errs})
        assert reglas == ["DECL_DUPLICADA", "LLAMADA_ARIDAD",
                          "TIPO_ASIGNACION", "TIPO_CONDICION",
                          "USO_NO_DECLARADO"], (
            f"[{nombre_parser}] esperaba las cinco reglas; obtuvo "
            f"reglas={reglas}, errores={errs}"
        )
        assert len(errs) == 5, (
            f"[{nombre_parser}] esperaba exactamente 5 errores; "
            f"obtuvo {len(errs)}: {errs}"
        )
        print(f"  ✓ [{nombre_parser}] {len(errs)} errores combinados: {reglas}")


# ══════════════════════════════════════════════
#  SMOKE TESTS DE CIERRE (los tres de la TAREA 5)
# ══════════════════════════════════════════════

def test_smoke_cascada_argumento_error():
    """sumar(1 + "hola") con sumar(entero, entero):
    TIPO_OPERADOR (por 1 + "hola") + LLAMADA_ARIDAD (espera 2, recibe 1).
    La cascada suprime LLAMADA_TIPO sobre el argumento ERROR."""
    codigo = (
        "funcion sumar(entero a, entero b) retornar entero\n"
        "hacer\n"
        "    retornar a + b\n"
        "fin_funcion\n"
        "\n"
        "funcion principal() retornar entero\n"
        "hacer\n"
        "    entero r <- sumar(1 + \"hola\")\n"
        "    retornar r\n"
        "fin_funcion\n"
    )
    for nombre_parser, ParserClase in PARSERS:
        p, r = _analizar(ParserClase, codigo)
        assert len(p.errores) == 0, p.errores
        reglas = [e["regla"] for e in r["errores_semanticos"]]
        assert reglas == ["TIPO_OPERADOR", "LLAMADA_ARIDAD"], (
            f"[{nombre_parser}] esperaba ['TIPO_OPERADOR', 'LLAMADA_ARIDAD']; "
            f"obtuvo {reglas}"
        )
        print(f"  ✓ [{nombre_parser}] 'sumar(1 + \"hola\")' -> "
              f"TIPO_OPERADOR + LLAMADA_ARIDAD (sin LLAMADA_TIPO)")


def test_smoke_tipo_segundo_argumento():
    """sumar(1, 2.5) con sumar(entero, entero):
    LLAMADA_TIPO sobre el SEGUNDO argumento (real no es compatible con
    entero). El primero (1, entero) es válido."""
    codigo = (
        "funcion sumar(entero a, entero b) retornar entero\n"
        "hacer\n"
        "    retornar a + b\n"
        "fin_funcion\n"
        "\n"
        "funcion principal() retornar entero\n"
        "hacer\n"
        "    entero r <- sumar(1, 2.5)\n"
        "    retornar r\n"
        "fin_funcion\n"
    )
    for nombre_parser, ParserClase in PARSERS:
        p, r = _analizar(ParserClase, codigo)
        assert len(p.errores) == 0, p.errores
        errs = r["errores_semanticos"]
        reglas = [e["regla"] for e in errs]
        assert reglas == ["LLAMADA_TIPO"], (
            f"[{nombre_parser}] esperaba ['LLAMADA_TIPO']; obtuvo {reglas}"
        )
        ctx = errs[0]["contexto"]
        assert ctx.get("posicion_argumento") == 2, (
            f"[{nombre_parser}] LLAMADA_TIPO debería señalar el argumento 2; "
            f"contexto={ctx}"
        )
        assert ctx.get("tipo_esperado") == "entero", ctx
        assert ctx.get("tipo_recibido") == "real", ctx
        print(f"  ✓ [{nombre_parser}] 'sumar(1, 2.5)' (params entero,entero) -> "
              f"LLAMADA_TIPO en argumento 2")


def test_smoke_doble_promocion():
    """sumar(1, 2) con sumar(real, real):
    sin errores (ambos enteros se promocionan a real)."""
    codigo = (
        "funcion sumar(real a, real b) retornar real\n"
        "hacer\n"
        "    retornar a + b\n"
        "fin_funcion\n"
        "\n"
        "funcion principal() retornar real\n"
        "hacer\n"
        "    real r <- sumar(1, 2)\n"
        "    retornar r\n"
        "fin_funcion\n"
    )
    for nombre_parser, ParserClase in PARSERS:
        p, r = _analizar(ParserClase, codigo)
        assert len(p.errores) == 0, p.errores
        errs = r["errores_semanticos"]
        assert errs == [], (
            f"[{nombre_parser}] 'sumar(1, 2)' (params real,real) no debería "
            f"reportar nada (doble promoción); obtuvo {errs}"
        )
        print(f"  ✓ [{nombre_parser}] 'sumar(1, 2)' (params real,real) -> "
              f"sin errores (doble promoción)")


# ══════════════════════════════════════════════
#  RUNNER
# ══════════════════════════════════════════════

def main() -> int:
    print("── TAREA 1: helper extraer_expresiones_de_argumentos ──")
    test_helper_extraer_argumentos()
    print("\n── Ejemplos .dml (16–22) ──")
    test_ejemplos_dml()
    print("\n── No-regresión: factorial recursivo ──")
    test_factorial_no_regresion()
    print("\n── Combinado: reglas 1 + 2 + 3 + 4 + 5 ──")
    test_cinco_reglas_combinadas()
    print("\n── Smoke tests de cierre ──")
    test_smoke_cascada_argumento_error()
    test_smoke_tipo_segundo_argumento()
    test_smoke_doble_promocion()
    print("\n✓ Todos los tests de la Etapa 7 pasaron.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
