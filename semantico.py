"""
╔══════════════════════════════════════════════════════════╗
║   DiamondLang 💎 — Analizador Semántico                  ║
║                    semantico.py                         ║
║  Entrega 4 — Etapa 7: reglas 1, 2, 3, 4 y 5.            ║
║                                                         ║
║  Visitor sobre el CST producido por cualquiera de los    ║
║  dos parsers (recursivo o predictivo).                   ║
║                                                         ║
║  Reglas implementadas:                                  ║
║    Regla 1 — Declaración duplicada en el mismo ámbito   ║
║              (variables, parámetros, funciones).        ║
║    Regla 2 — Uso de identificador no declarado          ║
║              (mensajes diferenciados:                   ║
║               "variable 'X' no declarada" vs            ║
║               "función 'X' no declarada").              ║
║    Regla 3 — Compatibilidad de tipos en asignación      ║
║              (declaración con valor inicial y            ║
║               reasignación). Sub-regla: 'vacio' no es    ║
║               un tipo válido de variable. TIPO_OPERADOR  ║
║               se delega al motor de tipos (Etapa 4).     ║
║    Regla 4 — La condición de 'si' y 'mientras' debe ser  ║
║              de tipo 'booleano' (TIPO_CONDICION). La     ║
║              cascada F.10 suprime el reporte si la        ║
║              condición ya infirió 'ERROR'.               ║
║    Regla 5 — Aridad y tipos de argumentos en llamadas    ║
║              a función deben coincidir con la firma      ║
║              declarada (LLAMADA_ARIDAD, LLAMADA_TIPO,    ║
║              LLAMADA_NO_FUNCION). Cascada F.10: un        ║
║              argumento 'ERROR' no genera LLAMADA_TIPO,   ║
║              pero la aridad SÍ se chequea aparte.         ║
╚══════════════════════════════════════════════════════════╝
"""

from arbol import (
    NodoArbol,
    raiz_logica,
    tiene_error_sintactico,
    etiqueta_normalizada,
    hijo_por_etiqueta,
    primer_terminal,
    extraer_expresiones_de_argumentos,
)
from tabla_simbolos    import (
    TablaSimbolos, Simbolo,
    como_dict as simbolo_a_dict,
)
from errores_semanticos import ErrorSemantico, como_dict as error_a_dict
from sugerencias_semanticas import sugerir as _sugerir_local
from tipos import (
    tipo_declarado,
    tipo_de_expresion_con_reporte,
    compatible,
)


# Conjunto de tipos primitivos reconocidos por la gramática.
# (La validación de "no usar 'vacio' como tipo de variable" es de Etapa 4.)
TIPOS_VALIDOS = {'entero', 'real', 'cadena', 'booleano', 'vacio'}


# ──────────────────────────────────────────────────────────────────
#  CONTENEDORES PARA EL ANÁLISIS PARCIAL (decisión F.11, Etapa 8.5)
# ──────────────────────────────────────────────────────────────────
#
# Cuando un programa tiene un error sintáctico aislado, el modo pánico
# marca un nodo con `es_error=True` y esa "suciedad" se propaga hacia
# arriba (la usa `tiene_error_sintactico`, que es recursivo): el
# `programa`, la `declaracion`, la `def_funcion`, el `bloque`, … que
# contienen al error quedan todos marcados como sucios.
#
# Para cumplir F.11 ("analizar las zonas limpias aunque haya errores
# sintácticos en otras") el visitor NO puede saltar un sub-árbol entero
# sólo porque contenga un error en algún punto: debe DESCENDER por los
# nodos CONTENEDORES —los que enrutan sentencias o envuelven un
# `bloque`— hasta llegar a las sentencias concretas, y saltar sólo la
# sentencia (u hoja) realmente rota.
#
# Estos son exactamente los no-terminales de la gramática
# (`tabla_ll.GRAMATICA`) que enrutan sentencias o contienen un `bloque`:
#   - enrutadores de sentencias: programa, declaracion, bloque,
#     bloque_prima, sentencia;
#   - los que envuelven un `bloque`: def_funcion, sent_si, rama_sino,
#     sent_mientras, sent_para.
# Las etiquetas ya vienen normalizadas (`bloque'` → `bloque_prima`), así
# que el conjunto sirve para los dos parsers.
_CONTENEDORES = frozenset({
    'programa', 'declaracion', 'def_funcion',
    'bloque', 'bloque_prima', 'sentencia',
    'sent_si', 'rama_sino', 'sent_mientras', 'sent_para',
})


# ══════════════════════════════════════════════
#  ANALIZADOR SEMÁNTICO
# ══════════════════════════════════════════════

