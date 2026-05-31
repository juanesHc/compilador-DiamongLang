"""
Tests de la regla semántica 3 — Etapa 5
(Compatibilidad de tipos en asignación).

Para cada ejemplo nuevo en `ejemplos_semanticos/` (05–10):
  - se parsea con el parser RECURSIVO y con el PREDICTIVO,
  - se ejecuta el analizador semántico,
  - se verifica número exacto de errores, regla, posición, lexema y
    (cuando aplica) un fragmento del mensaje y el contexto.

La regla 3 se dispara en:
  A) declaración con asignación inicial   (decl_variable)
  B) reasignación a variable existente     (sentencia_id con cola '<-')
Sub-reglas validadas aquí:
  - 'vacio' como tipo de variable  -> TIPO_VOID_EN_VARIABLE
  - TIPO_OPERADOR queda integrado al inferir el RHS (lo emite tipos.py);
    la cascada (F.10) suprime el TIPO_ASIGNACION redundante.

Adicionales:
  - No-regresión sobre un programa válido más complejo (varios tipos,
    reasignaciones y una promoción entero->real).
  - Test combinado: regla 1 (duplicada) + regla 2 (no declarada) +
    regla 3 (tipos) en el mismo programa; las tres deben reportarse.
  - Smoke tests de cierre: 'entero x <- "hola"' da UN solo
    TIPO_ASIGNACION; 'entero x <- 5 + "hola"' da UN solo TIPO_OPERADOR.

Ejecutar con:
    python3 test_etapa5_regla_3.py
"""

from parser_recursivo  import ParserRecursivo
from parser_predictivo import ParserPredictivo
from semantico         import AnalizadorSemantico


# ══════════════════════════════════════════════
#  ESPECIFICACIÓN DE LOS EJEMPLOS
# ══════════════════════════════════════════════

