"""
Tests del sistema de tipos — Etapa 4.

Cubre, por categorías:
  A) compatible(destino, origen)
  B) unificar_aritmetico / relacional / logico / unario (sin árbol)
  C) tipo_de_expresion sobre árboles reales (ambos parsers)
  D) propagación de ERROR y supresión de cascada
  E) identificadores (declarados y no declarados)
  F) llamadas a función (tipo_retorno; sin validar aridad)

Las categorías C-F se ejercen contra los DOS parsers (recursivo y
predictivo) para confirmar que la inferencia es agnóstica al método.

Ejecutar con:
    python3 test_etapa4_tipos.py
"""

from parser_recursivo  import ParserRecursivo
from parser_predictivo import ParserPredictivo
from arbol             import etiqueta_normalizada
from tabla_simbolos    import TablaSimbolos, Simbolo
from semantico         import AnalizadorSemantico
from tipos import (
    TIPOS_NUMERICOS, TIPOS_BASICOS,
    compatible,
    unificar_aritmetico, unificar_relacional, unificar_logico, unificar_unario,
    tipo_de_literal, tipo_declarado,
    tipo_de_expresion, tipo_de_expresion_con_reporte,
)


PARSERS = [("recursivo", ParserRecursivo), ("predictivo", ParserPredictivo)]


# ══════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════

def _buscar(nodo, etq):
    """Primer nodo (pre-orden) cuya etiqueta normalizada == etq, o None."""
    if etiqueta_normalizada(nodo.etiqueta) == etq:
        return nodo
    for h in nodo.hijos:
        r = _buscar(h, etq)
        if r is not None:
            return r
    return None


def _programa(stmt: str) -> str:
    """Envuelve una sentencia en una función mínima sintácticamente válida."""
    return f"funcion p()\nhacer\n    {stmt}\nfin_funcion\n"


def _rhs_de_decl(parser_clase, codigo):
    """Parsea `codigo`, exige que sea sintácticamente válido y devuelve el
    nodo `expresion` del lado derecho de la PRIMERA `decl_variable`."""
    p = parser_clase(codigo)
    p.analizar()
    assert len(p.errores) == 0, (
        f"el código de prueba debería ser sintácticamente válido; "
        f"reportó {len(p.errores)} errores sintácticos: {codigo!r}"
    )
    decl = _buscar(p.arbol_raiz, 'decl_variable')
    assert decl is not None, f"no se encontró decl_variable en: {codigo!r}"
    return _buscar(decl, 'expresion')


def _nuevo_reportador():
    """Una instancia de AnalizadorSemantico sólo para usar su `_reportar`
    (idéntico al callable que recibirán las Etapas 5-7)."""
    return AnalizadorSemantico(None)


# ══════════════════════════════════════════════
#  A) COMPATIBILIDAD
# ══════════════════════════════════════════════

def test_compatibilidad():
    casos = [
        (('entero', 'entero'),   True),
        (('real', 'real'),       True),
        (('real', 'entero'),     True),    # promoción
        (('entero', 'real'),     False),   # sin truncamiento
        (('cadena', 'entero'),   False),
        (('booleano', 'cadena'), False),
        (('booleano', 'ERROR'),  True),    # suprime cascada
        (('ERROR', 'cadena'),    True),    # suprime cascada
        (('ERROR', 'ERROR'),     True),
        (('booleano', 'booleano'), True),
    ]
    for (dest, orig), esperado in casos:
        actual = compatible(dest, orig)
        assert actual == esperado, (
            f"compatible({dest!r}, {orig!r}) = {actual}, esperaba {esperado}"
        )
    print(f"  ✓ compatibilidad: {len(casos)} casos OK")


# ══════════════════════════════════════════════
#  B) UNIFICACIÓN DE OPERADORES (sin árbol)
# ══════════════════════════════════════════════

