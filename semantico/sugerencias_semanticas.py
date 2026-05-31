"""
╔══════════════════════════════════════════════════════════╗
║   DiamondLang 💎 — Sugerencias locales de la fase        ║
║                    semántica                            ║
║                sugerencias_semanticas.py                 ║
║  Entrega 4 — Etapa 8.                                    ║
║                                                         ║
║  Análogo a `sugerencias.py` (fase sintáctica): a partir  ║
║  de un `ErrorSemantico` ya construido, produce un texto  ║
║  humano de ayuda según su `regla` y su `contexto`.       ║
║                                                         ║
║  Estas sugerencias son LOCALES (fuente_sugerencia =      ║
║  'local'). El bonus IA (Etapa 9) podrá enriquecerlas     ║
║  después, igual que hace `sugerencias_ia` con las        ║
║  sintácticas.                                            ║
╚══════════════════════════════════════════════════════════╝
"""

from semantico.errores_semanticos import ErrorSemantico


def sugerir(error: ErrorSemantico) -> str:
    """
    Devuelve una sugerencia en español para `error`, escogida según
    `error.regla` y leyendo los datos auxiliares de `error.contexto`.

    Lee el contexto de forma DEFENSIVA (`.get`), así que si una clave
    faltara, la sugerencia degrada con elegancia (usa el lexema o un
    texto genérico) en lugar de romper.

    Si la regla no se reconoce, devuelve '' para que quien llama pueda
    aplicar un fallback (p.ej. conservar la sugerencia que ya traía el
    error).
    """
    regla = error.regla
    ctx = error.contexto or {}
    lex = error.lexema or "?"

    # ── Regla 1 ──
    if regla == "DECL_DUPLICADA":
        return (f"El identificador '{lex}' ya fue declarado en este ámbito. "
                f"Renómbralo o elimina la declaración anterior.")

    # ── Regla 2 ──
    if regla == "USO_NO_DECLARADO":
        clase = "función" if ctx.get("es_llamada") else "variable"
        return (f"La {clase} '{lex}' no fue declarada. ¿Olvidaste declararla, "
                f"o quizás hay un error de ortografía?")

    # ── Regla 3 ──
    if regla == "TIPO_ASIGNACION":
        destino = ctx.get("tipo_destino") or ctx.get("tipo_declarado")
        recibido = ctx.get("tipo_recibido")
        if destino == "funcion":
            nombre = ctx.get("identificador", lex)
            return (f"'{nombre}' es una función, no una variable: no puede "
                    f"ser el destino de una asignación. Usa una variable.")
        return (f"No puedes asignar un valor de tipo '{recibido}' a una "
                f"variable de tipo '{destino}'. Considera cambiar el tipo de "
                f"la variable o convertir el valor.")

    if regla == "TIPO_VOID_EN_VARIABLE":
        return ("El tipo 'vacio' solo se usa para funciones que no retornan "
                "valor. Una variable debe tener un tipo concreto: entero, "
                "real, cadena o booleano.")

    # ── TIPO_OPERADOR (transversal; lo emite el motor de tipos) ──
    if regla == "TIPO_OPERADOR":
        op = ctx.get("operador", lex)
        if "tipo_operando" in ctx:           # operador unario (no / -)
            return (f"El operador '{op}' no admite un operando de tipo "
                    f"'{ctx.get('tipo_operando')}'. Verifica el tipo de la "
                    f"expresión.")
        t1 = ctx.get("tipo_izquierdo")
        t2 = ctx.get("tipo_derecho")
        return (f"El operador '{op}' no admite operandos de tipos '{t1}' y "
                f"'{t2}'. Verifica los tipos de las expresiones.")

    # ── Regla 4 ──
    if regla == "TIPO_CONDICION":
        estr = ctx.get("estructura", "si")
        return (f"La condición de '{estr}' debe evaluar a verdadero/falso. "
                f"Usa un operador de comparación (==, !=, <, >, etc.) o una "
                f"expresión booleana.")

    # ── Regla 5 ──
    if regla == "LLAMADA_ARIDAD":
        n = ctx.get("aridad_esperada")
        m = ctx.get("aridad_recibida")
        return (f"La función '{lex}' espera {n} argumento(s) pero recibió "
                f"{m}. Ajusta la llamada.")

    if regla == "LLAMADA_TIPO":
        n = ctx.get("posicion_argumento")
        fn = ctx.get("funcion", lex)
        esperado = ctx.get("tipo_esperado")
        recibido = ctx.get("tipo_recibido")
        return (f"El argumento {n} de '{fn}' debe ser de tipo '{esperado}'. "
                f"Recibiste '{recibido}'.")

    if regla == "LLAMADA_NO_FUNCION":
        return (f"'{lex}' no es una función. Solo se pueden llamar "
                f"identificadores declarados con 'funcion'.")

    # Regla desconocida → sin sugerencia local (fallback en quien llama).
    return ""


# ══════════════════════════════════════════════
#  PRUEBA RÁPIDA
# ══════════════════════════════════════════════

if __name__ == "__main__":
    ejemplos = [
        ErrorSemantico(indice=1, regla="DECL_DUPLICADA", lexema="x",
                       contexto={"ambito": "principal"}),
        ErrorSemantico(indice=2, regla="USO_NO_DECLARADO", lexema="foo",
                       contexto={"es_llamada": True}),
        ErrorSemantico(indice=3, regla="TIPO_ASIGNACION", lexema="x",
                       contexto={"tipo_destino": "entero",
                                 "tipo_recibido": "cadena"}),
        ErrorSemantico(indice=4, regla="TIPO_VOID_EN_VARIABLE", lexema="v",
                       contexto={"tipo_declarado": "vacio"}),
        ErrorSemantico(indice=5, regla="TIPO_OPERADOR", lexema="+",
                       contexto={"operador": "+", "tipo_izquierdo": "entero",
                                 "tipo_derecho": "cadena"}),
        ErrorSemantico(indice=6, regla="TIPO_CONDICION", lexema="x",
                       contexto={"estructura": "mientras",
                                 "tipo_recibido": "entero"}),
        ErrorSemantico(indice=7, regla="LLAMADA_ARIDAD", lexema="sumar",
                       contexto={"aridad_esperada": 2, "aridad_recibida": 3}),
        ErrorSemantico(indice=8, regla="LLAMADA_TIPO", lexema="42",
                       contexto={"funcion": "saludar", "posicion_argumento": 1,
                                 "tipo_esperado": "cadena",
                                 "tipo_recibido": "entero"}),
        ErrorSemantico(indice=9, regla="LLAMADA_NO_FUNCION", lexema="x",
                       contexto={"categoria": "variable"}),
    ]
    for e in ejemplos:
        print(f"[{e.regla}] -> {sugerir(e)}")
