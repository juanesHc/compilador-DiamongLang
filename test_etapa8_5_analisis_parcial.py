"""
Tests del análisis semántico PARCIAL — Etapa 8.5 (decisión F.11).

Antes de esta etapa, `_visitar` chequeaba `tiene_error_sintactico` en la
RAÍZ: como ese chequeo es recursivo, un solo error sintáctico en
cualquier parte del programa hacía que la fase semántica saltara el árbol
COMPLETO (errores_semanticos=[]). Eso incumplía F.11.

El fix (Etapa 8.5) mueve el filtrado a granularidad POR-HIJO, centralizado
en `_visitar`: se desciende por los nodos CONTENEDORES (programa,
declaracion, def_funcion, bloque, bloque_prima, sentencia, sent_si,
rama_sino, sent_mientras, sent_para) aunque tengan errores internos, y se
salta sólo la sentencia/hoja realmente rota. Resultado: las zonas limpias
de un programa con errores sintácticos SÍ se analizan semánticamente.

Casos (todos con AMBOS parsers):
  A) Error sintáctico aislado + 3 errores semánticos en zonas limpias de
     la MISMA función → los 3 semánticos se reportan.
  B) Función con error sintáctico + función separada limpia → el error
     semántico de la función limpia se reporta.
  C) Error sintáctico dentro de una expresión + sentencia limpia hermana
     con error semántico → el semántico se reporta.
  D) Programa SIN errores sintácticos, varios semánticos → idéntico a
     antes del fix (no-regresión de la funcionalidad principal).
  E) Programa con SÓLO errores sintácticos → no crashea; semánticos = [].

Ejecutar con:
    python3 test_etapa8_5_analisis_parcial.py
"""

from parser_recursivo  import ParserRecursivo
from parser_predictivo import ParserPredictivo
from semantico         import AnalizadorSemantico


PARSERS = [("recursivo", ParserRecursivo), ("predictivo", ParserPredictivo)]


def _analizar(parser_clase, codigo):
    p = parser_clase(codigo)
    p.analizar()
    r = AnalizadorSemantico(p.arbol_raiz).analizar()
    return p, r


def _reglas(r):
    return sorted(e["regla"] for e in r["errores_semanticos"])


# ══════════════════════════════════════════════
#  A) ERROR SINTÁCTICO AISLADO + 3 SEMÁNTICOS LIMPIOS
# ══════════════════════════════════════════════

# - 'entero x <- 20'   → DECL_DUPLICADA   (x ya declarada)
# - 'si 1 + 2 entonces'→ TIPO_CONDICION   (1+2 es entero, no booleano)
# - 'escribir(noexiste)' → USO_NO_DECLARADO
# - 'entero y 5'       → ERROR SINTÁCTICO (falta '<-'); se salta
CODIGO_A = (
    "funcion principal() retornar entero\n"
    "hacer\n"
    "    entero x <- 10\n"
    "    entero x <- 20\n"
    "    si 1 + 2 entonces\n"
    "        escribir(noexiste)\n"
    "    fin_si\n"
    "    entero y 5\n"
    "    retornar x\n"
    "fin_funcion\n"
)


def test_A_error_aislado_y_semanticos_en_misma_funcion():
    for nombre, ParserClase in PARSERS:
        p, r = _analizar(ParserClase, CODIGO_A)
        assert len(p.errores) >= 1, (
            f"[{nombre}] se esperaba al menos un error sintáctico "
            f"('entero y 5'); obtuvo {len(p.errores)}"
        )
        reglas = _reglas(r)
        assert reglas == ["DECL_DUPLICADA", "TIPO_CONDICION",
                          "USO_NO_DECLARADO"], (
            f"[{nombre}] tras el fix se esperaban los 3 errores semánticos "
            f"de las zonas limpias; obtuvo {reglas} "
            f"({r['errores_semanticos']})"
        )
        print(f"  ✓ [{nombre}] error sintáctico aislado + 3 semánticos "
              f"limpios: {reglas}")


# ══════════════════════════════════════════════
#  B) ERROR SINTÁCTICO EN UNA FUNCIÓN + FUNCIÓN LIMPIA
# ══════════════════════════════════════════════

# 'uno' tiene un error sintáctico aislado que NO deja referencias colgando
# ('entero b 10', con b sin usar). 'dos' es sintácticamente limpia y usa
# 'noexiste' → USO_NO_DECLARADO. El único semántico esperado es el de
# 'dos'.
CODIGO_B = (
    "funcion uno() retornar entero\n"
    "hacer\n"
    "    entero a <- 5\n"
    "    entero b 10\n"
    "fin_funcion\n"
    "\n"
    "funcion dos() retornar entero\n"
    "hacer\n"
    "    escribir(noexiste)\n"
    "    retornar 0\n"
    "fin_funcion\n"
)


def test_B_funcion_rota_y_funcion_limpia():
    for nombre, ParserClase in PARSERS:
        p, r = _analizar(ParserClase, CODIGO_B)
        assert len(p.errores) >= 1, (
            f"[{nombre}] se esperaba al menos un error sintáctico en 'uno'"
        )
        errs = r["errores_semanticos"]
        assert len(errs) == 1, (
            f"[{nombre}] se esperaba exactamente 1 error semántico (el de "
            f"'dos'); obtuvo {len(errs)}: {errs}"
        )
        e = errs[0]
        assert e["regla"] == "USO_NO_DECLARADO" and e["lexema"] == "noexiste", e
        print(f"  ✓ [{nombre}] función limpia analizada pese al error en otra: "
              f"USO_NO_DECLARADO 'noexiste'")