def test_unificar_aritmetico():
    casos = [
        (('entero', 'entero', '+'),  'entero'),
        (('entero', 'real',   '+'),  'real'),
        (('real',   'real',   '+'),  'real'),
        (('real',   'entero', '*'),  'real'),
        (('entero', 'entero', '*'),  'entero'),
        (('entero', 'entero', '%'),  'entero'),
        (('entero', 'entero', '**'), 'entero'),
        (('cadena', 'cadena', '+'),  'cadena'),     # concatenación
        (('cadena', 'cadena', '-'),  'ERROR'),      # sólo '+' concatena
        (('entero', 'cadena', '+'),  'ERROR'),
        (('booleano', 'entero', '+'), 'ERROR'),
        (('booleano', 'booleano', '+'), 'ERROR'),
        (('ERROR', 'entero', '+'),   'ERROR'),      # cascada
    ]
    for (t1, t2, op), esperado in casos:
        actual = unificar_aritmetico(t1, t2, op)
        assert actual == esperado, (
            f"unificar_aritmetico({t1!r},{t2!r},{op!r}) = {actual}, "
            f"esperaba {esperado}"
        )
    print(f"  ✓ aritméticos: {len(casos)} casos OK")


def test_unificar_relacional():
    casos = [
        (('entero', 'entero', '=='), 'booleano'),
        (('real',   'entero', '<='), 'booleano'),
        (('entero', 'real',   '>'),  'booleano'),
        (('cadena', 'cadena', '<'),  'booleano'),
        (('cadena', 'cadena', '=='), 'booleano'),
        (('booleano', 'booleano', '=='), 'booleano'),
        (('booleano', 'booleano', '!='), 'booleano'),
        (('booleano', 'booleano', '<'),  'ERROR'),
        (('booleano', 'booleano', '>='), 'ERROR'),
        (('entero', 'cadena', '=='), 'ERROR'),
        (('entero', 'booleano', '=='), 'ERROR'),
        (('ERROR', 'entero', '<'),   'ERROR'),
    ]
    for (t1, t2, op), esperado in casos:
        actual = unificar_relacional(t1, t2, op)
        assert actual == esperado, (
            f"unificar_relacional({t1!r},{t2!r},{op!r}) = {actual}, "
            f"esperaba {esperado}"
        )
    print(f"  ✓ relacionales: {len(casos)} casos OK")


def test_unificar_logico():
    casos = [
        (('booleano', 'booleano'), 'booleano'),
        (('entero',   'booleano'), 'ERROR'),
        (('booleano', 'entero'),   'ERROR'),
        (('cadena',   'cadena'),   'ERROR'),
        (('ERROR',    'booleano'), 'ERROR'),
    ]
    for (t1, t2), esperado in casos:
        actual = unificar_logico(t1, t2)
        assert actual == esperado, (
            f"unificar_logico({t1!r},{t2!r}) = {actual}, esperaba {esperado}"
        )
    print(f"  ✓ lógicos: {len(casos)} casos OK")


def test_unificar_unario():
    casos = [
        (('booleano', 'no'), 'booleano'),
        (('entero',   'no'), 'ERROR'),
        (('cadena',   'no'), 'ERROR'),
        (('entero',   '-'),  'entero'),
        (('real',     '-'),  'real'),
        (('cadena',   '-'),  'ERROR'),
        (('booleano', '-'),  'ERROR'),
        (('ERROR',    'no'), 'ERROR'),
        (('ERROR',    '-'),  'ERROR'),
    ]
    for (t, op), esperado in casos:
        actual = unificar_unario(t, op)
        assert actual == esperado, (
            f"unificar_unario({t!r},{op!r}) = {actual}, esperaba {esperado}"
        )
    print(f"  ✓ unarios: {len(casos)} casos OK")


def test_constantes_de_tipos():
    assert TIPOS_NUMERICOS == {'entero', 'real'}
    assert TIPOS_BASICOS == {'entero', 'real', 'cadena', 'booleano'}
    print("  ✓ conjuntos TIPOS_NUMERICOS / TIPOS_BASICOS OK")


# ══════════════════════════════════════════════
#  C) INFERENCIA SOBRE ÁRBOLES REALES
# ══════════════════════════════════════════════

