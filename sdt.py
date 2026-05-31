"""
╔══════════════════════════════════════════════════════════╗
║   DiamondLang 💎 — Traducción Dirigida por la Sintaxis    ║
║                        sdt.py                            ║
║  Entrega Final — Fase B.                                 ║
║                                                         ║
║  Toma el CST de un programa DiamondLang YA validado      ║
║  (sintáctica y semánticamente) y produce código Julia.   ║
║                                                         ║
║  Patrón: visitor sobre el CST (igual que semantico.py).  ║
║  Pre-condición: el árbol es válido. Este módulo NO        ║
║  valida; asume que las fases previas ya lo hicieron.      ║
║                                                         ║
║  Diseño completo en SDT_DESIGN.md (Fase A).             ║
╚══════════════════════════════════════════════════════════╝

Decisiones de Fase B (aprobadas por el usuario):
  · Concatenación de cadenas  "a" + "b"  →  "a" * "b"   (operador * de Julia)
  · División entera  entero / entero      →  a ÷ b        (Unicode ÷, da Int)
    División con algún real                →  a / b        (da Float64)
  · leer(var) → var = parse(Tipo, readline())  (cadena: sin parse)
  · si/sino con UN solo si anidado          → elseif       (colapso)
  · Identificadores con tildes/ñ            → tal cual (Julia soporta Unicode)
  · Tipos:  entero→Int  real→Float64  cadena→String  booleano→Bool  vacio→Nothing
"""

import re

from arbol import (
    etiqueta_normalizada,
    raiz_logica,
    primer_terminal,
    extraer_expresiones_de_argumentos,
)
# Se REUSAN las reglas de tipo del análisis semántico para no duplicar la
# lógica de inferencia (consistencia con tipos.py).
from tipos import unificar_aritmetico


# ══════════════════════════════════════════════
#  MAPEO DE TIPOS DiamondLang → Julia
# ══════════════════════════════════════════════
_TIPOS_JULIA = {
    'entero':   'Int',
    'real':     'Float64',
    'cadena':   'String',
    'booleano': 'Bool',
    'vacio':    'Nothing',
}

_INDENT = '    '   # 4 espacios por nivel