# ══════════════════════════════════════════════
#  C) ERROR SINTÁCTICO EN EXPRESIÓN + SENTENCIA LIMPIA HERMANA
# ══════════════════════════════════════════════

# 'entero b <- 5 +' rompe la expresión (sintáctico); se salta. La
# sentencia hermana 'entero c <- "hola"' es limpia → TIPO_ASIGNACION.
CODIGO_C = (
    "funcion f() retornar entero\n"
    "hacer\n"
    "    entero a <- 10\n"
    "    entero b <- 5 +\n"
    "    entero c <- \"hola\"\n"
    "    retornar a\n"
    "fin_funcion\n"
)


def test_C_error_en_expresion_y_sentencia_limpia():
    for nombre, ParserClase in PARSERS:
        p, r = _analizar(ParserClase, CODIGO_C)
        assert len(p.errores) >= 1, (
            f"[{nombre}] se esperaba al menos un error sintáctico "
            f"('entero b <- 5 +')"
        )
        reglas = _reglas(r)
        assert reglas == ["TIPO_ASIGNACION"], (
            f"[{nombre}] se esperaba TIPO_ASIGNACION sobre 'entero c <- "
            f'"hola"\'; obtuvo {reglas} ({r["errores_semanticos"]})'
        )
        e = r["errores_semanticos"][0]
        assert e["lexema"] == "c", e
        print(f"  ✓ [{nombre}] sentencia limpia hermana analizada: "
              f"TIPO_ASIGNACION sobre 'c'")


# ══════════════════════════════════════════════
#  D) NO-REGRESIÓN: PROGRAMA SIN ERRORES SINTÁCTICOS
# ══════════════════════════════════════════════

# Igual que A pero SIN el 'entero y 5' roto: debe seguir reportando los 3
# semánticos exactamente igual que antes del fix.
CODIGO_D = (
    "funcion principal() retornar entero\n"
    "hacer\n"
    "    entero x <- 10\n"
    "    entero x <- 20\n"
    "    si 1 + 2 entonces\n"
    "        escribir(noexiste)\n"
    "    fin_si\n"
    "    retornar x\n"
    "fin_funcion\n"
)


def test_D_no_regresion_sin_errores_sintacticos():
    for nombre, ParserClase in PARSERS:
        p, r = _analizar(ParserClase, CODIGO_D)
        assert len(p.errores) == 0, (
            f"[{nombre}] este programa NO debería tener errores sintácticos; "
            f"obtuvo {len(p.errores)}: {p.errores}"
        )
        reglas = _reglas(r)
        assert reglas == ["DECL_DUPLICADA", "TIPO_CONDICION",
                          "USO_NO_DECLARADO"], (
            f"[{nombre}] no-regresión: se esperaban los 3 semánticos de "
            f"siempre; obtuvo {reglas}"
        )
        print(f"  ✓ [{nombre}] sin errores sintácticos → 3 semánticos "
              f"(idéntico a antes del fix)")


# ══════════════════════════════════════════════
#  E) SÓLO ERRORES SINTÁCTICOS — NO CRASHEA
# ══════════════════════════════════════════════

CODIGO_E = (
    "funcion principal() retornar entero\n"
    "hacer\n"
    "    entero y 5\n"
    "    retornar 0\n"
    "fin_funcion\n"
)


def test_E_solo_errores_sintacticos_no_crashea():
    for nombre, ParserClase in PARSERS:
        # El contrato es: no excepción. Si _analizar levantara, el test falla.
        p, r = _analizar(ParserClase, CODIGO_E)
        assert len(p.errores) >= 1, (
            f"[{nombre}] se esperaba al menos un error sintáctico"
        )
        assert isinstance(r["errores_semanticos"], list), r["errores_semanticos"]
        # 'entero y 5' (la única sentencia con contenido) está rota y se
        # salta; no quedan zonas limpias con errores semánticos.
        assert r["errores_semanticos"] == [], (
            f"[{nombre}] no debería haber errores semánticos; "
            f"obtuvo {r['errores_semanticos']}"
        )
        print(f"  ✓ [{nombre}] sólo errores sintácticos → sin crash, "
              f"semánticos=[]")


# ══════════════════════════════════════════════
#  RUNNER
# ══════════════════════════════════════════════

def main() -> int:
    print("── A) error sintáctico aislado + 3 semánticos (misma función) ──")
    test_A_error_aislado_y_semanticos_en_misma_funcion()
    print("\n── B) función rota + función limpia ──")
    test_B_funcion_rota_y_funcion_limpia()
    print("\n── C) error en expresión + sentencia limpia hermana ──")
    test_C_error_en_expresion_y_sentencia_limpia()
    print("\n── D) no-regresión: sin errores sintácticos ──")
    test_D_no_regresion_sin_errores_sintacticos()
    print("\n── E) sólo errores sintácticos (no crashea) ──")
    test_E_solo_errores_sintacticos_no_crashea()
    print("\n✓ Todos los tests de la Etapa 8.5 (análisis parcial F.11) pasaron.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