# (sentencia que declara, expresión esperada del RHS)
CASOS_INFERENCIA = [
    ('entero  x <- 5 + 3',              'entero'),
    ('real    rr <- 5 + 3.14',          'real'),
    ('cadena  s <- "hola" + "mundo"',   'cadena'),
    ('booleano b <- 5 < 10',            'booleano'),
    ('booleano b <- 5 < 10 y 3 == 3',   'booleano'),
    ('entero  z <- 5 + "hola"',         'ERROR'),
    ('real    w <- 2 ** 3',             'entero'),   # potencia entero/entero
    ('real    q <- (5 + 3) * 2.0',      'real'),     # paréntesis + promoción
    ('booleano n <- no verdadero',      'booleano'),
    ('entero  m <- -7',                 'entero'),
    ('entero  e <- no 5',               'ERROR'),    # 'no' sobre entero
]


def test_inferencia_arboles():
    for stmt, esperado in CASOS_INFERENCIA:
        codigo = _programa(stmt)
        for nombre, ParserClase in PARSERS:
            rhs = _rhs_de_decl(ParserClase, codigo)
            t = tipo_de_expresion(rhs, TablaSimbolos())
            assert t == esperado, (
                f"[{nombre}] '{stmt}': tipo_de_expresion = {t!r}, "
                f"esperaba {esperado!r}"
            )
        print(f"  ✓ '{stmt.strip()}' → {esperado}")


def test_reporte_error_de_operador():
    """'5 + "hola"' debe producir EXACTAMENTE un error TIPO_OPERADOR
    en la versión con reporte, apuntando al operador '+'."""
    codigo = _programa('entero z <- 5 + "hola"')
    for nombre, ParserClase in PARSERS:
        rhs = _rhs_de_decl(ParserClase, codigo)
        az = _nuevo_reportador()
        t = tipo_de_expresion_con_reporte(rhs, TablaSimbolos(), az._reportar)
        assert t == 'ERROR', f"[{nombre}] esperaba ERROR, obtuvo {t!r}"
        assert len(az.errores) == 1, (
            f"[{nombre}] esperaba 1 error TIPO_OPERADOR, "
            f"obtuvo {len(az.errores)}: {az.errores}"
        )
        e = az.errores[0]
        assert e.regla == 'TIPO_OPERADOR', e.regla
        assert e.lexema == '+', e.lexema
        assert e.fila is not None and e.columna is not None, (
            f"[{nombre}] el error debe tener posición: {e}"
        )
        assert e.contexto.get('tipo_izquierdo') == 'entero', e.contexto
        assert e.contexto.get('tipo_derecho') == 'cadena', e.contexto
        print(f"  ✓ [{nombre}] '5 + \"hola\"' reporta TIPO_OPERADOR "
              f"en L{e.fila}:C{e.columna}")


# ══════════════════════════════════════════════
#  D) PROPAGACIÓN DE ERROR / SUPRESIÓN DE CASCADA
# ══════════════════════════════════════════════

def test_propagacion_error_silenciosa():
    """Una variable no declarada hace ERROR su uso, y al combinarla con
    un operando válido NO se genera reporte adicional (sólo la causa raíz
    se reportaría — por la Regla 2, no por tipos)."""
    codigo = _programa('entero z <- noexiste + 1')
    for nombre, ParserClase in PARSERS:
        rhs = _rhs_de_decl(ParserClase, codigo)
        tabla = TablaSimbolos()                     # 'noexiste' NO está

        # silenciosa: ERROR sin tocar nada
        t = tipo_de_expresion(rhs, tabla)
        assert t == 'ERROR', f"[{nombre}] esperaba ERROR, obtuvo {t!r}"

        # con reporte: NO debe reportar TIPO_OPERADOR (cascada suprimida)
        az = _nuevo_reportador()
        t2 = tipo_de_expresion_con_reporte(rhs, tabla, az._reportar)
        assert t2 == 'ERROR', f"[{nombre}] esperaba ERROR, obtuvo {t2!r}"
        assert len(az.errores) == 0, (
            f"[{nombre}] la cascada no debe reportar; obtuvo "
            f"{[e.regla for e in az.errores]}"
        )
        print(f"  ✓ [{nombre}] 'noexiste + 1' → ERROR, sin reporte derivado")


