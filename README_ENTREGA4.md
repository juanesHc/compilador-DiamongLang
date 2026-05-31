# DiamondLang 💎 — Entrega 4: Análisis Semántico

Fase de **análisis semántico** sobre el árbol que ya construían los parsers
de la Entrega 3, con cinco reglas semánticas, tabla de símbolos, sistema de
tipos, integración al endpoint `/parsear`, visualización en el frontend y un
bonus opcional de IA que enriquece las sugerencias con Claude.

## Resumen ejecutivo

El análisis semántico se implementó como **una pasada adicional (visitor)
sobre el CST** que producen los dos parsers (recursivo y predictivo), sin
tocar el lexer ni los parsers y sin construir un AST nuevo (decisión de
arquitectura (b) del plan). El visitor recorre el árbol, mantiene una
**tabla de símbolos** con ámbitos (global + función), consulta un **motor de
tipos** con promoción `entero → real`, y reporta `ErrorSemantico`s con regla,
posición, lexema, mensaje y una sugerencia. Cada regla se construyó y probó
de forma incremental (una etapa por regla) contra **ambos parsers**.

El sistema es robusto frente a programas con errores sintácticos: corre
**análisis parcial** (decisión F.11), analizando las zonas limpias del árbol
y saltando solo las sentencias rotas. Todo el análisis es determinista; el
**bonus de IA es aditivo** (Modalidad A): si hay `ANTHROPIC_API_KEY`, las
sugerencias de los errores semánticos se pueden enriquecer con Claude, pero
las reglas clásicas siguen siendo la única fuente de detección.

## Las cinco reglas semánticas

1. **Declaración duplicada** (`DECL_DUPLICADA`): un identificador (variable,
   parámetro o función) no puede declararse dos veces en el mismo ámbito.
2. **Uso de identificador no declarado** (`USO_NO_DECLARADO`): toda variable
   o función usada debe haberse declarado antes (mensaje diferenciado
   "variable" vs "función" según haya o no paréntesis de llamada).
3. **Compatibilidad de tipos en asignación** (`TIPO_ASIGNACION`,
   `TIPO_VOID_EN_VARIABLE`): el tipo del valor asignado debe ser compatible
   con el de la variable (con promoción `entero → real`); `vacio` no es un
   tipo válido de variable.
4. **Condición booleana** (`TIPO_CONDICION`): la condición de `si` y
   `mientras` debe ser de tipo `booleano`.
5. **Aridad y tipos en llamadas** (`LLAMADA_ARIDAD`, `LLAMADA_TIPO`,
   `LLAMADA_NO_FUNCION`): una llamada debe pasar el número de argumentos de
   la firma, con tipos compatibles, y solo se pueden llamar funciones.

Transversal a todas: `TIPO_OPERADOR` (operadores aplicados a operandos de
tipos incompatibles), emitido por el motor de tipos, con **supresión de
cascada** (un sub-resultado `ERROR` no genera errores derivados).

## Arquitectura: módulos del análisis semántico

| Módulo | Rol |
|--------|-----|
| `arbol.py` | `NodoArbol` unificado (con `linea`/`columna`) + helpers de navegación del CST (`hijo_por_etiqueta`, `primer_terminal`, `tiene_error_sintactico`, `etiqueta_normalizada`, `extraer_expresiones_de_argumentos`, …). |
| `tabla_simbolos.py` | `Simbolo` (con `parametros`/`tipo_retorno`) y `TablaSimbolos` (pila de ámbitos: `declarar`, `buscar`, `abrir/cerrar_ambito`). |
| `tipos.py` | Motor de tipos: `compatible`, `unificar_*`, `tipo_de_expresion` y `tipo_de_expresion_con_reporte` (inferencia + `TIPO_OPERADOR`). |
| `errores_semanticos.py` | `ErrorSemantico` (dataclass serializable) + formateadores. |
| `semantico.py` | `AnalizadorSemantico`: el visitor con las 5 reglas, el análisis parcial (F.11) y el reporte. |
| `sugerencias_semanticas.py` | Sugerencias locales humanas por regla (`sugerir(error)`). |
| `sugerencias_ia_semantica.py` | Bonus: enriquecimiento de sugerencias semánticas con Claude (paralelo a `sugerencias_ia.py`). |

