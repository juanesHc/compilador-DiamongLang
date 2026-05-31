"""
╔══════════════════════════════════════════════════════════╗
║   DiamondLang 💎 — Parser Descendente Recursivo         ║
║               parser_recursivo.py                       ║
║  Una función por cada no-terminal de la gramática.      ║
║  Construye el árbol sintáctico como JSON serializable   ║
║  para ser dibujado en el navegador (sin dependencias).  ║
║                                                         ║
║  Entrega 3: recuperación en modo pánico — el parser     ║
║  reporta TODOS los errores en una sola pasada y         ║
║  continúa hasta agotar la entrada (o hasta              ║
║  MAX_ERRORES). El árbol sigue construyéndose;           ║
║  cada error inserta un nodo "ERROR<…>" como marcador.   ║
╚══════════════════════════════════════════════════════════╝
"""

from lexico.lexer import Lexer, Token

from sintactico.arbol import NodoArbol, propagar_posicion_terminales
from sintactico.errores import ErrorSintactico, formatear_error
from sintactico.sugerencias import sugerencia_local
from sintactico.recuperacion import (
    conjunto_sync_para, sincronizar,
    SYNC_SENTENCIA, SYNC_GLOBAL, INICIOS_SENTENCIA,
)


# ══════════════════════════════════════════════
#  CLASE PARSER RECURSIVO
# ══════════════════════════════════════════════

