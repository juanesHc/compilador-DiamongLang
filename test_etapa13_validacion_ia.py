"""
╔══════════════════════════════════════════════════════════╗
║   DiamondLang 💎 — Tests Fase D (bonus IA: /validar_julia)║
║                test_etapa13_validacion_ia.py             ║
║                                                         ║
║  Ejecutable directo (sin pytest ni RED real):           ║
║      python test_etapa13_validacion_ia.py               ║
║                                                         ║
║  Mockea cliente_anthropic con monkeypatch, así que NO    ║
║  hace llamadas reales a la API de Claude. Cubre el       ║
║  endpoint POST /validar_julia (Entrega Final, Modalidad  ║
║  C: validación + optimización del Julia generado):       ║
║    · Claude responde JSON válido → parseo estructurado.  ║
║    · Claude responde JSON sin cercas ```json → fallback.  ║
║    · Claude responde texto sin JSON → campo "raw".       ║
║    · Claude no disponible → ok=false con explicación.    ║
║    · request sin "julia" → HTTP 400.                     ║
╚══════════════════════════════════════════════════════════╝
"""

import sys
import contextlib

import server
import cliente_anthropic


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


@contextlib.contextmanager
def mock_anthropic(disponible, respuesta="(sin respuesta)"):
    """Parchea cliente_anthropic.disponible()/responder() temporalmente.
    `respuesta` es el texto crudo que devolvería Claude (o None si no disp.)."""
    orig_disp = cliente_anthropic.disponible
    orig_resp = cliente_anthropic.responder

    def fake_responder(prompt, system=None, timeout=None, cache=None, max_tokens=None):
        return respuesta if disponible else None

    cliente_anthropic.disponible = (lambda: disponible)
    cliente_anthropic.responder  = fake_responder
    try:
        yield
    finally:
        cliente_anthropic.disponible = orig_disp
        cliente_anthropic.responder  = orig_resp


# Un Julia plausible (el factorial que genera el SDT). El contenido exacto no
# importa para los tests: la respuesta de Claude está mockeada.
JULIA_FACTORIAL = """function factorial(n::Int64)::Int64
    if n <= 1
        return 1
    else
        return n * factorial(n - 1)
    end
end"""

# Respuesta "buena" de Claude: bloque ```json bien formado.
RESP_JSON_OK = """Aquí tienes el análisis:

```json
{
  "validacion": "El código es sintácticamente correcto y los tipos son coherentes.",
  "problemas_encontrados": [],
  "optimizaciones": [
    "Podrías reaprovechar Base.factorial de la stdlib.",
    "Considera tipos paramétricos para mayor flexibilidad."
  ]
}
```
Espero que ayude."""

# Respuesta con JSON pero SIN cercas ```json (fallback al primer {...}).
RESP_JSON_SIN_CERCAS = (
    '{"validacion": "Correcto.", "problemas_encontrados": ["Uno"], '
    '"optimizaciones": ["Otra"]}'
)

# Respuesta SIN JSON ninguno (texto libre) → debe caer al campo "raw".
RESP_SIN_JSON = "El código se ve bien, no tengo formato estructurado para darte."


# ══════════════════════════════════════════════
#  A) Claude responde JSON válido → parseo estructurado
# ══════════════════════════════════════════════
def test_json_valido():
    print("\n── A) /validar_julia con JSON válido ──")
    c = server.app.test_client()
    with mock_anthropic(True, respuesta=RESP_JSON_OK):
        d = c.post('/validar_julia', json={"julia": JULIA_FACTORIAL}).get_json()
    check("ok=True", d.get('ok') is True, extra=str(d))
    check("modelo == 'Claude Haiku'", d.get('modelo') == 'Claude Haiku')
    check("validacion parseada del JSON",
          d.get('validacion', '').startswith('El código es sintácticamente'))
    check("problemas_encontrados vacío", d.get('problemas_encontrados') == [])
    check("optimizaciones: 2 sugerencias",
          isinstance(d.get('optimizaciones'), list) and len(d['optimizaciones']) == 2,
          extra=str(d.get('optimizaciones')))
    check("optimizacion menciona Base.factorial",
          any('Base.factorial' in o for o in d.get('optimizaciones', [])))
    check("raw incluye la respuesta cruda", 'json' in (d.get('raw') or ''))


