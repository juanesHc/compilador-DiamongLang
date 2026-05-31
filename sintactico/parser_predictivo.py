"""
╔══════════════════════════════════════════════════════════╗
║  DiamondLang 💎 — Parser Predictivo Descendente LL(1)   ║
║               parser_predictivo.py                      ║
║  Implementa el algoritmo clásico de pila:               ║
║    - Inicializa pila con [START, $]                      ║
║    - Consulta tabla LL(1) en cada paso                   ║
║    - Genera traza paso a paso                            ║
║    - Construye árbol sintáctico                          ║
║                                                         ║
║  Entrega 3: recuperación en modo pánico — al detectar   ║
║  un error sigue analizando aplicando una de tres        ║
║  acciones: SINCRONIZAR, INSERTAR o DESCARTAR.           ║
╚══════════════════════════════════════════════════════════╝
"""

from lexico.lexer import Lexer, Token
from sintactico.tabla_ll import (
    generar_tabla, GRAMATICA, NO_TERMINALES,
    START, EPSILON, EOF,
    tabla_a_dict_serializable, sets_a_dict_serializable
)
from sintactico.arbol import NodoArbol, propagar_posicion_terminales
from sintactico.errores import ErrorSintactico, formatear_error
from sintactico.sugerencias import sugerencia_local
from sintactico.recuperacion import (
    conjunto_sync_para, sincronizar,
    SYNC_GLOBAL, SYNC_SENTENCIA,
)


# Tokens "de cierre fuerte": cuando la pila los espera y el lookahead
# no los aporta, los INSERTAMOS implícitamente (es más probable que
# el programador los haya olvidado a que sobre algo).
TERMINALES_INSERTABLES = {
    'fin_funcion', 'fin_si', 'fin_mientras', 'fin_para', 'fin_clase',
    'entonces', 'hacer', 'desde', 'hasta',
    ')', '<-',
}


# ══════════════════════════════════════════════
#  CLASE PARSER PREDICTIVO
# ══════════════════════════════════════════════