class ParserRecursivo:
    """
    Analizador sintáctico descendente recursivo para DiamondLang.

    Uso:
        parser = ParserRecursivo("funcion f() hacer escribir(1) fin_funcion")
        resultado = parser.analizar()
        # resultado['valido'], resultado['errores'], resultado['nodos']
    """

    # Conjuntos de sincronización (cargados perezosamente)
    _SIGUIENTE_CACHE = None

    @classmethod
    def _cargar_siguiente(cls):
        if cls._SIGUIENTE_CACHE is None:
            from sintactico.tabla_ll import generar_tabla
            _, sig, _ = generar_tabla()
            cls._SIGUIENTE_CACHE = sig

    def __init__(self, codigo_fuente: str, max_errores: int = 100):
        ParserRecursivo._cargar_siguiente()

        # Tokenizar con el lexer de la Entrega 1
        lex = Lexer(codigo_fuente)
        tokens_raw, _ = lex.tokenizar()

        # Filtrar comentarios (no son parte de la sintaxis)
        self.tokens     = [t for t in tokens_raw if t.tipo != 'COMENTARIO']
        self.pos        = 0
        self.errores    = []         # lista de ErrorSintactico
        self.error      = None       # compatibilidad: primer error formateado
        self.max_errores = max_errores
        self.pasos      = []         # log de derivaciones para depuración

        # Detector de bucles infinitos: si llamamos consumir/sync sin avanzar
        # demasiadas veces, abortamos.
        self._iters_sin_avance = 0
        self._pos_anterior     = -1

    # ── Utilidades ──────────────────────────────

    def token_actual(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        # Token centinela EOF — usamos la última posición conocida
        if self.tokens:
            ult = self.tokens[-1]
            return Token('$', '$', ult.linea, ult.columna + len(ult.lexema))
        return Token('$', '$', 1, 1)

    def tipo_actual(self) -> str:
        t = self.token_actual()
        # Para keywords, tipos, booleanos y operadores usamos el lexema
        if t.tipo in ('KEYWORD', 'TIPO', 'BOOLEANO', 'OPERADOR', 'SIMBOLO'):
            return t.lexema
        return t.tipo    # IDENTIFICADOR, ENTERO, REAL, CADENA, $

    def _sync_para(self, no_terminal: str) -> set:
        return conjunto_sync_para(
            no_terminal or 'sentencia',
            self._SIGUIENTE_CACHE,
        )

    def _sigue_vivo(self) -> bool:
        """True si aún podemos seguir reportando errores."""
        return len(self.errores) < self.max_errores

    def _registrar_error(self, no_terminal: str, esperados,
                         produccion: str = None, padre: NodoArbol = None) -> None:
        """
        Registra un error sintáctico y, opcionalmente, inserta un nodo
        ERROR<lexema> en el árbol como marcador visual.
        """
        tok      = self.token_actual()
        esperados_lst = list(esperados) if esperados else []

        e = ErrorSintactico(
            indice=len(self.errores) + 1,
            fila=tok.linea,
            columna=tok.columna,
            lexema=tok.lexema,
            tipo_token=tok.tipo,
            tokens_esperados=esperados_lst,
            no_terminal=no_terminal,
            produccion_intentada=produccion,
            sugerencia=sugerencia_local(no_terminal, esperados_lst,
                                        tok.lexema, tok.tipo),
        )
        self.errores.append(e)

        # Compatibilidad: self.error contiene el primer error formateado
        if self.error is None:
            self.error = formatear_error(e)

        if padre is not None:
            padre.agregar_hijo(
                NodoArbol(f"ERROR<{tok.lexema}>",
                          es_terminal=True, es_error=True,
                          linea=tok.linea, columna=tok.columna)
            )

    def consumir(self, esperado: str, padre: NodoArbol,
                 no_terminal: str = None) -> bool:
        """
        Intenta consumir el token actual si coincide con `esperado`.
        Si no coincide, registra error y aplica modo pánico:

          1. Sincroniza con SYNC(no_terminal) ∪ {esperado}.
          2. Si tras sincronizar el token actual ES `esperado`, lo
             consume (era un token sobrante por delante).
          3. En caso contrario inserta un marcador ERROR y deja el
             lookahead donde quedó (inserción implícita).

        Devuelve True salvo que se haya superado MAX_ERRORES (fatal).
        """
        actual = self.tipo_actual()
        if actual == esperado:
            tok = self.token_actual()
            padre.agregar_hijo(NodoArbol(tok.lexema, es_terminal=True,
                                         linea=tok.linea, columna=tok.columna))
            self.pos += 1
            return True

        # ── Error: no coincidió ──
        self._registrar_error(no_terminal or 'sentencia',
                              [esperado], padre=None)
        if not self._sigue_vivo():
            return False

        # ── Recuperación: sincronizar ──
        sync_set = self._sync_para(no_terminal) | {esperado}
        nueva_pos, _ = sincronizar(self.tokens, self.pos, sync_set)
        self.pos = nueva_pos

        if self.tipo_actual() == esperado:
            # El token esperado estaba un poco más adelante — lo consumimos
            tok = self.token_actual()
            padre.agregar_hijo(NodoArbol(tok.lexema, es_terminal=True,
                                         linea=tok.linea, columna=tok.columna))
            self.pos += 1
        else:
            # Inserción implícita: marcador en el árbol, no consumimos.
            # Posición = la del token actual (el que estaba en el lookahead).
            tok = self.token_actual()
            padre.agregar_hijo(
                NodoArbol(f"ERROR<falta '{esperado}'>",
                          es_terminal=True, es_error=True,
                          linea=tok.linea, columna=tok.columna)
            )
        return True

    # ── Punto de entrada ────────────────────────

    def analizar(self) -> dict:
        raiz = NodoArbol('programa')
        self.arbol_raiz = raiz   # expuesto para fases posteriores (semántica)
        try:
            self.parse_programa(raiz)
        except _AbortoFatal:
            pass

        # Verificar que se consumió toda la entrada
        if self._sigue_vivo() and self.tipo_actual() != '$':
            tok = self.token_actual()
            self._registrar_error(
                'programa',
                ['$'],
                produccion="(fin de programa)",
                padre=raiz,
            )
            # Saltamos el resto para no emitir un error por cada token
            self.pos = len(self.tokens)

        # Propagar posición desde los terminales a sus ancestros no terminales
        propagar_posicion_terminales(raiz)

        valido = (len(self.errores) == 0)
        return {
            'valido':   valido,
            'errores':  [e.to_dict() for e in self.errores],
            'error':    self.error,
            'nodos':    self._serializar_arbol(raiz),
        }

    # ══════════════════════════════════════════
    #  FUNCIONES DE PARSE — una por no-terminal
    # ══════════════════════════════════════════

    def parse_programa(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol('programa')
        padre.agregar_hijo(nodo)
        # programa ::= declaracion* (se repite mientras haya tokens)
        inicio_decl = {
            'funcion','si','mientras','para','retornar',
            'escribir','leer',
            'entero','real','cadena','booleano','vacio',
            'IDENTIFICADOR',
        }
        while self.tipo_actual() in inicio_decl:
            if not self._sigue_vivo(): return False
            self._chequear_avance('programa')
            if not self.parse_declaracion(nodo): return False
        return True

    def _chequear_avance(self, nt: str):
        """
        Detecta bucles infinitos: si llamamos a un parser repetidamente
        sin que `self.pos` avance, abortamos con _AbortoFatal.
        """
        if self.pos == self._pos_anterior:
            self._iters_sin_avance += 1
            if self._iters_sin_avance > 200:
                self._registrar_error(nt, ['$'],
                                      produccion="(bucle de recuperación)")
                raise _AbortoFatal()
        else:
            self._iters_sin_avance = 0
            self._pos_anterior = self.pos

    def parse_declaracion(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol('declaracion')
        padre.agregar_hijo(nodo)
        ta = self.tipo_actual()
        if ta == 'funcion':
            return self.parse_def_funcion(nodo)
        else:
            return self.parse_sentencia(nodo)

    # ── Funciones ──
    def parse_def_funcion(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol('def_funcion')
        padre.agregar_hijo(nodo)
        return (self.consumir('funcion', nodo, 'def_funcion') and
                self.consumir('IDENTIFICADOR', nodo, 'def_funcion') and
                self.consumir('(', nodo, 'def_funcion') and
                self.parse_parametros(nodo) and
                self.consumir(')', nodo, 'def_funcion') and
                self.parse_tipo_retorno_opt(nodo) and
                self.consumir('hacer', nodo, 'def_funcion') and
                self.parse_bloque(nodo) and
                self.consumir('fin_funcion', nodo, 'def_funcion'))

    def parse_tipo_retorno_opt(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol('tipo_retorno_opt')
        padre.agregar_hijo(nodo)
        if self.tipo_actual() == 'retornar':
            return (self.consumir('retornar', nodo, 'tipo_retorno_opt') and
                    self.parse_tipo(nodo))
        nodo.agregar_hijo(NodoArbol('ε', es_terminal=True))
        return True

    def parse_parametros(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol('parametros')
        padre.agregar_hijo(nodo)
        tipos = {'entero','real','cadena','booleano','vacio'}
        if self.tipo_actual() in tipos:
            return self.parse_param_lista(nodo)
        nodo.agregar_hijo(NodoArbol('ε', es_terminal=True))
        return True

    def parse_param_lista(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol('param_lista')
        padre.agregar_hijo(nodo)
        if not (self.parse_tipo(nodo) and
                self.consumir('IDENTIFICADOR', nodo, 'param_lista')):
            return False
        return self.parse_param_lista_prima(nodo)

    def parse_param_lista_prima(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol("param_lista'")
        padre.agregar_hijo(nodo)
        if self.tipo_actual() == ',':
            return (self.consumir(',', nodo, 'param_lista') and
                    self.parse_tipo(nodo) and
                    self.consumir('IDENTIFICADOR', nodo, 'param_lista') and
                    self.parse_param_lista_prima(nodo))
        nodo.agregar_hijo(NodoArbol('ε', es_terminal=True))
        return True

    # ── Tipos ──
    def parse_tipo(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol('tipo')
        padre.agregar_hijo(nodo)
        ta = self.tipo_actual()
        if ta in {'entero','real','cadena','booleano','vacio'}:
            return self.consumir(ta, nodo, 'tipo')
        # ── Error en tipo ──
        self._registrar_error(
            'tipo',
            ['entero','real','cadena','booleano','vacio'],
            produccion="tipo → entero | real | cadena | booleano | vacio",
            padre=nodo,
        )
        if not self._sigue_vivo(): return False
        sync = self._sync_para('tipo')
        nuevo, _ = sincronizar(self.tokens, self.pos, sync)
        self.pos = nuevo
        return True

    # ── Bloque y sentencias ──
    def parse_bloque(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol('bloque')
        padre.agregar_hijo(nodo)
        if not self.parse_sentencia(nodo): return False
        return self.parse_bloque_prima(nodo)

    def parse_bloque_prima(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol("bloque'")
        padre.agregar_hijo(nodo)
        inicio = {
            'si','mientras','para','retornar','escribir','leer',
            'entero','real','cadena','booleano','vacio','IDENTIFICADOR',
        }
        while self.tipo_actual() in inicio:
            if not self._sigue_vivo(): return False
            self._chequear_avance('bloque_prima')
            if not self.parse_sentencia(nodo): return False
        nodo.agregar_hijo(NodoArbol('ε', es_terminal=True))
        return True

    def parse_sentencia(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol('sentencia')
        padre.agregar_hijo(nodo)
        ta = self.tipo_actual()
        if ta in {'entero','real','cadena','booleano','vacio'}:
            return self.parse_decl_variable(nodo)
        elif ta == 'IDENTIFICADOR':
            return self.parse_sentencia_id(nodo)
        elif ta == 'si':
            return self.parse_sent_si(nodo)
        elif ta == 'mientras':
            return self.parse_sent_mientras(nodo)
        elif ta == 'para':
            return self.parse_sent_para(nodo)
        elif ta == 'retornar':
            return self.parse_sent_retornar(nodo)
        elif ta == 'escribir':
            return self.parse_sent_escribir(nodo)
        elif ta == 'leer':
            return self.parse_sent_leer(nodo)
        else:
            esperados = sorted({
                'entero','real','cadena','booleano','vacio','IDENTIFICADOR',
                'si','mientras','para','retornar','escribir','leer',
            })
            self._registrar_error('sentencia', esperados, padre=nodo)
            if not self._sigue_vivo(): return False
            sync = SYNC_SENTENCIA
            nuevo, _ = sincronizar(self.tokens, self.pos, sync)
            self.pos = nuevo
            return True

    def parse_decl_variable(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol('decl_variable')
        padre.agregar_hijo(nodo)
        return (self.parse_tipo(nodo) and
                self.consumir('IDENTIFICADOR', nodo, 'decl_variable') and
                self.consumir('<-', nodo, 'decl_variable') and
                self.parse_expresion(nodo))

    def parse_sentencia_id(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol('sentencia_id')
        padre.agregar_hijo(nodo)
        if not self.consumir('IDENTIFICADOR', nodo, 'sentencia_id'):
            return False
        return self.parse_sentencia_id_cola(nodo)

    def parse_sentencia_id_cola(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol("sentencia_id_cola")
        padre.agregar_hijo(nodo)
        ta = self.tipo_actual()
        if ta == '<-':
            return (self.consumir('<-', nodo, 'sentencia_id_cola') and
                    self.parse_expresion(nodo))
        elif ta == '(':
            return (self.consumir('(', nodo, 'sentencia_id_cola') and
                    self.parse_argumentos(nodo) and
                    self.consumir(')', nodo, 'sentencia_id_cola'))
        else:
            self._registrar_error('sentencia_id_cola', ['<-', '('],
                                  padre=nodo)
            if not self._sigue_vivo(): return False
            sync = self._sync_para('sentencia_id_cola')
            nuevo, _ = sincronizar(self.tokens, self.pos, sync)
            self.pos = nuevo
            return True

    # ── Condicional ──
    def parse_sent_si(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol('sent_si')
        padre.agregar_hijo(nodo)
        return (self.consumir('si', nodo, 'sent_si') and
                self.parse_expresion(nodo) and
                self.consumir('entonces', nodo, 'sent_si') and
                self.parse_bloque(nodo) and
                self.parse_rama_sino(nodo) and
                self.consumir('fin_si', nodo, 'sent_si'))

    def parse_rama_sino(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol('rama_sino')
        padre.agregar_hijo(nodo)
        if self.tipo_actual() == 'sino':
            return (self.consumir('sino', nodo, 'rama_sino') and
                    self.parse_bloque(nodo))
        nodo.agregar_hijo(NodoArbol('ε', es_terminal=True))
        return True

    # ── Mientras ──
    def parse_sent_mientras(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol('sent_mientras')
        padre.agregar_hijo(nodo)
        return (self.consumir('mientras', nodo, 'sent_mientras') and
                self.parse_expresion(nodo) and
                self.consumir('hacer', nodo, 'sent_mientras') and
                self.parse_bloque(nodo) and
                self.consumir('fin_mientras', nodo, 'sent_mientras'))

    # ── Para ──
    def parse_sent_para(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol('sent_para')
        padre.agregar_hijo(nodo)
        return (self.consumir('para', nodo, 'sent_para') and
                self.consumir('IDENTIFICADOR', nodo, 'sent_para') and
                self.consumir('desde', nodo, 'sent_para') and
                self.parse_expresion(nodo) and
                self.consumir('hasta', nodo, 'sent_para') and
                self.parse_expresion(nodo) and
                self.parse_paso_opt(nodo) and
                self.consumir('hacer', nodo, 'sent_para') and
                self.parse_bloque(nodo) and
                self.consumir('fin_para', nodo, 'sent_para'))

    def parse_paso_opt(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol('paso_opt')
        padre.agregar_hijo(nodo)
        if self.tipo_actual() == 'paso':
            return (self.consumir('paso', nodo, 'paso_opt') and
                    self.parse_expresion(nodo))
        nodo.agregar_hijo(NodoArbol('ε', es_terminal=True))
        return True

    # ── Retorno, escribir, leer ──
    def parse_sent_retornar(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol('sent_retornar')
        padre.agregar_hijo(nodo)
        return (self.consumir('retornar', nodo, 'sent_retornar') and
                self.parse_expresion(nodo))

    def parse_sent_escribir(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol('sent_escribir')
        padre.agregar_hijo(nodo)
        return (self.consumir('escribir', nodo, 'sent_escribir') and
                self.consumir('(', nodo, 'sent_escribir') and
                self.parse_expresion(nodo) and
                self.consumir(')', nodo, 'sent_escribir'))

    def parse_sent_leer(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol('sent_leer')
        padre.agregar_hijo(nodo)
        return (self.consumir('leer', nodo, 'sent_leer') and
                self.consumir('(', nodo, 'sent_leer') and
                self.consumir('IDENTIFICADOR', nodo, 'sent_leer') and
                self.consumir(')', nodo, 'sent_leer'))

    # ── Expresiones ──
    def parse_expresion(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol('expresion')
        padre.agregar_hijo(nodo)
        return self.parse_expr_or(nodo)

    def parse_expr_or(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol('expr_or')
        padre.agregar_hijo(nodo)
        return self.parse_expr_and(nodo) and self.parse_expr_or_prima(nodo)

    def parse_expr_or_prima(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol("expr_or'")
        padre.agregar_hijo(nodo)
        if self.tipo_actual() == 'o':
            return (self.consumir('o', nodo, 'expr_or') and
                    self.parse_expr_and(nodo) and
                    self.parse_expr_or_prima(nodo))
        nodo.agregar_hijo(NodoArbol('ε', es_terminal=True))
        return True

    def parse_expr_and(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol('expr_and')
        padre.agregar_hijo(nodo)
        return self.parse_expr_rel(nodo) and self.parse_expr_and_prima(nodo)

    def parse_expr_and_prima(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol("expr_and'")
        padre.agregar_hijo(nodo)
        if self.tipo_actual() == 'y':
            return (self.consumir('y', nodo, 'expr_and') and
                    self.parse_expr_rel(nodo) and
                    self.parse_expr_and_prima(nodo))
        nodo.agregar_hijo(NodoArbol('ε', es_terminal=True))
        return True

    def parse_expr_rel(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol('expr_rel')
        padre.agregar_hijo(nodo)
        return self.parse_expr_add(nodo) and self.parse_expr_rel_prima(nodo)

    def parse_expr_rel_prima(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol("expr_rel'")
        padre.agregar_hijo(nodo)
        ops = {'==','!=','<','>','<=','>='}
        if self.tipo_actual() in ops:
            return self.parse_op_rel(nodo) and self.parse_expr_add(nodo)
        nodo.agregar_hijo(NodoArbol('ε', es_terminal=True))
        return True

    def parse_op_rel(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol('op_rel')
        padre.agregar_hijo(nodo)
        ta = self.tipo_actual()
        if ta in {'==','!=','<','>','<=','>='}:
            return self.consumir(ta, nodo, 'op_rel')
        self._registrar_error('op_rel',
                              ['==','!=','<','>','<=','>='],
                              padre=nodo)
        if not self._sigue_vivo(): return False
        sync = self._sync_para('op_rel')
        nuevo, _ = sincronizar(self.tokens, self.pos, sync)
        self.pos = nuevo
        return True

    def parse_expr_add(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol('expr_add')
        padre.agregar_hijo(nodo)
        return self.parse_expr_mul(nodo) and self.parse_expr_add_prima(nodo)

    def parse_expr_add_prima(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol("expr_add'")
        padre.agregar_hijo(nodo)
        ta = self.tipo_actual()
        if ta in {'+','-'}:
            return (self.consumir(ta, nodo, 'expr_add') and
                    self.parse_expr_mul(nodo) and
                    self.parse_expr_add_prima(nodo))
        nodo.agregar_hijo(NodoArbol('ε', es_terminal=True))
        return True

    def parse_expr_mul(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol('expr_mul')
        padre.agregar_hijo(nodo)
        return self.parse_expr_pot(nodo) and self.parse_expr_mul_prima(nodo)

    def parse_expr_mul_prima(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol("expr_mul'")
        padre.agregar_hijo(nodo)
        ta = self.tipo_actual()
        if ta in {'*','/','%'}:
            return (self.consumir(ta, nodo, 'expr_mul') and
                    self.parse_expr_pot(nodo) and
                    self.parse_expr_mul_prima(nodo))
        nodo.agregar_hijo(NodoArbol('ε', es_terminal=True))
        return True

    def parse_expr_pot(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol('expr_pot')
        padre.agregar_hijo(nodo)
        return self.parse_expr_unaria(nodo) and self.parse_expr_pot_prima(nodo)

    def parse_expr_pot_prima(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol("expr_pot'")
        padre.agregar_hijo(nodo)
        if self.tipo_actual() == '**':
            return (self.consumir('**', nodo, 'expr_pot') and
                    self.parse_expr_pot(nodo))
        nodo.agregar_hijo(NodoArbol('ε', es_terminal=True))
        return True

    def parse_expr_unaria(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol('expr_unaria')
        padre.agregar_hijo(nodo)
        ta = self.tipo_actual()
        if ta == 'no':
            return (self.consumir('no', nodo, 'expr_unaria') and
                    self.parse_expr_unaria(nodo))
        elif ta == '-':
            return (self.consumir('-', nodo, 'expr_unaria') and
                    self.parse_expr_unaria(nodo))
        return self.parse_expr_primaria(nodo)

    def parse_expr_primaria(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol('expr_primaria')
        padre.agregar_hijo(nodo)
        ta = self.tipo_actual()
        if ta == 'ENTERO':
            return self.consumir('ENTERO', nodo, 'expr_primaria')
        elif ta == 'REAL':
            return self.consumir('REAL', nodo, 'expr_primaria')
        elif ta == 'CADENA':
            return self.consumir('CADENA', nodo, 'expr_primaria')
        elif ta == 'verdadero':
            return self.consumir('verdadero', nodo, 'expr_primaria')
        elif ta == 'falso':
            return self.consumir('falso', nodo, 'expr_primaria')
        elif ta == 'IDENTIFICADOR':
            return (self.consumir('IDENTIFICADOR', nodo, 'expr_primaria') and
                    self.parse_sufijo_id(nodo))
        elif ta == '(':
            return (self.consumir('(', nodo, 'expr_primaria') and
                    self.parse_expresion(nodo) and
                    self.consumir(')', nodo, 'expr_primaria'))
        else:
            esperados = ['ENTERO','REAL','CADENA','verdadero','falso',
                         'IDENTIFICADOR','(']
            self._registrar_error('expr_primaria', esperados, padre=nodo)
            if not self._sigue_vivo(): return False
            sync = self._sync_para('expr_primaria')
            nuevo, _ = sincronizar(self.tokens, self.pos, sync)
            self.pos = nuevo
            return True

    def parse_sufijo_id(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol('sufijo_id')
        padre.agregar_hijo(nodo)
        if self.tipo_actual() == '(':
            return (self.consumir('(', nodo, 'sufijo_id') and
                    self.parse_argumentos(nodo) and
                    self.consumir(')', nodo, 'sufijo_id'))
        nodo.agregar_hijo(NodoArbol('ε', es_terminal=True))
        return True

    def parse_argumentos(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol('argumentos')
        padre.agregar_hijo(nodo)
        inicio_expr = {'ENTERO','REAL','CADENA','IDENTIFICADOR',
                       'verdadero','falso','(','no','-'}
        if self.tipo_actual() in inicio_expr:
            return self.parse_arg_lista(nodo)
        nodo.agregar_hijo(NodoArbol('ε', es_terminal=True))
        return True

    def parse_arg_lista(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol('arg_lista')
        padre.agregar_hijo(nodo)
        return self.parse_expresion(nodo) and self.parse_arg_lista_prima(nodo)

    def parse_arg_lista_prima(self, padre: NodoArbol) -> bool:
        nodo = NodoArbol("arg_lista'")
        padre.agregar_hijo(nodo)
        if self.tipo_actual() == ',':
            return (self.consumir(',', nodo, 'arg_lista') and
                    self.parse_expresion(nodo) and
                    self.parse_arg_lista_prima(nodo))
        nodo.agregar_hijo(NodoArbol('ε', es_terminal=True))
        return True

    def _serializar_arbol(self, nodo: NodoArbol) -> dict:
        """Serializa el árbol a dict JSON-serializable para dibujarlo en el navegador."""
        return {
            'id':           nodo.id,
            'etiqueta':     nodo.etiqueta,
            'es_terminal':  nodo.es_terminal,
            'es_error':     nodo.es_error,
            'hijos':        [self._serializar_arbol(h) for h in nodo.hijos],
        }


# Excepción interna usada para abortar el parse cuando detectamos un
# bucle de recuperación (no se filtra al usuario).
class _AbortoFatal(Exception):
    pass


# ── Prueba rápida ──
if __name__ == '__main__':
    codigo_ok = """
funcion factorial(entero n) retornar entero
hacer
    si n <= 1 entonces
        retornar 1
    sino
        retornar n * factorial(n - 1)
    fin_si
fin_funcion
"""
    p = ParserRecursivo(codigo_ok)
    r = p.analizar()
    print("── Programa válido ──")
    print("Válido:", r['valido'], "  errores:", len(r['errores']))
    print()

    codigo_err = """
funcion prueba()
hacer
    entero x 10
    si x > 0
        escribir(x)
    fin_si
fin_funcion
"""
    p2 = ParserRecursivo(codigo_err)
    r2 = p2.analizar()
    print("── Programa con errores ──")
    print("Válido:", r2['valido'], "  errores:", len(r2['errores']))
    for e in r2['errores']:
        print(f"  [{e['indice']}] L{e['fila']}:C{e['columna']} "
              f"NT={e['no_terminal']:18s} esperado={e['tokens_esperados']} "
              f"lex='{e['lexema']}'")
        print(f"      → {e['sugerencia']}")
