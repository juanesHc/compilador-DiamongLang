"""
╔══════════════════════════════════════════════════════════╗
║    DiamondLang 💎 — Servidor Flask (Entrega Final)      ║
║                    server.py                            ║
║                                                         ║
║  Rutas disponibles:                                     ║
║    GET  /ping          → estado del servidor            ║
║    GET  /ping_ia       → diagnóstico del bonus IA       ║
║    POST /analizar      → análisis léxico (Entrega 1)    ║
║    POST /parsear       → análisis sintáctico con        ║
║                          recuperación de errores        ║
║    GET  /tabla_ll      → tabla LL(1) + PRIMERO/SIGUIENTE║
║    GET  /ejemplos_semanticos → catálogo de .dml para    ║
║                          el selector del frontend (E10) ║
║    GET  /ping_chat     → disponibilidad de modelos chat ║
║    POST /chat          → asistente multi-modelo (5b)    ║
║    POST /traducir      → SDT → Julia (Entrega Final)    ║
║    POST /validar_julia → bonus IA: valida/optimiza el   ║
║                          Julia generado (Modalidad C)   ║
╚══════════════════════════════════════════════════════════╝
"""

import json
import re
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from lexico.lexer import Lexer
from sintactico.parser_recursivo import ParserRecursivo
from sintactico.parser_predictivo import ParserPredictivo
from semantico.semantico import AnalizadorSemantico
from sintactico.tabla_ll import (generar_tabla, tabla_a_dict_serializable,
                               sets_a_dict_serializable, NO_TERMINALES, GRAMATICA)
# Al importar sugerencias_ia se carga automáticamente el archivo
# .env de la raíz del proyecto (con ruta absoluta, sin importar CWD).
from ai.sugerencias_ia import sugerencia_ia, info as info_ia, disponible as ia_disponible
# Bonus Etapa 9: IA sobre errores SEMÁNTICOS (Modalidad A).
from ai.sugerencias_ia_semantica import (
    sugerencia_ia_semantica,
    info       as info_ia_sem,
    disponible as ia_sem_disponible,
)
# Fase 5b: clientes genéricos para el chatbot multi-modelo (/chat, /ping_chat).
# Claude (Anthropic) y Gemini (Google), simétricos. Importación perezosa del
# SDK dentro de cada módulo: el server arranca aunque falte alguna librería.
from ai import cliente_anthropic
from ai import cliente_gemini

from traduccion import sdt
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────────
#  Frontend estático: la app (HTML/CSS/JS) vive en frontend/ y se sirve
#  desde el mismo origen que la API. Así un único servicio web (local o
#  Render) entrega UI + API juntos, sin URLs hardcodeadas ni CORS.
# ─────────────────────────────────────────────
_FRONTEND_DIR = Path(__file__).resolve().parent / 'frontend'

@app.route('/', methods=['GET'])
def index():
    return send_from_directory(_FRONTEND_DIR, 'diamondlang.html')

@app.route('/style.css', methods=['GET'])
def _frontend_css():
    return send_from_directory(_FRONTEND_DIR, 'style.css')

@app.route('/script.js', methods=['GET'])
def _frontend_js():
    return send_from_directory(_FRONTEND_DIR, 'script.js')

# Cache en memoria de las sugerencias IA semánticas, VIVO entre peticiones.
# Decisión: un dict de módulo (no por-request) para que, dentro de una
# misma sesión del servidor, dos análisis con el mismo error
# (regla, mensaje, lexema) reusen la respuesta de Claude y ahorren red.
_CACHE_IA_SEMANTICA: dict = {}

# Pre-generar la tabla al arrancar (evita latencia en la primera llamada)
print("💎 Generando tabla LL(1)...")
_PRIMERO, _SIGUIENTE, _TABLA_LL = generar_tabla()
print(f"   Tabla lista: {len(_TABLA_LL)} entradas, {len(NO_TERMINALES)} no-terminales")
print(f"   Bonus IA (sintáctica): {'disponible' if ia_disponible() else 'no disponible (sin API key o sin librería)'} [Gemini]")
print(f"   Bonus IA (semántica):  {'disponible' if ia_sem_disponible() else 'no disponible (sin API key o sin librería)'} [Claude]")
print(f"   Chatbot — Claude: {'sí' if cliente_anthropic.disponible() else 'no'} · "
      f"Gemini: {'sí' if cliente_gemini.disponible() else 'no'}")