Integración: `server.py` invoca `AnalizadorSemantico` tras el parser y
añade al JSON de `/parsear` las claves `errores_semanticos`,
`valido_semantico` y `simbolos`. `diamondlang.html` las muestra en un panel
ámbar (errores semánticos) y un panel teal (tabla de símbolos), con un banner
de estado combinado.

## Cómo correr el proyecto

```bash
# 1. Instalar dependencias (anthropic / python-dotenv son opcionales)
pip install -r requirements.txt

# 2. Ejecutar el servidor
python server.py

# 3. Abrir diamondlang.html en el navegador, pestaña ② Sintáctico
#    Pegar código, elegir método (recursivo/predictivo) y ▶ Analizar
```

En el arranque verás el estado de los bonus de IA y del chatbot:

```
💎 Generando tabla LL(1)...
   Tabla lista: 453 entradas, 44 no-terminales
   Bonus IA (sintáctica): disponible [Gemini]
   Bonus IA (semántica):  disponible [Claude]
   Chatbot — Claude: sí · Gemini: sí
```

### Modelos de IA: quién hace qué (Fase 5b)

DiamondLang usa **dos proveedores**, cada uno con su API key. Todo es
**opcional**: sin keys, el sistema funciona con sugerencias locales y el
chatbot responde con respuestas locales de prueba.

| Función | Modelo | API key | Módulo |
|---|---|---|---|
| Sugerencias **sintácticas** (toggle "IA sintaxis") | **Gemini Flash** | `GOOGLE_API_KEY` | `sugerencias_ia.py` → `cliente_gemini.py` |
| Sugerencias **semánticas** (toggle "IA semántica") | **Claude Haiku** | `ANTHROPIC_API_KEY` | `sugerencias_ia_semantica.py` |
| **Chatbot** (asistente modal) | **ambos**, a elección del usuario | la del modelo elegido | `/chat` → `cliente_anthropic.py` / `cliente_gemini.py` |

> ⚠ **Cambio respecto a entregas previas:** las sugerencias **sintácticas**
> migraron de Claude a **Gemini**. Por eso, con SOLO `ANTHROPIC_API_KEY`
> definida, el toggle "IA sintaxis" queda **deshabilitado** (necesita
> `GOOGLE_API_KEY`); el toggle "IA semántica" sigue funcionando con Claude.

### Configurar las API keys

Crea/edita `.env` en la raíz del proyecto (se carga con ruta absoluta y está
en `.gitignore`):

```bash
ANTHROPIC_API_KEY=sk-ant-...     # habilita IA semántica + chatbot Claude
GOOGLE_API_KEY=AIza...           # habilita IA sintáctica + chatbot Gemini
# (alias aceptado para Google: GEMINI_API_KEY)
```

Instalar dependencias (incluye el nuevo cliente de Google):

```bash
pip install -r requirements.txt          # trae anthropic + google-genai
# o solo el nuevo:
pip install google-genai
```

Ambas librerías se importan de forma **perezosa**: si falta una, la app
arranca igual y la función correspondiente reporta "no disponible".

- **Sin ninguna key** → todo local; toggles de IA deshabilitados; el chatbot
  responde con placeholders locales.
- **Solo una key** → ese proveedor funciona; en el selector del chatbot, la
  pill del modelo sin key aparece **atenuada** con un tooltip explicativo.
- **Ambas keys** → todo activo; el chatbot alterna Claude/Gemini a voluntad.

El endpoint `GET /ping_chat` reporta la disponibilidad; el frontend lo usa
para atenuar las pills. El `POST /chat` recibe
`{mensaje, modelo, historial}` y devuelve `{respuesta, modelo_usado, error}`.

## Cómo correr los tests

Todos los tests son ejecutables directos (no requieren pytest ni red):

