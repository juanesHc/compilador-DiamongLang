"""
Tests de la regla semántica 4 — Etapa 6
(La condición de 'si' y 'mientras' debe ser de tipo 'booleano').

Para cada ejemplo nuevo en `ejemplos_semanticos/` (11–15):
  - se parsea con el parser RECURSIVO y con el PREDICTIVO,
  - se ejecuta el analizador semántico,
  - se verifica número exacto de errores, regla, posición, lexema y
    (cuando aplica) un fragmento del mensaje y el contexto.

La regla 4 se dispara en:
  - sent_si       → si EXPRESION entonces …   (la condición)
  - sent_mientras → mientras EXPRESION hacer … (la condición)
NO entra: sent_para (excluida por decisión), ni la rama_sino (es un
bloque, no una condición).

Cascada (F.10): si la condición infiere 'ERROR' (p.ej. usa una variable
no declarada), NO se emite TIPO_CONDICION; el error raíz ya lo reportó
la regla que lo generó.

Adicionales:
  - No-regresión: programa con si/mientras anidados y condiciones
    correctas (0 errores).
  - Combinado: regla 1 + 2 + 3 + 4 en un mismo programa; las cuatro
    deben reportarse sin abortar.
  - Smoke de cascada: condición con variable no declarada → sólo
    USO_NO_DECLARADO, no TIPO_CONDICION.

Ejecutar con:
    python3 test_etapa6_regla_4.py
"""

import os as _os, sys as _sys
_PROJ_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _PROJ_ROOT not in _sys.path:
    _sys.path.insert(0, _PROJ_ROOT)
from sintactico.parser_recursivo import ParserRecursivo
from sintactico.parser_predictivo import ParserPredictivo
from semantico.semantico import AnalizadorSemantico


# ══════════════════════════════════════════════
#  ESPECIFICACIÓN DE LOS EJEMPLOS
# ══════════════════════════════════════════════

