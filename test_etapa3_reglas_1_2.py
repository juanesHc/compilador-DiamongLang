"""
Tests de las reglas semánticas 1 y 2 — Etapa 3.

Para cada ejemplo en `ejemplos_semanticos/`:
  - se parsea con el parser RECURSIVO y con el PREDICTIVO,
  - se ejecuta el analizador semántico,
  - se verifica número de errores, regla, posición y lexema.

Adicionales:
  - No-regresión sobre un programa válido (factorial).
  - Smoke test que mezcla un duplicado y un uso no declarado: deben
    reportarse AMBOS errores, no abortar al primero.

Ejecutar con:
    python3 test_etapa3_reglas_1_2.py
"""

from parser_recursivo  import ParserRecursivo
from parser_predictivo import ParserPredictivo
from semantico         import AnalizadorSemantico


# ══════════════════════════════════════════════
#  ESPECIFICACIÓN DE LOS EJEMPLOS
# ══════════════════════════════════════════════

# Cada entrada describe el resultado esperado del análisis semántico
# para el .dml correspondiente. Mantener sincronizado con los archivos
# de `ejemplos_semanticos/`.
ESPECIFICACION = [
    {
        "ruta":     "ejemplos_semanticos/01_decl_duplicada_variable.dml",
        "n_errores": 1,
        "primer_error": {
            "regla":   "DECL_DUPLICADA",
            "fila":    5,
            "columna": 12,
            "lexema":  "x",
        },
        "contexto_primer_error": {
            "tipo_simbolo": "variable",
            "ambito":       "principal",
        },
    },
    {
        "ruta":     "ejemplos_semanticos/02_decl_duplicada_parametro.dml",
        "n_errores": 1,
        "primer_error": {
            "regla":   "DECL_DUPLICADA",
            "fila":    2,
            "columna": 32,
            "lexema":  "a",
        },
        "contexto_primer_error": {
            "tipo_simbolo": "parámetro",
            "ambito":       "sumar",
        },
    },
    {
        "ruta":     "ejemplos_semanticos/03_uso_variable_no_declarada.dml",
        "n_errores": 1,
        "primer_error": {
            "regla":   "USO_NO_DECLARADO",
            "fila":    5,
            "columna": 14,
            "lexema":  "desconocida",
        },
        "contexto_primer_error": {"es_llamada": False},
        "mensaje_contiene": "variable",
    },
    {
        "ruta":     "ejemplos_semanticos/04_llamada_funcion_no_declarada.dml",
        "n_errores": 1,
        "primer_error": {
            "regla":   "USO_NO_DECLARADO",
            "fila":    4,
            "columna": 17,
            "lexema":  "inexistente",
        },
        "contexto_primer_error": {"es_llamada": True},
        "mensaje_contiene": "función",
    },
]


PARSERS = [("recursivo", ParserRecursivo), ("predictivo", ParserPredictivo)]


# ══════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════

def _analizar(parser_clase, codigo):
    p = parser_clase(codigo)
    p.analizar()
    r = AnalizadorSemantico(p.arbol_raiz).analizar()
    return p, r


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
#  TESTS DE CADA EJEMPLO
# ══════════════════════════════════════════════

def test_ejemplos_dml():
    for spec in ESPECIFICACION:
        ruta = spec["ruta"]
        print(f"  ── {ruta} ──")
        with open(ruta, encoding='utf-8') as f:
            codigo = f.read()

        for nombre_parser, ParserClase in PARSERS:
            p, r = _analizar(ParserClase, codigo)

            # No debe haber errores sintácticos (los .dml están bien formados)
            assert len(p.errores) == 0, (
                f"[{nombre_parser}] el ejemplo {ruta} debería ser "
                f"sintácticamente válido; reportó {len(p.errores)} errores"
            )

            errs = r["errores_semanticos"]
            assert len(errs) == spec["n_errores"], (
                f"[{nombre_parser}] {ruta}: esperaba {spec['n_errores']} "
                f"errores semánticos, obtuvo {len(errs)}: {errs}"
            )
            assert r["valido_semantico"] is False, (
                f"[{nombre_parser}] {ruta}: valido_semantico debería ser False"
            )

            _check_primer_error(errs, spec["primer_error"], nombre_parser)
            _check_contexto(errs, spec["contexto_primer_error"], nombre_parser)

            if "mensaje_contiene" in spec:
                frag = spec["mensaje_contiene"]
                assert frag in errs[0]["mensaje"], (
                    f"[{nombre_parser}] {ruta}: el mensaje debería contener "
                    f"{frag!r}; mensaje='{errs[0]['mensaje']}'"
                )

            print(f"    ✓ [{nombre_parser}] {len(errs)} error(es) "
                  f"esperados, primer error OK")


# ══════════════════════════════════════════════
#  NO-REGRESIÓN: PROGRAMA VÁLIDO
# ══════════════════════════════════════════════

CODIGO_VALIDO = (
    "funcion factorial(entero n) retornar entero\n"
    "hacer\n"
    "    si n <= 1 entonces\n"
    "        retornar 1\n"
    "    sino\n"
    "        retornar n * factorial(n - 1)\n"
    "    fin_si\n"
    "fin_funcion\n"
)


def test_programa_valido_sin_errores():
    for nombre_parser, ParserClase in PARSERS:
        p, r = _analizar(ParserClase, CODIGO_VALIDO)
        assert len(p.errores) == 0, (
            f"[{nombre_parser}] el factorial no debería tener errores sintácticos"
        )
        assert r["valido_semantico"] is True, r
        assert r["errores_semanticos"] == [], r["errores_semanticos"]
        print(f"  ✓ [{nombre_parser}] factorial: sin errores semánticos")


# ══════════════════════════════════════════════
#  SMOKE TEST: VARIOS ERRORES NO ABORTAN
# ══════════════════════════════════════════════

# Programa con DECL_DUPLICADA Y USO_NO_DECLARADO en la misma función.
# El analizador debe reportar ambos errores, no abortar al primero.
CODIGO_MIXTO = (
    "funcion principal()\n"
    "hacer\n"
    "    entero a <- 10\n"
    "    entero a <- 20\n"            # DECL_DUPLICADA (línea 4, col 12)
    "    escribir(noexiste)\n"        # USO_NO_DECLARADO (línea 5, col 14)
    "fin_funcion\n"
)


def test_multiples_errores_no_abortan():
    for nombre_parser, ParserClase in PARSERS:
        p, r = _analizar(ParserClase, CODIGO_MIXTO)
        assert len(p.errores) == 0, (
            f"[{nombre_parser}] el código mixto no debería tener errores "
            f"sintácticos; obtuvo {len(p.errores)}"
        )
        errs = r["errores_semanticos"]
        reglas = sorted({e["regla"] for e in errs})
        assert reglas == ["DECL_DUPLICADA", "USO_NO_DECLARADO"], (
            f"[{nombre_parser}] esperaba ambas reglas en la lista; "
            f"obtuvo reglas={reglas}, errores={errs}"
        )
        print(f"  ✓ [{nombre_parser}] {len(errs)} errores mixtos reportados: "
              f"{reglas}")


# ══════════════════════════════════════════════
#  RUNNER
# ══════════════════════════════════════════════

def main() -> int:
    print("── Ejemplos .dml ──")
    test_ejemplos_dml()
    print("\n── No-regresión: programa válido ──")
    test_programa_valido_sin_errores()
    print("\n── Smoke test: varios errores no abortan ──")
    test_multiples_errores_no_abortan()
    print("\n✓ Todos los tests de la Etapa 3 pasaron.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