def test_un_solo_reporte_en_cadena():
    """En '5 + "a" + 3' sólo el primer '+' (entero+cadena) debe reportar;
    el segundo '+' opera sobre un ERROR y se contagia en silencio."""
    codigo = _programa('entero z <- 5 + "a" + 3')
    for nombre, ParserClase in PARSERS:
        rhs = _rhs_de_decl(ParserClase, codigo)
        az = _nuevo_reportador()
        t = tipo_de_expresion_con_reporte(rhs, TablaSimbolos(), az._reportar)
        assert t == 'ERROR', f"[{nombre}] esperaba ERROR, obtuvo {t!r}"
        assert len(az.errores) == 1, (
            f"[{nombre}] esperaba 1 solo reporte; obtuvo {len(az.errores)}: "
            f"{[e.mensaje for e in az.errores]}"
        )
        print(f"  ✓ [{nombre}] '5 + \"a\" + 3' reporta una sola vez")


# ══════════════════════════════════════════════
#  E) IDENTIFICADORES
# ══════════════════════════════════════════════

def test_identificador_declarado():
    """'x + 1' con x:entero en la tabla → entero."""
    codigo = _programa('entero res <- x + 1')
    for nombre, ParserClase in PARSERS:
        rhs = _rhs_de_decl(ParserClase, codigo)
        tabla = TablaSimbolos()
        tabla.declarar(Simbolo('x', 'entero', 'variable', 'global',
                               fila=1, columna=1))
        t = tipo_de_expresion(rhs, tabla)
        assert t == 'entero', f"[{nombre}] esperaba entero, obtuvo {t!r}"
        print(f"  ✓ [{nombre}] 'x + 1' con x:entero → entero")


def test_identificador_real_promociona():
    """'x + 1' con x:real → real (promoción)."""
    codigo = _programa('real res <- x + 1')
    for nombre, ParserClase in PARSERS:
        rhs = _rhs_de_decl(ParserClase, codigo)
        tabla = TablaSimbolos()
        tabla.declarar(Simbolo('x', 'real', 'variable', 'global'))
        t = tipo_de_expresion(rhs, tabla)
        assert t == 'real', f"[{nombre}] esperaba real, obtuvo {t!r}"
        print(f"  ✓ [{nombre}] 'x + 1' con x:real → real")


def test_identificador_no_declarado():
    """Identificador ausente de la tabla → ERROR."""
    codigo = _programa('entero res <- fantasma')
    for nombre, ParserClase in PARSERS:
        rhs = _rhs_de_decl(ParserClase, codigo)
        t = tipo_de_expresion(rhs, TablaSimbolos())
        assert t == 'ERROR', f"[{nombre}] esperaba ERROR, obtuvo {t!r}"
        print(f"  ✓ [{nombre}] 'fantasma' (no declarada) → ERROR")


# ══════════════════════════════════════════════
#  F) LLAMADAS A FUNCIÓN (sin validar aridad)
# ══════════════════════════════════════════════

def _tabla_con_funcion(nombre, tipo_retorno):
    tabla = TablaSimbolos()
    tabla.declarar(Simbolo(
        nombre=nombre, tipo='funcion', categoria='funcion', ambito='global',
        fila=1, columna=1,
        parametros=[('entero', 'a')], tipo_retorno=tipo_retorno,
    ))
    return tabla


def test_llamada_funcion_entero():
    """f(...) con f:tipo_retorno=entero → entero (no valida aridad)."""
    codigo = _programa('entero r <- f(5, 99, 1)')   # aridad "errónea": da igual
    for nombre, ParserClase in PARSERS:
        rhs = _rhs_de_decl(ParserClase, codigo)
        t = tipo_de_expresion(rhs, _tabla_con_funcion('f', 'entero'))
        assert t == 'entero', f"[{nombre}] esperaba entero, obtuvo {t!r}"
        print(f"  ✓ [{nombre}] 'f(...)' con retorno entero → entero")


def test_llamada_funcion_vacio():
    """g(...) con g:tipo_retorno=vacio → vacio."""
    codigo = _programa('entero r <- g(5)')
    for nombre, ParserClase in PARSERS:
        rhs = _rhs_de_decl(ParserClase, codigo)
        t = tipo_de_expresion(rhs, _tabla_con_funcion('g', 'vacio'))
        assert t == 'vacio', f"[{nombre}] esperaba vacio, obtuvo {t!r}"
        print(f"  ✓ [{nombre}] 'g(...)' con retorno vacio → vacio")