class TraductorJulia:
    """
    Visitor que recorre el CST y acumula código Julia.

    Estado:
      · self.salida        — lista de fragmentos; al final "".join(...).
      · self.nivel         — nivel de indentación actual (entero).
      · self.scopes        — pila de dicts nombre→tipo (entorno de tipos propio
                             del SDT; la tabla del semántico ya cerró sus
                             ámbitos, ver SDT_DESIGN.md §4 y §Apéndice.8).
      · self.funciones     — registro nombre→{params, retorno, aridad}
                             (pre-escaneado para tipar llamadas y detectar
                             'principal').
    """

    def __init__(self, arbol, tabla_simbolos=None, fecha=None, con_header=True):
        self.arbol = arbol
        self.tabla = tabla_simbolos        # fuente secundaria (no imprescindible)
        self.fecha = fecha
        self.con_header = con_header
        self.salida = []
        self.nivel = 0
        self.scopes = [{}]                 # ámbito global en la base
        self.funciones = {}

    # ──────────────────────────────────────────
    #  API pública
    # ──────────────────────────────────────────
    def traducir(self) -> str:
        raiz = raiz_logica(self.arbol)
        self._prescan_funciones(raiz)

        if self.con_header:
            self._emit('# Código Julia generado por DiamondLang Compiler v4.0\n')
            if self.fecha:
                self._emit(f'# Fecha de generación: {self.fecha}\n')
            self._emit('\n')

        for contenido in self._declaraciones(raiz):
            norm = etiqueta_normalizada(contenido.etiqueta)
            if norm == 'def_funcion':
                self._visitar_def_funcion(contenido)
            elif norm == 'sentencia':
                # Sentencia suelta de nivel superior (la gramática lo permite).
                self._visitar_sentencia(contenido)

        # Punto de entrada: si existe 'principal' sin parámetros, invocarla.
        prin = self.funciones.get('principal')
        if prin and prin['aridad'] == 0:
            self._emit('principal()\n')

        return ''.join(self.salida)

    # ──────────────────────────────────────────
    #  Emisión / indentación
    # ──────────────────────────────────────────
    def _emit(self, texto):
        self.salida.append(texto)

    def _indent(self) -> str:
        return _INDENT * self.nivel

    def _linea(self, texto):
        """Emite una línea con la indentación actual."""
        self.salida.append(self._indent() + texto + '\n')

    def _entrar_bloque(self):
        self.nivel += 1

    def _salir_bloque(self):
        self.nivel -= 1

    # ──────────────────────────────────────────
    #  Helpers de navegación del CST
    # ──────────────────────────────────────────
    def _hijo_norm(self, nodo, norm):
        """Primer hijo directo cuya etiqueta normalizada == norm, o None."""
        if nodo is None:
            return None
        for h in nodo.hijos:
            if etiqueta_normalizada(h.etiqueta) == norm:
                return h
        return None

    def _hijos_norm(self, nodo, norm):
        return [h for h in nodo.hijos
                if etiqueta_normalizada(h.etiqueta) == norm]

    def _declaraciones(self, programa_node):
        """Lista PLANA del contenido de cada `declaracion` (def_funcion o
        sentencia), en orden de aparición, recorriendo la cadena `programa`."""
        out = []

        def rec(n):
            for h in n.hijos:
                norm = etiqueta_normalizada(h.etiqueta)
                if norm == 'declaracion':
                    if h.hijos:
                        out.append(h.hijos[0])   # def_funcion | sentencia
                elif norm == 'programa':
                    rec(h)

        rec(programa_node)
        return out

    def _sentencias(self, bloque_node):
        """Lista de nodos `sentencia` de un bloque (recorre la cadena bloque')."""
        out = []

        def rec(n):
            for h in n.hijos:
                norm = etiqueta_normalizada(h.etiqueta)
                if norm == 'sentencia':
                    out.append(h)
                elif norm == 'bloque_prima':
                    rec(h)

        rec(bloque_node)
        return out

    def _nombre_tipo(self, tipo_node):
        """Devuelve el lexema del tipo ('entero', 'real', ...)."""
        t = primer_terminal(tipo_node)
        return t.etiqueta if t else 'entero'

    def _traducir_tipo(self, tipo_dml: str) -> str:
        return _TIPOS_JULIA.get(tipo_dml, 'Any')

    # ── Entorno de tipos del SDT ──
    def _registrar_tipo(self, nombre, tipo):
        self.scopes[-1][nombre] = tipo

    def _tipo_var(self, nombre):
        for scope in reversed(self.scopes):
            if nombre in scope:
                return scope[nombre]
        return None

    # ──────────────────────────────────────────
    #  Pre-escaneo de firmas de función
    # ──────────────────────────────────────────
    def _prescan_funciones(self, programa_node):
        for contenido in self._declaraciones(programa_node):
            if etiqueta_normalizada(contenido.etiqueta) == 'def_funcion':
                nombre = contenido.hijos[1].etiqueta
                params = self._parametros(self._hijo_norm(contenido, 'parametros'))
                ret = self._tipo_retorno(self._hijo_norm(contenido, 'tipo_retorno_opt'))
                self.funciones[nombre] = {
                    'params':  params,
                    'retorno': ret or 'vacio',
                    'aridad':  len(params),
                }

    def _parametros(self, parametros_node):
        """Lista de (nombre, tipo) de un nodo `parametros`."""
        out = []
        if parametros_node is None:
            return out
        pl = self._hijo_norm(parametros_node, 'param_lista')
        if pl is None:
            return out
        # param_lista → tipo IDENTIFICADOR param_lista'
        out.append((pl.hijos[1].etiqueta, self._nombre_tipo(pl.hijos[0])))
        prima = pl.hijos[2]
        # param_lista' → , tipo IDENTIFICADOR param_lista' | ε
        while len(prima.hijos) >= 4 and prima.hijos[0].etiqueta == ',':
            out.append((prima.hijos[2].etiqueta, self._nombre_tipo(prima.hijos[1])))
            prima = prima.hijos[3]
        return out

    def _tipo_retorno(self, tro_node):
        """tipo_retorno_opt → retornar tipo | ε  →  devuelve el tipo o None."""
        if tro_node is None:
            return None
        tipo_node = self._hijo_norm(tro_node, 'tipo')
        return self._nombre_tipo(tipo_node) if tipo_node else None

    # ──────────────────────────────────────────
    #  Declaraciones de función
    # ──────────────────────────────────────────
    def _visitar_def_funcion(self, nodo):
        nombre = nodo.hijos[1].etiqueta
        params = self._parametros(self._hijo_norm(nodo, 'parametros'))
        ret = self._tipo_retorno(self._hijo_norm(nodo, 'tipo_retorno_opt'))
        bloque = self._hijo_norm(nodo, 'bloque')

        params_str = ', '.join(
            f'{n}::{self._traducir_tipo(t)}' for n, t in params)
        cabecera = f'function {nombre}({params_str})'
        # 'vacio' (o sin retorno declarado) → sin anotación de retorno.
        if ret and ret != 'vacio':
            cabecera += f'::{self._traducir_tipo(ret)}'
        self._linea(cabecera)

        self.scopes.append({})
        for n, t in params:
            self._registrar_tipo(n, t)
        self._entrar_bloque()
        self._traducir_bloque(bloque)
        self._salir_bloque()
        self.scopes.pop()

        self._linea('end')
        self._emit('\n')

    def _traducir_bloque(self, bloque_node):
        if bloque_node is None:
            return
        for sentencia in self._sentencias(bloque_node):
            self._visitar_sentencia(sentencia)

    def _visitar_sentencia(self, sentencia_node):
        """Despacha el contenido de un nodo `sentencia`."""
        if not sentencia_node.hijos:
            return
        contenido = sentencia_node.hijos[0]
        norm = etiqueta_normalizada(contenido.etiqueta)
        despacho = {
            'decl_variable':  self._visitar_decl_variable,
            'sentencia_id':   self._visitar_sentencia_id,
            'sent_si':        self._visitar_sent_si,
            'sent_mientras':  self._visitar_sent_mientras,
            'sent_para':      self._visitar_sent_para,
            'sent_retornar':  self._visitar_sent_retornar,
            'sent_escribir':  self._visitar_sent_escribir,
            'sent_leer':      self._visitar_sent_leer,
        }
        fn = despacho.get(norm)
        if fn:
            fn(contenido)
        else:
            # Consideración I: nunca lanzar; emitir TODO y continuar.
            self._linea(f'# TODO: nodo "{contenido.etiqueta}" sin implementar')

    # ──────────────────────────────────────────
    #  Sentencias
    # ──────────────────────────────────────────
    def _visitar_decl_variable(self, nodo):
        # decl_variable → tipo IDENTIFICADOR <- expresion
        tipo = self._nombre_tipo(self._hijo_norm(nodo, 'tipo'))
        nombre = nodo.hijos[1].etiqueta
        expr = self._hijo_norm(nodo, 'expresion')
        codigo, _ = self._traducir_expresion(expr)
        self._linea(f'{nombre}::{self._traducir_tipo(tipo)} = {codigo}')
        # Registrar DESPUÉS de traducir el RHS (el RHS no puede usar 'nombre').
        self._registrar_tipo(nombre, tipo)

    def _visitar_sentencia_id(self, nodo):
        # sentencia_id → IDENTIFICADOR (  <- expresion  |  ( argumentos )  )
        nombre = nodo.hijos[0].etiqueta
        cola = self._hijo_norm(nodo, 'sentencia_id_cola')
        if cola is None or not cola.hijos:
            return
        if cola.hijos[0].es_terminal and cola.hijos[0].etiqueta == '<-':
            expr = self._hijo_norm(cola, 'expresion')
            codigo, _ = self._traducir_expresion(expr)
            self._linea(f'{nombre} = {codigo}')
        else:
            # llamada-sentencia: ( argumentos )
            args_node = self._hijo_norm(cola, 'argumentos')
            args = [self._traducir_expresion(e)[0]
                    for e in extraer_expresiones_de_argumentos(args_node)]
            self._linea(f'{nombre}({", ".join(args)})')

    def _visitar_sent_si(self, nodo):
        """Emite el if/elseif/else completo y un único `end`."""
        self._emit_si(nodo, 'if')
        self._linea('end')

    def _emit_si(self, nodo, palabra):
        # sent_si → si expresion entonces bloque rama_sino fin_si
        cond, _ = self._traducir_expresion(self._hijo_norm(nodo, 'expresion'))
        self._linea(f'{palabra} {cond}')
        self._entrar_bloque()
        self._traducir_bloque(self._hijo_norm(nodo, 'bloque'))
        self._salir_bloque()

        rama = self._hijo_norm(nodo, 'rama_sino')
        sino_bloque = self._rama_sino_bloque(rama)
        if sino_bloque is None:
            return
        # Colapso a elseif: el bloque 'sino' contiene EXACTAMENTE un sent_si.
        anidado = self._unico_sent_si(sino_bloque)
        if anidado is not None:
            self._emit_si(anidado, 'elseif')
        else:
            self._linea('else')
            self._entrar_bloque()
            self._traducir_bloque(sino_bloque)
            self._salir_bloque()

    def _rama_sino_bloque(self, rama_node):
        """rama_sino → sino bloque | ε  →  bloque o None."""
        if rama_node is None:
            return None
        if rama_node.hijos and rama_node.hijos[0].es_terminal \
                and rama_node.hijos[0].etiqueta == 'sino':
            return self._hijo_norm(rama_node, 'bloque')
        return None

    def _unico_sent_si(self, bloque_node):
        """Si el bloque tiene EXACTAMENTE una sentencia que es un sent_si,
        devuelve ese nodo sent_si; si no, None (no se colapsa a elseif)."""
        sentencias = self._sentencias(bloque_node)
        if len(sentencias) != 1:
            return None
        contenido = sentencias[0].hijos[0] if sentencias[0].hijos else None
        if contenido is not None and \
                etiqueta_normalizada(contenido.etiqueta) == 'sent_si':
            return contenido
        return None

    def _visitar_sent_mientras(self, nodo):
        # sent_mientras → mientras expresion hacer bloque fin_mientras
        cond, _ = self._traducir_expresion(self._hijo_norm(nodo, 'expresion'))
        self._linea(f'while {cond}')
        self._entrar_bloque()
        self._traducir_bloque(self._hijo_norm(nodo, 'bloque'))
        self._salir_bloque()
        self._linea('end')

    def _visitar_sent_para(self, nodo):
        # sent_para → para ID desde E1 hasta E2 paso_opt hacer bloque fin_para
        nombre = nodo.hijos[1].etiqueta
        exprs = self._hijos_norm(nodo, 'expresion')   # [E1 (desde), E2 (hasta)]
        e1, e1_tipo = self._traducir_expresion(exprs[0])
        e2, _ = self._traducir_expresion(exprs[1])
        paso_opt = self._hijo_norm(nodo, 'paso_opt')
        paso = None
        if paso_opt is not None and len(paso_opt.hijos) >= 2:
            paso, _ = self._traducir_expresion(self._hijo_norm(paso_opt, 'expresion'))
        rango = f'{e1}:{paso}:{e2}' if paso is not None else f'{e1}:{e2}'
        self._linea(f'for {nombre} in {rango}')
        # si/mientras/para NO abren ámbito (decisión de DiamondLang): la var de
        # iteración vive en el ámbito de la función.
        self._registrar_tipo(nombre, e1_tipo or 'entero')
        self._entrar_bloque()
        self._traducir_bloque(self._hijo_norm(nodo, 'bloque'))
        self._salir_bloque()
        self._linea('end')

    def _visitar_sent_retornar(self, nodo):
        # sent_retornar → retornar expresion  (siempre con expresión)
        codigo, _ = self._traducir_expresion(self._hijo_norm(nodo, 'expresion'))
        self._linea(f'return {codigo}')

    def _visitar_sent_escribir(self, nodo):
        # sent_escribir → escribir ( expresion )   (un solo argumento)
        codigo, _ = self._traducir_expresion(self._hijo_norm(nodo, 'expresion'))
        self._linea(f'println({codigo})')

    def _visitar_sent_leer(self, nodo):
        # sent_leer → leer ( IDENTIFICADOR )
        nombre = nodo.hijos[2].etiqueta
        tipo = self._tipo_var(nombre)
        if tipo == 'cadena':
            self._linea(f'{nombre} = readline()')
        else:
            jt = self._traducir_tipo(tipo) if tipo else 'String'
            if tipo is None:
                # variable sin tipo conocido → fallback a String (no rompe)
                self._linea(f'{nombre} = readline()')
            else:
                self._linea(f'{nombre} = parse({jt}, readline())')

    # ──────────────────────────────────────────
    #  Expresiones  →  (codigo_julia, tipo_inferido)
    # ──────────────────────────────────────────
    def _traducir_expresion(self, nodo):
        if nodo is None:
            return '', 'entero'
        norm = etiqueta_normalizada(nodo.etiqueta)

        if norm == 'expresion':
            return self._traducir_expresion(self._hijo_norm(nodo, 'expr_or'))
        if norm == 'expr_or':
            return self._fold(nodo, lambda op, a, b: ' || ',
                              lambda a, b, op: 'booleano')
        if norm == 'expr_and':
            return self._fold(nodo, lambda op, a, b: ' && ',
                              lambda a, b, op: 'booleano')
        if norm == 'expr_rel':
            return self._trad_expr_rel(nodo)
        if norm == 'expr_add':
            return self._fold(nodo, self._op_add, unificar_aritmetico)
        if norm == 'expr_mul':
            return self._fold(nodo, self._op_mul, unificar_aritmetico)
        if norm == 'expr_pot':
            return self._trad_expr_pot(nodo)
        if norm == 'expr_unaria':
            return self._trad_expr_unaria(nodo)
        if norm == 'expr_primaria':
            return self._trad_expr_primaria(nodo)

        # Cualquier envoltorio inesperado: descender al primer hijo.
        if nodo.hijos:
            return self._traducir_expresion(nodo.hijos[0])
        return '', 'entero'

    def _fold(self, nodo, op_decide, tipo_combine):
        """Pliega una cadena binaria izquierda: operando (op operando)*.
        nodo.hijos = [operando, prima];  prima = [op, operando, prima] | [ε]."""
        codigo, tipo = self._traducir_expresion(nodo.hijos[0])
        prima = nodo.hijos[1]
        while (len(prima.hijos) >= 3 and prima.hijos[0].es_terminal
               and prima.hijos[0].etiqueta != 'ε'):
            op = prima.hijos[0].etiqueta
            rcod, rtipo = self._traducir_expresion(prima.hijos[1])
            codigo = codigo + op_decide(op, tipo, rtipo) + rcod
            tipo = tipo_combine(tipo, rtipo, op)
            prima = prima.hijos[2]
        return codigo, tipo

    def _op_add(self, op, t1, t2):
        # '+' sobre cadenas → '*' (concatenación en Julia); si no, '+'.
        if op == '+':
            return ' * ' if (t1 == 'cadena' or t2 == 'cadena') else ' + '
        return ' - '

    def _op_mul(self, op, t1, t2):
        # '/' entre dos enteros → '÷' (división entera); si no, '/'.
        if op == '/':
            return ' ÷ ' if (t1 == 'entero' and t2 == 'entero') else ' / '
        return f' {op} '   # '*'  o  '%'

    def _trad_expr_rel(self, nodo):
        # expr_rel → expr_add expr_rel' ;  expr_rel' → op_rel expr_add | ε
        lcod, ltipo = self._traducir_expresion(nodo.hijos[0])
        prima = nodo.hijos[1]
        op_rel = self._hijo_norm(prima, 'op_rel')
        if op_rel is not None:
            op = primer_terminal(op_rel).etiqueta            # idéntico en Julia
            rexpr = self._hijo_norm(prima, 'expr_add')
            rcod, _ = self._traducir_expresion(rexpr)
            return f'{lcod} {op} {rcod}', 'booleano'
        return lcod, ltipo

    def _trad_expr_pot(self, nodo):
        # expr_pot → expr_unaria expr_pot' ;  expr_pot' → ** expr_pot | ε
        bcod, btipo = self._traducir_expresion(nodo.hijos[0])
        prima = nodo.hijos[1]
        if (len(prima.hijos) >= 2 and prima.hijos[0].es_terminal
                and prima.hijos[0].etiqueta == '**'):
            rcod, rtipo = self._traducir_expresion(prima.hijos[1])
            return f'{bcod} ^ {rcod}', unificar_aritmetico(btipo, rtipo, '**')
        return bcod, btipo

    def _trad_expr_unaria(self, nodo):
        # expr_unaria → no expr_unaria | - expr_unaria | expr_primaria
        first = nodo.hijos[0]
        if first.es_terminal and first.etiqueta == 'no':
            cod, _ = self._traducir_expresion(nodo.hijos[1])
            return f'!{cod}', 'booleano'
        if first.es_terminal and first.etiqueta == '-':
            cod, tipo = self._traducir_expresion(nodo.hijos[1])
            return f'-{cod}', tipo
        return self._traducir_expresion(first)

    def _trad_expr_primaria(self, nodo):
        hijos = nodo.hijos
        # ENTERO | REAL | CADENA | verdadero | falso  (un solo terminal)
        if len(hijos) == 1 and hijos[0].es_terminal:
            return self._trad_literal(hijos[0].etiqueta)
        # ( expresion )
        if hijos[0].es_terminal and hijos[0].etiqueta == '(':
            cod, tipo = self._traducir_expresion(hijos[1])
            return f'({cod})', tipo
        # IDENTIFICADOR sufijo_id
        nombre = hijos[0].etiqueta
        sufijo = hijos[1]
        if (sufijo.hijos and sufijo.hijos[0].es_terminal
                and sufijo.hijos[0].etiqueta == '('):
            # llamada a función como expresión
            args_node = self._hijo_norm(sufijo, 'argumentos')
            args = [self._traducir_expresion(e)[0]
                    for e in extraer_expresiones_de_argumentos(args_node)]
            ret = self.funciones.get(nombre, {}).get('retorno', 'entero')
            return f'{nombre}({", ".join(args)})', ret
        # variable simple
        return nombre, (self._tipo_var(nombre) or 'entero')

    def _trad_literal(self, lex):
        if lex == 'verdadero':
            return 'true', 'booleano'
        if lex == 'falso':
            return 'false', 'booleano'
        if lex[:1] in ('"', "'"):
            return self._cadena_julia(lex), 'cadena'
        if re.fullmatch(r'\d+\.\d+', lex):
            return lex, 'real'
        if re.fullmatch(r'\d+', lex):
            return lex, 'entero'
        return lex, 'entero'   # fallback defensivo (no debería ocurrir)

    # ──────────────────────────────────────────
    #  Cadenas:  re-encomillado y escape para Julia
    # ──────────────────────────────────────────
    def _cadena_julia(self, lexema):
        """Convierte un literal de cadena DiamondLang ('..' o "..") a un
        literal Julia con comillas dobles, escapando lo necesario (incluido el
        '$' que Julia usa para interpolar)."""
        valor = self._valor_cadena(lexema)
        s = (valor.replace('\\', '\\\\')
                  .replace('"', '\\"')
                  .replace('$', '\\$')
                  .replace('\n', '\\n')
                  .replace('\t', '\\t')
                  .replace('\r', '\\r'))
        return f'"{s}"'

    def _valor_cadena(self, lexema):
        """Decodifica el literal DiamondLang a su valor real (quita comillas
        externas y resuelve los escapes \\n \\t \\\\ \\" \\' ...)."""
        inner = lexema[1:-1]
        out = []
        i = 0
        escapes = {'n': '\n', 't': '\t', 'r': '\r', '\\': '\\',
                   '"': '"', "'": "'", '0': '\0'}
        while i < len(inner):
            c = inner[i]
            if c == '\\' and i + 1 < len(inner):
                nxt = inner[i + 1]
                out.append(escapes.get(nxt, nxt))
                i += 2
            else:
                out.append(c)
                i += 1
        return ''.join(out)


# ══════════════════════════════════════════════
#  PUNTO DE ENTRADA PÚBLICO
# ══════════════════════════════════════════════
def traducir(arbol, tabla_simbolos=None, fecha=None, con_header=True) -> str:
    """
    Traduce el CST `arbol` (ya validado) a código fuente Julia.

    Parámetros:
        arbol          — raíz del CST (NodoArbol). Se normaliza con raiz_logica.
        tabla_simbolos — TablaSimbolos del análisis semántico (opcional; el SDT
                         mantiene su propio entorno de tipos, ver SDT_DESIGN.md).
        fecha          — string ISO-8601 para el header (lo inyecta el endpoint;
                         None en tests para salida determinista).
        con_header     — si False, omite el comentario de cabecera (útil para
                         comparaciones golden en tests).

    Retorna: el código Julia como string.
    """
    return TraductorJulia(arbol, tabla_simbolos, fecha=fecha,
                          con_header=con_header).traducir()
