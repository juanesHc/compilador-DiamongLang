"""
╔══════════════════════════════════════════════════════════╗
║   DiamondLang 💎 — Tests Fase 5b (chatbot + Gemini)      ║
║                 test_etapa11_chat.py                     ║
║                                                         ║
║  Ejecutable directo (sin pytest ni RED real):           ║
║      python test_etapa11_chat.py                        ║
║                                                         ║
║  Mockea los SDK (cliente_gemini / cliente_anthropic) con ║
║  monkeypatch, así que NO hace llamadas reales a las APIs. ║
║  Cubre:                                                  ║
║    · /ping_chat (disponibilidad por modelo)             ║
║    · /chat (dispatch Claude/Gemini, error si no disp.)  ║
║    · Migración de sugerencias sintácticas a Gemini:     ║
║         no-disponible → local · mock → 'ia' · caché     ║
║                                                         ║
║  NOTA: regenerado a partir del código real (el original  ║
║  se perdió; la copia de respaldo era anterior a 5b).     ║
╚══════════════════════════════════════════════════════════╝
"""

import sys
import contextlib

import server
import cliente_gemini
import cliente_anthropic
import sugerencias_ia


_PASS = 0
_FAIL = 0


def check(nombre, cond, extra=''):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ✓ {nombre}")
    else:
        _FAIL += 1
        print(f"  ✗ {nombre}   {extra}")


# ── Mock de un cliente (gemini/anthropic): disponibilidad + respuesta canned,
#    contando cuántas veces se invoca el "SDK" (para verificar la caché). ──
class _Contador:
    def __init__(self):
        self.n = 0


@contextlib.contextmanager
def mock_cliente(modulo, disponible, respuesta="[IA] sugerencia de prueba"):
    """Parchea modulo.disponible() y modulo.responder() temporalmente."""
    orig_disp = modulo.disponible
    orig_resp = modulo.responder
    cont = _Contador()

    def fake_responder(prompt, system=None, timeout=None, cache=None):
        cont.n += 1
        return respuesta if disponible else None

    modulo.disponible = (lambda: disponible)
    modulo.responder = fake_responder
    try:
        yield cont
    finally:
        modulo.disponible = orig_disp
        modulo.responder = orig_resp


# Programa con UN error sintáctico (falta 'entonces').
PROG_SINT_MAL = ("funcion principal()\nhacer\n    si 1 > 0\n"
                 "        escribir(1)\n    fin_si\nfin_funcion")


# ══════════════════════════════════════════════
#  A) /ping_chat — disponibilidad por modelo
# ══════════════════════════════════════════════
def test_ping_chat():
    print("\n── A) /ping_chat ──")
    c = server.app.test_client()
    with mock_cliente(cliente_anthropic, True), mock_cliente(cliente_gemini, True):
        d = c.get('/ping_chat').get_json()
        check("ambos disponibles → claude_disponible y gemini_disponible True",
              d.get('claude_disponible') is True and d.get('gemini_disponible') is True)
        check("modelos incluye ambas etiquetas",
              'Claude Haiku' in d.get('modelos', []) and 'Gemini Flash' in d.get('modelos', []))
    with mock_cliente(cliente_anthropic, True), mock_cliente(cliente_gemini, False):
        d = c.get('/ping_chat').get_json()
        check("solo Claude → gemini_disponible False",
              d.get('claude_disponible') is True and d.get('gemini_disponible') is False)