# ── Chatbot (Fase 5b): system prompt + helpers compartidos ──
SYSTEM_CHAT = (
    "Eres un asistente para el compilador DiamondLang, un lenguaje imperativo "
    "en español con tipado estático. Responde de forma concisa, en español, "
    "ayudando al usuario con preguntas sobre su código o el compilador.\n\n"
    "SINTAXIS DE DiamondLang (respétala SIEMPRE al dar ejemplos de código):\n"
    "- Funciones: `funcion nombre(tipo param, ...) retornar tipo` (el `retornar tipo` "
    "es opcional), cuerpo entre `hacer` y `fin_funcion`.\n"
    "- Tipos: entero, real, cadena, booleano, vacio.\n"
    "- Declaración + asignación con `<-`:  `entero x <- 10`. Reasignación: `x <- x + 1`.\n"
    "- Condicional: `si EXPR entonces ... sino ... fin_si` (el `sino` es opcional).\n"
    "- Bucles: `mientras EXPR hacer ... fin_mientras` y `para ... fin_para`.\n"
    "- Retorno: `retornar EXPR`. Entrada/salida: `escribir(EXPR)`, `leer(var)`.\n"
    "- Booleanos: `verdadero`/`falso`; operadores lógicos `y`, `o`, `no`; "
    "comparación `<`, `<=`, `>`, `>=`, `==`, `!=`.\n"
    "- Comentarios de línea con `//`. NO se usan `;` ni llaves `{}`.\n\n"
    "Ejemplo COMPLETO y válido (úsalo como referencia de estilo):\n"
    "funcion factorial(entero n) retornar entero\n"
    "hacer\n"
    "    si n <= 1 entonces\n"
    "        retornar 1\n"
    "    sino\n"
    "        retornar n * factorial(n - 1)\n"
    "    fin_si\n"
    "fin_funcion\n\n"
    "Cuando generes código, devuélvelo siempre con esta sintaxis exacta; no "
    "inventes palabras clave en inglés ni símbolos que no estén arriba."
)
# Modelo → (cliente, etiqueta legible que ve el frontend).
_CHAT_CLIENTES = {
    'claude': (cliente_anthropic, 'Claude Haiku'),
    'gemini': (cliente_gemini,    'Gemini Flash'),
}
# Variable de entorno que el usuario debe definir por modelo (para el mensaje
# de error cuando no está disponible).
_CHAT_ENV = {'claude': 'ANTHROPIC_API_KEY', 'gemini': 'GOOGLE_API_KEY'}
_CHAT_MAX_HISTORIAL = 10


def _construir_prompt_chat(mensaje: str, historial) -> str:
    """
    Aplana los últimos N mensajes del historial + el mensaje nuevo en un
    transcript de texto. El system message va aparte (SYSTEM_CHAT).

    `historial` es una lista de {role:'user'|'assistant', text:str} que el
    frontend envía SIN el mensaje nuevo (ese llega en `mensaje`).
    """
    lineas = []
    if isinstance(historial, list):
        for m in historial[-_CHAT_MAX_HISTORIAL:]:
            if not isinstance(m, dict):
                continue
            texto = (m.get('text') or '').strip()
            if not texto:
                continue
            etiqueta = 'Usuario' if m.get('role') == 'user' else 'Asistente'
            lineas.append(f"{etiqueta}: {texto}")
    lineas.append(f"Usuario: {mensaje}")
    lineas.append("Asistente:")
    return "\n".join(lineas)


# ══════════════════════════════════════════════
#  RUTA: PING
# ══════════════════════════════════════════════
@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({'estado': 'DiamondLang server activo 💎 (Entrega Final)'})


@app.route('/ping_ia', methods=['GET'])
def ping_ia():
    """Diagnóstico del bonus IA — usado por el frontend para mostrar/ocultar el checkbox."""
    return jsonify(info_ia())


@app.route('/ping_ia_semantica', methods=['GET'])
def ping_ia_semantica():
    """Diagnóstico del bonus IA SEMÁNTICA (Etapa 9) — el frontend lo usa
    para habilitar/deshabilitar el checkbox 'Usar IA en errores semánticos'."""
    return jsonify(info_ia_sem())


# ══════════════════════════════════════════════
#  RUTA: PING CHATBOT (Fase 5b)
# ══════════════════════════════════════════════
@app.route('/ping_chat', methods=['GET'])
def ping_chat():
    """
    Disponibilidad de cada modelo del chatbot, según las API keys/librerías
    configuradas. El frontend lo usa para atenuar las pills no disponibles.
    """
    claude_ok = cliente_anthropic.disponible()
    gemini_ok = cliente_gemini.disponible()
    modelos = []
    if claude_ok:
        modelos.append('Claude Haiku')
    if gemini_ok:
        modelos.append('Gemini Flash')
    return jsonify({
        'claude_disponible': claude_ok,
        'gemini_disponible': gemini_ok,
        'modelos':           modelos,
    })