# ══════════════════════════════════════════════
#  B) JSON sin cercas ```json → fallback al primer {...}
# ══════════════════════════════════════════════
def test_json_sin_cercas():
    print("\n── B) /validar_julia con JSON sin cercas ──")
    c = server.app.test_client()
    with mock_anthropic(True, respuesta=RESP_JSON_SIN_CERCAS):
        d = c.post('/validar_julia', json={"julia": JULIA_FACTORIAL}).get_json()
    check("ok=True (fallback parseó el {...})", d.get('ok') is True, extra=str(d))
    check("validacion == 'Correcto.'", d.get('validacion') == 'Correcto.')
    check("problemas_encontrados == ['Uno']", d.get('problemas_encontrados') == ['Uno'])
    check("optimizaciones == ['Otra']", d.get('optimizaciones') == ['Otra'])


# ══════════════════════════════════════════════
#  C) Texto sin JSON → graceful con campo "raw"
# ══════════════════════════════════════════════
def test_texto_sin_json():
    print("\n── C) /validar_julia con texto sin JSON ──")
    c = server.app.test_client()
    with mock_anthropic(True, respuesta=RESP_SIN_JSON):
        d = c.post('/validar_julia', json={"julia": JULIA_FACTORIAL}).get_json()
    check("ok=True (no es error, se degrada con gracia)", d.get('ok') is True, extra=str(d))
    check("raw contiene el texto crudo", d.get('raw') == RESP_SIN_JSON)
    check("problemas/optimizaciones vacíos",
          d.get('problemas_encontrados') == [] and d.get('optimizaciones') == [])
    check("validacion explica que no se pudo estructurar",
          'estructurar' in (d.get('validacion') or '').lower())


# ══════════════════════════════════════════════
#  D) Claude NO disponible → ok=false con explicación
# ══════════════════════════════════════════════
def test_no_disponible():
    print("\n── D) /validar_julia con Claude no disponible ──")
    c = server.app.test_client()
    with mock_anthropic(False):
        d = c.post('/validar_julia', json={"julia": JULIA_FACTORIAL}).get_json()
    check("ok=False", d.get('ok') is False, extra=str(d))
    check("error menciona ANTHROPIC_API_KEY",
          'ANTHROPIC_API_KEY' in (d.get('error') or ''))


# ══════════════════════════════════════════════
#  E) request sin "julia" → HTTP 400
# ══════════════════════════════════════════════
def test_sin_julia():
    print("\n── E) /validar_julia sin campo julia ──")
    c = server.app.test_client()
    # No hace falta mockear: el guardia de body corre antes de tocar la IA.
    r = c.post('/validar_julia', json={})
    check("HTTP 400 cuando falta julia", r.status_code == 400, extra=f"status={r.status_code}")
    check("ok=False en el body", r.get_json().get('ok') is False)

    r2 = c.post('/validar_julia', json={"julia": "   "})
    check("HTTP 400 cuando julia está en blanco", r2.status_code == 400,
          extra=f"status={r2.status_code}")


# ══════════════════════════════════════════════
#  F) Claude devuelve None (timeout/fallo) aunque esté disponible
# ══════════════════════════════════════════════
def test_respuesta_none():
    print("\n── F) /validar_julia con respuesta None (timeout) ──")
    c = server.app.test_client()
    with mock_anthropic(True, respuesta=None):
        d = c.post('/validar_julia', json={"julia": JULIA_FACTORIAL}).get_json()
    check("ok=False cuando Claude no devuelve nada", d.get('ok') is False, extra=str(d))
    check("error menciona timeout/fallo",
          'timeout' in (d.get('error') or '').lower() or 'fallo' in (d.get('error') or '').lower())


# ══════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════
if __name__ == '__main__':
    print("═" * 60)
    print("  💎 Tests Fase D — Bonus IA /validar_julia (mockeado)")
    print("═" * 60)

    test_json_valido()
    test_json_sin_cercas()
    test_texto_sin_json()
    test_no_disponible()
    test_sin_julia()
    test_respuesta_none()

    print("\n" + "═" * 60)
    print(f"  Resultado: {_PASS} ✓   {_FAIL} ✗")
    print("═" * 60)
    if _FAIL == 0:
        print("✓ Todos los tests de la Fase D (bonus IA) pasaron.")
        sys.exit(0)
    else:
        print("✗ Hubo fallos en la Fase D.")
        sys.exit(1)