```bash
python test_etapa1_posiciones.py          # posición línea/columna en el CST
python test_etapa2_infraestructura.py     # TablaSimbolos + helpers de arbol
python test_etapa3_reglas_1_2.py          # DECL_DUPLICADA, USO_NO_DECLARADO
python test_etapa4_tipos.py               # motor de tipos (compatible, unificar…)
python test_etapa5_regla_3.py             # TIPO_ASIGNACION, TIPO_VOID_EN_VARIABLE
python test_etapa6_regla_4.py             # TIPO_CONDICION
python test_etapa7_regla_5.py             # LLAMADA_ARIDAD / _TIPO / _NO_FUNCION
python test_etapa8_endpoint.py            # /parsear con claves semánticas
python test_etapa8_5_analisis_parcial.py  # análisis parcial (F.11)
python test_etapa9_bonus_ia.py            # bonus IA semántica (Claude, mockeado)
python test_etapa11_chat.py               # chatbot /chat + /ping_chat + IA sintáctica Gemini (mockeado)
python test_etapa12_sdt.py                # traducción a Julia (SDT) + endpoint /traducir
```

Cada test ejercita los ejemplos con **ambos parsers** (recursivo y
predictivo) y verifica número exacto de errores, regla, posición y lexema.

## Cómo se demuestra cada regla

Los programas de ejemplo viven en `ejemplos_semanticos/`. Cada uno es
sintácticamente válido y dispara exactamente el error semántico indicado:

| Regla | Ejemplo | Error esperado |
|-------|---------|----------------|
| 1 | `01_decl_duplicada_variable.dml` | `DECL_DUPLICADA` (variable `x` dos veces) |
| 1 | `02_decl_duplicada_parametro.dml` | `DECL_DUPLICADA` (parámetro `a` repetido) |
| 2 | `03_uso_variable_no_declarada.dml` | `USO_NO_DECLARADO` (variable `desconocida`) |
| 2 | `04_llamada_funcion_no_declarada.dml` | `USO_NO_DECLARADO` (función `inexistente`) |
| 3 | `05_tipo_asignacion_decl.dml` | `TIPO_ASIGNACION` (`entero x <- "hola"`) |
| 3 | `07_tipo_void_en_variable.dml` | `TIPO_VOID_EN_VARIABLE` (`vacio v <- 0`) |
| 3 | `08_tipo_promocion_ok.dml` | (válido: `real a <- 5`) + `entero z <- 3.14` falla |
| 4 | `11_condicion_si_no_booleana.dml` | `TIPO_CONDICION` (`si x` con `x` entero) |
| 4 | `13_condicion_si_ok.dml` | (válido: `si x > 3`) |
| 5 | `16_llamada_aridad_mas.dml` | `LLAMADA_ARIDAD` (3 args, espera 2) |
| 5 | `18_llamada_tipo_incompatible.dml` | `LLAMADA_TIPO` (arg 1 debe ser cadena) |
| 5 | `19_llamada_promocion_ok.dml` | (válido: `area(5)`, `5`→real) |
| 5 | `20_llamada_no_funcion.dml` | `LLAMADA_NO_FUNCION` (`x(5)` con `x` variable) |
| 5 | `22_llamada_recursiva_ok.dml` | (válido: factorial recursivo) |

Bonus IA: `ejemplos_semanticos/bonus_ia_demo.md` documenta un caso
end-to-end (código → error → sugerencia local → sugerencia de Claude).

## Decisiones de diseño clave

- **Arquitectura (b)**: pasada de visitor sobre el CST existente; sin AST
  nuevo, sin tocar parsers.
- **Scoping**: dos niveles (global + función); `si`/`mientras`/`para` **no**
  abren ámbito.
- **Tipos**: `entero → real` se promociona; `cadena + cadena` concatena;
  asignar `real` a `entero` es error; `vacio` solo como tipo de retorno.
- **Cascada (F.10)**: un sub-resultado `ERROR` no genera errores derivados.
- **Análisis parcial (F.11)**: con errores sintácticos, se analizan las
  zonas limpias y se saltan solo las sentencias rotas.
- **Agnóstico al parser**: el visitor normaliza las etiquetas auxiliares
  (`bloque'` ↔ `bloque_prima`) y funciona igual con ambos parsers.
- **Bonus IA aditivo (Modalidad A)**: la IA enriquece, no detecta; sin API
  key todo sigue funcionando.