# ══════════════════════════════════════════════
#  RUTA: CHAT (Fase 5b)
# ══════════════════════════════════════════════
@app.route('/chat', methods=['POST'])
def chat():
    """
    Recibe:
        {
          "mensaje":   str,                 # mensaje del usuario (obligatorio)
          "modelo":    "claude" | "gemini", # default "claude"
          "historial": [ {"role": "...", "text": "..."}, ... ]  # opcional
        }
    Devuelve (siempre HTTP 200 salvo body inválido):
        { "respuesta": str, "modelo_usado": str, "error": null|str }

    Dispatch a Claude o Gemini según `modelo`. Si el modelo pedido no tiene
    su API key, devuelve un error claro (sin reventar). Errores capturados.
    """
    datos = request.get_json(silent=True) or {}
    mensaje = (datos.get('mensaje') or '').strip()
    modelo  = (datos.get('modelo') or 'claude').lower()
    historial = datos.get('historial', [])

    if not mensaje:
        return jsonify({'respuesta': '', 'modelo_usado': '',
                        'error': 'El campo "mensaje" es obligatorio.'}), 400
    if modelo not in _CHAT_CLIENTES:
        return jsonify({'respuesta': '', 'modelo_usado': '',
                        'error': f'Modelo desconocido: {modelo!r} '
                                 '(usa "claude" o "gemini").'}), 400

    cliente, etiqueta = _CHAT_CLIENTES[modelo]

    # Modelo seleccionado sin API key / librería → error claro, no excepción.
    if not cliente.disponible():
        return jsonify({
            'respuesta': '',
            'modelo_usado': etiqueta,
            'error': f"Modelo '{modelo}' no disponible: "
                     f"define {_CHAT_ENV[modelo]} en el servidor.",
        })

    prompt = _construir_prompt_chat(mensaje, historial)
    try:
        respuesta = cliente.responder(prompt, system=SYSTEM_CHAT, timeout=15.0)
    except Exception as e:  # red defensiva: el cliente ya captura, por si acaso
        print(f"[chat:{modelo}] {type(e).__name__}: {e}")
        respuesta = None

    if not respuesta:
        return jsonify({
            'respuesta': '',
            'modelo_usado': etiqueta,
            'error': f'{etiqueta} no devolvió respuesta (timeout o fallo de API).',
        })

    return jsonify({
        'respuesta':    respuesta,
        'modelo_usado': etiqueta,
        'error':        None,
    })


# ══════════════════════════════════════════════
#  RUTA: ANÁLISIS LÉXICO (Entrega 1, sin cambios)
# ══════════════════════════════════════════════
@app.route('/analizar', methods=['POST'])
def analizar():
    datos = request.get_json()
    if not datos or 'codigo' not in datos:
        return jsonify({'error': 'Se esperaba { "codigo": "..." }'}), 400

    lexer = Lexer(datos['codigo'])
    tokens, errores = lexer.tokenizar()

    tokens_json = [
        {'lexema': t.lexema, 'tipo': t.tipo, 'linea': t.linea, 'columna': t.columna}
        for t in tokens
    ]
    estadisticas = {'total': len(tokens)}
    for t in tokens:
        estadisticas[t.tipo] = estadisticas.get(t.tipo, 0) + 1

    return jsonify({'tokens': tokens_json, 'errores': errores, 'estadisticas': estadisticas})


