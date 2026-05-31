"""
Test de contrato para la Etapa 1 del análisis semántico.

Verifica que tras llamar a `parser.analizar()`:
  1. El parser expone `parser.arbol_raiz` (un NodoArbol).
  2. Todo nodo terminal con un lexema real (no ε, no marcador de
     hueco) tiene `linea` y `columna` no nulos.
  3. Todo nodo no terminal cuyo subárbol contiene al menos un
     terminal real tiene `linea` y `columna` no nulos (lo aporta el
     helper `propagar_posicion_terminales`).
  4. Ambos parsers (recursivo y predictivo) cumplen lo anterior.

Ejecutar con:
    python test_etapa1_posiciones.py
"""

from arbol import NodoArbol
from parser_recursivo  import ParserRecursivo
from parser_predictivo import ParserPredictivo


# ── Fixtures ──────────────────────────────────────────────

# Programa trivial, válido, una sola sentencia top-level.
CODIGO_TRIVIAL = "entero x <- 10\n"

# Programa "real" con función, condicional y bucle: ejercita más
# producciones y verifica que la propagación funciona en árboles
# profundos.
CODIGO_FUNCION = (
    "funcion factorial(entero n) retornar entero\n"
    "hacer\n"
    "    si n <= 1 entonces\n"
    "        retornar 1\n"
    "    sino\n"
    "        retornar n * factorial(n - 1)\n"
    "    fin_si\n"
    "fin_funcion\n"
)


# ── Helpers de inspección ─────────────────────────────────

def tiene_terminal_real(nodo: NodoArbol) -> bool:
    """True si el subárbol de `nodo` contiene al menos un terminal
    cuyo lexema NO es ε (todo terminal real proviene de un Token).
    Los marcadores ERROR<...> también son terminales 'reales' en este
    sentido: en E1 los construimos con la posición del token actual.
    """
    if nodo.es_terminal:
        return nodo.etiqueta != 'ε'
    return any(tiene_terminal_real(h) for h in nodo.hijos)


def recolectar_violaciones(nodo: NodoArbol, ruta: str = "root") -> list:
    """Recorre el árbol y devuelve una lista de strings describiendo
    cualquier nodo que viole el contrato de posiciones."""
    violaciones = []

    if nodo.es_terminal:
        if nodo.etiqueta == 'ε':
            # ε es sintético, no proviene de un token → ok que sea None
            return violaciones
        if nodo.linea is None or nodo.columna is None:
            violaciones.append(
                f"[terminal] {ruta} etiqueta={nodo.etiqueta!r} "
                f"linea={nodo.linea} columna={nodo.columna}"
            )
        return violaciones

    # No terminal: solo es obligatorio tener posición si su subárbol
    # contiene al menos un terminal real (los no-terminales puramente
    # ε, como `parametros → ε`, quedan legítimamente sin posición).
    if tiene_terminal_real(nodo):
        if nodo.linea is None or nodo.columna is None:
            violaciones.append(
                f"[no-term] {ruta} etiqueta={nodo.etiqueta!r} "
                f"linea={nodo.linea} columna={nodo.columna}"
            )

    for hijo in nodo.hijos:
        sub_ruta = f"{ruta}/{nodo.etiqueta}"
        violaciones.extend(recolectar_violaciones(hijo, sub_ruta))

    return violaciones


def contar_nodos(nodo: NodoArbol) -> tuple:
    """Devuelve (total, terminales_reales, terminales_eps)."""
    total = 1
    term_reales = 0
    term_eps = 0
    if nodo.es_terminal:
        if nodo.etiqueta == 'ε':
            term_eps = 1
        else:
            term_reales = 1
    for h in nodo.hijos:
        t, tr, te = contar_nodos(h)
        total += t
        term_reales += tr
        term_eps += te
    return total, term_reales, term_eps


# ── Núcleo del test ────────────────────────────────────────

def correr_un_caso(nombre_parser: str, parser, codigo: str) -> bool:
    """Devuelve True si el caso pasa, False si encuentra violaciones."""
    parser.analizar()

    assert hasattr(parser, 'arbol_raiz'), (
        f"{nombre_parser}: el parser no expone `arbol_raiz` "
        f"tras llamar a analizar()."
    )
    raiz = parser.arbol_raiz
    assert isinstance(raiz, NodoArbol), (
        f"{nombre_parser}: arbol_raiz no es una instancia de NodoArbol."
    )

    total, tr, te = contar_nodos(raiz)
    violaciones = recolectar_violaciones(raiz)

    print(f"  [{nombre_parser}] nodos={total} terminales_reales={tr} eps={te} "
          f"violaciones={len(violaciones)}")

    if violaciones:
        print(f"  [{nombre_parser}] DETALLES (primeros 10):")
        for v in violaciones[:10]:
            print(f"      - {v}")
        return False
    return True


def main() -> int:
    casos = [
        ("trivial",  CODIGO_TRIVIAL),
        ("funcion",  CODIGO_FUNCION),
    ]

    total_ok = True
    for nombre, codigo in casos:
        print(f"\n── Caso: {nombre} ──")
        print("Código:")
        for i, linea in enumerate(codigo.splitlines(), start=1):
            print(f"  {i:>2} │ {linea}")

        # Parser recursivo
        pr = ParserRecursivo(codigo)
        ok_rec = correr_un_caso("recursivo",  pr,  codigo)

        # Parser predictivo
        pp = ParserPredictivo(codigo)
        ok_pred = correr_un_caso("predictivo", pp, codigo)

        total_ok = total_ok and ok_rec and ok_pred

    print()
    if total_ok:
        print("✓ TODOS los casos pasaron en ambos parsers.")
        return 0
    print("✗ Hay violaciones del contrato de posiciones.")
    return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
