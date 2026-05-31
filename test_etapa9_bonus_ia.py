"""
Tests del bonus IA semántica — Etapa 9 (Modalidad A).

NINGÚN test hace una llamada real a la red: el cliente de Anthropic se
mockea sustituyendo el símbolo `Anthropic` del módulo
`sugerencias_ia_semantica` por una clase falsa (y fijando una API key
dummy). Así los tests son herméticos y rápidos, con o sin API key real
en el entorno.

Casos:
  A) IA NO disponible → sugerencia_ia_semantica retorna None; la
     sugerencia local del error queda intacta.
  B) IA disponible (mock con respuesta canned) → retorna la respuesta
     canned; al aplicarla, error.sugerencia se reemplaza y
     error.fuente_sugerencia pasa a 'ia'.
  C) Cache → segunda llamada con el mismo error NO vuelve a llamar a la
     API mockeada (un contador en el mock lo verifica).
  D) Endpoint /parsear:
     - usar_ia_semantica=False → comportamiento de la Etapa 8 (local).
     - usar_ia_semantica=True con IA mockeada → errores_semanticos llegan
       con sugerencia enriquecida y fuente_sugerencia='ia'.

Ejecutar con:
    python3 test_etapa9_bonus_ia.py
"""

import os
import contextlib

import sugerencias_ia_semantica as sem
from errores_semanticos import ErrorSemantico


# ══════════════════════════════════════════════
#  MOCK DEL CLIENTE ANTHROPIC (sin red)
# ══════════════════════════════════════════════

class _Contador:
    def __init__(self):
        self.n = 0


def _hacer_fake(contador, texto):
    """Fabrica una clase 'Anthropic' falsa cuyo .messages.create() devuelve
    `texto` e incrementa `contador.n`. No toca la red."""
    class _Block:
        def __init__(self, t): self.text = t

    class _Resp:
        def __init__(self, t): self.content = [_Block(t)]

    class _Msgs:
        def create(self, **kwargs):
            contador.n += 1
            return _Resp(texto)

    class _FakeAnthropic:
        def __init__(self, **kwargs):
            self.messages = _Msgs()

    return _FakeAnthropic


@contextlib.contextmanager
def ia_mock(fake_cls):
    """
    Context manager que instala un cliente Anthropic falso y una API key
    dummy, y restaura el estado original al salir.

    - fake_cls=None  → simula IA NO disponible (sin librería).
    - fake_cls=clase → simula IA disponible con ese cliente falso.

    Limpia los cachés (de módulo y del server) a la entrada y la salida
    para que los tests sean herméticos entre sí.
    """
    orig_anthropic = sem.Anthropic
    orig_key = os.environ.get("ANTHROPIC_API_KEY")
    try:
        sem.Anthropic = fake_cls
        if fake_cls is None:
            os.environ.pop("ANTHROPIC_API_KEY", None)
        else:
            os.environ["ANTHROPIC_API_KEY"] = "test-key-mock"
        sem.limpiar_cache()
        yield
    finally:
        sem.Anthropic = orig_anthropic
        if orig_key is None:
            os.environ.pop("ANTHROPIC_API_KEY", None)
        else:
            os.environ["ANTHROPIC_API_KEY"] = orig_key
        sem.limpiar_cache()


# ── Datos de prueba ─────────────────────────────

CODIGO_DEMO = (
    "funcion principal() retornar entero\n"
    "hacer\n"
    "    entero x <- \"hola\"\n"
    "    retornar 0\n"
    "fin_funcion\n"
)


def _error_demo():
    """Un ErrorSemantico TIPO_ASIGNACION con sugerencia local de partida."""
    return ErrorSemantico(
        indice=1, fila=3, columna=12, lexema='x',
        regla='TIPO_ASIGNACION',
        mensaje=("No se puede asignar un valor de tipo 'cadena' a una "
                 "variable de tipo 'entero'."),
        sugerencia="LOCAL_ORIG",
        fuente_sugerencia="local",
        contexto={'tipo_destino': 'entero', 'tipo_recibido': 'cadena',
                  'identificador': 'x'},
    )


# ══════════════════════════════════════════════
#  A) IA NO DISPONIBLE → None, local intacta
# ══════════════════════════════════════════════

def test_A_ia_no_disponible():
    e = _error_demo()
    with ia_mock(None):
        assert sem.disponible() is False, (
            "con Anthropic=None la IA debe reportarse como NO disponible"
        )
        out = sem.sugerencia_ia_semantica(e, CODIGO_DEMO)
        assert out is None, f"se esperaba None; obtuvo {out!r}"
    # La sugerencia local del error no se tocó.
    assert e.sugerencia == "LOCAL_ORIG"
    assert e.fuente_sugerencia == "local"
    print("  ✓ A) IA no disponible → None; sugerencia local intacta")