# ══════════════════════════════════════════════
#  RUTA: ANÁLISIS SINTÁCTICO (Entrega 3)
# ══════════════════════════════════════════════
@app.route('/parsear', methods=['POST'])
def parsear():
    """
    Recibe:
        {
          "codigo":            "...",
          "metodo":            "recursivo" | "predictivo",
          "usar_ia":           bool  (opcional, default false) — IA sobre
                                     errores SINTÁCTICOS,
          "usar_ia_semantica": bool  (opcional, default false) — IA sobre
                                     errores SEMÁNTICOS (Etapa 9),
          "max_errores":       int   (opcional, default 100)
        }

    Devuelve:
        {
          "valido":             bool,     # = valido_sintactico (E3, intacto)
          "errores":            [ErrorSintactico, ...],
          "error":              str|null, # COMPATIBILIDAD: primer error
          "nodos":              {...},
          "traza":              [...]     # solo predictivo
          "metodo":             "recursivo"|"predictivo",
          # ── Análisis semántico (Etapa 8) ──
          "valido_semantico":   bool,
          "errores_semanticos": [ErrorSemantico, ...],
          "simbolos":           [Simbolo, ...]
        }

    El campo 'valido' conserva su semántica de E3 (validez SINTÁCTICA);
    'valido_semantico' es independiente. La fase semántica corre incluso
    con errores sintácticos (decisión F.11): el visitor salta los
    sub-árboles marcados con es_error=True y reporta lo que pueda.
    """
    datos = request.get_json()
    if not datos or 'codigo' not in datos:
        return jsonify({'error': 'Se esperaba { "codigo": "...", "metodo": "..." }'}), 400

    codigo             = datos.get('codigo', '')
    metodo             = datos.get('metodo', 'recursivo')
    usar_ia            = bool(datos.get('usar_ia', False))
    usar_ia_semantica  = bool(datos.get('usar_ia_semantica', False))
    max_errores        = int(datos.get('max_errores', 100))

    if metodo == 'recursivo':
        parser    = ParserRecursivo(codigo, max_errores=max_errores)
        resultado = parser.analizar()
        resultado['metodo'] = 'recursivo'

    elif metodo == 'predictivo':
        parser    = ParserPredictivo(codigo, max_errores=max_errores)
        resultado = parser.analizar()
        resultado['metodo'] = 'predictivo'
        # La tabla y los conjuntos viajan por /tabla_ll, no en cada parse
        resultado.pop('tabla_ll',  None)
        resultado.pop('primero',   None)
        resultado.pop('siguiente', None)

    else:
        return jsonify({'error': f'Método desconocido: {metodo}'}), 400

    # ── Análisis semántico (Etapa 8) ──
    # Corre SIEMPRE que haya un árbol (incluso con errores sintácticos:
    # el AnalizadorSemantico salta los sub-árboles con es_error=True,
    # decisión F.11). No combinamos su veredicto con 'valido' (= validez
    # sintáctica de E3): exponemos 'valido_semantico' como campo aparte.
    arbol_raiz = getattr(parser, 'arbol_raiz', None)
    if arbol_raiz is not None:
        analizador          = AnalizadorSemantico(arbol_raiz, max_errores=max_errores)
        resultado_semantico = analizador.analizar()
        resultado['errores_semanticos'] = resultado_semantico['errores_semanticos']
        resultado['valido_semantico']   = resultado_semantico['valido_semantico']
        resultado['simbolos']           = resultado_semantico['simbolos']
    else:
        # Caso extremo: el parser no produjo árbol. No hay nada que analizar.
        analizador = None
        resultado['errores_semanticos'] = []
        resultado['valido_semantico']   = True
        resultado['simbolos']           = []

    # ── Bonus IA: enriquecer las sugerencias SINTÁCTICAS ──
    if usar_ia and ia_disponible() and resultado.get('errores'):
        _enriquecer_con_ia(resultado, codigo, parser)

    # ── Bonus IA (Etapa 9): enriquecer las sugerencias SEMÁNTICAS ──
    if (usar_ia_semantica and ia_sem_disponible() and analizador is not None
            and resultado['errores_semanticos']):
        _enriquecer_semantico_con_ia(resultado, codigo, analizador)

    return jsonify(resultado)


def _enriquecer_semantico_con_ia(resultado, codigo_fuente, analizador):
    """
    Recorre los errores semánticos y reemplaza la sugerencia local por una
    versión enriquecida por Claude. Si la API falla para un error, deja la
    sugerencia local intacta (fallback). Usa el caché de módulo vivo entre
    peticiones (`_CACHE_IA_SEMANTICA`).

    `analizador.errores` tiene los objetos ErrorSemantico originales;
    `resultado['errores_semanticos']` tiene los dicts ya serializados, en
    el MISMO orden (ambos provienen de `self.errores`). Se recorren en
    paralelo, igual que la versión sintáctica.
    """
    for err_obj, err_dict in zip(analizador.errores,
                                 resultado['errores_semanticos']):
        try:
            mejorada = sugerencia_ia_semantica(err_obj, codigo_fuente,
                                                cache=_CACHE_IA_SEMANTICA)
        except Exception as e:
            print(f"[IA-semántica] error procesando #{err_obj.indice}: {e}")
            mejorada = None
        if mejorada:
            err_dict['sugerencia']        = mejorada
            err_dict['fuente_sugerencia'] = 'ia'


def _enriquecer_con_ia(resultado, codigo_fuente, parser):
    """
    Recorre la lista de errores y reemplaza la sugerencia local por
    una versión enriquecida por Claude. Si falla la API por cualquier
    razón, deja la sugerencia local intacta.
    """
    # `parser.errores` tiene los objetos ErrorSintactico originales.
    # `resultado['errores']` tiene dicts ya serializados.
    for err_obj, err_dict in zip(parser.errores, resultado['errores']):
        try:
            mejorada = sugerencia_ia(err_obj, codigo_fuente)
        except Exception as e:
            print(f"[IA] error procesando error #{err_obj.indice}: {e}")
            mejorada = None
        if mejorada:
            err_dict['sugerencia']        = mejorada
            err_dict['fuente_sugerencia'] = 'ia'