def test_llamada_funcion_inexistente():
    """Llamada a función ausente → ERROR."""
    codigo = _programa('entero r <- inexistente(5)')
    for nombre, ParserClase in PARSERS:
        rhs = _rhs_de_decl(ParserClase, codigo)
        t = tipo_de_expresion(rhs, TablaSimbolos())
        assert t == 'ERROR', f"[{nombre}] esperaba ERROR, obtuvo {t!r}"
        print(f"  ✓ [{nombre}] 'inexistente(...)' → ERROR")


def test_funcion_como_variable_y_viceversa():
    """Confusión variable/función → ERROR."""
    for nombre, ParserClase in PARSERS:
        # función 'f' usada SIN paréntesis (como variable) → ERROR
        rhs = _rhs_de_decl(ParserClase, _programa('entero r <- f'))
        t = tipo_de_expresion(rhs, _tabla_con_funcion('f', 'entero'))
        assert t == 'ERROR', f"[{nombre}] función como variable debió dar ERROR"

        # variable 'v' usada CON paréntesis (como función) → ERROR
        tabla = TablaSimbolos()
        tabla.declarar(Simbolo('v', 'entero', 'variable', 'global'))
        rhs2 = _rhs_de_decl(ParserClase, _programa('entero r <- v(3)'))
        t2 = tipo_de_expresion(rhs2, tabla)
        assert t2 == 'ERROR', f"[{nombre}] variable como función debió dar ERROR"
        print(f"  ✓ [{nombre}] confusión variable/función → ERROR")


# ══════════════════════════════════════════════
#  G) LITERALES Y TIPO DECLARADO (helpers directos)
# ══════════════════════════════════════════════

def test_tipo_de_literal_y_declarado():
    """tipo_de_literal y tipo_declarado sobre nodos reales del árbol."""
    for nombre, ParserClase in PARSERS:
        # tipo_declarado: nodo 'tipo' de la decl
        p = ParserClase(_programa('cadena s <- "x"'))
        p.analizar()
        decl = _buscar(p.arbol_raiz, 'decl_variable')
        nodo_tipo = _buscar(decl, 'tipo')
        assert tipo_declarado(nodo_tipo) == 'cadena', (
            f"[{nombre}] tipo_declarado debía ser 'cadena'"
        )

        # tipo_de_literal: terminales bajo expr_primaria
        for stmt, esperado in [('entero a <- 42', 'entero'),
                               ('real b <- 4.5', 'real'),
                               ('cadena c <- "hi"', 'cadena'),
                               ('booleano d <- verdadero', 'booleano'),
                               ('booleano e <- falso', 'booleano')]:
            pp = ParserClase(_programa(stmt))
            pp.analizar()
            prim = _buscar(pp.arbol_raiz, 'expr_primaria')
            term = next(h for h in prim.hijos if h.es_terminal)
            assert tipo_de_literal(term) == esperado, (
                f"[{nombre}] tipo_de_literal({term.etiqueta!r}) "
                f"debía ser {esperado!r}"
            )
        print(f"  ✓ [{nombre}] tipo_de_literal / tipo_declarado OK")


# ══════════════════════════════════════════════
#  RUNNER
# ══════════════════════════════════════════════

def main() -> int:
    print("── A) Compatibilidad ──")
    test_compatibilidad()

    print("\n── B) Unificación de operadores ──")
    test_constantes_de_tipos()
    test_unificar_aritmetico()
    test_unificar_relacional()
    test_unificar_logico()
    test_unificar_unario()

    print("\n── C) Inferencia sobre árboles ──")
    test_inferencia_arboles()
    test_reporte_error_de_operador()

    print("\n── D) Propagación de ERROR / cascada ──")
    test_propagacion_error_silenciosa()
    test_un_solo_reporte_en_cadena()

    print("\n── E) Identificadores ──")
    test_identificador_declarado()
    test_identificador_real_promociona()
    test_identificador_no_declarado()

    print("\n── F) Llamadas a función ──")
    test_llamada_funcion_entero()
    test_llamada_funcion_vacio()
    test_llamada_funcion_inexistente()
    test_funcion_como_variable_y_viceversa()

    print("\n── G) Literales y tipo declarado ──")
    test_tipo_de_literal_y_declarado()

    print("\n✓ Todos los tests de la Etapa 4 pasaron.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