# ══════════════════════════════════════════════
#  B) /chat — dispatch y errores
# ══════════════════════════════════════════════
def test_chat():
    print("\n── B) /chat ──")
    c = server.app.test_client()

    with mock_cliente(cliente_gemini, True, respuesta="Hola desde Gemini"):
        d = c.post('/chat', json={"mensaje": "hola", "modelo": "gemini", "historial": []}).get_json()
        check("chat gemini (mock) → respuesta canned, error None",
              d.get('respuesta') == "Hola desde Gemini" and not d.get('error'))
        check("chat gemini → modelo_usado='Gemini Flash'", d.get('modelo_usado') == 'Gemini Flash')

    with mock_cliente(cliente_anthropic, True, respuesta="Hola desde Claude"):
        d = c.post('/chat', json={"mensaje": "hola", "modelo": "claude", "historial": []}).get_json()
        check("chat claude (mock) → respuesta canned", d.get('respuesta') == "Hola desde Claude")

    with mock_cliente(cliente_gemini, False):
        d = c.post('/chat', json={"mensaje": "hola", "modelo": "gemini", "historial": []}).get_json()
        check("chat gemini NO disponible → error no nulo", bool(d.get('error')))


# ══════════════════════════════════════════════
#  C) Migración de sugerencias SINTÁCTICAS a Gemini
# ══════════════════════════════════════════════
def test_ia_sintactica_gemini():
    print("\n── C) Sugerencias sintácticas (migradas a Gemini) ──")
    c = server.app.test_client()

    # h) info() reporta el modelo Gemini Flash.
    check("info()['modelo'] == 'Gemini Flash'",
          sugerencias_ia.info().get('modelo') == 'Gemini Flash')

    # g) Gemini NO disponible → las sugerencias quedan locales (fuente != 'ia').
    sugerencias_ia.limpiar_cache()
    with mock_cliente(cliente_gemini, False):
        d = c.post('/parsear', json={"codigo": PROG_SINT_MAL, "metodo": "recursivo", "usar_ia": True}).get_json()
        errs = d.get('errores', [])
        check("Gemini no disponible → fuente_sugerencia='local' y sugerencia presente",
              len(errs) >= 1 and all(e.get('fuente_sugerencia') == 'local' for e in errs)
              and all(e.get('sugerencia') for e in errs))

    # h+j) Gemini mock → la sugerencia viene de IA (fuente='ia') con el texto canned.
    for metodo in ('recursivo', 'predictivo'):
        sugerencias_ia.limpiar_cache()
        with mock_cliente(cliente_gemini, True, respuesta="SUGERENCIA-GEMINI"):
            d = c.post('/parsear', json={"codigo": PROG_SINT_MAL, "metodo": metodo, "usar_ia": True}).get_json()
            errs = d.get('errores', [])
            con_ia = [e for e in errs if e.get('fuente_sugerencia') == 'ia']
            check(f"[{metodo}] usar_ia=True + Gemini mock → fuente='ia', texto canned",
                  len(con_ia) >= 1 and con_ia[0].get('sugerencia') == "SUGERENCIA-GEMINI",
                  extra=str(errs))

    # i) Caché: dos análisis idénticos → el SDK se llama UNA sola vez.
    sugerencias_ia.limpiar_cache()
    with mock_cliente(cliente_gemini, True, respuesta="CACHED") as cont:
        c.post('/parsear', json={"codigo": PROG_SINT_MAL, "metodo": "recursivo", "usar_ia": True})
        c.post('/parsear', json={"codigo": PROG_SINT_MAL, "metodo": "recursivo", "usar_ia": True})
        check("dos análisis idénticos → 1 sola llamada al SDK (caché)", cont.n == 1,
              extra=f"llamadas={cont.n}")


# ══════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════
if __name__ == '__main__':
    print("═" * 60)
    print("  💎 Tests Fase 5b — Chatbot + Gemini (mockeado)")
    print("═" * 60)

    test_ping_chat()
    test_chat()
    test_ia_sintactica_gemini()

    print("\n" + "═" * 60)
    print(f"  Resultado: {_PASS} ✓   {_FAIL} ✗")
    print("═" * 60)
    if _FAIL == 0:
        print("✓ Todos los tests de la Fase 5b (chatbot + Gemini) pasaron.")
        sys.exit(0)
    else:
        print("✗ Hubo fallos en la Fase 5b.")
        sys.exit(1)