# ══════════════════════════════════════════════
#  RUTA: TABLA LL(1)
# ══════════════════════════════════════════════
@app.route('/tabla_ll', methods=['GET'])
def tabla_ll():
    """
    Devuelve la tabla LL(1) completa junto con los
    conjuntos PRIMERO y SIGUIENTE de cada no-terminal.
    """
    return jsonify({
        'tabla':      tabla_a_dict_serializable(_TABLA_LL),
        'primero':    sets_a_dict_serializable(_PRIMERO),
        'siguiente':  sets_a_dict_serializable(_SIGUIENTE),
        'no_terminales': sorted(list(NO_TERMINALES)),
        'terminales': sorted(list({t for (_, t) in _TABLA_LL.keys()})),
    })


# ══════════════════════════════════════════════
#  RUTA: EJEMPLOS DE ERRORES SEMÁNTICOS (Etapa 10)
# ══════════════════════════════════════════════
# Carpeta absoluta resuelta una sola vez (no depende del CWD del proceso).
_EJEMPLOS_SEM_DIR = Path(__file__).resolve().parent / 'ejemplos_semanticos'

# Mapeo nombre_archivo → (titulo legible, regla, grupo).
# El campo "regla" se alinea con los códigos que emite el analizador
# semántico; el campo "grupo" es el header visible en el <optgroup> del
# frontend. Los casos válidos ("_ok" o INVALIDO/VALIDO en el comentario)
# se marcan con "(válido)" para que la demo deje claro que no producen
# error semántico.
_GRUPO_R1 = 'Regla 1 — Declaración duplicada'
_GRUPO_R2 = 'Regla 2 — Uso no declarado'
_GRUPO_R3 = 'Regla 3 — Tipos en asignación'
_GRUPO_R4 = 'Regla 4 — Condición booleana'
_GRUPO_R5 = 'Regla 5 — Llamadas a función'

_MAPEO_EJEMPLOS_SEM = {
    '01_decl_duplicada_variable.dml':
        ('Declaración duplicada (variable)',          'DECL_DUPLICADA',         _GRUPO_R1),
    '02_decl_duplicada_parametro.dml':
        ('Declaración duplicada (parámetro)',         'DECL_DUPLICADA',         _GRUPO_R1),
    '03_uso_variable_no_declarada.dml':
        ('Uso de variable no declarada',              'USO_NO_DECLARADO',       _GRUPO_R2),
    '04_llamada_funcion_no_declarada.dml':
        ('Llamada a función no declarada',            'USO_NO_DECLARADO',       _GRUPO_R2),
    '05_tipo_asignacion_decl.dml':
        ('Tipo incompatible en declaración',          'TIPO_ASIGNACION',        _GRUPO_R3),
    '06_tipo_asignacion_reasignacion.dml':
        ('Tipo incompatible en reasignación',         'TIPO_ASIGNACION',        _GRUPO_R3),
    '07_tipo_void_en_variable.dml':
        ('Asignar resultado vacío a variable',        'TIPO_VOID_EN_VARIABLE',  _GRUPO_R3),
    '08_tipo_promocion_ok.dml':
        ('Promoción entero → real (válido)',          'TIPO_ASIGNACION',        _GRUPO_R3),
    '09_cadena_concat_ok.dml':
        ('Concatenación de cadenas (válido)',         'TIPO_ASIGNACION',        _GRUPO_R3),
    '10_cadena_concat_mixto.dml':
        ('Concatenar cadena con entero',              'TIPO_OPERADOR',          _GRUPO_R3),
    '11_condicion_si_no_booleana.dml':
        ('Condición de "si" no booleana',             'TIPO_CONDICION',         _GRUPO_R4),
    '12_condicion_mientras_no_booleana.dml':
        ('Condición de "mientras" no booleana',       'TIPO_CONDICION',         _GRUPO_R4),
    '13_condicion_si_ok.dml':
        ('Condición de "si" con comparación (válido)','TIPO_CONDICION',         _GRUPO_R4),
    '14_condicion_si_compuesta_ok.dml':
        ('Condición compuesta con "y" (válido)',      'TIPO_CONDICION',         _GRUPO_R4),
    '15_condicion_cascada.dml':
        ('Condición en cascada con uso no declarado', 'TIPO_CONDICION',         _GRUPO_R4),
    '16_llamada_aridad_mas.dml':
        ('Llamada con demasiados argumentos',         'LLAMADA_ARIDAD',         _GRUPO_R5),
    '17_llamada_aridad_menos.dml':
        ('Llamada con muy pocos argumentos',          'LLAMADA_ARIDAD',         _GRUPO_R5),
    '18_llamada_tipo_incompatible.dml':
        ('Tipo de argumento incompatible',            'LLAMADA_TIPO',           _GRUPO_R5),
    '19_llamada_promocion_ok.dml':
        ('Promoción de argumento entero → real (válido)', 'LLAMADA_TIPO',       _GRUPO_R5),
    '20_llamada_no_funcion.dml':
        ('Llamar a algo que no es función',           'LLAMADA_NO_FUNCION',     _GRUPO_R5),
    '21_llamada_cascada.dml':
        ('Argumento con error en cascada',            'LLAMADA_TIPO',           _GRUPO_R5),
    '22_llamada_recursiva_ok.dml':
        ('Llamada recursiva bien tipada (válido)',    'LLAMADA_TIPO',           _GRUPO_R5),
}


