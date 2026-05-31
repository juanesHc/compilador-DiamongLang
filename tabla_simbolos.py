"""
╔══════════════════════════════════════════════════════════╗
║   DiamondLang 💎 — Tabla de símbolos                     ║
║                  tabla_simbolos.py                       ║
║  Entrega 4 — Etapa 2: infraestructura.                   ║
║                                                         ║
║  Pila de ámbitos para el análisis semántico.            ║
║  Scoping de DiamondLang (decisión aprobada):            ║
║    - dos niveles: 'global' y nombre de función.         ║
║    - si/mientras/para NO abren ámbito nuevo.            ║
║  La clase soporta profundidad arbitraria por si en el   ║
║  futuro se decide abrir scopes locales.                 ║
╚══════════════════════════════════════════════════════════╝
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Tuple


# ══════════════════════════════════════════════
#  SÍMBOLO
# ══════════════════════════════════════════════

@dataclass
class Simbolo:
    """
    Una entrada de la tabla de símbolos.

    `tipo` admite: 'entero', 'real', 'cadena', 'booleano', 'vacio',
    'funcion' o 'ERROR' (este último para propagar errores en cascada
    sin reportar derivados).
    `categoria` admite: 'variable', 'parametro', 'funcion'.
    """
    nombre: str
    tipo: str
    categoria: str
    ambito: str
    fila: Optional[int] = None
    columna: Optional[int] = None
    inicializado: bool = True
    parametros: Optional[List[Tuple[str, str]]] = None   # solo funciones
    tipo_retorno: Optional[str] = None                   # solo funciones


def como_dict(s: Simbolo) -> dict:
    """Serialización JSON-friendly de un símbolo."""
    return asdict(s)


# ══════════════════════════════════════════════
#  TABLA DE SÍMBOLOS
# ══════════════════════════════════════════════

class TablaSimbolos:
    """
    Pila de ámbitos. El tope de la pila es el ámbito vigente.

    El ámbito raíz 'global' se crea en __init__ y nunca se cierra
    durante el análisis normal (queda como red de seguridad: si por
    bug interno se cerrara, `ambito_actual()` devolvería 'global'
    igual gracias al fallback).
    """

    AMBITO_RAIZ = 'global'

    def __init__(self):
        # Lista de tuplas (nombre_ambito, dict[nombre_simbolo, Simbolo]).
        self._pila: List[Tuple[str, dict]] = []
        self.abrir_ambito(self.AMBITO_RAIZ)

    # ── Gestión de ámbitos ──────────────────────

    def abrir_ambito(self, nombre: str) -> None:
        """Empuja un nuevo ámbito vacío al tope de la pila."""
        self._pila.append((nombre, {}))

    def cerrar_ambito(self) -> None:
        """
        Cierra el ámbito del tope. No falla si la pila ya está vacía
        (defensa contra bugs internos del visitor).
        """
        if self._pila:
            self._pila.pop()

    def ambito_actual(self) -> str:
        """Nombre del ámbito del tope. Defaultea a 'global' si la pila
        quedó vacía por error interno."""
        if not self._pila:
            return self.AMBITO_RAIZ
        return self._pila[-1][0]

    # ── Operaciones sobre símbolos ──────────────

    def declarar(self, simbolo: Simbolo) -> bool:
        """
        Inserta `simbolo` en el ámbito actual.

        Returns:
            True  si la inserción tuvo éxito,
            False si ya existía un símbolo con ese nombre en el ámbito
                  actual (no mira ancestros — el sombreo es legal).
        """
        if not self._pila:
            return False
        _, scope = self._pila[-1]
        if simbolo.nombre in scope:
            return False
        scope[simbolo.nombre] = simbolo
        return True

    def buscar(self, nombre: str) -> Optional[Simbolo]:
        """
        Busca `nombre` desde el tope hacia la raíz (sombreo correcto).
        Devuelve el primer match o None.
        """
        for _, scope in reversed(self._pila):
            if nombre in scope:
                return scope[nombre]
        return None

    def existe_en_ambito_actual(self, nombre: str) -> bool:
        """¿`nombre` está en el ámbito del tope? (sin mirar padres)"""
        if not self._pila:
            return False
        _, scope = self._pila[-1]
        return nombre in scope

    def todos_los_simbolos(self) -> List[Simbolo]:
        """
        Devuelve todos los símbolos de todos los ámbitos VIVOS, en orden
        global → más interno. Útil para depuración y para mostrar la
        tabla en el frontend.
        """
        resultado: List[Simbolo] = []
        for _, scope in self._pila:
            resultado.extend(scope.values())
        return resultado

    def simbolos_del_ambito_actual(self) -> List[Simbolo]:
        """
        Devuelve solo los símbolos del ámbito del tope (sin mirar
        padres). Útil para hacer snapshot de un ámbito justo antes
        de cerrarlo, para conservar el listado de parámetros y
        variables locales de una función ya analizada.
        """
        if not self._pila:
            return []
        _, scope = self._pila[-1]
        return list(scope.values())

    # ── Depuración ─────────────────────────────

    def __repr__(self) -> str:
        partes = []
        for nombre, scope in self._pila:
            simbolos = ", ".join(
                f"{s.nombre}:{s.tipo}" for s in scope.values()
            ) or "(vacío)"
            partes.append(f"[{nombre} {{{simbolos}}}]")
        cadena = " > ".join(partes) if partes else "(pila vacía)"
        return f"TablaSimbolos({cadena})"


# ══════════════════════════════════════════════
#  PRUEBA RÁPIDA
# ══════════════════════════════════════════════

if __name__ == '__main__':
    t = TablaSimbolos()
    print("Inicial:", t)
    print()

    # Globales
    print("Declarar 'PI' en global:",
          t.declarar(Simbolo('PI', 'real', 'variable', 'global',
                             fila=1, columna=1)))
    # Función
    f = Simbolo('factorial', 'funcion', 'funcion', 'global',
                fila=2, columna=1,
                parametros=[('n', 'entero')], tipo_retorno='entero')
    print("Declarar 'factorial' en global:", t.declarar(f))
    # Duplicado
    print("Re-declarar 'PI':",
          t.declarar(Simbolo('PI', 'entero', 'variable', 'global')))
    print()

    # Entrar a una función
    t.abrir_ambito('factorial')
    print("Entré a 'factorial':", t)
    t.declarar(Simbolo('n', 'entero', 'parametro', 'factorial',
                       fila=2, columna=22))
    t.declarar(Simbolo('acc', 'entero', 'variable', 'factorial'))
    print("Buscar 'n':", t.buscar('n'))
    print("Buscar 'PI' (debe ir a global):", t.buscar('PI'))
    print("Buscar 'nada':", t.buscar('nada'))
    print()

    t.cerrar_ambito()
    print("Cerré 'factorial':", t)
    print("Buscar 'n' tras cerrar:", t.buscar('n'))
