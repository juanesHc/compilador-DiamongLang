"""
Tests del endpoint POST /parsear — Etapa 8
(Integración del análisis semántico en el servidor Flask).

Se usa el TEST CLIENT de Flask (`server.app.test_client()`): no se
levanta un servidor real ni se abre un puerto. Cada caso se corre con
los DOS métodos ('recursivo' y 'predictivo') vía el parámetro 'metodo'
del body.

Cubre:
  1. Programa sintáctica Y semánticamente VÁLIDO (factorial) →
     valido=True, errores=[], valido_semantico=True, errores_semanticos=[].
  2. Programa sintácticamente válido pero con ERROR SEMÁNTICO
     (entero x <- "hola") → valido=True, errores=[],
     valido_semantico=False, errores_semanticos=[1 entrada].
  3. Programa con AMBOS tipos de error (sintáctico + algo semántico en
     otra parte) → valido=False, errores≥1; lo esencial es que el
     endpoint NO crashee y devuelva las claves nuevas.
  4. Shape del JSON: claves nuevas (errores_semanticos, valido_semantico,
     simbolos) + las de E3 (error, errores, valido, nodos, metodo; traza
     solo en predictivo).
  5. Campos de cada entrada de errores_semanticos (ErrorSemantico
     serializado).

NOTA sobre el caso 3 (decisión F.11): desde la Etapa 8.5 el
AnalizadorSemantico hace análisis PARCIAL: salta sólo las sentencias/hojas
con errores sintácticos y analiza las zonas limpias. Por eso, un programa
con un error sintáctico + un error semántico en una zona limpia ahora
reporta ESE error semántico (errores_semanticos con al menos 1 entrada),
además de los sintácticos. El test 3 lo verifica.

Ejecutar con:
    python3 test_etapa8_endpoint.py
"""

import os as _os, sys as _sys
_PROJ_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _PROJ_ROOT not in _sys.path:
    _sys.path.insert(0, _PROJ_ROOT)
import server


CLIENTE = server.app.test_client()
METODOS = ("recursivo", "predictivo")

# Claves que el endpoint ya devolvía en E3 (deben seguir presentes).
CLAVES_E3        = {"valido", "errores", "error", "nodos", "metodo"}
# Claves nuevas de la Etapa 8.
CLAVES_SEMANTICA = {"errores_semanticos", "valido_semantico", "simbolos"}
# Campos esperados de un ErrorSemantico serializado.
CAMPOS_ERROR_SEM = {"indice", "fila", "columna", "lexema", "regla",
                    "mensaje", "sugerencia", "fuente_sugerencia", "contexto"}


# Programas de prueba ----------------------------------------------------

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

CODIGO_ERROR_SEMANTICO = (
    "funcion principal() retornar entero\n"
    "hacer\n"
    "    entero x <- \"hola\"\n"
    "    retornar 0\n"
    "fin_funcion\n"
)

# Error sintáctico (falta '<-' en 'entero x 5') en la función `uno`, y un
# error semántico (TIPO_ASIGNACION) en la función `dos`, sintácticamente
# limpia.
CODIGO_AMBOS_ERRORES = (
    "funcion uno() retornar entero\n"
    "hacer\n"
    "    entero x 5\n"
    "    retornar x\n"
    "fin_funcion\n"
    "\n"
    "funcion dos() retornar entero\n"
    "hacer\n"
    "    entero a <- \"hola\"\n"
    "    retornar 0\n"
    "fin_funcion\n"
)


# Helpers ----------------------------------------------------------------

def _post(codigo, metodo):
    resp = CLIENTE.post("/parsear",
                        json={"codigo": codigo, "metodo": metodo,
                              "max_errores": 100})
    assert resp.status_code == 200, (
        f"[{metodo}] /parsear devolvió HTTP {resp.status_code}, "
        f"esperaba 200"
    )
    data = resp.get_json()
    assert data is not None, f"[{metodo}] la respuesta no es JSON válido"
    return data


def _check_claves(data, metodo):
    faltan_e3 = CLAVES_E3 - data.keys()
    assert not faltan_e3, (
        f"[{metodo}] faltan claves de E3 en la respuesta: {faltan_e3}"
    )
    faltan_sem = CLAVES_SEMANTICA - data.keys()
    assert not faltan_sem, (
        f"[{metodo}] faltan claves semánticas (Etapa 8): {faltan_sem}"
    )
    if metodo == "predictivo":
        assert "traza" in data, (
            f"[{metodo}] el método predictivo debería incluir 'traza'"
        )
    # Tipos de las claves nuevas.
    assert isinstance(data["errores_semanticos"], list), data["errores_semanticos"]
    assert isinstance(data["valido_semantico"], bool), data["valido_semantico"]
    assert isinstance(data["simbolos"], list), data["simbolos"]


def _check_campos_errores_sem(data, metodo):
    for e in data["errores_semanticos"]:
        faltan = CAMPOS_ERROR_SEM - e.keys()
        assert not faltan, (
            f"[{metodo}] una entrada de errores_semanticos no tiene los "
            f"campos esperados; faltan {faltan}; entrada={e}"
        )
        assert isinstance(e["contexto"], dict), e["contexto"]


# Tests ------------------------------------------------------------------

def test_valido_completo():
    """Factorial bien escrito: válido sintáctica y semánticamente."""
    for metodo in METODOS:
        data = _post(CODIGO_VALIDO, metodo)
        _check_claves(data, metodo)
        assert data["valido"] is True, (
            f"[{metodo}] valido debería ser True; errores={data['errores']}"
        )
        assert data["errores"] == [], data["errores"]
        assert data["valido_semantico"] is True, (
            f"[{metodo}] valido_semantico debería ser True; "
            f"errores_semanticos={data['errores_semanticos']}"
        )
        assert data["errores_semanticos"] == [], data["errores_semanticos"]
        print(f"  ✓ [{metodo}] factorial válido: sin errores de ningún tipo")