@app.route('/ejemplos_semanticos', methods=['GET'])
def ejemplos_semanticos():
    """
    Devuelve la lista de ejemplos .dml de la carpeta `ejemplos_semanticos/`
    para poblar el desplegable del frontend (Etapa 10).

    Cada item incluye:
        archivo   — nombre del .dml
        titulo    — texto legible para mostrar en la opción
        regla     — código de regla semántica que ilustra
        grupo     — header visible (<optgroup>) en el frontend
        contenido — texto completo del archivo

    Si la carpeta no existe o está vacía, devuelve [] (no crashea).
    Los archivos no registrados en `_MAPEO_EJEMPLOS_SEM` se incluyen con
    título derivado del nombre y grupo "Otros".
    """
    if not _EJEMPLOS_SEM_DIR.is_dir():
        return jsonify([])

    items = []
    for ruta in sorted(_EJEMPLOS_SEM_DIR.glob('*.dml')):
        nombre = ruta.name
        if nombre in _MAPEO_EJEMPLOS_SEM:
            titulo, regla, grupo = _MAPEO_EJEMPLOS_SEM[nombre]
        else:
            # Fallback: ejemplo nuevo no registrado. Lo mostramos igual.
            base = ruta.stem.replace('_', ' ')
            titulo = base[3:].strip().capitalize() if base[:2].isdigit() else base
            regla, grupo = '—', 'Otros'
        try:
            contenido = ruta.read_text(encoding='utf-8')
        except OSError:
            continue
        items.append({
            'archivo':   nombre,
            'titulo':    titulo,
            'regla':     regla,
            'grupo':     grupo,
            'contenido': contenido,
        })
    return jsonify(items)


# ══════════════════════════════════════════════
#  RUTA: EJEMPLOS DE ERRORES SINTÁCTICOS
# ══════════════════════════════════════════════
# Carpeta de programas con errores SINTÁCTICOS (paralela a ejemplos_semanticos/).
_EJEMPLOS_SINT_DIR = Path(__file__).resolve().parent / 'ejemplos_errores'

# Mapeo nombre_archivo → título legible para el <option> del frontend.
_MAPEO_EJEMPLOS_SINT = {
    'parentesis_sin_cerrar.dml':       'Paréntesis sin cerrar',
    'operando_faltante.dml':           'Operando faltante en expresión',
    'bucle_para_incompleto.dml':       "Bucle 'para' incompleto",
    'errores_multiples_simples.dml':   'Errores múltiples simples',
    'errores_en_funcion.dml':          'Función con varios errores',
}


@app.route('/ejemplos_sintacticos', methods=['GET'])
def ejemplos_sintacticos():
    """
    Devuelve la lista de ejemplos .dml de la carpeta `ejemplos_errores/`
    para poblar el desplegable de ejemplos SINTÁCTICOS del frontend.

    Mismo schema que /ejemplos_semanticos (archivo, titulo, grupo, contenido),
    para que el frontend reutilice la misma lógica de poblado. Si la carpeta
    no existe o está vacía, devuelve [] (no crashea).
    """
    if not _EJEMPLOS_SINT_DIR.is_dir():
        return jsonify([])

    items = []
    for ruta in sorted(_EJEMPLOS_SINT_DIR.glob('*.dml')):
        nombre = ruta.name
        titulo = _MAPEO_EJEMPLOS_SINT.get(
            nombre, ruta.stem.replace('_', ' ').capitalize())
        try:
            contenido = ruta.read_text(encoding='utf-8')
        except OSError:
            continue
        items.append({
            'archivo':   nombre,
            'titulo':    titulo,
            'grupo':     'Errores sintácticos',
            'contenido': contenido,
        })
    return jsonify(items)


