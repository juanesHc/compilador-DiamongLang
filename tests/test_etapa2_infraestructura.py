"""
Tests de la infraestructura semántica — Etapa 2.

Cubre:
  - TablaSimbolos: declarar, duplicado, sombreo, cierre de ámbito.
  - Helpers de arbol.py: hijos_por_etiqueta, hijo_por_etiqueta,
    primer_terminal (sin nodos error), recolectar_terminales,
    etiqueta_normalizada (apóstrofo ↔ _prima), raiz_logica (doble
    nodo programa del recursivo), tiene_error_sintactico.
  - AnalizadorSemantico (esqueleto): se instancia con árbol de ambos
    parsers, analizar() devuelve valido_semantico=True y lista vacía
    de errores, sin excepciones.

Ejecutar con:
    python3 test_etapa2_infraestructura.py
"""

import os as _os, sys as _sys
_PROJ_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _PROJ_ROOT not in _sys.path:
    _sys.path.insert(0, _PROJ_ROOT)
from sintactico.arbol import (
    NodoArbol,
    hijos_por_etiqueta, hijo_por_etiqueta,
    primer_terminal, recolectar_terminales,
    tiene_error_sintactico, etiqueta_normalizada,
    raiz_logica,
)
from semantico.tabla_simbolos import TablaSimbolos, Simbolo
from semantico.semantico import AnalizadorSemantico
from sintactico.parser_recursivo import ParserRecursivo
from sintactico.parser_predictivo import ParserPredictivo


# ══════════════════════════════════════════════
#  TESTS — TablaSimbolos
# ══════════════════════════════════════════════

def test_tabla_basica():
    t = TablaSimbolos()
    assert t.ambito_actual() == 'global'
    s = Simbolo(nombre='x', tipo='entero', categoria='variable',
                ambito='global', fila=1, columna=8)
    assert t.declarar(s) is True
    assert t.existe_en_ambito_actual('x') is True
    assert t.buscar('x') is s
    print("  ✓ test_tabla_basica")


def test_tabla_duplicado():
    t = TablaSimbolos()
    s1 = Simbolo(nombre='x', tipo='entero', categoria='variable', ambito='global')
    s2 = Simbolo(nombre='x', tipo='real',   categoria='variable', ambito='global')
    assert t.declarar(s1) is True
    assert t.declarar(s2) is False, "no debe permitir duplicado en el mismo scope"
    assert t.buscar('x') is s1, "debe quedarse con el original"
    print("  ✓ test_tabla_duplicado")


def test_tabla_sombreo_y_resolucion():
    t = TablaSimbolos()
    s_global = Simbolo(nombre='x', tipo='entero', categoria='variable',
                       ambito='global')
    assert t.declarar(s_global) is True

    t.abrir_ambito('f1')
    assert t.ambito_actual() == 'f1'

    s_local = Simbolo(nombre='x', tipo='real', categoria='variable',
                      ambito='f1')
    assert t.declarar(s_local) is True, (
        "sombreo legal: la x global no debe bloquear la x local"
    )
    encontrado = t.buscar('x')
    assert encontrado is s_local, (
        f"esperaba ver el x de f1, devolvió {encontrado}"
    )
    print("  ✓ test_tabla_sombreo_y_resolucion")


def test_tabla_cierre_de_ambito():
    t = TablaSimbolos()
    t.abrir_ambito('f1')
    t.declarar(Simbolo(nombre='x', tipo='entero', categoria='variable',
                       ambito='f1'))
    assert t.buscar('x') is not None
    t.cerrar_ambito()
    assert t.ambito_actual() == 'global'
    assert t.buscar('x') is None, (
        "tras cerrar 'f1', su x no debe ser visible desde global"
    )
    print("  ✓ test_tabla_cierre_de_ambito")


# ══════════════════════════════════════════════
#  TESTS — helpers de arbol.py
# ══════════════════════════════════════════════

def _construir_arbol_decl_simple():
    """
    Construye manualmente un mini-CST para `entero x <- 10` (sin
    pasar por el parser). Devuelve la raíz `programa`.
    """
    raiz = NodoArbol('programa', linea=1, columna=1)

    decl = NodoArbol('decl_variable', linea=1, columna=1)
    tipo = NodoArbol('tipo',          linea=1, columna=1)
    tipo.agregar_hijo(NodoArbol('entero', es_terminal=True,
                                linea=1, columna=1))
    decl.agregar_hijo(tipo)
    decl.agregar_hijo(NodoArbol('x',  es_terminal=True, linea=1, columna=8))
    decl.agregar_hijo(NodoArbol('<-', es_terminal=True, linea=1, columna=10))
    decl.agregar_hijo(NodoArbol('10', es_terminal=True, linea=1, columna=13))

    raiz.agregar_hijo(decl)
    return raiz, decl


def test_helpers_hijos_por_etiqueta():
    raiz, decl = _construir_arbol_decl_simple()
    assert hijos_por_etiqueta(raiz, 'decl_variable') == [decl]
    assert hijo_por_etiqueta(raiz, 'decl_variable') is decl
    assert hijo_por_etiqueta(raiz, 'inexistente') is None
    print("  ✓ hijos_por_etiqueta / hijo_por_etiqueta")


def test_helpers_primer_terminal():
    nodo = NodoArbol('expr_primaria')
    nodo.agregar_hijo(NodoArbol("ERROR<x>", es_terminal=True,
                                es_error=True, linea=1, columna=1))
    real = NodoArbol("42", es_terminal=True, linea=1, columna=2)
    nodo.agregar_hijo(real)
    obtenido = primer_terminal(nodo)
    assert obtenido is real, (
        f"primer_terminal no debe devolver nodos con es_error=True; "
        f"devolvió {obtenido}"
    )
    print("  ✓ primer_terminal salta nodos con es_error=True")