# ══════════════════════════════════════════════
#  B) IA DISPONIBLE → canned; reemplazo y fuente 'ia'
# ══════════════════════════════════════════════

def test_B_ia_disponible_canned():
    contador = _Contador()
    fake = _hacer_fake(contador, "SUG_IA_MOCK")
    e = _error_demo()
    with ia_mock(fake):
        assert sem.disponible() is True
        out = sem.sugerencia_ia_semantica(e, CODIGO_DEMO)
    assert out == "SUG_IA_MOCK", f"se esperaba la respuesta canned; obtuvo {out!r}"
    assert contador.n == 1, f"se esperaba 1 llamada a la API; hubo {contador.n}"

    # Aplicar la sugerencia (lo que hace el server): reemplaza y marca 'ia'.
    if out:
        e.sugerencia = out
        e.fuente_sugerencia = "ia"
    assert e.sugerencia == "SUG_IA_MOCK"
    assert e.fuente_sugerencia == "ia"
    print("  ✓ B) IA disponible → canned; error.sugerencia='ia' aplicada")


# ══════════════════════════════════════════════
#  C) CACHE → no llama dos veces a la API
# ══════════════════════════════════════════════

def test_C_cache():
    contador = _Contador()
    fake = _hacer_fake(contador, "CACHED")
    e = _error_demo()
    cache = {}
    with ia_mock(fake):
        o1 = sem.sugerencia_ia_semantica(e, CODIGO_DEMO, cache=cache)
        o2 = sem.sugerencia_ia_semantica(e, CODIGO_DEMO, cache=cache)
    assert o1 == o2 == "CACHED"
    assert contador.n == 1, (
        f"la 2ª llamada debía venir del cache; la API se llamó {contador.n} veces"
    )
    # La clave de cache es (regla, mensaje, lexema).
    assert (e.regla, e.mensaje, e.lexema) in cache
    print("  ✓ C) cache: 2 llamadas → 1 sola a la API (la 2ª cacheada)")


# ══════════════════════════════════════════════
#  D) ENDPOINT /parsear con el flag usar_ia_semantica
# ══════════════════════════════════════════════

def test_D_endpoint_sin_ia():
    import server
    server._CACHE_IA_SEMANTICA.clear()
    c = server.app.test_client()
    d = c.post('/parsear', json={'codigo': CODIGO_DEMO, 'metodo': 'recursivo',
                                 'usar_ia_semantica': False}).get_json()
    errs = d['errores_semanticos']
    assert len(errs) == 1, errs
    assert errs[0]['fuente_sugerencia'] == 'local', (
        f"sin IA, la fuente debe ser 'local'; obtuvo {errs[0]['fuente_sugerencia']}"
    )
    assert errs[0]['regla'] == 'TIPO_ASIGNACION'
    print("  ✓ D1) endpoint usar_ia_semantica=False → fuente='local' (E8 intacta)")


def test_D_endpoint_con_ia_mock():
    import server
    contador = _Contador()
    fake = _hacer_fake(contador, "IA_ENDPOINT_MOCK")
    server._CACHE_IA_SEMANTICA.clear()
    c = server.app.test_client()
    for metodo in ('recursivo', 'predictivo'):
        server._CACHE_IA_SEMANTICA.clear()
        with ia_mock(fake):
            d = c.post('/parsear', json={'codigo': CODIGO_DEMO, 'metodo': metodo,
                                         'usar_ia_semantica': True}).get_json()
        errs = d['errores_semanticos']
        assert len(errs) == 1, errs
        assert errs[0]['fuente_sugerencia'] == 'ia', (
            f"[{metodo}] con IA mockeada la fuente debe ser 'ia'; "
            f"obtuvo {errs[0]['fuente_sugerencia']}"
        )
        assert errs[0]['sugerencia'] == "IA_ENDPOINT_MOCK", errs[0]
        print(f"  ✓ D2) [{metodo}] endpoint usar_ia_semantica=True → "
              f"sugerencia enriquecida, fuente='ia'")
    assert contador.n >= 1


# ══════════════════════════════════════════════
#  RUNNER
# ══════════════════════════════════════════════

def main() -> int:
    print("── A) IA no disponible ──")
    test_A_ia_no_disponible()
    print("\n── B) IA disponible (canned) ──")
    test_B_ia_disponible_canned()
    print("\n── C) cache ──")
    test_C_cache()
    print("\n── D) endpoint /parsear ──")
    test_D_endpoint_sin_ia()
    test_D_endpoint_con_ia_mock()
    print("\n✓ Todos los tests de la Etapa 9 (bonus IA) pasaron.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