## Limitaciones conocidas

1. **Palabras reservadas como identificadores**: `y`, `o`, `no`, `este`,
   `nuevo` son palabras clave; usarlas como nombre de variable produce un
   error *sintáctico* (no semántico). Los ejemplos los evitan.
2. **`retornar` obligatorio con expresión**: la gramática actual exige
   `sent_retornar → retornar expresion`. La sub-regla "función `vacio` no
   debe retornar valor" (decisión F.8) quedó fuera del alcance de E4 como
   regla independiente.
3. **No hay regla de tipo de retorno** (Regla 6): no se valida que el cuerpo
   de una función de retorno `entero` efectivamente retorne `entero`. Fuera
   del alcance acordado.
4. **`sent_para` fuera de la Regla 3**: las expresiones `desde`/`hasta`/
   `paso` se tipan (para no perder `TIPO_OPERADOR`) pero no se valida la
   asignación implícita de la variable de iteración.
5. **Análisis parcial por sentencia**: una sentencia con un error sintáctico
   interno se salta entera; no se recupera el sub-fragmento limpio dentro de
   esa misma sentencia.
6. **Cache IA en memoria**: vive en el proceso del server; reiniciar lo
   borra. La IA puede, ocasionalmente, sugerir construcciones que no existen
   en la gramática (es una capa de ayuda, no autoritativa).

## Bonus IA — Modalidad C (validación + optimización del Julia generado)

> Esta sección documenta el **segundo bonus de IA** del entregable, distinto
> del bonus aditivo de sugerencias semánticas (Modalidad A, arriba). Es la
> capa que pide el enunciado de la Entrega Final en su apartado *Bonus
> Opcional*.

### Modalidad elegida

**Modalidad C: combinada (validación + optimización).** Una vez el SDT
(`sdt.py`) traduce DiamondLang a Julia, el usuario puede enviar ese código
generado a **Claude Haiku** (`claude-haiku-4-5`) para que un "experto en
Julia" lo audite: confirma si es sintáctica y semánticamente correcto y
sugiere optimizaciones idiomáticas. El resultado se muestra estructurado en
la pestaña **Traducción**, en un panel propio **"Análisis con IA"**.

La integración es **una capa adicional**: el compilador traduce a Julia y
funciona end-to-end sin la IA. Si `ANTHROPIC_API_KEY` no está definida, el
botón "Validar y optimizar con IA" queda deshabilitado con un *tooltip*
explicativo y nada más cambia.

### Dónde está la integración en el código (para la sustentación)

- **Llamada a la API**: `server.py` → endpoint `POST /validar_julia`
  (función `validar_julia()`), que invoca `cliente_anthropic.responder(...)`.
- **El prompt** (literal y visible): constantes `SYSTEM_VALIDAR_JULIA` y
  `_prompt_validar_julia(julia_code)` en `server.py`.
- **Manejo de la respuesta**: `_parsear_respuesta_julia(raw)` extrae el
  bloque ```` ```json ```` con un regex y hace `json.loads`; si falla, se
  degrada con gracia devolviendo el texto crudo en el campo `raw`.
- **Presentación al usuario**: `diamondlang.html` → panel `#tr-ia-panel`,
  funciones JS `solicitarAnalisisIA()`, `renderAnalisisIA()`,
  `mostrarErrorIA()`, y CSS scopeado `.tr-ia-*`.
- **Tests**: `test_etapa13_validacion_ia.py` (cliente Anthropic mockeado).

### El prompt utilizado (literal)

**System prompt:**

```
Eres un experto en Julia que audita código generado automáticamente por
compiladores. Tu rol es validar la corrección y sugerir optimizaciones
idiomáticas. Responde siempre en español. Para cada análisis: identifica
problemas reales (si los hay), sugiere mejoras idiomáticas concretas, y
mantén las sugerencias accionables. No inventes problemas donde no hay. Si
el código está bien, dilo claramente.
```

**Prompt de usuario** (`{julia_code}` se sustituye por el código generado):

````
Audita este código Julia y devuelve un análisis estructurado.

```julia
{julia_code}
```