def test_error_semantico_puro():
    """Sintaxis OK, un error semántico (TIPO_ASIGNACION)."""
    for metodo in METODOS:
        data = _post(CODIGO_ERROR_SEMANTICO, metodo)
        _check_claves(data, metodo)
        _check_campos_errores_sem(data, metodo)
        assert data["valido"] is True, (
            f"[{metodo}] valido (sintáctico) debería ser True; "
            f"errores={data['errores']}"
        )
        assert data["errores"] == [], data["errores"]
        assert data["valido_semantico"] is False, (
            f"[{metodo}] valido_semantico debería ser False"
        )
        assert len(data["errores_semanticos"]) == 1, (
            f"[{metodo}] esperaba 1 error semántico; "
            f"obtuvo {data['errores_semanticos']}"
        )
        e = data["errores_semanticos"][0]
        assert e["regla"] == "TIPO_ASIGNACION", e
        assert e["sugerencia"], (
            f"[{metodo}] el error semántico debería traer sugerencia local; "
            f"entrada={e}"
        )
        assert e["fuente_sugerencia"] == "local", e
        print(f"  ✓ [{metodo}] error semántico: 1 TIPO_ASIGNACION con sugerencia")


def test_ambos_errores_no_crashea():
    """Error sintáctico + zona limpia con error semántico. No crashea,
    devuelve las claves, valido=False, errores≥1, y —desde la Etapa 8.5—
    reporta el error semántico de la zona limpia (TIPO_ASIGNACION)."""
    for metodo in METODOS:
        data = _post(CODIGO_AMBOS_ERRORES, metodo)
        _check_claves(data, metodo)
        _check_campos_errores_sem(data, metodo)
        assert data["valido"] is False, (
            f"[{metodo}] valido debería ser False (hay error sintáctico)"
        )
        assert len(data["errores"]) >= 1, (
            f"[{metodo}] esperaba al menos 1 error sintáctico; "
            f"obtuvo {data['errores']}"
        )
        # Etapa 8.5: el análisis parcial ahora SÍ reporta el error
        # semántico de la zona limpia (TIPO_ASIGNACION en la función 'dos').
        sem = data["errores_semanticos"]
        assert isinstance(data["valido_semantico"], bool)
        assert len(sem) >= 1, (
            f"[{metodo}] tras el análisis parcial (F.11) debería reportarse "
            f"al menos 1 error semántico de la zona limpia; obtuvo {sem}"
        )
        reglas = {e["regla"] for e in sem}
        assert "TIPO_ASIGNACION" in reglas, (
            f"[{metodo}] esperaba el TIPO_ASIGNACION de la función limpia "
            f"'dos'; obtuvo reglas={reglas}"
        )
        assert data["valido_semantico"] is False, (
            f"[{metodo}] valido_semantico debería ser False (hay semántico)"
        )
        print(f"  ✓ [{metodo}] ambos errores: {len(data['errores'])} "
              f"sintáctico(s) + {len(sem)} semántico(s) {sorted(reglas)} "
              f"(análisis parcial OK)")


def test_shape_y_compatibilidad():
    """El JSON mantiene las claves de E3 y añade las semánticas, en los
    tres escenarios y ambos métodos."""
    for codigo in (CODIGO_VALIDO, CODIGO_ERROR_SEMANTICO, CODIGO_AMBOS_ERRORES):
        for metodo in METODOS:
            data = _post(codigo, metodo)
            _check_claves(data, metodo)
            _check_campos_errores_sem(data, metodo)
    print("  ✓ shape del JSON correcto (claves E3 + semánticas) en los 3 "
          "escenarios × 2 métodos")


def test_simbolos_presentes():
    """En un programa válido, la tabla de símbolos viaja en 'simbolos'
    con la forma esperada (nombre, categoria, tipo, ambito)."""
    for metodo in METODOS:
        data = _post(CODIGO_VALIDO, metodo)
        simbolos = data["simbolos"]
        assert len(simbolos) >= 1, (
            f"[{metodo}] esperaba al menos un símbolo (la función factorial "
            f"y su parámetro); obtuvo {simbolos}"
        )
        for s in simbolos:
            for campo in ("nombre", "categoria", "tipo", "ambito"):
                assert campo in s, (
                    f"[{metodo}] al símbolo le falta el campo {campo!r}: {s}"
                )
        nombres = {s["nombre"] for s in simbolos}
        assert "factorial" in nombres, (
            f"[{metodo}] 'factorial' debería estar en la tabla; "
            f"símbolos={nombres}"
        )
        print(f"  ✓ [{metodo}] tabla de símbolos: {sorted(nombres)}")


# Runner -----------------------------------------------------------------

def main() -> int:
    print("── Programa válido (sintáctico + semántico) ──")
    test_valido_completo()
    print("\n── Error semántico puro ──")
    test_error_semantico_puro()
    print("\n── Ambos tipos de error (no crashea) ──")
    test_ambos_errores_no_crashea()
    print("\n── Shape del JSON y compatibilidad ──")
    test_shape_y_compatibilidad()
    print("\n── Tabla de símbolos en la respuesta ──")
    test_simbolos_presentes()
    print("\n✓ Todos los tests de la Etapa 8 (endpoint) pasaron.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