# Un `n_errores` de 0 indica un ejemplo VÁLIDO.
ESPECIFICACION = [
    {
        "ruta":      "ejemplos_semanticos/11_condicion_si_no_booleana.dml",
        "n_errores": 1,
        "primer_error": {
            "regla":   "TIPO_CONDICION",
            "fila":    6,
            "columna": 8,
            "lexema":  "x",
        },
        "contexto_primer_error": {
            "estructura":    "si",
            "tipo_recibido": "entero",
        },
        "mensaje_contiene": "'si'",
    },
    {
        "ruta":      "ejemplos_semanticos/12_condicion_mientras_no_booleana.dml",
        "n_errores": 1,
        "primer_error": {
            "regla":   "TIPO_CONDICION",
            "fila":    6,
            "columna": 14,
            "lexema":  "s",
        },
        "contexto_primer_error": {
            "estructura":    "mientras",
            "tipo_recibido": "cadena",
        },
        "mensaje_contiene": "'mientras'",
    },
    {
        "ruta":      "ejemplos_semanticos/13_condicion_si_ok.dml",
        "n_errores": 0,                       # ejemplo VÁLIDO (x > 3)
    },
    {
        "ruta":      "ejemplos_semanticos/14_condicion_si_compuesta_ok.dml",
        "n_errores": 0,                       # ejemplo VÁLIDO ((x > 3) y flag)
    },
    {
        "ruta":      "ejemplos_semanticos/15_condicion_cascada.dml",
        "n_errores": 1,
        "primer_error": {
            "regla":   "USO_NO_DECLARADO",
            "fila":    6,
            "columna": 8,
            "lexema":  "desconocida",
        },
        "contexto_primer_error": {"es_llamada": False},
        "mensaje_contiene": "variable",
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
            print(f"    ✓ [{nombre_parser}] {len(errs)} error(es) "
                  f"esperados, primer error OK")


# ══════════════════════════════════════════════
#  NO-REGRESIÓN: si/mientras ANIDADOS Y VÁLIDOS
# ══════════════════════════════════════════════

# 'mientras' con condición relacional, 'si/sino' anidado con condición
# relacional, y un 'si' con condición booleana simple. Reasignación
# entero<-entero. No debe reportar nada.
CODIGO_VALIDO = (
    "funcion principal()\n"
    "hacer\n"
    "    entero i <- 0\n"
    "    booleano activo <- verdadero\n"
    "    mientras i < 10 hacer\n"
    "        si i > 5 entonces\n"
    "            escribir(\"alto\")\n"
    "        sino\n"
    "            escribir(\"bajo\")\n"
    "        fin_si\n"
    "        i <- i + 1\n"
    "    fin_mientras\n"
    "    si activo entonces\n"
    "        escribir(\"activo\")\n"
    "    fin_si\n"
    "fin_funcion\n"
)


def test_programa_valido_sin_errores():
    for nombre_parser, ParserClase in PARSERS:
        p, r = _analizar(ParserClase, CODIGO_VALIDO)
        assert len(p.errores) == 0, (
            f"[{nombre_parser}] el programa válido no debería tener errores "
            f"sintácticos; obtuvo {len(p.errores)}: {p.errores}"
        )
        assert r["valido_semantico"] is True, r["errores_semanticos"]
        assert r["errores_semanticos"] == [], r["errores_semanticos"]
        print(f"  ✓ [{nombre_parser}] si/mientras anidados: sin errores")


# ══════════════════════════════════════════════
#  COMBINADO: REGLAS 1 + 2 + 3 + 4 NO ABORTAN
# ══════════════════════════════════════════════

# - 'entero a' duplicada            -> DECL_DUPLICADA   (regla 1)
# - 'b' no declarada en asignación  -> USO_NO_DECLARADO (regla 2)
# - 'entero c <- "texto"'           -> TIPO_ASIGNACION  (regla 3)
# - 'si a entonces' con a:entero    -> TIPO_CONDICION   (regla 4)
CODIGO_COMBINADO = (
    "funcion principal()\n"
    "hacer\n"
    "    entero a <- 10\n"
    "    entero a <- 20\n"
    "    b <- 5\n"
    "    entero c <- \"texto\"\n"
    "    si a entonces\n"
    "        escribir(\"x\")\n"
    "    fin_si\n"
    "fin_funcion\n"
)


def test_reglas_1_2_3_4_combinadas():
    for nombre_parser, ParserClase in PARSERS:
        p, r = _analizar(ParserClase, CODIGO_COMBINADO)
        assert len(p.errores) == 0, (
            f"[{nombre_parser}] el código combinado no debería tener errores "
            f"sintácticos; obtuvo {len(p.errores)}"
        )
        errs = r["errores_semanticos"]
        reglas = sorted({e["regla"] for e in errs})
        assert reglas == ["DECL_DUPLICADA", "TIPO_ASIGNACION",
                          "TIPO_CONDICION", "USO_NO_DECLARADO"], (
            f"[{nombre_parser}] esperaba las cuatro reglas; obtuvo "
            f"reglas={reglas}, errores={errs}"
        )
        assert len(errs) == 4, (
            f"[{nombre_parser}] esperaba exactamente 4 errores; "
            f"obtuvo {len(errs)}: {errs}"
        )
        print(f"  ✓ [{nombre_parser}] {len(errs)} errores combinados: {reglas}")


# ══════════════════════════════════════════════
#  SMOKE TESTS DE CIERRE
# ══════════════════════════════════════════════

def test_smoke_condicion_no_booleana_unica():
    """Programa con condición no booleana → exactamente 1 TIPO_CONDICION."""
    codigo = (
        "funcion p()\n"
        "hacer\n"
        "    entero x <- 5\n"
        "    si x entonces\n"
        "        escribir(\"hola\")\n"
        "    fin_si\n"
        "fin_funcion\n"
    )
    for nombre_parser, ParserClase in PARSERS:
        p, r = _analizar(ParserClase, codigo)
        assert len(p.errores) == 0, p.errores
        reglas = [e["regla"] for e in r["errores_semanticos"]]
        assert reglas == ["TIPO_CONDICION"], (
            f"[{nombre_parser}] esperaba ['TIPO_CONDICION']; obtuvo {reglas}"
        )
        print(f"  ✓ [{nombre_parser}] 'si x entonces' (x:entero) -> "
              f"1 TIPO_CONDICION")


def test_smoke_cascada_suprime_condicion():
    """Condición con variable no declarada → sólo USO_NO_DECLARADO; la
    cascada (F.10) suprime el TIPO_CONDICION."""
    codigo = (
        "funcion p()\n"
        "hacer\n"
        "    si desconocida entonces\n"
        "        escribir(\"a\")\n"
        "    fin_si\n"
        "fin_funcion\n"
    )
    for nombre_parser, ParserClase in PARSERS:
        p, r = _analizar(ParserClase, codigo)
        assert len(p.errores) == 0, p.errores
        reglas = [e["regla"] for e in r["errores_semanticos"]]
        assert reglas == ["USO_NO_DECLARADO"], (
            f"[{nombre_parser}] esperaba ['USO_NO_DECLARADO'] (cascada "
            f"suprime TIPO_CONDICION); obtuvo {reglas}"
        )
        print(f"  ✓ [{nombre_parser}] 'si desconocida' -> "
              f"1 USO_NO_DECLARADO (sin TIPO_CONDICION)")


def test_smoke_condicion_mientras_operador():
    """'mientras 1 + "a" hacer' → 1 TIPO_OPERADOR; la cascada suprime el
    TIPO_CONDICION (la condición ya infirió ERROR)."""
    codigo = (
        "funcion p()\n"
        "hacer\n"
        "    mientras 1 + \"a\" hacer\n"
        "        escribir(\"x\")\n"
        "    fin_mientras\n"
        "fin_funcion\n"
    )
    for nombre_parser, ParserClase in PARSERS:
        p, r = _analizar(ParserClase, codigo)
        assert len(p.errores) == 0, p.errores
        reglas = [e["regla"] for e in r["errores_semanticos"]]
        assert reglas == ["TIPO_OPERADOR"], (
            f"[{nombre_parser}] esperaba ['TIPO_OPERADOR'] (cascada suprime "
            f"TIPO_CONDICION); obtuvo {reglas}"
        )
        print(f"  ✓ [{nombre_parser}] 'mientras 1 + \"a\"' -> "
              f"1 TIPO_OPERADOR (sin TIPO_CONDICION)")


# ══════════════════════════════════════════════
#  RUNNER
# ══════════════════════════════════════════════

def main() -> int:
    print("── Ejemplos .dml ──")
    test_ejemplos_dml()
    print("\n── No-regresión: si/mientras anidados válidos ──")
    test_programa_valido_sin_errores()
    print("\n── Combinado: reglas 1 + 2 + 3 + 4 ──")
    test_reglas_1_2_3_4_combinadas()
    print("\n── Smoke tests de cierre ──")
    test_smoke_condicion_no_booleana_unica()
    test_smoke_cascada_suprime_condicion()
    test_smoke_condicion_mientras_operador()
    print("\n✓ Todos los tests de la Etapa 6 pasaron.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