class AnalizadorSemantico:
    """
    Recorre el árbol sintáctico y aplica las reglas semánticas. Está
    pensado para correr sobre el CST de cualquiera de los dos parsers:
    las etiquetas de no-terminales auxiliares se normalizan vía
    `etiqueta_normalizada()`.

    Si en algún sub-árbol hay un nodo `es_error=True`, ese sub-árbol
    se SALTA (decisión F.11 aprobada): el análisis semántico no debe
    derivar errores espurios de código que el modo pánico ya
    estabilizó con marcadores sintéticos.
    """

    def __init__(self, arbol_raiz: NodoArbol, max_errores: int = 100):
        self.raiz = raiz_logica(arbol_raiz) if arbol_raiz is not None else None
        self.tabla = TablaSimbolos()
        self.errores: list = []                      # list[ErrorSemantico]
        self.max_errores = max_errores
        self._simbolos_historicos: list = []          # snapshots de ámbitos

    # ── Punto de entrada ─────────────────────────

    def analizar(self) -> dict:
        if self.raiz is not None:
            self._visitar(self.raiz)
        # Snapshot del ámbito global (que no se cierra durante el análisis)
        self._simbolos_historicos.extend(
            self.tabla.simbolos_del_ambito_actual()
        )
        return self._resultado()

    def _resultado(self) -> dict:
        return {
            "valido_semantico":   len(self.errores) == 0,
            "errores_semanticos": [error_a_dict(e) for e in self.errores],
            "simbolos":           [simbolo_a_dict(s)
                                   for s in self._simbolos_historicos],
        }

    # ── Recorrido (dispatch dinámico por etiqueta) ──

    def _visitar(self, nodo: NodoArbol) -> None:
        # Marcador sintético del modo pánico (ERROR<…>): nada que analizar.
        if nodo.es_error:
            return

        etiqueta = etiqueta_normalizada(nodo.etiqueta)

        # Decisión F.11 con granularidad POR-HIJO (Etapa 8.5): si el
        # sub-árbol contiene errores sintácticos y este nodo NO es un
        # contenedor (ver `_CONTENEDORES`), se salta —no es analizable—.
        # Los contenedores SÍ se descienden aunque tengan errores
        # internos, para alcanzar las sentencias limpias que cuelgan de
        # ellos. Así un error sintáctico aislado deja de anular el
        # análisis semántico del resto del programa.
        if etiqueta not in _CONTENEDORES and tiene_error_sintactico(nodo):
            return

        metodo = getattr(self, f"_visit_{etiqueta}", None)
        if metodo is None:
            self._visit_generico(nodo)
        else:
            metodo(nodo)

    def _visit_generico(self, nodo: NodoArbol) -> None:
        """
        Visitor por defecto: recorre todos los hijos en orden. El
        filtrado de sub-árboles sucios (F.11) está centralizado en
        `_visitar`, así que aquí basta con descender a cada hijo.
        """
        for hijo in nodo.hijos:
            self._visitar(hijo)

    # ══════════════════════════════════════════
    #  REPORTE DE ERRORES SEMÁNTICOS
    # ══════════════════════════════════════════

    def _reportar(self, regla: str, mensaje: str, *,
                  nodo: NodoArbol = None,
                  lexema: str = None,
                  sugerencia: str = None,
                  contexto: dict = None) -> None:
        if len(self.errores) >= self.max_errores:
            return

        fila = nodo.linea   if nodo is not None else None
        columna = nodo.columna if nodo is not None else None

        if lexema is None and nodo is not None and nodo.es_terminal:
            lexema = nodo.etiqueta

        error = ErrorSemantico(
            indice=len(self.errores) + 1,
            fila=fila, columna=columna,
            lexema=lexema,
            regla=regla,
            mensaje=mensaje,
            sugerencia=sugerencia,
            fuente_sugerencia="local",
            contexto=contexto or {},
        )
        # Sugerencia local centralizada (Etapa 8): el módulo
        # `sugerencias_semanticas` es la fuente de verdad de las
        # sugerencias por regla. Si no reconoce la regla devuelve '' y
        # se conserva la `sugerencia` que ya traía el error (fallback).
        sugerencia_local = _sugerir_local(error)
        if sugerencia_local:
            error.sugerencia = sugerencia_local
        self.errores.append(error)

    def _reportar_duplicado(self, nombre: str, ident_node: NodoArbol,
                            ambito: str, *,
                            tipo_simbolo: str = "identificador") -> None:
        """
        Variante de `_reportar` especializada en la Regla 1. El
        `tipo_simbolo` puede ser 'variable', 'parámetro', 'función', o el
        genérico 'identificador'. Se incluye la posición de la
        declaración previa en `contexto` para que el frontend pueda
        navegar a ella.
        """
        previo = self.tabla.buscar(nombre)
        self._reportar(
            regla="DECL_DUPLICADA",
            mensaje=(f"El {tipo_simbolo} '{nombre}' ya está declarado "
                     f"en el ámbito '{ambito}'."),
            nodo=ident_node,
            lexema=nombre,
            sugerencia=("Renómbralo o elimina la declaración duplicada."),
            contexto={
                "ambito": ambito,
                "tipo_simbolo": tipo_simbolo,
                "declaracion_previa_fila":    previo.fila    if previo else None,
                "declaracion_previa_columna": previo.columna if previo else None,
            },
        )

    def _reportar_uso_no_declarado(self, ident_node: NodoArbol,
                                   nombre: str, es_llamada: bool) -> None:
        """Regla 2 con mensaje diferenciado variable vs función."""
        if es_llamada:
            mensaje = f"La función '{nombre}' no está declarada."
            sugerencia = ("Defínela primero con 'funcion ...' o verifica "
                          "que el nombre coincida con una función existente.")
        else:
            mensaje = f"La variable '{nombre}' no está declarada."
            sugerencia = ("Declárala con su tipo antes de usarla, o verifica "
                          "que el nombre coincida con una declaración previa.")
        self._reportar(
            regla="USO_NO_DECLARADO",
            mensaje=mensaje,
            nodo=ident_node,
            lexema=nombre,
            sugerencia=sugerencia,
            contexto={"es_llamada": es_llamada},
        )

    # ══════════════════════════════════════════
    #  HELPERS DE EXTRACCIÓN DE INFORMACIÓN
    # ══════════════════════════════════════════

    @staticmethod
    def _extraer_nombre_tipo(nodo_tipo: NodoArbol) -> str:
        """De un nodo `tipo` (producción `tipo → entero | real | ...`),
        devuelve el lexema del único terminal hijo. None si no se puede
        determinar (por ejemplo, si el sub-árbol está mal formado)."""
        if nodo_tipo is None:
            return None
        for h in nodo_tipo.hijos:
            if (h.es_terminal and not h.es_error and
                    h.etiqueta in TIPOS_VALIDOS):
                return h.etiqueta
        return None

    @classmethod
    def _extraer_tipo_retorno(cls, nodo_tipo_retorno_opt: NodoArbol) -> str:
        """Del nodo `tipo_retorno_opt` devuelve el nombre del tipo de
        retorno. Si la producción se redujo a ε, devuelve 'vacio'."""
        if nodo_tipo_retorno_opt is None:
            return 'vacio'
        nodo_tipo = hijo_por_etiqueta(nodo_tipo_retorno_opt, 'tipo')
        if nodo_tipo is None:
            return 'vacio'
        return cls._extraer_nombre_tipo(nodo_tipo) or 'vacio'

    @classmethod
    def _recolectar_parametros(cls, nodo_parametros: NodoArbol) -> list:
        """
        Recorre el sub-árbol `parametros` (incluyendo `param_lista` y
        `param_lista_prima` recursivos) y devuelve una lista de tuplas
        `(tipo_str, ident_node)` en orden de aparición.

        Robusto al hecho de que el parser recursivo usa `param_lista'`
        y el predictivo `param_lista_prima`: la condición usa
        `etiqueta_normalizada`.
        """
        acumulador: list = []
        cls._rec_params(nodo_parametros, acumulador)
        return acumulador

    @classmethod
    def _rec_params(cls, nodo: NodoArbol, acumulador: list) -> None:
        # Estrategia: por cada hijo `tipo`, el hijo inmediatamente
        # siguiente es el IDENTIFICADOR del parámetro. Después recursamos
        # en los hijos no-terminales que sean param_lista / param_lista_prima.
        hijos = nodo.hijos
        i = 0
        while i < len(hijos):
            h = hijos[i]
            if h.etiqueta == 'tipo':
                tipo_str = cls._extraer_nombre_tipo(h)
                if (i + 1 < len(hijos) and hijos[i + 1].es_terminal
                        and not hijos[i + 1].es_error):
                    acumulador.append((tipo_str, hijos[i + 1]))
                    i += 2
                    continue
            i += 1
        for h in hijos:
            if h.es_terminal:
                continue
            if etiqueta_normalizada(h.etiqueta) in {
                'parametros', 'param_lista', 'param_lista_prima'
            }:
                cls._rec_params(h, acumulador)

    @staticmethod
    def _tiene_hijo_terminal(nodo: NodoArbol, lexema: str) -> bool:
        """True si `nodo` tiene un hijo directo terminal cuya etiqueta
        coincide con `lexema` (excluyendo marcadores ERROR)."""
        if nodo is None:
            return False
        for h in nodo.hijos:
            if h.es_terminal and not h.es_error and h.etiqueta == lexema:
                return True
        return False

    # ══════════════════════════════════════════
    #  PROCESAMIENTO DE EXPRESIONES (Regla 2 + tipos)
    # ══════════════════════════════════════════

    def _visitar_y_tipar_expresion(self, nodo_expr: NodoArbol) -> str:
        """
        Procesa una expresión en dos pasadas COMPLEMENTARIAS y devuelve
        su tipo inferido (puede ser 'ERROR'):

          1. `_visitar` recorre el sub-árbol aplicando la Regla 2
             (USO_NO_DECLARADO) sobre los identificadores que contiene.
          2. `tipo_de_expresion_con_reporte` infiere el tipo y, de paso,
             emite TIPO_OPERADOR cuando un operador rechaza sus operandos
             (motor de tipos, Etapa 4). La supresión de cascada (decisión
             F.10) está centralizada en tipos.py.

        Las dos pasadas reportan reglas DISJUNTAS (Regla 2 vs
        TIPO_OPERADOR), así que no hay doble conteo de errores. El tipo
        que devuelve alimenta la validación de compatibilidad (Regla 3)
        en quien llama.
        """
        if nodo_expr is None:
            return 'ERROR'
        self._visitar(nodo_expr)
        return tipo_de_expresion_con_reporte(nodo_expr, self.tabla,
                                             self._reportar)

    # ══════════════════════════════════════════
    #  REGLA 5 — ARIDAD Y TIPOS EN LLAMADAS
    # ══════════════════════════════════════════

    def _validar_llamada(self, nombre: str, sim: Simbolo,
                         nodo_argumentos: NodoArbol,
                         nodo_id: NodoArbol) -> None:
        """
        Regla 5: la aridad y los tipos de los argumentos de una llamada
        deben coincidir con la firma declarada de la función.

        Parámetros:
          - nombre:           lexema del identificador invocado.
          - sim:              Simbolo recuperado de la tabla (o None si el
                              identificador no existe).
          - nodo_argumentos:  sub-árbol `argumentos` que cuelga del
                              `sufijo_id` (llamada como expresión) o del
                              `sentencia_id_cola` (llamada como sentencia).
                              Puede ser None.
          - nodo_id:          nodo del IDENTIFICADOR, usado para anclar la
                              posición de LLAMADA_ARIDAD / LLAMADA_NO_FUNCION.

        Sub-validaciones:
          1. NO EXISTE (sim is None): USO_NO_DECLARADO ya lo reportó quien
             llama. No se reporta nada aquí (cascada).
          2. NO LLAMABLE (sim no es función): LLAMADA_NO_FUNCION. No se
             valida aridad ni tipos.
          3. ARIDAD: len(args) debe ser == len(sim.parametros). Se reporta
             LLAMADA_ARIDAD INCLUSO si algún argumento es 'ERROR' (aridad y
             tipos son chequeos independientes).
          4. TIPOS: para cada argumento presente (hasta min(esperada,
             recibida)), compatible(tipo_param, tipo_arg). Un argumento de
             tipo 'ERROR' se salta (cascada F.10). El error se ancla en el
             primer terminal del argumento.

        IMPORTANTE (sorpresa de la firma de datos): el campo
        `Simbolo.parametros` es una lista de tuplas **(tipo, nombre)** —así
        las construye `_visit_def_funcion`—, NO (nombre, tipo). Por eso el
        tipo esperado del parámetro i es `sim.parametros[i][0]`.

        NOTA sobre el recorrido de argumentos: cada argumento se procesa con
        `_visitar_y_tipar_expresion`, que hace DOS pasadas disjuntas: la
        Regla 2 (USO_NO_DECLARADO sobre identificadores del argumento) y la
        inferencia con reporte (TIPO_OPERADOR). Es una desviación deliberada
        de la TAREA 2 del enunciado (que sólo pedía
        `tipo_de_expresion_con_reporte`): sin la pasada de `_visitar`, un
        identificador no declarado usado como argumento —p.ej.
        `sumar(noexiste)`— quedaría sin reportar, porque `_visit_expr_primaria`
        ya NO recorre el sufijo de una llamada (delega aquí).
        """
        # 1. NO EXISTE.
        if sim is None:
            return

        # 2. NO LLAMABLE: el símbolo existe pero no es una función.
        if sim.categoria != 'funcion':
            self._reportar(
                regla="LLAMADA_NO_FUNCION",
                mensaje=f"'{nombre}' no es una función.",
                nodo=nodo_id,
                lexema=nombre,
                sugerencia=("Sólo se pueden invocar funciones. Verifica el "
                            "nombre o declara una función con ese nombre."),
                contexto={'categoria': sim.categoria},
            )
            return

        # 3. Extraer las expresiones de los argumentos.
        args = extraer_expresiones_de_argumentos(nodo_argumentos)

        # 4. Inferir el tipo de cada argumento. _visitar_y_tipar_expresion
        #    también aplica la Regla 2 (USO_NO_DECLARADO) y TIPO_OPERADOR
        #    sobre el contenido de cada argumento.
        tipos_args = [self._visitar_y_tipar_expresion(a) for a in args]

        # 5. ARIDAD (se reporta aunque algún argumento sea 'ERROR').
        parametros = sim.parametros or []
        esperada = len(parametros)
        recibida = len(args)
        if esperada != recibida:
            self._reportar(
                regla="LLAMADA_ARIDAD",
                mensaje=(f"la función '{nombre}' espera {esperada} "
                         f"argumentos, recibió {recibida}"),
                nodo=nodo_id,
                lexema=nombre,
                sugerencia=(f"Ajusta la llamada para pasar exactamente "
                            f"{esperada} argumento(s)."),
                contexto={'aridad_esperada': esperada,
                          'aridad_recibida': recibida},
            )

        # 6. TIPOS de los argumentos presentes (hasta min(esperada, recibida)).
        for i in range(min(esperada, recibida)):
            tipo_esperado = parametros[i][0]    # tupla (tipo, nombre)
            tipo_recibido = tipos_args[i]
            if tipo_recibido == 'ERROR':
                continue                        # cascada F.10
            if not compatible(tipo_esperado, tipo_recibido):
                arg_node = args[i]
                inicio = primer_terminal(arg_node)
                nodo_pos = (inicio if (inicio is not None
                                       and inicio.linea is not None)
                            else nodo_id)
                lexema = inicio.etiqueta if inicio is not None else None
                self._reportar(
                    regla="LLAMADA_TIPO",
                    mensaje=(f"el argumento {i + 1} de '{nombre}' debe ser "
                             f"'{tipo_esperado}', se recibió '{tipo_recibido}'"),
                    nodo=nodo_pos,
                    lexema=lexema,
                    sugerencia=("Convierte el argumento al tipo esperado o "
                                "ajusta la firma de la función."),
                    contexto={'funcion': nombre,
                              'posicion_argumento': i + 1,
                              'tipo_esperado': tipo_esperado,
                              'tipo_recibido': tipo_recibido},
                )

    # ══════════════════════════════════════════
    #  VISITORS — ESTRUCTURA DEL PROGRAMA
    # ══════════════════════════════════════════

    def _visit_programa(self, nodo: NodoArbol) -> None:
        """
        El ámbito 'global' ya existe (lo crea `TablaSimbolos.__init__`).
        Solo recorremos los hijos. Como la gramática es
        `programa → declaracion programa | ε`, el sub-árbol del parser
        predictivo es recursivo (programa anidado). El visitor genérico
        se ocupa de bajar por ambos casos.
        """
        self._visit_generico(nodo)

    # ── Funciones ────────────────────────────────

    def _visit_def_funcion(self, nodo: NodoArbol) -> None:
        """
        def_funcion → funcion IDENTIFICADOR ( parametros ) tipo_retorno_opt
                      hacer bloque fin_funcion

        Posición del IDENTIFICADOR de la función: hijos[1]
        (los direct children de def_funcion no contienen epsilons).
        """
        if len(nodo.hijos) < 2:
            self._visit_generico(nodo)
            return

        ident_funcion = nodo.hijos[1]
        if not (ident_funcion.es_terminal and not ident_funcion.es_error):
            self._visit_generico(nodo)
            return

        nombre_funcion = ident_funcion.etiqueta

        nodo_params  = hijo_por_etiqueta(nodo, 'parametros')
        nodo_tipo_r  = hijo_por_etiqueta(nodo, 'tipo_retorno_opt')
        nodo_bloque  = hijo_por_etiqueta(nodo, 'bloque')

        # Extraer parámetros como (tipo_str, ident_node)
        parametros_raw = (self._recolectar_parametros(nodo_params)
                          if nodo_params is not None else [])
        tipo_retorno = self._extraer_tipo_retorno(nodo_tipo_r)

        # Lista de tuplas para guardar en el Simbolo de la función
        # (tipo_param, nombre_param) — el orden importa para Regla 5 (Etapa 7).
        parametros_para_simbolo = [
            (tipo or 'ERROR', ident.etiqueta)
            for tipo, ident in parametros_raw
        ]

        # ── Regla 1: registrar la función en el ámbito global ──
        sim_funcion = Simbolo(
            nombre=nombre_funcion,
            tipo='funcion',
            categoria='funcion',
            ambito=self.tabla.ambito_actual(),   # debería ser 'global'
            fila=ident_funcion.linea,
            columna=ident_funcion.columna,
            inicializado=True,
            parametros=parametros_para_simbolo,
            tipo_retorno=tipo_retorno,
        )
        if not self.tabla.declarar(sim_funcion):
            # Ya existía un símbolo con ese nombre en global.
            # NO se sobrescribe el original; reportamos y seguimos
            # procesando el cuerpo (recuperación = continuar).
            self._reportar_duplicado(
                nombre_funcion, ident_funcion,
                ambito=self.tabla.ambito_actual(),
                tipo_simbolo="función",
            )

        # ── Abrir ámbito de la función ──
        self.tabla.abrir_ambito(nombre_funcion)

        # ── Declarar parámetros (Regla 1 puede dispararse aquí) ──
        for tipo_p, ident_p in parametros_raw:
            sim_param = Simbolo(
                nombre=ident_p.etiqueta,
                tipo=(tipo_p or 'ERROR'),
                categoria='parametro',
                ambito=nombre_funcion,
                fila=ident_p.linea,
                columna=ident_p.columna,
                inicializado=True,
            )
            if not self.tabla.declarar(sim_param):
                self._reportar_duplicado(
                    ident_p.etiqueta, ident_p,
                    ambito=nombre_funcion,
                    tipo_simbolo="parámetro",
                )

        # ── Visitar el cuerpo ──
        if nodo_bloque is not None:
            self._visitar(nodo_bloque)

        # ── Snapshot y cierre del ámbito de la función ──
        self._simbolos_historicos.extend(
            self.tabla.simbolos_del_ambito_actual()
        )
        self.tabla.cerrar_ambito()

    # ── Declaración de variable ──────────────────

    def _visit_decl_variable(self, nodo: NodoArbol) -> None:
        """
        decl_variable → tipo IDENTIFICADOR <- expresion

        Hijos directos en orden fijo:
            hijos[0] = tipo
            hijos[1] = IDENTIFICADOR (terminal)
            hijos[2] = '<-' terminal
            hijos[3] = expresion

        Reglas aplicadas:
          - Sub-regla 'vacio' (decisión F.7): declarar una variable de
            tipo 'vacio' es error (TIPO_VOID_EN_VARIABLE). Se reporta
            ANTES de validar el RHS y NO aborta el resto del análisis.
          - Regla 1: declaración duplicada (igual que en Etapa 3).
          - Regla 3: compatibilidad de tipos en la asignación inicial
            (TIPO_ASIGNACION).
          - TIPO_OPERADOR del RHS lo emite el motor de tipos al inferir
            la expresión (Etapa 4); aquí sólo se pasa el callable.
        """
        if len(nodo.hijos) < 4:
            self._visit_generico(nodo)
            return

        nodo_tipo = nodo.hijos[0]
        ident     = nodo.hijos[1]
        nodo_expr = nodo.hijos[3]

        tipo_declarado_str = tipo_declarado(nodo_tipo)   # 'entero'…'vacio'/'ERROR'
        es_vacio = (tipo_declarado_str == 'vacio')
        ident_valido = ident.es_terminal and not ident.es_error

        # ── Sub-regla 'vacio': reportar ANTES de validar la expresión ──
        if es_vacio and ident_valido:
            self._reportar(
                regla="TIPO_VOID_EN_VARIABLE",
                mensaje=("No se puede declarar una variable de tipo 'vacio'; "
                         "'vacio' sólo es válido como tipo de retorno."),
                nodo=ident,
                lexema=ident.etiqueta,
                sugerencia=("Usa un tipo de dato concreto: entero, real, "
                            "cadena o booleano."),
                contexto={'tipo_declarado': 'vacio'},
            )

        # Tipo que se GUARDA en la tabla. Para 'vacio' guardamos 'ERROR':
        # así cualquier uso posterior de la variable —y la propia
        # validación de compatibilidad del RHS de abajo— queda suprimido
        # por la regla de cascada (F.10). El único error visible para una
        # declaración 'vacio' es TIPO_VOID_EN_VARIABLE, sin un
        # TIPO_ASIGNACION redundante encima.
        tipo_simbolo = 'ERROR' if es_vacio else tipo_declarado_str

        # ── Regla 1: declarar la variable en el ámbito actual ──
        if ident_valido:
            ambito = self.tabla.ambito_actual()
            sim = Simbolo(
                nombre=ident.etiqueta,
                tipo=tipo_simbolo,
                categoria='variable',
                ambito=ambito,
                fila=ident.linea,
                columna=ident.columna,
                inicializado=True,
            )
            if not self.tabla.declarar(sim):
                # Ya existía un símbolo con ese nombre. NO se sobrescribe
                # el original; se reporta el duplicado y se sigue. La
                # validación de compatibilidad del RHS (más abajo) se hace
                # contra el CONTRATO del símbolo ya existente (su tipo
                # original) —porque eso es lo que sigue vigente en la
                # tabla—, no contra esta segunda declaración rechazada.
                self._reportar_duplicado(
                    ident.etiqueta, ident,
                    ambito=ambito,
                    tipo_simbolo="variable",
                )

        # ── Inferir el RHS: Regla 2 sobre sus identificadores +
        #    TIPO_OPERADOR sobre sus operadores; devuelve el tipo. ──
        tipo_rhs = self._visitar_y_tipar_expresion(nodo_expr)

        # ── Regla 3: compatibilidad de tipos en la asignación ──
        # tipo_destino = el tipo del símbolo TAL COMO QUEDÓ EN LA TABLA:
        #   · declaración exitosa  → el tipo recién declarado (o 'ERROR'
        #                            si era 'vacio');
        #   · declaración duplicada → el tipo del símbolo PREVIO.
        # Si tipo_destino o tipo_rhs es 'ERROR', `compatible` devuelve True
        # (F.10) y NO se reporta TIPO_ASIGNACION (la causa raíz ya se
        # reportó por otra regla).
        if ident_valido:
            sim_vigente = self.tabla.buscar(ident.etiqueta)
            tipo_destino = (sim_vigente.tipo if sim_vigente is not None
                            else tipo_simbolo)
            if not compatible(tipo_destino, tipo_rhs):
                self._reportar(
                    regla="TIPO_ASIGNACION",
                    mensaje=(f"No se puede asignar un valor de tipo "
                             f"'{tipo_rhs}' a una variable de tipo "
                             f"'{tipo_destino}'."),
                    nodo=ident,
                    lexema=ident.etiqueta,
                    sugerencia=("Convierte el valor al tipo declarado o "
                                "cambia el tipo de la variable."),
                    contexto={
                        'tipo_declarado': tipo_destino,
                        'tipo_recibido':  tipo_rhs,
                        'identificador':  ident.etiqueta,
                    },
                )

    # ══════════════════════════════════════════
    #  VISITORS — USOS DE IDENTIFICADOR (Regla 2)
    # ══════════════════════════════════════════

    def _visit_expr_primaria(self, nodo: NodoArbol) -> None:
        """
        expr_primaria → ENTERO | REAL | CADENA | verdadero | falso
                      | IDENTIFICADOR sufijo_id
                      | ( expresion )

        El caso IDENTIFICADOR sufijo_id se detecta por la presencia
        de un sub-árbol `sufijo_id` entre los hijos.

        Reglas aplicadas:
          - Regla 2: el identificador debe existir (mensaje diferenciado
            variable vs función según el sufijo).
          - Regla 5 (sólo si es llamada): aridad y tipos de los argumentos
            (LLAMADA_ARIDAD / LLAMADA_TIPO / LLAMADA_NO_FUNCION). Se delega
            en `_validar_llamada`, que además recorre cada argumento para la
            Regla 2 y TIPO_OPERADOR. Por eso, en el caso de llamada ya NO se
            recorre el sufijo aquí (lo haría dos veces).
        """
        sufijo = hijo_por_etiqueta(nodo, 'sufijo_id')
        if sufijo is not None and nodo.hijos:
            ident = nodo.hijos[0]
            if ident.es_terminal and not ident.es_error:
                es_llamada = self._tiene_hijo_terminal(sufijo, '(')
                nombre = ident.etiqueta
                sim = self.tabla.buscar(nombre)
                if sim is None:
                    self._reportar_uso_no_declarado(
                        ident, nombre, es_llamada,
                    )
                if es_llamada:
                    # Regla 5. _validar_llamada recorre y tipa los argumentos.
                    nodo_args = hijo_por_etiqueta(sufijo, 'argumentos')
                    self._validar_llamada(nombre, sim, nodo_args, ident)
                # Uso como variable: el sufijo es ε, no hay nada que recorrer.
                return

        # Otros casos (literales, paréntesis): recorrido genérico.
        self._visit_generico(nodo)

    def _visit_sentencia_id(self, nodo: NodoArbol) -> None:
        """
        sentencia_id → IDENTIFICADOR sentencia_id_cola
        sentencia_id_cola → <- expresion | ( argumentos )

        Si la cola tiene '(' → llamada (función); si tiene '<-' →
        asignación (variable). Ambas exigen que el identificador exista.

        Reglas aplicadas:
          - Regla 2: el identificador debe existir.
          - Regla 3 (sólo en asignación): el tipo del RHS debe ser
            compatible con el tipo de la variable destino
            (TIPO_ASIGNACION). Asignar a una función es siempre error.
          - Regla 5 (sólo en llamada): aridad y tipos de los argumentos
            (LLAMADA_ARIDAD / LLAMADA_TIPO / LLAMADA_NO_FUNCION), delegada
            en `_validar_llamada`.
          - TIPO_OPERADOR del RHS lo emite el motor de tipos.
        """
        if len(nodo.hijos) < 2:
            self._visit_generico(nodo)
            return

        ident = nodo.hijos[0]
        cola  = nodo.hijos[1]
        if not (ident.es_terminal and not ident.es_error):
            self._visit_generico(nodo)
            return

        nombre = ident.etiqueta
        es_llamada    = self._tiene_hijo_terminal(cola, '(')
        es_asignacion = self._tiene_hijo_terminal(cola, '<-')

        # ── Regla 2: existencia del identificador ──
        sim = self.tabla.buscar(nombre)
        if sim is None:
            self._reportar_uso_no_declarado(ident, nombre, es_llamada)

        if es_asignacion:
            # ── Asignación: Regla 3 ──
            nodo_expr = hijo_por_etiqueta(cola, 'expresion')
            # Inferir el RHS SIEMPRE —aunque el destino no exista— para
            # no perder los TIPO_OPERADOR internos. El helper también
            # aplica la Regla 2 a los identificadores del RHS.
            tipo_rhs = self._visitar_y_tipar_expresion(nodo_expr)

            if sim is None:
                # Ya se reportó USO_NO_DECLARADO. El destino se trata
                # implícitamente como 'ERROR': NO se reporta TIPO_ASIGNACION.
                return
            if sim.categoria == 'funcion':
                # Asignar a una función es semánticamente absurdo
                # (f <- 5). El lado izquierdo de '<-' debe ser variable.
                self._reportar(
                    regla="TIPO_ASIGNACION",
                    mensaje=(f"No se puede asignar a la función '{nombre}'; "
                             f"el destino de una asignación debe ser una "
                             f"variable."),
                    nodo=ident,
                    lexema=nombre,
                    sugerencia="Usa una variable como destino de la asignación.",
                    contexto={'tipo_destino': 'funcion',
                              'identificador': nombre},
                )
                return
            tipo_destino = sim.tipo
            if not compatible(tipo_destino, tipo_rhs):
                self._reportar(
                    regla="TIPO_ASIGNACION",
                    mensaje=(f"No se puede asignar un valor de tipo "
                             f"'{tipo_rhs}' a la variable '{nombre}' de "
                             f"tipo '{tipo_destino}'."),
                    nodo=ident,
                    lexema=nombre,
                    sugerencia=("Convierte el valor al tipo de la variable o "
                                "cambia el tipo de la variable."),
                    contexto={
                        'tipo_destino':  tipo_destino,
                        'tipo_recibido': tipo_rhs,
                        'identificador': nombre,
                    },
                )
        elif es_llamada:
            # ── Llamada como sentencia: Regla 5 (aridad y tipos). ──
            # `_validar_llamada` recorre y tipa cada argumento (Regla 2 +
            # TIPO_OPERADOR), por lo que no se recorre la cola aquí.
            nodo_args = hijo_por_etiqueta(cola, 'argumentos')
            self._validar_llamada(nombre, sim, nodo_args, ident)
        else:
            # ── Cola malformada (ni '<-' ni '('): recorrido genérico
            #    defensivo para no perder reglas internas. ──
            self._visitar(cola)

    def _visit_sent_leer(self, nodo: NodoArbol) -> None:
        """
        sent_leer → leer ( IDENTIFICADOR )

        Posición del IDENTIFICADOR entre los hijos: hijos[2].
        `leer` siempre lee a variable, no a función → es_llamada=False.
        """
        if len(nodo.hijos) >= 3:
            ident = nodo.hijos[2]
            if ident.es_terminal and not ident.es_error:
                nombre = ident.etiqueta
                if self.tabla.buscar(nombre) is None:
                    self._reportar_uso_no_declarado(
                        ident, nombre, es_llamada=False,
                    )
        # No recurro: `leer` no tiene expresiones, solo el identificador
        # ya validado.

    def _visit_sent_para(self, nodo: NodoArbol) -> None:
        """
        sent_para → para IDENTIFICADOR desde expresion hasta expresion
                    paso_opt hacer bloque fin_para

        Decisión F.5 aprobada: el 'para' NO abre scope. La variable
        de iteración debe estar declarada previamente en el ámbito de
        la función (o globalmente).

        ALCANCE DE LA REGLA 3 (Etapa 5): el 'para' queda
        DELIBERADAMENTE fuera de la validación de compatibilidad de
        tipos. La asignación implícita de la variable de iteración (toma
        el valor de 'desde', avanza con 'paso', se compara con 'hasta')
        exigiría tres validaciones cruzadas en un solo nodo, lo que
        excede el alcance estricto de la regla 3 según el plan. Por eso
        NO se emite TIPO_ASIGNACION aquí.

        Lo que SÍ se hace (cambio mínimo de la Etapa 5) es procesar las
        expresiones desde/hasta/paso con `_visitar_y_tipar_expresion`,
        para que sus TIPO_OPERADOR internos (p.ej. 'desde 1 + "a"') no se
        pierdan. Pero no se compara su tipo contra la variable iteradora.
        """
        if len(nodo.hijos) >= 2:
            ident = nodo.hijos[1]
            if ident.es_terminal and not ident.es_error:
                nombre = ident.etiqueta
                if self.tabla.buscar(nombre) is None:
                    self._reportar_uso_no_declarado(
                        ident, nombre, es_llamada=False,
                    )

        # Resto del sub-árbol. Las expresiones (desde/hasta y la de
        # paso_opt) se procesan con _visitar_y_tipar_expresion para
        # capturar Regla 2 + TIPO_OPERADOR; el bloque y demás caen por
        # el visit genérico. La variable iteradora (hijos[1]) ya se trató.
        for i, hijo in enumerate(nodo.hijos):
            if i == 1 or hijo.es_terminal:
                continue
            etq = etiqueta_normalizada(hijo.etiqueta)
            if etq == 'expresion':
                self._visitar_y_tipar_expresion(hijo)
            elif etq == 'paso_opt':
                # paso_opt → paso expresion | ε. Si trae expresión,
                # tiparla con reporte; si es ε, no hay nada que validar.
                expr_paso = hijo_por_etiqueta(hijo, 'expresion')
                if expr_paso is not None:
                    self._visitar_y_tipar_expresion(expr_paso)
                else:
                    self._visitar(hijo)
            else:
                self._visitar(hijo)

    # ══════════════════════════════════════════
    #  VISITORS — CONDICIONALES Y BUCLES (Regla 4)
    # ══════════════════════════════════════════

    def _validar_condicion_booleana(self, nodo_expr: NodoArbol,
                                    nombre_estructura: str,
                                    nodo_fallback: NodoArbol) -> None:
        """
        Regla 4: la condición de 'si'/'mientras' debe ser de tipo
        'booleano'.

        Infiere el tipo de la condición con `_visitar_y_tipar_expresion`
        (que de paso aplica la Regla 2 sobre los identificadores y emite
        TIPO_OPERADOR si algún operador rechaza sus operandos). Luego:

          - tipo == 'ERROR'    → NO reporta (cascada F.10: la causa raíz
                                 ya se reportó aguas abajo, p.ej.
                                 USO_NO_DECLARADO o TIPO_OPERADOR).
          - tipo == 'booleano' → condición correcta, nada que reportar.
          - cualquier otro     → reporta TIPO_CONDICION.

        El error se ancla en el PRIMER terminal de la condición (su
        inicio), no en el keyword 'si'/'mientras', porque "el error está
        en la condición que empieza acá". Si ese terminal no tiene
        posición (caso raro), se cae a `nodo_fallback` (el nodo de la
        estructura) para la fila/columna.
        """
        if nodo_expr is None:
            return
        tipo = self._visitar_y_tipar_expresion(nodo_expr)
        if tipo == 'ERROR' or tipo == 'booleano':
            return

        inicio = primer_terminal(nodo_expr)
        nodo_pos = (inicio if (inicio is not None and inicio.linea is not None)
                    else nodo_fallback)
        lexema = inicio.etiqueta if inicio is not None else None
        self._reportar(
            regla="TIPO_CONDICION",
            mensaje=(f"La condición de '{nombre_estructura}' debe ser de "
                     f"tipo 'booleano', se recibió '{tipo}'."),
            nodo=nodo_pos,
            lexema=lexema,
            sugerencia=("Usa una comparación (==, <, > …) o una expresión "
                        "lógica (y, o, no) que produzca un booleano."),
            contexto={'estructura': nombre_estructura, 'tipo_recibido': tipo},
        )

    def _visit_sent_si(self, nodo: NodoArbol) -> None:
        """
        sent_si → si expresion entonces bloque rama_sino fin_si

        Regla 4: la primera 'expresion' (la condición) debe ser booleana.
        La `rama_sino` es un bloque SIN condición → no se valida su tipo,
        sólo se recorre. El cuerpo (bloque y rama_sino) se recorre con el
        visitor genérico para que las reglas 1/2/3 internas se sigan
        disparando. La condición no se vuelve a recorrer (ya la procesó
        `_validar_condicion_booleana`).
        """
        nodo_cond = hijo_por_etiqueta(nodo, 'expresion')
        self._validar_condicion_booleana(nodo_cond, 'si', nodo)
        for hijo in nodo.hijos:
            if hijo is nodo_cond or hijo.es_terminal:
                continue
            self._visitar(hijo)

    def _visit_sent_mientras(self, nodo: NodoArbol) -> None:
        """
        sent_mientras → mientras expresion hacer bloque fin_mientras

        Regla 4: la 'expresion' (la condición del bucle) debe ser
        booleana. El cuerpo (bloque) se recorre con el visitor genérico.
        La condición no se vuelve a recorrer (ya la procesó
        `_validar_condicion_booleana`).
        """
        nodo_cond = hijo_por_etiqueta(nodo, 'expresion')
        self._validar_condicion_booleana(nodo_cond, 'mientras', nodo)
        for hijo in nodo.hijos:
            if hijo is nodo_cond or hijo.es_terminal:
                continue
            self._visitar(hijo)