def test_helpers_recolectar_terminales():
    _raiz, decl = _construir_arbol_decl_simple()
    terms = recolectar_terminales(decl)
    etiquetas = [t.etiqueta for t in terms]
    assert etiquetas == ['entero', 'x', '<-', '10'], (
        f"orden inesperado: {etiquetas}"
    )
    print("  ✓ recolectar_terminales (pre-orden)")


def test_helpers_etiqueta_normalizada():
    assert etiqueta_normalizada("bloque'")        == "bloque_prima"
    assert etiqueta_normalizada("bloque_prima")   == "bloque_prima"
    assert etiqueta_normalizada("expr_or'")       == "expr_or_prima"
    assert etiqueta_normalizada("expr_or_prima")  == "expr_or_prima"
    assert etiqueta_normalizada("programa")       == "programa"
    assert etiqueta_normalizada("ε")              == "ε"
    print("  ✓ etiqueta_normalizada (apóstrofo ↔ _prima)")


def test_helpers_raiz_logica():
    # Caso recursivo: doble nodo 'programa'
    outer = NodoArbol('programa')
    inner = NodoArbol('programa')
    outer.agregar_hijo(inner)
    assert raiz_logica(outer) is inner, (
        "debe desempacar el doble nodo del parser recursivo"
    )

    # Caso predictivo: un solo 'programa' con otros hijos
    solo = NodoArbol('programa')
    solo.agregar_hijo(NodoArbol('declaracion'))
    solo.agregar_hijo(NodoArbol('declaracion'))
    assert raiz_logica(solo) is solo, (
        "no debe modificar la raíz cuando no aplica el patrón"
    )

    # Caso degenerado: nodo sin hijos
    vacio = NodoArbol('programa')
    assert raiz_logica(vacio) is vacio
    print("  ✓ raiz_logica desempaca doble 'programa' del recursivo")


def test_helpers_tiene_error_sintactico():
    sin_err = NodoArbol('s')
    sin_err.agregar_hijo(NodoArbol('a', es_terminal=True, linea=1, columna=1))
    sin_err.agregar_hijo(NodoArbol('b', es_terminal=True, linea=1, columna=2))
    assert tiene_error_sintactico(sin_err) is False

    con_err = NodoArbol('s')
    con_err.agregar_hijo(NodoArbol('a', es_terminal=True, linea=1, columna=1))
    profundo = NodoArbol('expr')
    profundo.agregar_hijo(NodoArbol("ERROR<falta ')'>", es_terminal=True,
                                    es_error=True, linea=1, columna=3))
    con_err.agregar_hijo(profundo)
    assert tiene_error_sintactico(con_err) is True, (
        "debe detectar es_error=True a cualquier profundidad"
    )
    print("  ✓ tiene_error_sintactico")


# ══════════════════════════════════════════════
#  TESTS — AnalizadorSemantico (esqueleto)
# ══════════════════════════════════════════════

CODIGO_VALIDO = (
    "funcion principal()\n"
    "hacer\n"
    "    entero x <- 10\n"
    "    escribir(x)\n"
    "fin_funcion\n"
)


def test_esqueleto_con_parser_recursivo():
    p = ParserRecursivo(CODIGO_VALIDO)
    p.analizar()
    a = AnalizadorSemantico(p.arbol_raiz)
    r = a.analizar()
    assert r["valido_semantico"] is True, r
    assert r["errores_semanticos"] == [], r["errores_semanticos"]
    print("  ✓ esqueleto (recursivo): valido_semantico=True, sin errores")


def test_esqueleto_con_parser_predictivo():
    p = ParserPredictivo(CODIGO_VALIDO)
    p.analizar()
    a = AnalizadorSemantico(p.arbol_raiz)
    r = a.analizar()
    assert r["valido_semantico"] is True, r
    assert r["errores_semanticos"] == [], r["errores_semanticos"]
    print("  ✓ esqueleto (predictivo): valido_semantico=True, sin errores")


def test_esqueleto_resultado_shape():
    """El dict de salida debe tener exactamente estas claves."""
    p = ParserRecursivo(CODIGO_VALIDO)
    p.analizar()
    r = AnalizadorSemantico(p.arbol_raiz).analizar()
    esperadas = {"valido_semantico", "errores_semanticos", "simbolos"}
    assert set(r.keys()) == esperadas, f"claves={set(r.keys())}"
    print("  ✓ shape del dict de salida")


# ══════════════════════════════════════════════
#  RUNNER
# ══════════════════════════════════════════════

def main() -> int:
    print("── TablaSimbolos ──")
    test_tabla_basica()
    test_tabla_duplicado()
    test_tabla_sombreo_y_resolucion()
    test_tabla_cierre_de_ambito()

    print("\n── Helpers arbol.py ──")
    test_helpers_hijos_por_etiqueta()
    test_helpers_primer_terminal()
    test_helpers_recolectar_terminales()
    test_helpers_etiqueta_normalizada()
    test_helpers_raiz_logica()
    test_helpers_tiene_error_sintactico()

    print("\n── AnalizadorSemantico (esqueleto) ──")
    test_esqueleto_con_parser_recursivo()
    test_esqueleto_con_parser_predictivo()
    test_esqueleto_resultado_shape()

    print("\n✓ Todos los tests de la Etapa 2 pasaron.")
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