# Cada entrada describe el resultado esperado del análisis semántico
# para el .dml correspondiente. Mantener sincronizado con los archivos
# de `ejemplos_semanticos/`. Un `n_errores` de 0 indica un ejemplo
# VÁLIDO (sin errores semánticos).
ESPECIFICACION = [
    {
        "ruta":      "ejemplos_semanticos/05_tipo_asignacion_decl.dml",
        "n_errores": 1,
        "primer_error": {
            "regla":   "TIPO_ASIGNACION",
            "fila":    5,
            "columna": 12,
            "lexema":  "x",
        },
        "contexto_primer_error": {
            "tipo_declarado": "entero",
            "tipo_recibido":  "cadena",
            "identificador":  "x",
        },
        "mensaje_contiene": "'cadena'",
    },
    {
        "ruta":      "ejemplos_semanticos/06_tipo_asignacion_reasignacion.dml",
        "n_errores": 1,
        "primer_error": {
            "regla":   "TIPO_ASIGNACION",
            "fila":    6,
            "columna": 5,
            "lexema":  "x",
        },
        "contexto_primer_error": {
            "tipo_destino":  "entero",
            "tipo_recibido": "cadena",
            "identificador": "x",
        },
        "mensaje_contiene": "variable 'x'",
    },
    {
        "ruta":      "ejemplos_semanticos/07_tipo_void_en_variable.dml",
        "n_errores": 1,
        "primer_error": {
            "regla":   "TIPO_VOID_EN_VARIABLE",
            "fila":    7,
            "columna": 11,
            "lexema":  "v",
        },
        "contexto_primer_error": {
            "tipo_declarado": "vacio",
        },
        "mensaje_contiene": "vacio",
    },
    {
        "ruta":      "ejemplos_semanticos/08_tipo_promocion_ok.dml",
        "n_errores": 1,
        "primer_error": {
            "regla":   "TIPO_ASIGNACION",
            "fila":    9,
            "columna": 12,
            "lexema":  "z",
        },
        "contexto_primer_error": {
            "tipo_declarado": "entero",
            "tipo_recibido":  "real",
            "identificador":  "z",
        },
        "mensaje_contiene": "'real'",
    },
    {
        "ruta":      "ejemplos_semanticos/09_cadena_concat_ok.dml",
        "n_errores": 0,                       # ejemplo VÁLIDO
    },
    {
        "ruta":      "ejemplos_semanticos/10_cadena_concat_mixto.dml",
        "n_errores": 1,
        "primer_error": {
            "regla":   "TIPO_OPERADOR",
            "fila":    8,
            "columna": 26,
            "lexema":  "+",
        },
        "contexto_primer_error": {
            "tipo_izquierdo": "cadena",
            "tipo_derecho":   "entero",
        },
        "mensaje_contiene": "operador '+'",
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
                # Ejemplo VÁLIDO.
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
#  NO-REGRESIÓN: PROGRAMA VÁLIDO MÁS COMPLEJO
# ══════════════════════════════════════════════

# Declara variables de varios tipos, reasigna y usa una promoción
# entero->real (real promedio <- n * factor) y una concatenación
# implícita-no (sólo aritmética válida). No debe reportar nada.
CODIGO_VALIDO = (
    "funcion calcular(entero n, real factor) retornar real\n"
    "hacer\n"
    "    entero contador <- 0\n"
    "    real total <- 0.0\n"
    "    real promedio <- n * factor\n"          # entero*real -> real (promoción)
    "    cadena etiqueta <- \"resultado: \"\n"
    "    booleano listo <- verdadero\n"
    "    contador <- contador + 1\n"              # reasignación entero<-entero
    "    total <- total + promedio\n"             # reasignación real<-real
    "    retornar total\n"
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
        print(f"  ✓ [{nombre_parser}] programa complejo: sin errores semánticos")


# ══════════════════════════════════════════════
#  COMBINADO: REGLAS 1 + 2 + 3 NO ABORTAN
# ══════════════════════════════════════════════

# - 'entero a' duplicada            -> DECL_DUPLICADA   (regla 1)
# - 'b' no declarada en asignación  -> USO_NO_DECLARADO (regla 2)
# - 'entero c <- "texto"'           -> TIPO_ASIGNACION  (regla 3)
CODIGO_COMBINADO = (
    "funcion principal()\n"
    "hacer\n"
    "    entero a <- 10\n"
    "    entero a <- 20\n"
    "    b <- 5\n"
    "    entero c <- \"texto\"\n"
    "fin_funcion\n"
)


def test_reglas_1_2_3_combinadas():
    for nombre_parser, ParserClase in PARSERS:
        p, r = _analizar(ParserClase, CODIGO_COMBINADO)
        assert len(p.errores) == 0, (
            f"[{nombre_parser}] el código combinado no debería tener errores "
            f"sintácticos; obtuvo {len(p.errores)}"
        )
        errs = r["errores_semanticos"]
        reglas = sorted({e["regla"] for e in errs})
        assert reglas == ["DECL_DUPLICADA", "TIPO_ASIGNACION",
                          "USO_NO_DECLARADO"], (
            f"[{nombre_parser}] esperaba las tres reglas; obtuvo "
            f"reglas={reglas}, errores={errs}"
        )
        assert len(errs) == 3, (
            f"[{nombre_parser}] esperaba exactamente 3 errores; "
            f"obtuvo {len(errs)}: {errs}"
        )
        print(f"  ✓ [{nombre_parser}] {len(errs)} errores combinados: {reglas}")


# ══════════════════════════════════════════════
#  SMOKE TESTS DE CIERRE
# ══════════════════════════════════════════════

def _programa(stmt: str) -> str:
    return f"funcion p()\nhacer\n    {stmt}\nfin_funcion\n"


def test_smoke_tipo_asignacion_unico():
    """'entero x <- "hola"' reporta UN solo TIPO_ASIGNACION (sin
    TIPO_OPERADOR adicional: no hay operador en el RHS)."""
    codigo = _programa('entero x <- "hola"')
    for nombre_parser, ParserClase in PARSERS:
        p, r = _analizar(ParserClase, codigo)
        assert len(p.errores) == 0, p.errores
        errs = r["errores_semanticos"]
        reglas = [e["regla"] for e in errs]
        assert reglas == ["TIPO_ASIGNACION"], (
            f"[{nombre_parser}] esperaba ['TIPO_ASIGNACION']; obtuvo {reglas}"
        )
        print(f"  ✓ [{nombre_parser}] 'entero x <- \"hola\"' -> 1 TIPO_ASIGNACION")


def test_smoke_tipo_operador_suprime_asignacion():
    """'entero x <- 5 + "hola"' reporta UN solo TIPO_OPERADOR; la
    cascada (F.10) hace que TIPO_ASIGNACION NO se emita (RHS = ERROR)."""
    codigo = _programa('entero x <- 5 + "hola"')
    for nombre_parser, ParserClase in PARSERS:
        p, r = _analizar(ParserClase, codigo)
        assert len(p.errores) == 0, p.errores
        errs = r["errores_semanticos"]
        reglas = [e["regla"] for e in errs]
        assert reglas == ["TIPO_OPERADOR"], (
            f"[{nombre_parser}] esperaba ['TIPO_OPERADOR'] (cascada suprime "
            f"TIPO_ASIGNACION); obtuvo {reglas}: {errs}"
        )
        print(f"  ✓ [{nombre_parser}] 'entero x <- 5 + \"hola\"' -> "
              f"1 TIPO_OPERADOR (sin TIPO_ASIGNACION)")


def test_smoke_asignar_a_funcion():
    """Asignar a una función ('f <- 5' con f declarada como función) es
    error TIPO_ASIGNACION con contexto tipo_destino='funcion'."""
    codigo = (
        "funcion f() retornar entero\n"
        "hacer\n"
        "    retornar 1\n"
        "fin_funcion\n"
        "funcion principal()\n"
        "hacer\n"
        "    f <- 5\n"
        "fin_funcion\n"
    )
    for nombre_parser, ParserClase in PARSERS:
        p, r = _analizar(ParserClase, codigo)
        assert len(p.errores) == 0, p.errores
        errs = r["errores_semanticos"]
        asign = [e for e in errs if e["regla"] == "TIPO_ASIGNACION"]
        assert len(asign) == 1, (
            f"[{nombre_parser}] esperaba 1 TIPO_ASIGNACION al asignar a una "
            f"función; obtuvo {errs}"
        )
        assert asign[0]["contexto"].get("tipo_destino") == "funcion", asign[0]
        print(f"  ✓ [{nombre_parser}] 'f <- 5' (f función) -> TIPO_ASIGNACION")


# ══════════════════════════════════════════════
#  RUNNER
# ══════════════════════════════════════════════

def main() -> int:
    print("── Ejemplos .dml ──")
    test_ejemplos_dml()
    print("\n── No-regresión: programa válido complejo ──")
    test_programa_valido_sin_errores()
    print("\n── Combinado: reglas 1 + 2 + 3 ──")
    test_reglas_1_2_3_combinadas()
    print("\n── Smoke tests de cierre ──")
    test_smoke_tipo_asignacion_unico()
    test_smoke_tipo_operador_suprime_asignacion()
    test_smoke_asignar_a_funcion()
    print("\n✓ Todos los tests de la Etapa 5 pasaron.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