# ══════════════════════════════════════════════
#  PRUEBA RÁPIDA
# ══════════════════════════════════════════════

if __name__ == '__main__':
    from parser_recursivo  import ParserRecursivo
    from parser_predictivo import ParserPredictivo

    codigo = (
        "funcion factorial(entero n) retornar entero\n"
        "hacer\n"
        "    si n <= 1 entonces\n"
        "        retornar 1\n"
        "    sino\n"
        "        retornar n * factorial(n - 1)\n"
        "    fin_si\n"
        "fin_funcion\n"
    )

    for nombre, ParserClase in [("recursivo", ParserRecursivo),
                                ("predictivo", ParserPredictivo)]:
        p = ParserClase(codigo)
        p.analizar()
        r = AnalizadorSemantico(p.arbol_raiz).analizar()
        print(f"── {nombre} ──")
        print("  valido_semantico:", r["valido_semantico"])
        print("  errores semánticos:", len(r["errores_semanticos"]))
        for e in r["errores_semanticos"]:
            print(f"    [{e['indice']}] L{e['fila']}:C{e['columna']} "
                  f"{e['regla']}: {e['mensaje']}")
        print("  símbolos:", len(r["simbolos"]))
        for s in r["simbolos"]:
            print(f"    {s['nombre']}:{s['tipo']} "
                  f"({s['categoria']}, ámbito={s['ambito']})")
        print()