# ══════════════════════════════════════════════
#  RUTA: TRADUCCIÓN A JULIA (Entrega Final — SDT, Fase B)
# ══════════════════════════════════════════════
@app.route('/traducir', methods=['POST'])
def traducir():
    """
    Traduce un programa DiamondLang a código fuente Julia mediante la fase SDT.

    Recibe:
        { "codigo": str, "metodo": "recursivo"|"predictivo" (opcional, default
          "predictivo") }

    Devuelve (HTTP 200):
        Éxito (válido léxica + sintáctica + semánticamente):
            { "ok": true, "julia": str, "advertencias": [] }
        Con errores (se detiene en la primera fase que falla):
            { "ok": false, "fase_fallida": "lexica"|"sintactica"|"semantica",
              "errores_lexicos": [...], "errores_sintacticos": [...],
              "errores_semanticos": [...] }

    El SDT solo se ejecuta si las 3 fases previas pasan: nunca genera Julia a
    partir de un programa con errores.
    """
    datos = request.get_json()
    if not datos or 'codigo' not in datos:
        return jsonify({'error': 'Se esperaba { "codigo": "...", "metodo": "..." }'}), 400

    codigo = datos.get('codigo', '')
    metodo = datos.get('metodo', 'predictivo')
    if metodo not in ('recursivo', 'predictivo'):
        return jsonify({'error': f'Método desconocido: {metodo}'}), 400

    def fallo(fase, lex=None, sint=None, sem=None):
        return jsonify({
            'ok': False,
            'fase_fallida': fase,
            'errores_lexicos':     lex  or [],
            'errores_sintacticos': sint or [],
            'errores_semanticos':  sem  or [],
        })

    # ── 1. Fase léxica ──
    tokens, errores_lexicos = Lexer(codigo).tokenizar()
    if errores_lexicos:
        return fallo('lexica', lex=errores_lexicos)

    # ── 2. Fase sintáctica ──
    if metodo == 'recursivo':
        parser = ParserRecursivo(codigo)
    else:
        parser = ParserPredictivo(codigo)
    resultado = parser.analizar()
    if not resultado.get('valido'):
        return fallo('sintactica', sint=resultado.get('errores', []))

    arbol_raiz = getattr(parser, 'arbol_raiz', None)
    if arbol_raiz is None:
        return fallo('sintactica', sint=resultado.get('errores', []))

    # ── 3. Fase semántica ──
    analizador = AnalizadorSemantico(arbol_raiz)
    resultado_sem = analizador.analizar()
    if not resultado_sem.get('valido_semantico'):
        return fallo('semantica', sem=resultado_sem.get('errores_semanticos', []))

    # ── 4. SDT → Julia ──
    julia = sdt.traducir(arbol_raiz, analizador.tabla,
                         fecha=datetime.now().isoformat(timespec='seconds'))
    return jsonify({'ok': True, 'julia': julia, 'advertencias': []})


# ══════════════════════════════════════════════
#  RUTA: VALIDACIÓN + OPTIMIZACIÓN CON IA (Entrega Final — Bonus, Modalidad C)
# ══════════════════════════════════════════════
#
#  Capa OPCIONAL sobre la traducción a Julia: toma el código Julia ya generado
#  por el SDT y lo envía a Claude Haiku pidiendo (1) una validación de
#  corrección sintáctica/semántica y (2) sugerencias de optimización idiomática.
#  El compilador funciona igual sin esto; si ANTHROPIC_API_KEY no está, el
#  endpoint responde ok=false con una explicación y el frontend deshabilita el
#  botón. El prompt completo queda literal aquí (SYSTEM_VALIDAR_JULIA +
#  _prompt_validar_julia) para la sustentación del bonus.

# System prompt: rol del modelo (experto Julia que audita código de compilador).
SYSTEM_VALIDAR_JULIA = (
    "Eres un experto en Julia que audita código generado automáticamente por "
    "compiladores. Tu rol es validar la corrección y sugerir optimizaciones "
    "idiomáticas. Responde siempre en español. Para cada análisis: identifica "
    "problemas reales (si los hay), sugiere mejoras idiomáticas concretas, y "
    "mantén las sugerencias accionables. No inventes problemas donde no hay. "
    "Si el código está bien, dilo claramente."
)


def _prompt_validar_julia(julia_code: str) -> str:
    """Prompt de usuario: pasa el código y pide un análisis estructurado en un
    bloque ```json para parseo robusto. Pide explícitamente validación
    (sintaxis, semántica, tipos) y optimizaciones idiomáticas."""
    return (
        "Audita este código Julia y devuelve un análisis estructurado.\n\n"
        "```julia\n"
        f"{julia_code}\n"
        "```\n\n"
        "Evalúa concretamente: (1) ¿es sintácticamente correcto en Julia?, "
        "(2) ¿es semánticamente coherente y usa tipos consistentes?, (3) ¿hay "
        "formas más idiomáticas, estructuras estándar de Julia o patrones que "
        "un desarrollador experimentado mejoraría?\n\n"
        "Responde EXCLUSIVAMENTE con un bloque JSON en este formato:\n\n"
        "```json\n"
        "{\n"
        '  "validacion": "<un párrafo evaluando la corrección sintáctica y semántica>",\n'
        '  "problemas_encontrados": ["<problema 1>", "..."],\n'
        '  "optimizaciones": ["<sugerencia idiomática 1>", "..."]\n'
        "}\n"
        "```\n\n"
        'Si no hay problemas, deja "problemas_encontrados" como lista vacía. '
        'Si el código es idiomático y no necesita cambios, dilo claramente como '
        'única entrada de "optimizaciones".'
    )