Evalúa concretamente: (1) ¿es sintácticamente correcto en Julia?, (2) ¿es
semánticamente coherente y usa tipos consistentes?, (3) ¿hay formas más
idiomáticas, estructuras estándar de Julia o patrones que un desarrollador
experimentado mejoraría?

Responde EXCLUSIVAMENTE con un bloque JSON en este formato:

```json
{
  "validacion": "<un párrafo evaluando la corrección sintáctica y semántica>",
  "problemas_encontrados": ["<problema 1>", "..."],
  "optimizaciones": ["<sugerencia idiomática 1>", "..."]
}
```

Si no hay problemas, deja "problemas_encontrados" como lista vacía. Si el
código es idiomático y no necesita cambios, dilo claramente como única
entrada de "optimizaciones".
````

### Ejemplo completo (entrada → Julia generado → respuesta real de Claude)

**1) Código fuente DiamondLang (entrada):**

```
funcion factorial(entero n) retornar entero
hacer
    si n <= 1 entonces
        retornar 1
    sino
        retornar n * factorial(n - 1)
    fin_si
fin_funcion

funcion principal() retornar vacio
hacer
    escribir(factorial(5))
fin_funcion
```

**2) Código Julia generado por el compilador (SDT):**

```julia
# Código Julia generado por DiamondLang Compiler v4.0

function factorial(n::Int)::Int
    if n <= 1
        return 1
    else
        return n * factorial(n - 1)
    end
end

function principal()
    println(factorial(5))
end

principal()
```

**3) Respuesta real de Claude Haiku (vía `/validar_julia`):**

*Validación:*
> El código es sintácticamente correcto y se ejecuta sin errores en Julia.
> La anotación de tipos `(n::Int)::Int` es válida y coherente. Sin embargo,
> hay un problema semántico importante: la función no maneja correctamente
> valores negativos (causaría un desbordamiento de pila infinito), y el tipo
> de retorno `Int` puede causar desbordamiento aritmético para factoriales
> grandes (`factorial(21) > typemax(Int64)`).

*Problemas encontrados:*
- No se validan valores negativos: `factorial(-5)` entraría en recursión infinita.
- Riesgo de desbordamiento de pila para valores grandes sin límite explícito.
- El tipo `Int` provoca desbordamiento aritmético (`factorial(21)` excede `Int64`); sería mejor retornar `BigInt` o documentar la limitación.

*Optimizaciones sugeridas:*
- Usar implementación iterativa en lugar de recursiva: `prod(1:n)` o un bucle `for`.
- Simplificar el condicional a una línea: `n <= 1 ? 1 : n * factorial(n - 1)`.
- Agregar validación: `n < 0 && throw(DomainError(n, "factorial requires non-negative integer"))`.
- Considerar la función estándar `Base.factorial` para código *production-ready*.

> **Nota de honestidad técnica:** la respuesta de Claude es mayormente
> correcta y útil (el desbordamiento de `Int64` en `factorial(21)` y la falta
> de validación de negativos son observaciones reales y verificables). Una
> sugerencia menor fue imprecisa (mencionó `Base.Combinatorics` / `Math.factorial`,
> cuando en Julia `factorial` vive directamente en `Base`); se documenta tal
> cual para reflejar el comportamiento real del modelo.

### Tolerancia a fallos

- Sin `ANTHROPIC_API_KEY`: `/validar_julia` responde `ok=false` con
  explicación y el botón del panel queda deshabilitado (tooltip). El resto de
  la pestaña Traducción (DiamondLang ↔ Julia, descarga, copia) sigue intacto.
- Si Claude responde texto sin el bloque JSON: el backend no falla; devuelve
  `ok=true` con la respuesta cruda en `raw` (degradación con gracia).
- `/traducir` y `sdt.py` **no se modifican**: el bonus es estrictamente
  aditivo.

## Documento de diseño

El detalle etapa por etapa (decisiones, sorpresas, verificaciones) está en
`PLAN_ENTREGA4.md`, desde la Etapa 0 (reconocimiento) hasta la Etapa 9
(bonus IA), y en `MIGRACION_VISUAL.md` (Fase D — Bonus IA validación).