class ParserPredictivo:
    """
    Analizador sintáctico predictivo descendente LL(1) para DiamondLang.

    Uso:
        parser = ParserPredictivo("si x > 0 entonces escribir(x) fin_si")
        resultado = parser.analizar()
    """

    # Tabla LL(1) se genera una vez al importar el módulo
    _PRIMERO  = None
    _SIGUIENTE = None
    _TABLA    = None

    @classmethod
    def _cargar_tabla(cls):
        if cls._TABLA is None:
            cls._PRIMERO, cls._SIGUIENTE, cls._TABLA = generar_tabla()

    def __init__(self, codigo_fuente: str, max_errores: int = 100):
        ParserPredictivo._cargar_tabla()

        # Tokenizar con el lexer de la Entrega 1
        lex = Lexer(codigo_fuente)
        tokens_raw, _ = lex.tokenizar()
        self.tokens = [t for t in tokens_raw if t.tipo != 'COMENTARIO']
        self.pos    = 0

        self.traza       = []     # lista de pasos para visualización
        self.errores     = []     # lista de ErrorSintactico
        self.error       = None   # compatibilidad: primer error formateado
        self.max_errores = max_errores

    # ── Utilidades ──────────────────────────────

    def token_actual(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        if self.tokens:
            ult = self.tokens[-1]
            return Token('$', '$', ult.linea, ult.columna + len(ult.lexema))
        return Token('$', '$', 1, 1)

    def tipo_actual(self) -> str:
        t = self.token_actual()
        if t.tipo in ('KEYWORD', 'TIPO', 'BOOLEANO', 'OPERADOR', 'SIMBOLO'):
            return t.lexema
        return t.tipo

    def _esperados_en_fila(self, no_terminal: str) -> list:
        """
        Devuelve los terminales para los que M[no_terminal, .] tiene
        producción válida (entradas no-vacías y no-conflictivas).
        Es la lista de tokens "esperados" para reportar al usuario.
        """
        esperados = []
        for (nt, term), prod in self._TABLA.items():
            if nt != no_terminal:
                continue
            if isinstance(prod, str) and 'CONFLICTO' in prod:
                continue
            esperados.append(term)
        return sorted(set(esperados))

    def _registrar_error(self, no_terminal: str, esperados,
                         produccion: str = None) -> None:
        tok = self.token_actual()
        e = ErrorSintactico(
            indice=len(self.errores) + 1,
            fila=tok.linea,
            columna=tok.columna,
            lexema=tok.lexema,
            tipo_token=tok.tipo,
            tokens_esperados=list(esperados),
            no_terminal=no_terminal,
            produccion_intentada=produccion,
            sugerencia=sugerencia_local(no_terminal, list(esperados),
                                        tok.lexema, tok.tipo),
        )
        self.errores.append(e)
        if self.error is None:
            self.error = formatear_error(e)

    def _sigue_vivo(self) -> bool:
        return len(self.errores) < self.max_errores

    # ── Algoritmo principal de pila ─────────────

    def analizar(self) -> dict:
        """
        Algoritmo LL(1) con pila explícita y recuperación en modo
        pánico. Acciones posibles ante un error:

          - SINCRONIZAR: descartar tokens hasta SIGUIENTE(tope) ∪
            SYNC_GLOBAL, luego pop del no-terminal en el tope.
          - INSERTAR  : cuando el tope es un terminal "fuerte"
            (cierre de bloque, palabra clave estructural) y no
            coincide, lo insertamos implícitamente (pop sin avanzar).
          - DESCARTAR : cuando el tope es un terminal "ligero" y
            no coincide, descartamos el lookahead (no avanzamos
            la pila) hasta que coincida o se llegue a EOF.

        Garantizamos terminación con un contador de iteraciones
        improductivas (sin avance de pos ni de pila).
        """
        # Crear raíz del árbol
        raiz         = NodoArbol(START)
        self.arbol_raiz = raiz         # expuesto para fases posteriores (semántica)
        pila_nodos   = [raiz]          # pila paralela de nodos del árbol
        pila_simbolos = [EOF, START]   # pila de símbolos (tope al final)
        # Pila paralela con el no-terminal "dueño" de cada símbolo:
        # cuando un terminal está en el tope, su dueño es el no-terminal
        # de cuya producción provino. Sirve para reportar errores con
        # contexto útil (ej. NT=sent_si en lugar de NT=<terminal entonces>).
        pila_owners  = [START, START]

        paso = 0
        sin_avance = 0
        pos_anterior = (-1, -1)  # (pos en input, len pila)

        while True:
            tope    = pila_simbolos[-1]
            ta      = self.tipo_actual()
            tok     = self.token_actual()
            paso   += 1

            # Detector de bucles improductivos
            estado_actual = (self.pos, len(pila_simbolos))
            if estado_actual == pos_anterior:
                sin_avance += 1
                if sin_avance > 200:
                    self._registrar_error(
                        '(pánico)', ['$'],
                        produccion='(bucle de recuperación)',
                    )
                    self.traza.append({
                        'paso': paso, 'pila': list(reversed(pila_simbolos)),
                        'lookahead': ta, 'lexema': tok.lexema,
                        'linea': tok.linea,
                        'accion': 'ABORT: bucle de recuperación',
                        'produccion': '',
                    })
                    break
            else:
                sin_avance = 0
                pos_anterior = estado_actual

            # ── Registrar estado actual ──
            self.traza.append({
                'paso':       paso,
                'pila':       list(reversed(pila_simbolos)),
                'lookahead':  ta,
                'lexema':     tok.lexema,
                'linea':      tok.linea,
                'accion':     '',
                'produccion': '',
            })

            # ── Caso 1: tope == $ y lookahead == $ → ACEPTAR ──
            if tope == EOF and ta == EOF:
                self.traza[-1]['accion'] = 'ACEPTAR ✓'
                break

            # ── Caso 2: tope == $ pero quedan tokens → ERROR ──
            if tope == EOF:
                if not self._sigue_vivo():
                    self.traza[-1]['accion'] = 'ABORT: máximo de errores'
                    break
                self._registrar_error(
                    '(pila vacía)', ['$'],
                    produccion='(fin de programa)',
                )
                self.traza[-1]['accion'] = (
                    f'DESCARTAR: token sobrante "{tok.lexema}"'
                )
                # Descartamos todo el resto en una sola acción agregada
                self.pos = len(self.tokens)
                continue

            # ── Caso 3: tope es terminal ──
            if tope not in NO_TERMINALES:
                if tope == ta:
                    # Match exitoso
                    self.traza[-1]['accion'] = f'MATCH: consume "{tok.lexema}"'
                    pila_simbolos.pop()
                    pila_owners.pop()
                    nodo_tope = pila_nodos.pop()
                    nodo_tope.etiqueta    = tok.lexema
                    nodo_tope.es_terminal = True
                    nodo_tope.linea       = tok.linea
                    nodo_tope.columna     = tok.columna
                    self.pos += 1
                    continue

                # ── Error: tope terminal sin match ──
                if not self._sigue_vivo():
                    self.traza[-1]['accion'] = 'ABORT: máximo de errores'
                    break

                owner = pila_owners[-1] if pila_owners else tope
                self._registrar_error(
                    owner, [tope],
                    produccion=f'match {tope}',
                )

                if tope in TERMINALES_INSERTABLES:
                    # INSERTAR: pop del terminal sin avanzar lookahead.
                    # Posición = la del token actual (el del lookahead).
                    self.traza[-1]['accion'] = (
                        f'INSERTAR: "{tope}" implícito'
                    )
                    pila_simbolos.pop()
                    pila_owners.pop()
                    nodo_tope = pila_nodos.pop()
                    nodo_tope.etiqueta    = f"ERROR<falta '{tope}'>"
                    nodo_tope.es_terminal = True
                    nodo_tope.es_error    = True
                    nodo_tope.linea       = tok.linea
                    nodo_tope.columna     = tok.columna
                else:
                    # DESCARTAR: avanzar el input dejando el terminal en pila
                    self.traza[-1]['accion'] = (
                        f'DESCARTAR: "{tok.lexema}" (esperaba "{tope}")'
                    )
                    self.pos += 1
                continue

            # ── Caso 4: tope es no-terminal → consultar tabla ──
            clave     = (tope, ta)
            produccion = self._TABLA.get(clave)

            if isinstance(produccion, str) and 'CONFLICTO' in produccion:
                self._registrar_error(tope, [],
                                      produccion=f'conflicto: {produccion}')
                self.traza[-1]['accion'] = 'ERROR: conflicto LL(1)'
                break

            if produccion is None:
                # ── Celda vacía: SINCRONIZAR ──
                if not self._sigue_vivo():
                    self.traza[-1]['accion'] = 'ABORT: máximo de errores'
                    break

                esperados = self._esperados_en_fila(tope)
                self._registrar_error(tope, esperados,
                                      produccion=f'M[{tope}, {ta}] vacío')

                # Conjunto de sincronización: SIGUIENTE(tope) ∪ SYNC_GLOBAL
                sync_set = (set(self._SIGUIENTE.get(tope, set())) |
                            SYNC_GLOBAL)
                # Si el lookahead actual ya está en sync, hacemos pop directamente
                if ta in sync_set:
                    self.traza[-1]['accion'] = (
                        f'POP: descarta no-terminal "{tope}" '
                        f'(lookahead {ta} ∈ SIGUIENTE)'
                    )
                    pila_simbolos.pop()
                    pila_owners.pop()
                    nodo_padre = pila_nodos.pop()
                    nodo_padre.agregar_hijo(
                        NodoArbol(f"ERROR<{tope}>",
                                  es_terminal=True, es_error=True,
                                  linea=tok.linea, columna=tok.columna)
                    )
                else:
                    nueva_pos, descartados = sincronizar(
                        self.tokens, self.pos, sync_set
                    )
                    self.pos = nueva_pos
                    self.traza[-1]['accion'] = (
                        f'SINCRONIZAR: descarta {len(descartados)} '
                        f'token(s) hasta SIGUIENTE({tope})'
                    )
                continue

            # ── Caso 4b: producción válida → expandir ──
            prod_str = ' '.join(produccion) if produccion != [EPSILON] else 'ε'
            self.traza[-1]['accion']     = f'EXPANDIR → {prod_str}'
            self.traza[-1]['produccion'] = f'{tope} → {prod_str}'

            pila_simbolos.pop()
            pila_owners.pop()
            nodo_padre = pila_nodos.pop()

            if produccion == [EPSILON]:
                hijo_eps = NodoArbol('ε', es_terminal=True)
                nodo_padre.agregar_hijo(hijo_eps)
            else:
                # Crear hijos y empujar en orden inverso
                nuevos_nodos = []
                for simbolo in produccion:
                    es_term = simbolo not in NO_TERMINALES
                    hijo = NodoArbol(simbolo, es_terminal=es_term)
                    nodo_padre.agregar_hijo(hijo)
                    nuevos_nodos.append(hijo)

                for simbolo, nodo in zip(reversed(produccion), reversed(nuevos_nodos)):
                    pila_simbolos.append(simbolo)
                    pila_nodos.append(nodo)
                    pila_owners.append(tope)   # tope era el no-terminal expandido

        # Propagar posición desde los terminales a sus ancestros no terminales
        propagar_posicion_terminales(raiz)

        valido = (len(self.errores) == 0)
        return {
            'valido':        valido,
            'errores':       [e.to_dict() for e in self.errores],
            'error':         self.error,
            'traza':         self.traza,
            'nodos':         self._serializar_arbol(raiz),
            'tabla_ll':      tabla_a_dict_serializable(self._TABLA),
            'primero':       sets_a_dict_serializable(self._PRIMERO),
            'siguiente':     sets_a_dict_serializable(self._SIGUIENTE),
        }

    def _serializar_arbol(self, nodo: NodoArbol) -> dict:
        return {
            'id':          nodo.id,
            'etiqueta':    nodo.etiqueta,
            'es_terminal': nodo.es_terminal,
            'es_error':    nodo.es_error,
            'hijos':       [self._serializar_arbol(h) for h in nodo.hijos],
        }


# ── Prueba rápida ──
if __name__ == '__main__':
    codigo_ok = """
mientras x < 10 hacer
    x <- x + 1
fin_mientras
"""
    p = ParserPredictivo(codigo_ok)
    r = p.analizar()
    print("── Programa válido ──")
    print("Válido:", r['valido'], "  errores:", len(r['errores']))
    print("Pasos:", len(r['traza']))
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
    p2 = ParserPredictivo(codigo_err)
    r2 = p2.analizar()
    print("── Programa con errores ──")
    print("Válido:", r2['valido'], "  errores:", len(r2['errores']))
    for e in r2['errores']:
        print(f"  [{e['indice']}] L{e['fila']}:C{e['columna']} "
              f"NT={e['no_terminal']:18s} esperado={e['tokens_esperados'][:4]}... "
              f"lex='{e['lexema']}'")
        print(f"      → {e['sugerencia']}")
    print()
    print("Acciones únicas en traza:")
    acciones = set()
    for p in r2['traza']:
        a = p['accion'].split(':')[0]
        acciones.add(a)
    print(" ", acciones)