# Bloque ```json ... ``` (o ``` ... ```) que envuelve el objeto JSON.
_RE_BLOQUE_JSON = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _parsear_respuesta_julia(raw: str):
    """
    Extrae el objeto JSON de la respuesta de Claude. Estrategia:
      1. Bloque ```json ... ``` (lo que pide el prompt).
      2. Fallback: primer {...} que abarque el texto, por si el modelo omitió
         las cercas de código.
    Devuelve el dict parseado, o None si no se puede parsear (el endpoint
    devuelve entonces la respuesta cruda en el campo "raw").
    """
    if not raw:
        return None
    m = _RE_BLOQUE_JSON.search(raw)
    candidato = m.group(1) if m else None
    if candidato is None:
        inicio = raw.find('{')
        fin    = raw.rfind('}')
        if inicio != -1 and fin > inicio:
            candidato = raw[inicio:fin + 1]
    if not candidato:
        return None
    try:
        obj = json.loads(candidato)
    except (json.JSONDecodeError, ValueError):
        return None
    return obj if isinstance(obj, dict) else None


@app.route('/validar_julia', methods=['POST'])
def validar_julia():
    """
    Recibe:
        { "julia": str }   # código Julia previamente generado por el SDT

    Devuelve (HTTP 200, salvo body inválido = 400):
        Éxito:
            { "ok": true, "modelo": "Claude Haiku",
              "validacion": str, "problemas_encontrados": [str],
              "optimizaciones": [str], "raw": str }
        Error (IA no disponible / sin respuesta):
            { "ok": false, "error": str }

    Esta ruta NO afecta a /traducir ni al SDT: es una capa adicional.
    """
    datos = request.get_json(silent=True) or {}
    julia = (datos.get('julia') or '').strip()
    if not julia:
        return jsonify({
            'ok': False,
            'error': 'Se esperaba { "julia": "..." } con código no vacío.',
        }), 400

    # IA no disponible → ok=false con explicación (el frontend ya deshabilita
    # el botón vía /ping_chat, pero esto es la red de seguridad del backend).
    if not cliente_anthropic.disponible():
        return jsonify({
            'ok': False,
            'error': 'Análisis con IA no disponible: define ANTHROPIC_API_KEY '
                     'en el servidor.',
        })

    prompt = _prompt_validar_julia(julia)
    try:
        raw = cliente_anthropic.responder(
            prompt, system=SYSTEM_VALIDAR_JULIA, timeout=20.0, max_tokens=1024)
    except Exception as e:  # red defensiva: el cliente ya captura, por si acaso
        print(f"[validar_julia] {type(e).__name__}: {e}")
        raw = None

    if not raw:
        return jsonify({
            'ok': False,
            'error': 'Claude Haiku no devolvió respuesta (timeout o fallo de API).',
        })

    parsed = _parsear_respuesta_julia(raw)
    if parsed is None:
        # Parseo fallido: devolvemos la respuesta cruda para que el usuario la
        # vea (graceful degradation, no error).
        return jsonify({
            'ok': True,
            'modelo': 'Claude Haiku',
            'validacion': 'No se pudo estructurar la respuesta del modelo; '
                          'se muestra la respuesta cruda abajo.',
            'problemas_encontrados': [],
            'optimizaciones': [],
            'raw': raw,
        })

    return jsonify({
        'ok': True,
        'modelo': 'Claude Haiku',
        'validacion':            parsed.get('validacion', '') or '',
        'problemas_encontrados': parsed.get('problemas_encontrados') or [],
        'optimizaciones':        parsed.get('optimizaciones') or [],
        'raw': raw,
    })


# ══════════════════════════════════════════════
#  INICIO
# ══════════════════════════════════════════════
if __name__ == '__main__':
    import os
    port  = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    print("\n💎 DiamondLang — Servidor Flask (Entrega Final)")
    print(f"   Corriendo en http://localhost:{port}")
    print("   Abre frontend/diamondlang.html en tu navegador")
    print("   Presiona Ctrl+C para detener\n")
    app.run(host="0.0.0.0", port=port, debug=debug)
