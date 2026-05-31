# DiamondLang 💎 — Entrega 4: Plan de Análisis Semántico

Documento de **reconocimiento** (Etapa 0). Resultado de lectura del código
existente; no propone ni implementa cambios. Sirve de base para que el
profesor del proyecto apruebe la Etapa 1.

---

## A. AST

### A.1 ¿Existe un AST navegable?

Sí, **existe un árbol explícito y serializable**, pero es un *árbol de
parseo concreto* (CST), no un AST abstracto.

- **Clase de nodo**: `NodoArbol` declarada por duplicado en
  `parser_recursivo.py:32-48` y en `parser_predictivo.py:37-47`. Misma
  forma en los dos:

  ```python
  class NodoArbol:
      etiqueta:    str    # nombre del no-terminal o lexema del terminal
      es_terminal: bool
      es_error:    bool
      hijos:       list[NodoArbol]
      id:          str    # uuid corto, para dibujar el árbol
  ```

  No hay clases por tipo de nodo: todo es un solo `NodoArbol` polimórfico
  cuyo significado se infiere de `etiqueta`.

- **Acceso después de parsear**:
  - `ParserRecursivo.analizar()` (línea 203-228) devuelve un `dict` con
    `'nodos': self._serializar_arbol(raiz)`. No expone la raíz
    `NodoArbol` viva; solo su serialización JSON.
  - `ParserPredictivo.analizar()` (línea 152-368) idéntico.
  - El método `_serializar_arbol` recorre y produce dicts con las mismas
    claves `id, etiqueta, es_terminal, es_error, hijos`.
  - **No hay ningún visitor, walker o iterador definido**. Quien quiera
    recorrer tiene que hacerlo a mano.

### A.2 ¿Qué guarda y qué pierde el árbol?

Guarda:
- Estructura sintáctica completa (todos los no-terminales aparecen como
  nodos, incluyendo los auxiliares `expr_or'`, `expr_and'`, `bloque'`,
  etc. introducidos para factorizar / eliminar recursión izquierda).
- Marcadores `ε` como hojas en producciones vacías.
- Nodos `ERROR<...>` que el modo pánico inserta como marcadores.

**Lo que se pierde** y es relevante para semántica:
1. **Línea y columna de cada token**: el `Token` original tiene
   `linea` y `columna`, pero al insertar el terminal como nodo del árbol
   (`parser_recursivo.py:173`, `parser_predictivo.py:249-252`) sólo se
   conserva `lexema` en `etiqueta`. Para reportar errores semánticos con
   posición habría que **enriquecer `NodoArbol`** con esos campos o
   pasar el `Token` completo. **Esto es deuda técnica crítica para
   E4.**
2. **Tipo léxico del token** (`ENTERO`, `REAL`, `CADENA`, `IDENTIFICADOR`,
   etc.): al volverse `etiqueta=lexema`, ya no distingo en el árbol si
   `42` vino como `ENTERO` o un identificador. Hay que reconstruirlo
   por la posición en la producción o re-anotar.

### A.3 ¿Los dos parsers producen lo mismo?

**Sí, estructuralmente equivalente**, con matices:

- El parser recursivo (`parse_*`) crea cada nodo manualmente y agrega
  hijos en orden. Conserva nombres de auxiliares con apóstrofo (ej.
  `"bloque'"`, `"expr_or'"`).
- El parser predictivo (`parser_predictivo.py:340-355`) crea hijos en el
  mismo orden a partir de la producción aplicada de la tabla LL(1).
  Como la gramática en `tabla_ll.py:GRAMATICA` usa nombres como
  `bloque_prima`, `expr_or_prima` (sin apóstrofo), **los nodos
  intermedios reciben esos nombres distintos**: `bloque_prima` vs
  `bloque'`.
- Ambos producen el mismo dict JSON con claves `id, etiqueta,
  es_terminal, es_error, hijos`.
- Nodos error (`ERROR<...>`) aparecen en posiciones distintas: el
  recursivo los inserta en el padre actual al consumir mal; el
  predictivo los pone como reemplazo de la etiqueta del nodo cuando
  hace INSERTAR. La forma del árbol es coherente pero los marcadores no
  están en la misma posición exacta.

> **Conclusión A**: el árbol existe y es navegable pero está pensado
> para *dibujarse*, no para hacer análisis semántico. Falta posición
> léxica, falta abstracción (auxiliares de factorización ensucian el
> árbol), y falta una jerarquía de tipos por construcción. Hay dos
> definiciones duplicadas de `NodoArbol` que conviene unificar.

---

## B. Arquitectura recomendada

### Recomendación: **(b) Pasada adicional sobre el árbol existente, agregando un visitor**

Justificación punto por punto:

1. **Reutilizo todo el trabajo de E1-E3.** El árbol ya se construye en
   ambos parsers y ya se serializa idéntico. No necesito tocar lexer ni
   parsers. Cumple "separación de fases" porque la pasada semántica
   recibe el árbol terminado y produce su propia lista de errores
   semánticos, sin tocar las clases sintácticas.

2. **No es opción (a) "Visitor sobre AST nuevo"** porque:
   - Construir un AST tipado paralelo (clases `NodoFuncion`, `NodoSi`,
     `NodoExpresionBin`, `NodoLiteralEntero`, ...) implica una pasada
     extra de *lowering* CST→AST que duplica esfuerzo. Eso es trabajo
     bonito pero no lo pide la rúbrica.
   - La gramática de DiamondLang ya está estable y es pequeña (≈40
     no-terminales): puedo trabajar contra el CST directamente sin
     pagar el coste de una jerarquía de clases.

3. **No es opción (c) "Acciones semánticas incrustadas"** porque:
   - Rompe la separación de fases que la rúbrica evalúa explícitamente
     y mezcla recuperación de errores sintácticos con validaciones
     semánticas.
   - Habría que duplicar las acciones en los dos parsers (recursivo y
     predictivo), o solo en uno, perdiendo paridad.
   - Más difícil de demostrar en sustentación ("¿dónde está la fase
     semántica?" — esparcida).

4. **Demostración en sustentación**: una pasada semántica separada se
   ve clarísimo: un módulo `semantico.py` (o `analizador_semantico.py`)
   con una clase `AnalizadorSemantico` que recibe el árbol del parser
   y un `TablaSimbolos`, y produce `errores_semanticos: list`. Endpoint
   nuevo o ampliación de `/parsear` con `errores_semanticos` además de
   los sintácticos.

### Trabajo concreto que requiere la opción (b)

- **Enriquecer `NodoArbol`** con dos campos opcionales `linea` y
  `columna` (heredados del token cuando es terminal; o calculados
  como "primer terminal descendiente" cuando es no-terminal). Es la
  única modificación intrusiva, pero mínima.
- **Helpers de navegación**: funciones como
  `hijo_por_etiqueta(nodo, "IDENTIFICADOR")` y
  `hijos_filtrados(nodo, "decl_variable")` para no escribir bucles a
  mano cada vez.
- **Saltar nodos auxiliares**: muchas producciones (`expr_or'`,
  `param_lista_prima`, `arg_lista_prima`) son ε o concatenan; el
  visitor debe colapsarlos. Esto es lo "fastidioso" del CST pero es
  manejable.

### Si el profesor prefiere (a): estimación de nodos AST a crear

Si finalmente se opta por construir un AST limpio (no recomendado en
mi análisis, pero por completitud), serían **~14 tipos de nodo**
nuevos derivados de la gramática:

| Tipo de nodo AST           | Producción gramatical original                  |
|----------------------------|-------------------------------------------------|
| `NodoPrograma`             | `programa`                                      |
| `NodoFuncion`              | `def_funcion`                                   |
| `NodoParametro`            | `param_lista` / `param_lista_prima`             |
| `NodoDeclVariable`         | `decl_variable`                                 |
| `NodoAsignacion`           | `sentencia_id` con cola `<-`                    |
| `NodoLlamada`              | `sentencia_id` con cola `(`  /  `sufijo_id`     |
| `NodoSi`                   | `sent_si` + `rama_sino`                         |
| `NodoMientras`             | `sent_mientras`                                 |
| `NodoPara`                 | `sent_para` + `paso_opt`                        |
| `NodoRetornar`             | `sent_retornar`                                 |
| `NodoEscribir` / `NodoLeer`| `sent_escribir`, `sent_leer`                    |
| `NodoExprBin`              | `expr_or/and/rel/add/mul/pot` + sus primas      |
| `NodoExprUnaria`           | `expr_unaria` (no / -)                          |
| `NodoLiteral` (int/real/str/bool) y `NodoIdent` | `expr_primaria`               |

---

## C. Mapeo regla semántica → producción gramatical

Notación: SYN = atributo sintetizado (sube de hijos a padre);
INH = atributo heredado (baja de padre a hijos).

### Regla 1 — Declaración duplicada en el mismo ámbito

- **Producciones donde se dispara**:
  - `decl_variable → tipo IDENTIFICADOR <- expresion` (variables
    locales).
  - `def_funcion → funcion IDENTIFICADOR ( parametros ) ...` (nombre
    de la función en el ámbito global).
  - `param_lista → tipo IDENTIFICADOR param_lista_prima` y su prima
    (parámetros formales en el ámbito de la función).
  - `sent_para → para IDENTIFICADOR desde ...` (variable de iteración
    en el ámbito del bucle, si decidimos que abre un scope).
- **Atributos**:
  - INH: el `ambito` actual baja desde el nodo padre (programa, función,
    bloque).
  - SYN: la acción de insertar en la tabla puede sintetizar
    `insertado: bool` para que el padre sepa si el subárbol introdujo
    un símbolo.
- **Tabla de símbolos**: necesita método
  `insertar(nombre, info, ambito_actual)` que **falle/reporte si ya
  existe `nombre` en ese mismo nivel** (sin mirar niveles padres).

### Regla 2 — Uso de identificador no declarado

- **Producciones donde se dispara**:
  - `expr_primaria → IDENTIFICADOR sufijo_id` (uso como variable o
    llamada).
  - `sentencia_id → IDENTIFICADOR sentencia_id_cola` (asignación
    `id <- expr` o llamada `id(args)`).
  - `sent_leer → leer ( IDENTIFICADOR )`.
  - `sent_para → para IDENTIFICADOR desde ...` (si la variable debe
    estar previamente declarada — decisión de diseño abierta, ver §F).
- **Atributos**:
  - INH: el `ambito` (pila de scopes visibles) baja desde el padre.
  - SYN: el nodo `expr_primaria` sintetiza `tipo` hacia arriba (si la
    variable no existe, `tipo = ERROR` y se reporta).
- **Tabla de símbolos**: requiere `lookup(nombre)` que recorra
  la pila de ámbitos visibles (local → enclosing → global).

### Regla 3 — Variable usada sin haber sido inicializada

- **Producciones donde se dispara**:
  - Las mismas que la regla 2 cuando el identificador aparece en
    **posición de lectura** (lado derecho de `<-`, dentro de una
    expresión, como argumento).
  - **Importante**: en `sentencia_id_cola → <- expresion`, el
    identificador izquierdo es asignación, **no lectura**, así que ahí
    no se valida; sí en la `expresion` derecha.
- **Atributos**:
  - INH: estado de inicialización `iniciada: bool` de cada variable
    en la tabla, que se vuelve `True` cuando aparece en el lado izquierdo
    de un `<-` o cuando se declara con valor (en DiamondLang la
    declaración siempre incluye `<- expresion`, ver §D, así que
    *toda variable declarada queda inicializada de entrada*; el caso
    interesante es **parámetros usados antes de asignar otra vez** —
    igualmente quedan iniciados — o **variables iterativas de `para`**).
  - Si confirmas que en DiamondLang **no existen declaraciones sin
    asignación inicial** (gramática: `decl_variable → tipo ID <- expr`
    obligatorio), entonces la regla 3 se vuelve casi trivial; solo
    queda valida la **variable de `para`** y los **parámetros de
    función**.
- **Tabla de símbolos**: bandera `iniciada` por cada símbolo de tipo
  variable.

### Regla 4 — Condición de `si` y `mientras` debe ser booleana

- **Producciones donde se dispara**:
  - `sent_si → si expresion entonces bloque rama_sino fin_si`: la
    primera `expresion`.
  - `sent_mientras → mientras expresion hacer bloque fin_mientras`:
    la `expresion`.
  - **(Opcional)** `sent_para → para ID desde expresion hasta
    expresion ...`: las dos expresiones deben ser numéricas (no
    booleano, pero es una validación gemela útil — confirmar si entra
    en el alcance de E4).
- **Atributos**:
  - SYN: `tipo` sube por toda la jerarquía de expresiones
    (`expr_or` → `expr_and` → `expr_rel` → `expr_add` → `expr_mul` →
    `expr_pot` → `expr_unaria` → `expr_primaria`).
  - El padre `sent_si`/`sent_mientras` lee el `tipo` sintetizado y lo
    compara con `booleano`.
- **Tabla de símbolos**: no necesita información especial; sí necesita
  las reglas de promoción de tipo en operadores:
  - `==, !=, <, >, <=, >= → booleano` (independiente de operandos
    numéricos compatibles).
  - `y, o, no → booleano` (operandos deben ser booleanos).
  - `+, -, *, /, %, ** → numérico` (entero o real con promoción).
  - Literales `verdadero`/`falso` → booleano.

### Regla 5 — Aridad y tipos de argumentos en llamadas a función

- **Producciones donde se dispara**:
  - `expr_primaria → IDENTIFICADOR sufijo_id` cuando `sufijo_id → (
    argumentos )` (llamada en posición de expresión).
  - `sentencia_id → IDENTIFICADOR sentencia_id_cola` cuando
    `sentencia_id_cola → ( argumentos )` (llamada en posición de
    sentencia).
  - Indirectamente: la firma se *registra* al procesar `def_funcion`
    (cada parámetro de `param_lista`).
- **Atributos**:
  - SYN: cada `expresion` dentro de `arg_lista` sintetiza su `tipo`;
    la lista de argumentos sintetiza `(aridad, tipos[])`.
  - INH: dentro de los argumentos no hace falta heredar nada — la
    validación ocurre en el padre `expr_primaria`/`sentencia_id_cola`
    una vez que tiene la lista de tipos.
- **Tabla de símbolos**: necesita guardar para cada función:
  `nombre`, `tipo_retorno`, `aridad`, `tipos_parametros: list[str]`,
  `nombres_parametros: list[str]`. El `lookup(nombre)` cuando ve una
  llamada compara aridad, después compara cada `tipo_arg[i]` con
  `tipos_parametros[i]` con compatibilidad simple
  (entero⊆real, exacto en lo demás).

---

## D. Lenguaje fuente: confirmación

A partir de `lexer.py`, `tabla_ll.py:GRAMATICA` y los ejemplos `.dml`:

### D.1 Tipos primitivos
`entero, real, cadena, booleano, vacio` (declarados como `TIPOS` en
`lexer.py:57` y como producción `tipo` en `tabla_ll.py:86-92`). Los
literales son `ENTERO` (regex `\d+`), `REAL` (`\d+\.\d+`), `CADENA`
(comillas `"` o `'`), y `verdadero` / `falso` para booleanos.

### D.2 Declaración de variables
**Solo con asignación inicial obligatoria**:
```
decl_variable → tipo IDENTIFICADOR <- expresion
```
No existe `entero x` suelto. Esto **simplifica la regla 3** (toda
declaración inicializa).

### D.3 Estructuras de control y delimitadores
| Construcción | Apertura | Cierre |
|---|---|---|
| Función      | `funcion ID ( params ) [retornar tipo] hacer` | `fin_funcion` |
| Condicional  | `si expr entonces` … `[sino ...]`               | `fin_si`       |
| Bucle `mientras` | `mientras expr hacer`                      | `fin_mientras` |
| Bucle `para` | `para ID desde expr hasta expr [paso expr] hacer` | `fin_para`  |

### D.4 Funciones, parámetros, retorno, recursión
- **Funciones sí**, definidas por `def_funcion` (`tabla_ll.py:66-68`).
- **Parámetros tipados** posicionalmente: `tipo ID, tipo ID, ...`.
- **Retorno opcional** (`tipo_retorno_opt → retornar tipo | ε`).
  Cuidado: en gramática la palabra `retornar` está sobrecargada,
  funciona como (a) anuncio de tipo de retorno en la firma y (b)
  sentencia `sent_retornar → retornar expresion`. Esto es legal
  porque el contexto desambigua, pero hay que tenerlo presente en
  semántica (la firma usa el `retornar` que aparece **después** de
  `)`; la sentencia usa el `retornar` que aparece **dentro** del
  bloque).
- **Recursión sí**: el ejemplo `factorial(n - 1)` la usa
  (`README_ENTREGA3.md:127`, ejemplos del lexer).

### D.5 Clases
**No implementadas.** `lexer.py:46-54` reserva `clase, fin_clase, nuevo,
este` como `KEYWORD`. `tabla_ll.py:36` los incluye en `TERMINALES`.
`recuperacion.py:31-34` los menciona en `SYNC_GLOBAL`. Pero **no hay
ninguna producción en `GRAMATICA` que use `clase` ni `fin_clase`**.
Confirmo lo que decía el README de E3: están reservados a futuro pero
**no parseables hoy**. Para E4 los podemos ignorar.

### D.6 Reglas de alcance (scoping)
**No observado explícitamente en el código revisado**. La gramática
no impone un comportamiento de scoping y no hay ningún módulo de
ámbitos. Las decisiones que toca tomar:

1. **Variables declaradas en el cuerpo de una función**: lo natural en
   un lenguaje sin bloques de llaves es que vivan en el ámbito de la
   función completa (no por bloque interno). DiamondLang no tiene
   delimitadores de bloque genéricos (`{...}`), solo `hacer`/`fin_*` —
   y todos esos `fin_*` cierran una estructura específica (función,
   si, mientras, para), no un bloque arbitrario.
2. **¿`si`/`mientras`/`para` abren un nuevo ámbito?** Decisión
   pedagógica. Lo más simple para E4: **no, todo el cuerpo de una
   función es un único ámbito**. Excepción: la variable de iteración
   de `para ID desde ...` podría considerarse local al bucle.
3. **Ámbito global**: existe a nivel de programa (funciones
   declaradas, posibles variables top-level si la gramática
   `programa → declaracion*` lo permite — y lo permite, porque
   `declaracion → sentencia` y `sentencia` puede ser una
   `decl_variable`).

**Recomendación a confirmar con el profesor (§F.5):** una pila de tres
niveles — global, función, bucle-`para` — es suficiente y demostrable.

---

## E. Integración con E3

### E.1 ¿Cómo se llama al parser desde el server?

`server.py:78-129` (`POST /parsear`):

```python
if metodo == 'recursivo':
    parser    = ParserRecursivo(codigo, max_errores=max_errores)
    resultado = parser.analizar()
elif metodo == 'predictivo':
    parser    = ParserPredictivo(codigo, max_errores=max_errores)
    resultado = parser.analizar()
```

El `dict` que devuelve `analizar()` se manda directamente con
`jsonify(resultado)`.

### E.2 Estructura del JSON de respuesta

```jsonc
{
  "valido":  bool,
  "errores": [
    {
      "indice":               int,
      "fila":                 int,
      "columna":              int,
      "lexema":               str,
      "tipo_token":           str,
      "tokens_esperados":     [str],
      "no_terminal":          str,
      "produccion_intentada": str | null,
      "sugerencia":           str,
      "fuente_sugerencia":    "local" | "ia"
    }
  ],
  "error":  str | null,    // compatibilidad: primer error formateado
  "nodos":  { "id":..., "etiqueta":..., "es_terminal":..., "es_error":..., "hijos":[...] },
  "traza":  [...],         // solo método predictivo
  "metodo": "recursivo" | "predictivo"
}
```

Endpoints adicionales: `/ping`, `/ping_ia`, `/analizar` (léxico),
`/tabla_ll`. Para E4 lo más prolijo es **extender la respuesta de
`/parsear` con `errores_semanticos: [...]`** (mismo modelo de
`ErrorSintactico` adaptado) más una bandera `valido_semantico: bool`,
manteniendo `valido` con el significado actual (`= valido_sintactico`).
Alternativa: endpoint nuevo `/analizar_semantico` que consuma el
árbol; menos elegante porque el frontend tendría que hacer dos
fetch encadenados.

### E.3 ¿Dónde se renderizan los errores en el frontend?

`diamondlang.html`:
- Función JS `parsear()` en línea 514-544: hace `POST /parsear` y
  llama a `renderErroresSintacticos(data.errores)`.
- Función `renderErroresSintacticos(errores)` en línea 569-604:
  pinta una lista numerada en `<ol id="errores-list">` dentro de
  `<div id="errores-panel">`. Cada item muestra índice, posición,
  lexema, no-terminal, tokens esperados, y la sugerencia. Click en
  un item resalta la línea/columna en el editor
  (`resaltarEnEditor`, línea 607-619).

Para E4 lo razonable es **agregar un segundo panel o sección dentro
del mismo panel** con `renderErroresSemanticos(data.errores_semanticos)`
reutilizando el estilo. Cambios mínimos en HTML.

---

## F. Riesgos y preguntas abiertas

### F.1 [DEUDA TÉCNICA] El árbol no guarda línea/columna
`NodoArbol` solo tiene `etiqueta` (string), no la referencia al
`Token` original. Para reportar errores semánticos con posición
necesito acceso a `linea`/`columna` del identificador o de la
expresión. **Tres alternativas, te las pongo para decidir**:

  (i)   Enriquecer `NodoArbol` con `linea, columna` opcionales
        rellenados en los puntos donde se crea desde un Token (un
        cambio en `consumir` y en el branch terminal del predictivo).
        Es ~5 líneas en cada parser, retrocompatible.

  (ii)  Pasar al analizador semántico también la lista de `tokens`
        del parser, y resolver posiciones por índice de aparición.
        Frágil con marcadores `ERROR<...>`.

  (iii) Construir un AST nuevo en la fase semántica (opción A de
        §B), aprovechando para enriquecer cada nodo con posición.
        Más trabajo, mejor diseño a largo plazo.

  Mi voto: (i), simple y suficiente.

### F.2 [DEUDA TÉCNICA] `NodoArbol` está duplicado
La clase está definida idéntica en `parser_recursivo.py:32` y
`parser_predictivo.py:37`. Si en E4 voy a agregar `linea/columna`,
hay que hacerlo en los dos lugares (o consolidarlo en un módulo
`ast.py` o `arbol.py` antes). Mi propuesta: extraerlo a un archivo
común al inicio de E4 para no duplicar el cambio.

### F.3 Nodos auxiliares "ensucian" el árbol
Producciones primas (`expr_or'`, `bloque'`, `arg_lista'`, …) y nodos
`ε` generan ruido al recorrer. El analizador semántico deberá
saltarlos o aplanarlos. Decisión: ¿el visitor los normaliza al
vuelo, o escribo un helper `aplanar_expresiones(nodo)` que devuelva
la lista plana de operandos y operadores de una expresión binaria
asociativa por izquierda? La segunda es más demostrable.

### F.4 Diferencia de nombres entre los dos parsers
`bloque_prima` (predictivo) vs `bloque'` (recursivo); idem para
todas las primas. El analizador semántico tiene que saber ambas o
asumir un único método. **¿Cuál de los dos parsers vamos a usar
como entrada al análisis semántico, o ambos?** Sugerencia: ambos
producen árboles equivalentes, así que el analizador semántico se
diseña agnóstico (consulta por prefijo `etiqueta.startswith("bloque")`
o tabla de equivalencias), y se prueba con los dos. Necesito tu
confirmación.

### F.5 Reglas de scoping no están en la spec
La gramática no fuerza nada. **Necesito que confirmes**:
- ¿Solo dos ámbitos (global + función)?
- ¿Tres (global + función + bucle `para`)?
- ¿`si`/`mientras` abren nuevo ámbito? (Mi recomendación: no.)
- Una variable declarada en una función, ¿se ve después de un `si`
  más abajo? (Sí, si solo hay un scope por función.)

### F.6 Definiciones múltiples de función
`programa → declaracion*` permite varias `def_funcion`. ¿Se permite
que dos funciones tengan el mismo nombre (overload)? ¿O se reporta
duplicado? Asumo **no se permite duplicado** (regla 1 aplica también
a nombres de función en el ámbito global), confirma.

### F.7 Compatibilidad de tipos
La gramática reconoce `entero, real, cadena, booleano, vacio`.
Preguntas que necesitan tu decisión:
- ¿`entero` se promociona a `real` en operaciones aritméticas?
  (Recomiendo sí, es lo más educativo.)
- ¿Una `cadena` admite concatenación con `+`? Si sí, hay que
  permitirlo en `expr_add`; si no, error semántico.
- ¿Asignar `real` a una variable `entero` es error o truncado
  implícito? (Recomiendo error.)
- `vacio` solo tiene sentido como tipo de retorno; usarlo en
  declaración de variable, ¿es error? (Recomiendo sí, error.)

### F.8 `retornar` dentro de función `vacio`
Si la firma declara `retornar vacio` (o no declara retorno: `→ ε` en
`tipo_retorno_opt`), ¿se permite `sent_retornar` con expresión?
Asumo: si el tipo de retorno es `vacio` o ausente, `retornar` sin
expresión; pero la gramática actual `sent_retornar → retornar
expresion` **obliga a una expresión**. **Esto es una inconsistencia
sintáctica que afecta E4**: o cambias la gramática (no para esta
entrega) o tratas el caso como "siempre debe haber expresión y debe
ser compatible con el tipo declarado".

### F.9 Llamadas a función desconocida vs. variable desconocida
En `expr_primaria → IDENTIFICADOR sufijo_id`, el `sufijo_id` decide
si es uso de variable (`ε`) o llamada (`( argumentos )`). Para
reportar bien hay que mirar el sufijo *antes* de decidir el mensaje
de error (no es "variable no declarada" si es una llamada, es
"función no declarada").

### F.10 Errores en cascada
Si una variable es no declarada, su uso en una expresión hace que la
expresión tenga `tipo = ERROR`. Hay que propagarlo y **no reportar
errores derivados** ("el operando izquierdo del `+` no es numérico")
cuando ya hay `tipo = ERROR` debajo. Implementarlo desde el día uno
evita ruido.

### F.11 Programas con errores sintácticos: ¿hago análisis semántico?
El árbol sale aún con errores (modo pánico inserta `ERROR<...>` y
sigue). **Decisión**: si hay errores sintácticos, ¿corro semántica
sobre el árbol degradado, o suprimo la fase? Mi recomendación: **sí
correr la fase semántica**, pero ignorar los subárboles que contengan
nodos `es_error = True`. Reportar lo que se pueda. Útil
pedagógicamente.

---

## Próximo paso propuesto (Etapa 1)

Si apruebas el plan, en la Etapa 1 haría **solo** estos tres cambios
chicos y autocontenidos, para dejar el terreno listo sin tocar todavía
la lógica de análisis semántico:

1. **Unificar `NodoArbol`** en un archivo nuevo `arbol.py` (importado
   por ambos parsers), agregándole campos `linea: int|None` y
   `columna: int|None`. Migrar los dos parsers a importar de ahí.
   Cero cambio funcional.
2. **Rellenar `linea`/`columna`** en los puntos donde el nodo nace de
   un `Token` (en `consumir()` del recursivo y en el branch de match
   del predictivo). Asegurar que los nodos no-terminales hereden la
   posición de su primer terminal descendiente (helper recursivo
   pequeño en serialización).
3. **Confirmar el contrato** con un test rápido (script `python -c
   '...'`) que parsea un ejemplo y verifica que los nodos terminales
   tienen `linea/columna` no nulos.

Después de eso, con el árbol enriquecido y unificado, en la Etapa 2
abriríamos el módulo `semantico.py` con la `TablaSimbolos` y empezaría
la implementación de las cinco reglas, una por una con sus tests
asociados. Pero esa propuesta queda pendiente de tu validación de
este plan.

---

## Decisiones aprobadas

Decisiones del usuario tras la revisión de este plan. Algunas no aplican
todavía a la Etapa 1 (preparación del terreno) pero quedan registradas
para etapas posteriores.

- **Arquitectura**: opción (b) — pasada adicional sobre el CST existente
  (no se construye AST nuevo; no se incrustan acciones semánticas en el
  parser).
- **Reglas semánticas finales** (la regla 3 cambia respecto al plan
  original):
  1. Declaración duplicada de identificador en el mismo ámbito.
  2. Uso de identificador no declarado.
  3. **Compatibilidad de tipos en asignación** *(reemplaza la regla
     original "variable usada sin inicializar", que quedaba débil porque
     DiamondLang obliga a inicializar en la declaración)*.
  4. La condición de `si` y `mientras` debe ser de tipo booleano.
  5. Aridad y tipos de argumentos en llamadas a función deben coincidir
     con la firma declarada.
- **Scoping**: solo dos niveles, global y función. `si`/`mientras`/`para`
  **no** abren ámbito nuevo.
- **Funciones con nombre duplicado**: error (la regla 1 también aplica a
  los nombres de función en el ámbito global).
- **Tipos**:
  - `entero` se promociona a `real` en operaciones aritméticas.
  - `cadena + cadena` es concatenación válida.
  - Asignar `real` a una variable `entero` es error.
  - `vacio` solo es válido como tipo de retorno; usarlo en una
    declaración de variable es error.
- **`retornar` en función `vacio`**: si el tipo de retorno declarado es
  `vacio`, cualquier `sent_retornar` con expresión es error semántico.
- **Mensajes de error**: distinguir "variable no declarada" vs "función
  no declarada" según presencia o no de sufijo de llamada.
- **Errores en cascada**: propagar `tipo = ERROR` y **no** reportar
  errores derivados aguas arriba.
- **Programas con errores sintácticos**: el análisis semántico **sí**
  corre, sobre subárboles que no contengan nodos `es_error=True`.
- **Diseño agnóstico al parser**: el analizador semántico debe funcionar
  tanto con la salida del parser recursivo (auxiliares con apóstrofo:
  `bloque'`, `expr_or'`, …) como con la del predictivo (con sufijo
  `_prima`: `bloque_prima`, `expr_or_prima`, …).

---

## Etapa 2 — Infraestructura semántica

Cerrada con todos los tests en verde. **No se invoca todavía desde
`server.py`**: la infraestructura está en su sitio pero el endpoint
`/parsear` devuelve exactamente el mismo JSON que en E3/Etapa 1. La
Etapa 3 enchufará el visitor con las cinco reglas semánticas.

### Archivos creados

- `errores_semanticos.py` — Dataclass `ErrorSemantico` (paralela a
  `ErrorSintactico`) + `como_dict()` + `formatear_error()` /
  `formatear_lista()` con el mismo estilo visual que `errores.py`.
- `tabla_simbolos.py` — Dataclass `Simbolo` y clase `TablaSimbolos`
  (pila de ámbitos con `abrir_ambito`, `cerrar_ambito`, `declarar`,
  `buscar`, `existe_en_ambito_actual`, `ambito_actual`,
  `todos_los_simbolos`, `__repr__`).
- `semantico.py` — Esqueleto del visitor `AnalizadorSemantico`:
  recorre el CST con dispatch por etiqueta normalizada, salta
  sub-árboles con errores sintácticos, expone `analizar()` que
  devuelve `{valido_semantico, errores_semanticos, simbolos}`. Sin
  métodos `_visit_<etiqueta>` específicos (pendientes para Etapa 3).
- `test_etapa2_infraestructura.py` — Tests unitarios: 4 sobre
  `TablaSimbolos`, 6 sobre los helpers de `arbol.py`, 3 sobre el
  esqueleto del analizador.

### Archivos modificados

- `arbol.py` — Helpers de navegación añadidos al final:
  `hijos_por_etiqueta`, `hijo_por_etiqueta`, `primer_terminal`,
  `recolectar_terminales`, `tiene_error_sintactico`,
  `etiqueta_normalizada`, `raiz_logica`. No cambia el comportamiento
  existente (`NodoArbol` y `propagar_posicion_terminales` intactos).

### Elección de nombre canónico para etiquetas auxiliares

El parser recursivo usa `bloque'`, `expr_or'`, `param_lista'`,
`arg_lista'`, … (con apóstrofo). El predictivo usa `bloque_prima`,
`expr_or_prima`, etc. (con sufijo `_prima`).

**Canónico elegido**: `_prima`.

**Razón**: `_prima` es un identificador Python válido, así que los
métodos del visitor pueden llamarse `_visit_bloque_prima`,
`_visit_param_lista_prima`, etc. Si hubiéramos elegido la forma con
apóstrofo, los métodos llevarían apóstrofo en el nombre — los podemos
indexar con `getattr` pero rompen el linter, no autocompletan, y
chocan con la convención del resto del proyecto. El costo de
normalizar las dos variantes a una forma única se paga una sola vez en
`etiqueta_normalizada()` y ahí queda.

---

## Etapa 3 — Reglas 1 y 2

Reglas semánticas implementadas:

- **Regla 1 — Declaración duplicada en el mismo ámbito**: dispara
  para variables (`decl_variable`), parámetros (`param_lista` /
  `param_lista_prima`) y funciones (`def_funcion`). El símbolo
  original se mantiene en la tabla; el duplicado se rechaza y se
  reporta, pero el cuerpo de la función se sigue procesando.
- **Regla 2 — Uso de identificador no declarado**: dispara en
  `expr_primaria → IDENTIFICADOR sufijo_id`,
  `sentencia_id → IDENTIFICADOR sentencia_id_cola`,
  `sent_leer → leer ( IDENTIFICADOR )` y
  `sent_para → para IDENTIFICADOR desde …` (la variable de iteración
  debe estar declarada previamente: decisión F.5 aprobada — el `para`
  no abre scope). El mensaje distingue "variable" vs "función" según
  la presencia de paréntesis en el sufijo / la cola (decisión F.9).

**El endpoint `/parsear` no se ha modificado todavía**. El analizador
semántico se ejerce sólo desde los tests; la integración con el
servidor es la Etapa 8.

### Archivos creados

- `ejemplos_semanticos/01_decl_duplicada_variable.dml` — doble
  declaración de `x` en la función `principal`.
- `ejemplos_semanticos/02_decl_duplicada_parametro.dml` — función
  `sumar` con dos parámetros llamados `a`.
- `ejemplos_semanticos/03_uso_variable_no_declarada.dml` — uso de
  variable `desconocida` (no declarada) dentro de `escribir(...)`.
- `ejemplos_semanticos/04_llamada_funcion_no_declarada.dml` —
  llamada a función `inexistente(5)` no declarada.
- `test_etapa3_reglas_1_2.py` — tests por ejemplo (con ambos
  parsers), test de no-regresión (factorial) y smoke test que
  combina los dos tipos de errores.

### Archivos modificados

- `semantico.py` — Implementación de los visitors:
  `_visit_programa`, `_visit_def_funcion`, `_visit_decl_variable`,
  `_visit_expr_primaria`, `_visit_sentencia_id`, `_visit_sent_leer`,
  `_visit_sent_para`; helpers de extracción
  (`_recolectar_parametros`, `_extraer_nombre_tipo`,
  `_extraer_tipo_retorno`, `_tiene_hijo_terminal`,
  `_reportar_duplicado`, `_reportar_uso_no_declarado`); snapshot de
  ámbitos en `_simbolos_historicos` antes de cerrar cada función.
- `tabla_simbolos.py` — Helper `simbolos_del_ambito_actual()` para
  snapshotear sólo el ámbito del tope (necesario para preservar
  parámetros/locales tras cerrar el ámbito de cada función).

### Decisiones tomadas sobre la marcha

1. **Identificadores extraídos por posición fija de hijos**. Como
   tanto el parser recursivo como el predictivo respetan el orden
   de los símbolos en la producción (y ninguno intercala epsilons en
   los hijos directos de las producciones afectadas), uso
   `nodo.hijos[1]` para el nombre de función / variable / parámetro
   de `para`, `nodo.hijos[2]` para `leer`, y `nodo.hijos[0]` para
   `sentencia_id` / `expr_primaria`. Es la forma menos frágil: no
   depende del valor textual del lexema (que ya es el nombre real
   del identificador, no el placeholder "IDENTIFICADOR").

2. **Detección de "es llamada"**: para el sufijo o cola tras un
   identificador, busco un hijo terminal `(`. Si está, es llamada
   (función); si no, es variable / asignación. Aplica tanto a
   `sufijo_id → ( argumentos ) | ε` como a
   `sentencia_id_cola → <- expresion | ( argumentos )`.

3. **Recolección de parámetros tipo-por-tipo**. Camino por el
   sub-árbol `parametros` buscando nodos `tipo`; el siguiente hijo
   inmediato es el `IDENTIFICADOR` de ese parámetro. Recurso por
   los hijos no-terminales cuya etiqueta normalizada caiga en
   `{'parametros', 'param_lista', 'param_lista_prima'}`. Robusto a
   las dos variantes (`param_lista'` vs `param_lista_prima`).

4. **Distinción palabra clave vs identificador**. Sorpresa durante
   la elaboración de los .dml: `y`, `o`, `no` son **palabras clave**
   en DiamondLang (operadores lógicos). El primer borrador del
   ejemplo 03 usaba `y` como nombre de variable, lo que generaba un
   error sintáctico en lugar de uno semántico. Lo cambié a
   `desconocida`. Punto a tener presente en pruebas futuras.

5. **Función registrada ANTES de abrir su scope**. Esto permite que
   la recursión funcione: cuando la fase semántica entra al cuerpo
   y encuentra una llamada a la propia función, ésta ya está en
   `global`. El factorial pasa el test de no-regresión por esto.

6. **Ordenamiento "declarar y luego visitar RHS"** en
   `_visit_decl_variable`, siguiendo literalmente la especificación
   de la Etapa 3. Consecuencia: `entero y <- y + 1` NO reporta a
   `y` como no declarada (porque al visitar el RHS, `y` ya está en
   la tabla). Si en una etapa posterior queremos cazar
   "uso-antes-de-inicialización", habrá que reordenar; por ahora
   queda como decisión consciente.

7. **Snapshot de símbolos antes de cerrar ámbito**. Para que el
   campo `simbolos` de la respuesta refleje también los parámetros
   y locales de cada función analizada, copio el contenido del
   ámbito del tope a `_simbolos_historicos` justo antes de
   `cerrar_ambito()`. El ámbito global se snapshea al final de
   `analizar()`. Sin esto, sólo se vería el global.

---

## Etapa 4 — Sistema de tipos

Etapa de **infraestructura de tipos**, no de reglas. No implementa
ninguna validación semántica nueva (asignación, condición, llamadas) ni
modifica ningún `_visit_*` existente; construye el motor de inferencia
que las Etapas 5, 6 y 7 consultarán. **No se invoca todavía** desde
`semantico.py` ni desde `server.py`: el endpoint `/parsear` devuelve el
mismo JSON que en E3 (`{valido, errores, error, nodos}`, sin claves
semánticas).

### Archivos creados

- `tipos.py` — sistema de tipos. Funciones públicas:
  - `TIPOS_NUMERICOS`, `TIPOS_BASICOS` (conjuntos).
  - `compatible(destino, origen)` — regla de compatibilidad con
    promoción `entero→real` y supresión de cascada vía `ERROR`.
  - `unificar_aritmetico / unificar_relacional / unificar_logico /
    unificar_unario` — puras, sintetizan el tipo resultante o `ERROR`.
  - `tipo_de_literal(terminal)` — tipo de un literal a partir del lexema.
  - `tipo_declarado(nodo_tipo)` — keyword de un nodo `tipo`.
  - `tipo_de_expresion(nodo, tabla)` — inferencia **silenciosa** (pura).
  - `tipo_de_expresion_con_reporte(nodo, tabla, reportar)` — idéntica,
    pero reporta `TIPO_OPERADOR` (la usarán E5-E7).
- `test_etapa4_tipos.py` — tests por categorías A-G, corriendo C-G
  contra **ambos parsers**.

### Archivos modificados

- Ninguno de código. Sólo este documento. (`arbol.py`,
  `tabla_simbolos.py`, `semantico.py`, `server.py` y los parsers quedan
  intactos.)

### Tabla resumida de reglas de operadores implementadas

| Familia      | Operadores              | Operandos válidos → resultado |
|--------------|-------------------------|-------------------------------|
| Aritmético   | `+ - * / % **`          | `entero⊕entero→entero`; cualquiera `real`→`real` (promoción); **excepción**: `cadena + cadena → cadena` (sólo `+`); resto → `ERROR` |
| Relacional   | `== != < > <= >=`       | numérico⊕numérico→`booleano`; `cadena⊕cadena→booleano`; `booleano⊕booleano`→`booleano` **sólo** con `==`/`!=` (orden `<,>,<=,>=` sobre booleanos → `ERROR`); resto → `ERROR` |
| Lógico       | `y  o`                  | `booleano⊕booleano→booleano`; resto → `ERROR` |
| Unario `no`  | `no`                    | `booleano→booleano`; resto → `ERROR` |
| Unario `-`   | `-`                     | `entero→entero`, `real→real`; resto → `ERROR` |
| Literal      | `ENTERO/REAL/CADENA/verdadero/falso` | → `entero/real/cadena/booleano` |
| Identificador| variable                | tipo del `Simbolo`; ausente → `ERROR` |
| Llamada      | `f(args)`               | `tipo_retorno` de `f`; `f` ausente o confundida → `ERROR` (no valida aridad/tipos: eso es E7) |

Compatibilidad (`compatible(destino, origen)`): `T,T`→True;
`real,entero`→True; `entero,real`→False; cualquier par con `ERROR`→True
(suprime cascadas); resto→False.

### Decisiones de diseño tomadas sobre la marcha

1. **El operador de potencia es `**`, no `^`.** El enunciado lo nota
   como `^`, pero la gramática (`tabla_ll.py`) y el lexer usan `**`. El
   sistema de tipos trabaja con `**`. La excepción de concatenación sólo
   se activa con `+`, así que `**` se trata como aritmético genérico.

2. **`tipo_de_literal` deduce el tipo del LEXEMA, no de la categoría
   léxica.** El CST guarda `etiqueta = lexema` y pierde si el token era
   `ENTERO`/`REAL`/`CADENA` (deuda técnica §A.2). Se re-deduce:
   `verdadero`/`falso`→booleano; lexema que empieza por `"`/`'`→cadena
   (las comillas quedan en el lexema); `\d+`→entero; `\d+\.\d+`→real.

3. **Nodos prima recorridos como cola de operadores.** Los niveles
   izquierda-asociativos (`expr_or/and/add/mul`) comparten el patrón
   `nivel → operando prima` / `prima → op operando prima | ε`. Se
   resuelven con un único `_nivel_binario` parametrizado por
   `(etiqueta_operando, etiqueta_prima, familia)` que **acumula de
   izquierda a derecha** siguiendo la cadena de primas. `expr_rel` (un
   solo operador, sin cadena; el operador vive dentro de un nodo
   `op_rel`) y `expr_pot` (derecha-asociativo, el operando derecho es
   otro `expr_pot`) tienen su propio helper.

4. **Operando único sin operador.** Cuando un nivel tiene su prima en ε
   (no hay operador), `tipo_de_expresion` simplemente **propaga hacia
   arriba el tipo del operando izquierdo** sin combinar nada. Así una
   expresión como `5` sube intacta por los ocho niveles hasta dar
   `entero`.

5. **`expr_primaria`: literal vs identificador vs llamada vs paréntesis.**
   Se distingue por estructura, sin mirar el texto del lexema:
   - tiene hijo `sufijo_id` → es `IDENTIFICADOR`; si el `sufijo_id`
     contiene `(` es **llamada** (tipo = `tipo_retorno`), si no es **uso
     de variable** (tipo = `Simbolo.tipo`);
   - tiene hijo `expresion` → es **paréntesis** `( expresion )`, se baja
     recursivamente;
   - en otro caso es un **literal** (único terminal) → `tipo_de_literal`.

6. **Cascada (decisión F.10) centralizada.** La versión con reporte sólo
   emite `TIPO_OPERADOR` cuando **ambos** operandos son tipos válidos y
   el operador los rechaza. Si cualquier operando ya es `ERROR`, el
   operador se contagia en silencio. Verificado con `5 + "a" + 3`:
   reporta **una sola vez** (el segundo `+` opera sobre `ERROR`).

7. **Un solo callable para ambas versiones.** `tipo_de_expresion` y
   `tipo_de_expresion_con_reporte` delegan en el mismo `_inferir`,
   pasando `reportar=None` o `reportar=self._reportar`. La guarda
   `tiene_error_sintactico(nodo)` en la entrada cumple el requisito de
   devolver `ERROR` sin análisis ante sub-árboles dañados por el modo
   pánico.

### Verificación de cierre

- Tests de Etapas 1, 2 y 3: verdes (sin regresión).
- `test_etapa4_tipos.py`: todas las categorías A-G en verde, contra los
  dos parsers.
- `server.py` arranca y `/parsear` devuelve el mismo JSON (el sistema de
  tipos no se invoca todavía).
- `tipo_de_expresion` sobre los cuatro `ejemplos_semanticos/` se invoca
  sin excepciones y devuelve tipos coherentes en ambos parsers.

---

## Etapa 5 — Regla 3 (compatibilidad de tipos en asignación)

Primera etapa que **consume el motor de tipos** (`tipos.py`) desde el
visitor. Implementa la **Regla 3 — compatibilidad de tipos en
asignación** en sus dos disparadores, más la sub-regla de `vacio`. El
endpoint `/parsear` sigue **sin tocarse** (la integración con el
servidor es la Etapa 8); el analizador se ejerce sólo desde los tests.

### Reglas implementadas en esta etapa

- **Regla 3.A — Declaración con asignación inicial**
  (`decl_variable → tipo IDENTIFICADOR <- expresion`): el tipo declarado
  del LHS debe ser compatible con el tipo inferido del RHS, o se reporta
  `TIPO_ASIGNACION`.
- **Regla 3.B — Reasignación a variable existente**
  (`sentencia_id` con cola `<- expresion`): el tipo del símbolo
  previamente declarado debe ser compatible con el tipo del RHS. Asignar
  a una **función** (`f <- 5`) es siempre `TIPO_ASIGNACION`
  (contexto `tipo_destino='funcion'`).
- **Sub-regla `vacio`** (decisión F.7): declarar `vacio v <- …` reporta
  `TIPO_VOID_EN_VARIABLE` (apuntando al IDENTIFICADOR) antes de validar
  el RHS, sin abortar.
- **`TIPO_OPERADOR`** queda integrado automáticamente: el RHS se infiere
  con `tipo_de_expresion_con_reporte`, que ya emite ese error (Etapa 4).
  La supresión de cascada (F.10) vive en `tipos.py`.

### Archivos creados

- `ejemplos_semanticos/05_tipo_asignacion_decl.dml` — `entero x <- "hola"`
  (1 × `TIPO_ASIGNACION`, L5:C12).
- `ejemplos_semanticos/06_tipo_asignacion_reasignacion.dml` —
  reasignación `x <- "cadena"` sobre `entero x` (1 × `TIPO_ASIGNACION`,
  L6:C5).
- `ejemplos_semanticos/07_tipo_void_en_variable.dml` — `vacio v <- 0`
  (1 × `TIPO_VOID_EN_VARIABLE`, L7:C11; **sin** `TIPO_ASIGNACION`
  gracias al truco del símbolo con tipo `ERROR`).
- `ejemplos_semanticos/08_tipo_promocion_ok.dml` — `real a <- 5` y
  `real b <- 3.14` válidos (promoción `entero→real`); sólo
  `entero z <- 3.14` falla (1 × `TIPO_ASIGNACION`, L9:C12).
- `ejemplos_semanticos/09_cadena_concat_ok.dml` — `cadena s <- "hola " +
  "mundo"` (0 errores, caso válido de concatenación).
- `ejemplos_semanticos/10_cadena_concat_mixto.dml` —
  `cadena s <- "edad: " + 25` (1 × `TIPO_OPERADOR` en el `+`, L8:C26;
  **sin** `TIPO_ASIGNACION`, cascada suprimida).
- `test_etapa5_regla_3.py` — tests por ejemplo (ambos parsers, número
  exacto de errores, regla, fila/columna, lexema, fragmento de mensaje y
  contexto), no-regresión con un programa más complejo, test combinado
  reglas 1+2+3, y tres smoke tests de cierre.

### Archivos modificados

- `semantico.py`:
  - Nuevo import de `tipos`: `tipo_declarado`,
    `tipo_de_expresion_con_reporte`, `compatible`.
  - Nuevo helper `_visitar_y_tipar_expresion(nodo_expr)`: hace dos
    pasadas complementarias y disjuntas sobre una expresión —`_visitar`
    (Regla 2 sobre identificadores) y `tipo_de_expresion_con_reporte`
    (TIPO_OPERADOR)— y devuelve el tipo inferido. Lo usan
    `_visit_decl_variable`, `_visit_sentencia_id` y `_visit_sent_para`.
  - `_visit_decl_variable`: añade sub-regla `vacio` (TIPO_VOID_EN_VARIABLE),
    guarda `ERROR` como tipo del símbolo cuando es `vacio`, infiere el RHS
    y valida `TIPO_ASIGNACION`.
  - `_visit_sentencia_id`: en asignación, valida `TIPO_ASIGNACION` contra
    el tipo del símbolo (o reporta "asignar a función"); en llamada se
    mantiene sólo la Regla 2 (aridad/tipos → Etapa 7).
  - `_visit_sent_para`: cambio mínimo —procesa desde/hasta/paso con
    `_visitar_y_tipar_expresion` para no perder TIPO_OPERADOR internos,
    sin introducir TIPO_ASIGNACION (queda fuera de la Regla 3 por
    simplicidad, ver decisión abajo).
- `PLAN_ENTREGA4.md`: esta sección.
- (`tipos.py`, `tabla_simbolos.py`, `errores_semanticos.py`, `arbol.py`,
  `server.py`, los parsers y el frontend quedan **intactos**.)

### Decisiones tomadas sobre la marcha

1. **El tipo destino se lee del símbolo TAL COMO QUEDÓ EN LA TABLA**
   (`self.tabla.buscar(nombre).tipo`), no de la etiqueta declarada en la
   línea. Esto resuelve elegantemente el caso de declaración duplicada:
   la segunda declaración se rechaza (Regla 1) pero su RHS se mide contra
   el **contrato del símbolo previo** (su tipo original), que es lo
   vigente. También hace que `vacio` (guardado como `ERROR`) suprima el
   `TIPO_ASIGNACION` redundante sin código especial: `compatible('ERROR',
   T)` es `True`.

2. **`vacio` se guarda como `ERROR` en la tabla**, no como `vacio`. Así
   los usos posteriores de esa variable y la propia validación del RHS no
   generan cascadas: el único error visible es `TIPO_VOID_EN_VARIABLE`.

3. **`sent_para` queda fuera de la Regla 3 por simplicidad** (alcance del
   plan). La variable de iteración recibe una asignación implícita que en
   rigor debería compararse con `desde`, `hasta` y `paso` —tres
   validaciones cruzadas en un nodo—. Se documenta en el código y aquí
   que esto NO se valida en la Etapa 5. Lo que sí se hace es **inferir
   desde/hasta/paso con reporte** para que sus `TIPO_OPERADOR` internos
   no se pierdan.

4. **Dos pasadas por expresión, reglas disjuntas.** `_visitar` reporta
   sólo `USO_NO_DECLARADO` (vía `_visit_expr_primaria`) y
   `tipo_de_expresion_con_reporte` reporta sólo `TIPO_OPERADOR`. Como no
   se solapan, recorrer la expresión dos veces no produce doble conteo.

5. **Sorpresa (reincidente).** El primer borrador del ejemplo 08 usaba
   `real y <- 3.14`: `y` es **palabra clave** (operador lógico `y`) en
   DiamondLang, así que el lexer/parser lo rechazaba con error
   *sintáctico* y el ejemplo no llegaba a la fase semántica. Mismo
   tropiezo que en la Etapa 3 (decisión 4). Renombrado a `a`/`b`/`z`.
   Recordatorio permanente: evitar `y`, `o`, `no` como identificadores en
   los `.dml` de prueba.

### Verificación de cierre

1. Tests de Etapas 1, 2, 3 y 4: **verdes** (sin regresión).
2. `test_etapa5_regla_3.py`: **pasa entero** contra ambos parsers
   (recursivo y predictivo).
3. `server.py` arranca y `/parsear` devuelve el mismo JSON que en E3
   (`valido, errores, error, nodos, metodo` [+ `traza` en predictivo]);
   no aparecen claves semánticas. El análisis semántico sigue sin
   invocarse desde el servidor.
4. Smoke tests: `entero x <- "hola"` → **un solo** `TIPO_ASIGNACION` (sin
   `TIPO_OPERADOR`); `entero x <- 5 + "hola"` → **un solo**
   `TIPO_OPERADOR` (la cascada suprime `TIPO_ASIGNACION`). Verificado en
   ambos parsers.

---

## Etapa 6 — Regla 4 (condición de si/mientras debe ser booleano)

Implementa la **Regla 4 — la condición de `si` y `mientras` debe ser de
tipo `booleano`** (`TIPO_CONDICION`). El endpoint `/parsear` sigue **sin
tocarse** (la integración con el servidor es la Etapa 8); el analizador
se ejerce sólo desde los tests.

### Reglas implementadas en esta etapa

- **Regla 4 — `sent_si`**
  (`si expresion entonces bloque rama_sino fin_si`): la **primera**
  `expresion` (la condición) debe inferir `booleano`, o se reporta
  `TIPO_CONDICION`. La `rama_sino` es un bloque **sin condición** → no se
  valida su tipo, sólo se recorre.
- **Regla 4 — `sent_mientras`**
  (`mientras expresion hacer bloque fin_mientras`): la `expresion` del
  bucle debe inferir `booleano`.
- **Cascada (F.10)**: si la condición infiere `ERROR` (p.ej. usa una
  variable no declarada, o contiene un operador inválido), **no** se
  emite `TIPO_CONDICION` — la causa raíz ya la reportó `USO_NO_DECLARADO`
  o `TIPO_OPERADOR`.
- **Fuera de alcance** (confirmado): `sent_para` (las expresiones
  desde/hasta/paso deberían ser numéricas, pero esa validación no entra),
  y la `rama_sino`.

### Archivos creados

- `ejemplos_semanticos/11_condicion_si_no_booleana.dml` — `si x entonces`
  con `x` entero (1 × `TIPO_CONDICION`, L6:C8, lexema `x`).
- `ejemplos_semanticos/12_condicion_mientras_no_booleana.dml` —
  `mientras s hacer` con `s` cadena (1 × `TIPO_CONDICION`, L6:C14,
  lexema `s`).
- `ejemplos_semanticos/13_condicion_si_ok.dml` — `si x > 3 entonces …
  sino …` (0 errores; condición relacional → booleano).
- `ejemplos_semanticos/14_condicion_si_compuesta_ok.dml` —
  `si x > 3 y flag entonces` (0 errores; `(x>3) y flag` → booleano).
- `ejemplos_semanticos/15_condicion_cascada.dml` — `si desconocida
  entonces` (1 × `USO_NO_DECLARADO`, L6:C8; **sin** `TIPO_CONDICION`,
  cascada suprimida).
- `test_etapa6_regla_4.py` — tests por ejemplo (ambos parsers, número
  exacto de errores, regla, fila/columna, lexema, fragmento de mensaje y
  contexto), no-regresión con `si`/`mientras` anidados válidos, test
  combinado reglas 1+2+3+4, y tres smoke tests de cierre (condición no
  booleana única; cascada con variable no declarada; cascada con operador
  inválido en la condición de `mientras`).

### Archivos modificados

- `semantico.py`:
  - Nuevo import de `arbol`: `primer_terminal` (para anclar el error en el
    inicio de la condición).
  - Nuevo helper `_validar_condicion_booleana(nodo_expr, nombre_estructura,
    nodo_fallback)`: infiere el tipo de la condición con
    `_visitar_y_tipar_expresion` (que de paso cubre Regla 2 y
    TIPO_OPERADOR), suprime si es `ERROR`, y reporta `TIPO_CONDICION` si
    no es `booleano`.
  - Nuevos visitors `_visit_sent_si` y `_visit_sent_mientras`: localizan
    la condición (`hijo_por_etiqueta(nodo, 'expresion')`), la validan con
    el helper y recorren el resto del cuerpo (bloque, rama_sino) con el
    visitor genérico, **sin** revisitar la condición.
- `PLAN_ENTREGA4.md`: esta sección.
- (`tipos.py`, `tabla_simbolos.py`, `errores_semanticos.py`, `arbol.py`,
  `server.py`, los parsers y el frontend quedan **intactos**.)

### Decisiones tomadas sobre la marcha

1. **El error se ancla en el PRIMER terminal de la condición**, no en el
   keyword `si`/`mientras`. Una condición puede extenderse varias líneas;
   apuntar a su inicio comunica mejor "el problema está en la condición
   que empieza acá" y da un lexema concreto para el resaltado del
   frontend. Si ese terminal no tuviera posición (caso raro), se cae al
   nodo de la estructura como fallback.

2. **Helper compartido `_validar_condicion_booleana`** (TAREA 3
   recomendada). `_visit_sent_si` y `_visit_sent_mientras` quedan en tres
   líneas cada uno: localizar la condición, validarla, recorrer el resto.
   Sólo cambian el nombre de la estructura ('si' vs 'mientras'). Facilita
   añadir futuras estructuras con condición.

3. **La condición se recorre una sola vez.** El helper ya llama a
   `_visitar_y_tipar_expresion(nodo_cond)` (que hace la pasada de Regla 2
   + TIPO_OPERADOR), así que al recorrer el resto del cuerpo se salta el
   nodo de la condición (`hijo is nodo_cond`) y los terminales. Sin esto,
   los identificadores de la condición se validarían dos veces.

4. **`booleano y booleano → booleano` ya lo daba el motor de tipos.** El
   ejemplo 14 (`(x > 3) y flag`) no necesitó nada nuevo: `unificar_logico`
   (Etapa 4) ya cubría el caso. La Regla 4 sólo consume el tipo
   sintetizado.

5. **Sin sorpresas con palabras reservadas esta vez.** Recordatorio
   aplicado desde el inicio: en los `.dml` se evitaron `y`, `o`, `no`,
   `este`, `nuevo` como identificadores (se usaron `x`, `s`, `i`,
   `activo`, `flag`).

### Verificación de cierre

1. Tests de Etapas 1, 2, 3, 4 y 5: **verdes** (sin regresión).
2. `test_etapa6_regla_4.py`: **pasa entero** contra ambos parsers.
3. `server.py` arranca y `/parsear` devuelve el mismo JSON que en E3
   (`valido, errores, error, nodos, metodo` [+ `traza` en predictivo]);
   sin claves semánticas. El análisis semántico sigue sin invocarse desde
   el servidor.
4. Smoke tests: condición no booleana (`si x entonces`, `x` entero) → **un
   solo** `TIPO_CONDICION`; condición con variable no declarada (`si
   desconocida entonces`) → **un solo** `USO_NO_DECLARADO` (la cascada
   suprime `TIPO_CONDICION`). Verificado en ambos parsers.

---

## Etapa 7 — Regla 5 (aridad y tipos en llamadas a función)

Implementa la **Regla 5 — la aridad y los tipos de los argumentos de una
llamada deben coincidir con la firma declarada de la función**
(`LLAMADA_ARIDAD`, `LLAMADA_TIPO`, `LLAMADA_NO_FUNCION`). Con esto se
**cierran las cinco reglas semánticas** del alcance de E4. El endpoint
`/parsear` sigue **sin tocarse** (la integración con el servidor es la
Etapa 8); el analizador se ejerce sólo desde los tests.

### Reglas implementadas en esta etapa

La regla 5 se dispara en los dos lugares donde aparece una llamada:

- **Llamada como expresión** — `expr_primaria → IDENTIFICADOR sufijo_id`
  cuando `sufijo_id → ( argumentos )`.
- **Llamada como sentencia** — `sentencia_id → IDENTIFICADOR
  sentencia_id_cola` cuando `sentencia_id_cola → ( argumentos )`.

Ambas delegan en el helper común `_validar_llamada`, que aplica:

- **`LLAMADA_ARIDAD`**: `len(argumentos) != len(parametros)`. Se reporta
  **incluso si algún argumento infiere `ERROR`** (aridad y tipos son
  chequeos independientes), anclado en el IDENTIFICADOR de la función.
- **`LLAMADA_TIPO`**: para cada argumento presente (hasta
  `min(esperada, recibida)`), si `compatible(tipo_param, tipo_arg)` es
  `False`. Promoción `entero→real` permitida (igual que en asignación). El
  error se ancla en el **primer terminal del argumento** (misma heurística
  que la condición de `si`/`mientras` en la Etapa 6), con fallback al
  IDENTIFICADOR.
- **`LLAMADA_NO_FUNCION`**: el símbolo existe pero su `categoria` no es
  `'funcion'` (p.ej. `x(5)` con `x` variable). En ese caso **no** se valida
  aridad ni tipos.
- **NO EXISTE** (símbolo `None`): `USO_NO_DECLARADO` ya lo reportó la
  Etapa 3; la regla 5 no añade nada (cascada).
- **Cascada F.10**: un argumento cuyo tipo inferido sea `ERROR` se **salta**
  en la validación de tipos (no genera `LLAMADA_TIPO`), pero la aridad se
  sigue chequeando.

### Archivos creados

- `ejemplos_semanticos/16_llamada_aridad_mas.dml` — `sumar(1, 2, 3)` sobre
  `sumar(entero, entero)` (1 × `LLAMADA_ARIDAD`, L9:C17, lexema `sumar`,
  espera 2 / recibe 3).
- `ejemplos_semanticos/17_llamada_aridad_menos.dml` — `sumar(1)` (1 ×
  `LLAMADA_ARIDAD`, L9:C17, espera 2 / recibe 1).
- `ejemplos_semanticos/18_llamada_tipo_incompatible.dml` — `saludar(42)`
  sobre `saludar(cadena)` (1 × `LLAMADA_TIPO`, L10:C13, lexema `42`,
  argumento 1 debe ser `cadena`, se recibió `entero`).
- `ejemplos_semanticos/19_llamada_promocion_ok.dml` — `area(5)` sobre
  `area(real)` (0 errores: el `5` entero se promociona a `real`).
- `ejemplos_semanticos/20_llamada_no_funcion.dml` — `x(5)` con `x` variable
  (1 × `LLAMADA_NO_FUNCION`, L7:C17, lexema `x`). Se usó `z` como segunda
  variable porque `y` es palabra reservada.
- `ejemplos_semanticos/21_llamada_cascada.dml` — `sumar(1 + "hola")` (2
  errores: `TIPO_OPERADOR` en el `+` (L11:C25) + `LLAMADA_ARIDAD` (espera 2
  / recibe 1); **sin** `LLAMADA_TIPO` sobre el argumento `ERROR`).
- `ejemplos_semanticos/22_llamada_recursiva_ok.dml` — `factorial(n - 1)`
  recursivo (0 errores: aridad 1 y tipo entero correctos).
- `test_etapa7_regla_5.py` — unit test del helper de argumentos (0/1/2/3 +
  caso anidado), tests por ejemplo (ambos parsers: número exacto de
  errores, regla, fila/columna, lexema, fragmento de mensaje y contexto),
  no-regresión del factorial, test combinado de las **cinco** reglas, y los
  tres smoke tests de cierre.

### Archivos modificados

- `arbol.py` — nuevo helper `extraer_expresiones_de_argumentos(nodo)`:
  devuelve la lista plana de nodos `expresion` que cuelgan de un nodo
  `argumentos`, recorriendo recursivamente `argumentos` / `arg_lista` /
  `arg_lista_prima` (agnóstico al parser vía `etiqueta_normalizada`).
  **No** desciende dentro de una `expresion`, así que una llamada anidada
  `f(g(x), y)` da 2 argumentos de nivel superior, no 3.
- `semantico.py`:
  - Nuevo import de `arbol`: `extraer_expresiones_de_argumentos`.
  - Nuevo helper `_validar_llamada(nombre, sim, nodo_argumentos, nodo_id)`
    con las cuatro sub-validaciones descritas arriba.
  - `_visit_expr_primaria`: en el caso de llamada, ya **no** recorre el
    `sufijo_id` (delega en `_validar_llamada`, que tipa los argumentos);
    sigue reportando `USO_NO_DECLARADO` si el símbolo no existe.
  - `_visit_sentencia_id`: en el caso de llamada como sentencia, localiza
    el `argumentos` dentro de `sentencia_id_cola` y llama a
    `_validar_llamada`. El caso de asignación (Regla 3) queda igual.
- `PLAN_ENTREGA4.md`: esta sección.
- (`tipos.py`, `tabla_simbolos.py`, `errores_semanticos.py`, `server.py`,
  los parsers y el frontend quedan **intactos**.)

### Decisiones tomadas sobre la marcha y sorpresas

1. **`Simbolo.parametros` es `(tipo, nombre)`, no `(nombre, tipo)`.** El
   enunciado de la TAREA 2 asumía `sim.parametros[i] == (nombre, tipo)` y
   por eso indicaba leer el tipo esperado en `sim.parametros[i][1]`. Pero
   `_visit_def_funcion` (Etapa 3) construye la lista como
   `(tipo_param, nombre_param)`. El tipo esperado del parámetro *i* es por
   tanto `sim.parametros[i][0]`. Se respetó la estructura ya existente en
   la tabla en lugar de cambiarla, para no romper Etapas 1–6; queda
   documentado en el docstring de `_validar_llamada`.

2. **Los argumentos se procesan con `_visitar_y_tipar_expresion`, no sólo
   con `tipo_de_expresion_con_reporte`.** Es una desviación deliberada de
   la TAREA 2. Como `_visit_expr_primaria` ya **no** recorre el sufijo de
   una llamada (delega aquí), si sólo se infiriera el tipo sin la pasada de
   `_visitar`, un identificador no declarado usado como argumento (p.ej.
   `sumar(noexiste)`) quedaría sin `USO_NO_DECLARADO`. Las dos pasadas
   reportan reglas disjuntas (Regla 2 vs `TIPO_OPERADOR`), así que no hay
   doble conteo.

3. **El helper de argumentos no desciende en las expresiones.** Recolecta
   sólo los `expresion` hijos directos de `argumentos`/`arg_lista`/
   `arg_lista_prima`. Así los argumentos de una llamada anidada no se
   confunden con los del nivel actual. Verificado con `f(g(x), z)` → 2
   argumentos en ambos parsers.

4. **`escribir(...)` no es una llamada a función.** En el ejemplo 18,
   `saludar` (de retorno `vacio`) usa `escribir(nombre)` en su cuerpo;
   `escribir` es una palabra clave (`sent_escribir`), no un identificador,
   así que **no** dispara `USO_NO_DECLARADO` ni la regla 5. El único error
   del ejemplo es el `LLAMADA_TIPO` esperado.

5. **El ejemplo 22 no define `principal`.** Es sólo un test de recursión;
   el analizador no exige una función de entrada, así que el factorial
   suelto pasa con 0 errores. La recursión resuelve porque la función se
   registra en `global` **antes** de abrir su ámbito (decisión de la
   Etapa 3).

6. **Paridad total entre parsers.** Las siete entradas (16–22), el
   combinado de cinco reglas y los tres smoke tests producen posiciones,
   lexemas y contextos **idénticos** con el parser recursivo y el
   predictivo.

7. **Sin sorpresas con palabras reservadas.** En los `.dml` se evitaron
   `y`, `o`, `no`, `este`, `nuevo` como identificadores (se usaron
   `a`, `b`, `r`, `x`, `z`, `radio`, `nombre`, `n`).

### Cierre de las cinco reglas semánticas

Con la Etapa 7 quedan implementadas y probadas las cinco reglas del
alcance de E4:

| # | Regla                                   | Códigos de error |
|---|-----------------------------------------|------------------|
| 1 | Declaración duplicada en el mismo ámbito | `DECL_DUPLICADA` |
| 2 | Uso de identificador no declarado        | `USO_NO_DECLARADO` |
| 3 | Compatibilidad de tipos en asignación    | `TIPO_ASIGNACION`, `TIPO_VOID_EN_VARIABLE` |
| 4 | Condición de `si`/`mientras` booleana    | `TIPO_CONDICION` |
| 5 | Aridad y tipos en llamadas a función     | `LLAMADA_ARIDAD`, `LLAMADA_TIPO`, `LLAMADA_NO_FUNCION` |

Transversal a todas: `TIPO_OPERADOR` (motor de tipos, Etapa 4) y la
supresión de cascada F.10. El test combinado dispara las cinco reglas en
un solo programa y verifica que las cinco se reportan sin abortar.

### Verificación de cierre

1. Tests de Etapas 1, 2, 3, 4, 5 y 6: **verdes** (sin regresión).
2. `test_etapa7_regla_5.py`: **pasa entero** contra ambos parsers
   (recursivo y predictivo).
3. `server.py` arranca y `/parsear` devuelve el mismo JSON que en E3
   (`valido, errores, error, nodos, metodo` [+ `traza` en predictivo]);
   sin claves semánticas. El análisis semántico sigue sin invocarse desde
   el servidor.
4. Smoke tests: `sumar(1 + "hola")` → `TIPO_OPERADOR` + `LLAMADA_ARIDAD`
   (la cascada suprime `LLAMADA_TIPO`); `sumar(1, 2.5)` con parámetros
   `(entero, entero)` → un solo `LLAMADA_TIPO` en el argumento 2;
   `sumar(1, 2)` con parámetros `(real, real)` → sin errores (doble
   promoción). Verificado en ambos parsers.

---

## Etapa 8 — Integración con /parsear y frontend

Primera etapa que hace **visible** el analizador semántico: lo enchufa al
endpoint `POST /parsear`, extiende el JSON de respuesta con tres claves
nuevas y actualiza el frontend (`diamondlang.html`) para mostrar los
errores semánticos en un panel propio, con la misma UX (numeración,
click → resaltado) que ya tenían los sintácticos en E3. Las cinco reglas
no cambian; esta etapa es **cableado + presentación + sugerencias
locales**.

### Lo que cambió en el contrato de `/parsear`

La respuesta conserva **íntegras** las claves de E3 (`valido`, `errores`,
`error`, `nodos`, `metodo`, y `traza` en predictivo) y añade tres:

- `valido_semantico: bool` — independiente de `valido` (que sigue siendo
  la validez **sintáctica**, decisión E.2/compatibilidad).
- `errores_semanticos: [ErrorSemantico, …]` — mismos campos que ya emite
  el analizador (`indice, fila, columna, lexema, regla, mensaje,
  sugerencia, fuente_sugerencia, contexto`).
- `simbolos: [Simbolo, …]` — la tabla de símbolos snapshoteada.

La fase semántica corre **siempre que haya árbol** (`parser.arbol_raiz`);
si por un caso extremo no hubiera árbol, se devuelven
`errores_semanticos=[]`, `valido_semantico=True`, `simbolos=[]`.

### Archivos creados

- `sugerencias_semanticas.py` — función `sugerir(error) -> str`, análoga a
  `sugerencias.py` de la fase sintáctica. Devuelve un texto humano por
  cada una de las nueve reglas/códigos (`DECL_DUPLICADA`,
  `USO_NO_DECLARADO`, `TIPO_ASIGNACION`, `TIPO_VOID_EN_VARIABLE`,
  `TIPO_OPERADOR`, `TIPO_CONDICION`, `LLAMADA_ARIDAD`, `LLAMADA_TIPO`,
  `LLAMADA_NO_FUNCION`), leyendo `error.contexto` de forma defensiva.
- `test_etapa8_endpoint.py` — tests del endpoint con el **test client de
  Flask** (sin levantar puerto), corriendo cada caso con ambos métodos:
  programa válido; error semántico puro; ambos tipos de error (no
  crashea); shape del JSON (claves E3 + semánticas); campos de cada
  `ErrorSemantico`; presencia de la tabla de símbolos.

### Archivos modificados

- `server.py` — tras `parser.analizar()`, instancia
  `AnalizadorSemantico(parser.arbol_raiz, max_errores=…)`, corre
  `analizar()` y mete `errores_semanticos`, `valido_semantico` y
  `simbolos` en `resultado`. Docstring del endpoint actualizado. El
  enriquecimiento IA (`_enriquecer_con_ia`) sigue aplicando **sólo** a las
  sugerencias sintácticas (el bonus semántico es la Etapa 9).
- `semantico.py` — `_reportar` ahora centraliza la sugerencia local: tras
  construir el `ErrorSemantico`, llama a
  `sugerencias_semanticas.sugerir(error)` y, si devuelve texto, lo asigna
  (si no reconoce la regla, conserva la `sugerencia` que ya traía →
  fallback). Cambio en **un solo punto**; ningún call site se tocó.
- `diamondlang.html` — banner de estado combinado, panel de errores
  semánticos, panel de tabla de símbolos, y las funciones JS
  `renderErroresSemanticos`, `renderSimbolos`, `renderBannerEstado`;
  `parsear()` las invoca y `limpiarSint()` las resetea.
- `PLAN_ENTREGA4.md` — esta sección.

### Cómo se ve la UI completa

Todo vive en la pestaña **② Sintáctico**, dentro del panel del árbol
(orden vertical):

1. **Banner de estado** (arriba del árbol). Cuatro estados con color:
   - verde (teal `--accent3`) → "✓ Análisis sintáctico y semántico válido";
   - ámbar (`--accent4`) → "⬥ Sintaxis OK, pero hay errores semánticos";
   - naranja (`--tok-sym`) → "⚠ Hay errores sintácticos (semántica OK en
     el resto)";
   - rojo (`--tok-err`) → "✗ Errores sintácticos y semánticos detectados".
2. **Árbol** (sin cambios) + los logs `err-sint`/`ok-sint` de E3.
3. **Panel de errores sintácticos** — rojo, como en E3 (intacto).
4. **Panel de errores semánticos** — tema **ámbar** para contrastar con el
   rojo sintáctico. Cada item: `[índice]`, **badge de la regla** (en rosa
   `--accent2`), posición `línea L, columna C`, lexema, mensaje y la
   sugerencia local (con 💡). Click en un item → `resaltarEnEditor(fila,
   columna)` (la misma función de E3). Un error sin posición se muestra
   con clase `nopos` y su click no hace nada.
5. **Panel de tabla de símbolos** — tema **teal**; tabla `Nombre /
   Categoría / Tipo / Ámbito`. Se oculta si no hay símbolos.

Los paneles semántico y de símbolos usan `max-height` + scroll propio para
no pelear con el árbol por el espacio vertical, y se muestran sólo cuando
tienen contenido.

### Decisiones tomadas sobre la marcha y sorpresas

1. **Sugerencias centralizadas en `_reportar` (mínimo invasivo).** En vez
   de tocar cada `self._reportar(...)` para pasar una sugerencia, se
   centralizó en un único punto: `_reportar` llama a `sugerir(error)`
   después de construir el error. `sugerencias_semanticas` queda como
   **fuente de verdad** de las sugerencias por regla; las hand-written que
   había en los call sites quedan como fallback inocuo (la centralizada
   gana). Ningún test de E1–E7 dependía del texto previo, así que no hubo
   regresión.

2. **`TIPO_OPERADOR` también recibe sugerencia.** Aunque lo emite
   `tipos.py` (no `semantico.py`), su reporte pasa por el mismo
   `self._reportar`, así que la centralización lo cubre gratis. `sugerir`
   distingue el caso binario (`tipo_izquierdo`/`tipo_derecho`) del unario
   (`tipo_operando`).

3. **`valido` NO se combinó con `valido_semantico`.** Se mantienen como
   campos independientes (compatibilidad E.2). El frontend los cruza sólo
   para elegir el texto/color del banner.

4. **[SORPRESA / HALLAZGO] La decisión F.11 hoy es "todo o nada", no
   "sub-árboles limpios".** El enunciado de la etapa asumía que el
   analizador ya analiza las zonas sin `es_error`. En la práctica,
   `_visitar` chequea `tiene_error_sintactico(nodo)` **en la raíz**: como
   esa función es recursiva sobre todo el sub-árbol, **un solo** error
   sintáctico en cualquier parte del programa hace que la fase semántica
   salte el árbol **completo** (→ `valido_semantico=True`,
   `errores_semanticos=[]`). Es decir, sólo se analiza semánticamente un
   programa sintácticamente impecable. No se tocó el analizador (está
   fuera del alcance de E8 y las Etapas 2–7 están cerradas/aprobadas; 
   ningún test depende de análisis parcial), pero **queda anotado como
   deuda**: para cumplir F.11 al pie de la letra haría falta mover el
   `skip` a granularidad por-hijo (saltar sólo el sub-árbol roto y seguir
   con los hermanos limpios). El test de "ambos errores" verifica lo que
   el enunciado pide explícitamente —que **no crashee**— sin exigir un
   conteo semántico parcial.

5. **Verificación del frontend sin navegador.** No había `jsdom` ni
   navegador headless disponibles. Se validó: (a) `node --check` sobre el
   JS extraído (sintaxis OK); (b) consistencia de IDs HTML↔JS; (c) un
   harness Node con un DOM mock mínimo que ejerció las tres funciones de
   render y confirmó los cuatro estados del banner, la activación de
   paneles, el badge de regla, la clase `nopos` para errores sin posición,
   y las filas de la tabla de símbolos; (d) arranque del server real y
   `curl` a `/parsear` confirmando las claves nuevas por HTTP.

### Verificación de cierre

1. Tests de Etapas 1–7: **verdes** (sin regresión; la centralización de
   sugerencias en `semantico.py` no rompió ningún assert previo).
2. `test_etapa8_endpoint.py`: **pasa entero** con ambos métodos
   (recursivo y predictivo).
3. `server.py` levanta sin errores y `/parsear` devuelve las claves
   nuevas (`errores_semanticos`, `valido_semantico`, `simbolos`) además de
   las de E3. Verificado con el test client **y** con el server real vía
   `curl`.
4. El frontend muestra los errores semánticos en su panel ámbar propio
   (distinto del rojo sintáctico), con click → resaltado reutilizando
   `resaltarEnEditor`, banner de estado combinado y tabla de símbolos.
   Validado con el harness de DOM mock.

---

## Etapa 8.5 — Análisis semántico parcial (F.11)

Etapa MICRO de corrección de deuda técnica. Salda el hallazgo de la
Etapa 8.

- **Problema (en una frase):** `_visitar` chequeaba
  `tiene_error_sintactico` en la **raíz** y, como ese chequeo es
  recursivo, un único error sintáctico en cualquier parte del programa
  hacía que la fase semántica saltara el árbol **completo**
  (`errores_semanticos=[]`), incumpliendo F.11.
- **Fix (en una frase):** se movió el filtrado a granularidad
  **por-hijo**, centralizado en `_visitar`: se desciende por los nodos
  **contenedores** (los que enrutan sentencias o envuelven un `bloque`)
  aunque tengan errores internos, y se salta sólo la sentencia/hoja
  realmente rota; así las zonas limpias se analizan igual.

### El cambio, en concreto (`semantico.py`)

- Nueva constante module-level `_CONTENEDORES` = `{programa, declaracion,
  def_funcion, bloque, bloque_prima, sentencia, sent_si, rama_sino,
  sent_mientras, sent_para}` — exactamente los no-terminales de
  `tabla_ll.GRAMATICA` que enrutan sentencias o contienen un `bloque`
  (etiquetas ya normalizadas, así sirve para ambos parsers).
- `_visitar` pasó de:
  ```python
  if tiene_error_sintactico(nodo):   # chequeo en la raíz → todo-o-nada
      return
  ```
  a:
  ```python
  if nodo.es_error:                  # marcador ERROR<…> directo
      return
  etiqueta = etiqueta_normalizada(nodo.etiqueta)
  if etiqueta not in _CONTENEDORES and tiene_error_sintactico(nodo):
      return                         # hoja/sentencia sucia → se salta
  ```
  Como `_visitar` es el **único punto** por el que se entra a cualquier
  nodo, el filtro queda centralizado: los contenedores se descienden
  (para alcanzar sus sentencias limpias) y las hojas/sentencias sucias se
  saltan. (No hay regresión de coste: antes se llamaba
  `tiene_error_sintactico` en cada `_visitar`; ahora se evita en los
  contenedores por el corto-circuito del `and`.)
- `_visit_generico` quedó como descenso plano (su docstring lo aclara):
  el filtrado vive en `_visitar`.

### `_visit_*` revisados (TAREA 3) — ninguno necesitó cambios

Todos los descensos pasan por `self._visitar(...)`,
`self._visit_generico(...)` o `self._visitar_y_tipar_expresion(...)`, y
los tres terminan en el choke-point `_visitar`. Por eso el filtro
centralizado los cubre a todos sin tocar ninguno:

| Método | Cómo desciende | Estado |
|--------|----------------|--------|
| `_visit_generico` | `self._visitar(hijo)` ∀ hijo | sin cambios (sólo docstring) |
| `_visitar_y_tipar_expresion` | `self._visitar(expr)` + `tipo_de_expresion_con_reporte` (con guard propio de E4) | sin cambios |
| `_validar_llamada` | `_visitar_y_tipar_expresion` por argumento | sin cambios |
| `_validar_condicion_booleana` | `_visitar_y_tipar_expresion(cond)` | sin cambios |
| `_visit_programa` | `_visit_generico` | sin cambios |
| `_visit_def_funcion` | `_visit_generico` (fallbacks) + `self._visitar(bloque)` | sin cambios; es contenedor → puede invocarse sobre función con cuerpo sucio, pero sus guards de firma (`ident.es_terminal`/`es_error`) ya lo hacían robusto |
| `_visit_decl_variable` | `_visit_generico` (fallback) | sin cambios; es hoja → sólo se invoca sobre nodos limpios |
| `_visit_expr_primaria` | `_visit_generico` | sin cambios; hoja → sólo limpios |
| `_visit_sentencia_id` | `_visit_generico` / `_visitar_y_tipar_expresion` / `self._visitar(cola)` | sin cambios; hoja → sólo limpios |
| `_visit_sent_leer` | no desciende | sin cambios; hoja → sólo limpios |
| `_visit_sent_para` | `_visitar_y_tipar_expresion` / `self._visitar(hijo)` | sin cambios; contenedor robusto (guard de `ident`, exprs con guard) |
| `_visit_sent_si` | `_validar_condicion_booleana` + `self._visitar(hijo)` | sin cambios; contenedor robusto |
| `_visit_sent_mientras` | igual que `sent_si` | sin cambios; contenedor robusto |

### Confirmación de no-regresión

Los **8** tests previos (Etapas 1–8) pasan **sin modificaciones**, salvo
el test 8 que se **reforzó** (TAREA 6): su caso "ambos errores" ahora
exige que `errores_semanticos` traiga el `TIPO_ASIGNACION` de la zona
limpia (antes sólo verificaba "no crashea"). Ningún assert previo dependía
del bug de todo-o-nada.

### Archivos

- **Creado:** `test_etapa8_5_analisis_parcial.py` (casos A–E, ambos
  parsers).
- **Modificados:** `semantico.py` (`_CONTENEDORES` + `_visitar` +
  docstring de `_visit_generico`); `test_etapa8_endpoint.py` (TAREA 6:
  caso "ambos errores" reforzado + NOTA del docstring actualizada);
  `PLAN_ENTREGA4.md` (esta sección).

### Sorpresas / decisiones de diseño

1. **La sugerencia literal del enunciado (filtro en `_visit_generico`) no
   bastaba.** La "suciedad" se propaga hasta la raíz por TODA la cadena de
   contenedores (`programa → declaracion → def_funcion → bloque →
   bloque_prima → …`), así que un `if tiene_error_sintactico(hijo):
   continue` en `_visit_generico` habría saltado la función entera en el
   primer eslabón. Por eso se optó por el filtro **centralizado en
   `_visitar` con la whitelist `_CONTENEDORES`**: descender por
   contenedores, saltar hojas sucias. Es la forma correcta para esta
   gramática y, de paso, soporta análisis parcial **anidado** (un `si`
   con una sentencia rota y otra limpia en el mismo cuerpo).
2. **El análisis parcial puede destapar errores semánticos *reales* en la
   función rota.** En el caso B inicial, `entero a 5` (sintáctico) deja
   `a` sin declarar y un `retornar a` limpio la usa → `USO_NO_DECLARADO`
   legítimo. No es ruido: es la consecuencia semántica correcta del error
   sintáctico. Para que el test B reflejara el enunciado ("sólo el error
   de la 2ª función"), se diseñó la función rota sin referencias colgando
   (`entero b 10`, con `b` sin usar).
3. **Cero cambios en los `_visit_*` específicos.** Al ser `_visitar` el
   único choke-point, el fix quedó en un solo lugar. Los visitors de
   contenedores-statement (`def_funcion`, `sent_si`, `sent_mientras`,
   `sent_para`) ahora **pueden** invocarse sobre nodos sucios (antes
   nunca), pero sus guards preexistentes los hacen robustos (verificado
   con los casos A–C).

---

## Etapa 9 — Bonus IA (Modalidad A)

Bonus opcional: **IA como capa adicional** sobre los errores semánticos
detectados por las reglas clásicas. Cada `ErrorSemantico` se envía a
Claude junto al fragmento de código, y Claude devuelve una sugerencia
enriquecida en lenguaje natural. Es **aditivo**: las reglas deterministas
siguen siendo la única fuente de detección; la IA solo reemplaza el texto
de la sugerencia.

### Por qué Modalidad A

Es la que da **paridad** con `sugerencias_ia.py` (la IA sintáctica de E3):
mismo cliente, mismo modelo, misma política de caché/timeout/fallback.
Reusa toda la infraestructura, no compromete la integridad de las reglas
clásicas (que valen los puntos de la rúbrica base) y no requiere construir
nada nuevo. Las modalidades B (IA como detector primario) y C (chat) se
descartaron por no aportar puntos extra y por desalinearse con la
arquitectura existente.

### Patrón seguido (paralelo a `sugerencias_ia.py`)

`sugerencias_ia_semantica.py` replica la estructura de la versión
sintáctica:

- Carga portable de `.env`, import perezoso de `Anthropic` (None si falta
  la librería).
- `disponible()` / `info()` (este último alimenta `/ping_ia_semantica`).
- `MODELO_IA` = `claude-haiku-4-5` (configurable por env
  `DIAMOND_IA_SEMANTICA_MODELO`), `MAX_TOKENS=250`, `TIMEOUT_SEG=10`.
- `_fragmento_codigo(...)` con marcador `↑` en la columna (duplicado a
  propósito; ver "deuda futura").
- `sugerencia_ia_semantica(error, codigo_fuente, cache=None)`: chequea
  disponibilidad, consulta caché por `(regla, mensaje, lexema)`, arma un
  prompt **instructivo** en español (regla, mensaje, lexema+posición,
  contexto serializado, sugerencia local de partida, y 5 líneas de código
  con `↑`), llama a la API y, ante cualquier fallo/timeout, devuelve
  `None` (fallback a la local).

### Diferencias respecto a la versión sintáctica

- El prompt pide explícitamente **explicar el porqué, proponer una
  corrección concreta y conjeturar el error humano** (orden de
  declaración, tipo equivocado, aridad).
- La clave de caché es `(regla, mensaje, lexema)` (no
  `(no_terminal, esperados, lexema)`).
- La función acepta un **caché externo** opcional; `server.py` le pasa su
  propio dict de módulo (`_CACHE_IA_SEMANTICA`) para mantenerlo **vivo
  entre peticiones**.

### Integración (`server.py`)

- Nuevo flag `usar_ia_semantica` en el body de `/parsear` (default
  `False`, igual que `usar_ia`).
- Tras el análisis semántico, si el flag está activo y la IA disponible,
  `_enriquecer_semantico_con_ia` recorre **en paralelo** `analizador.errores`
  (los objetos `ErrorSemantico`) y `resultado['errores_semanticos']` (los
  dicts), y por cada error reemplaza `sugerencia` y pone
  `fuente_sugerencia='ia'` si Claude respondió (si no, deja la local).
- Endpoint nuevo `GET /ping_ia_semantica` (análogo a `/ping_ia`).
- `'valido'`, `'valido_semantico'` y la detección de errores **no cambian**:
  la IA solo toca el campo `sugerencia`.

### Frontend (`diamondlang.html`)

- Segundo checkbox **"IA semántica"** junto a "IA sintaxis"; al arrancar,
  `pingIASemantica()` consulta `/ping_ia_semantica` y lo deshabilita con
  tooltip si no hay API key.
- `parsear()` envía `usar_ia_semantica` según el checkbox.
- En el panel de errores semánticos, cada sugerencia muestra su **origen**:
  badge gris **"local"** con prefijo 💡, o badge violeta **"✨ IA"** con
  prefijo ✨.

### Ejemplo demo (real, ejecutado en vivo)

Documentado en `ejemplos_semanticos/bonus_ia_demo.md`: `entero resultado <-
area(5)` donde `area` retorna `real`. La sugerencia local solo menciona los
tipos; la de Claude **infiere del código** que `area` retorna `real`,
propone `real resultado <- area(5)` y conjetura el error humano. (Se
documentó también una limitación: la IA propuso `entero(area(5))`, una
conversión inexistente en la gramática — por eso es capa de ayuda, no
autoritativa.)

### Cómo se activa / cómo se prueba sin API key

- **Activación:** `ANTHROPIC_API_KEY` en `.env` (o entorno) +
  `pip install anthropic` + marcar el checkbox "IA semántica". Sin eso,
  todo funciona con sugerencias locales y el checkbox queda deshabilitado.
- **Tests sin red:** `test_etapa9_bonus_ia.py` mockea el cliente
  sustituyendo `sugerencias_ia_semantica.Anthropic` por una clase falsa y
  fijando una key dummy (context manager `ia_mock`). Cubre: IA no
  disponible → `None`; IA disponible → respuesta canned + `fuente='ia'`;
  caché (2 llamadas → 1 sola a la API, vía contador en el mock); y el
  endpoint con `usar_ia_semantica` True/False en ambos parsers.

### Archivos

- **Creados:** `sugerencias_ia_semantica.py`, `test_etapa9_bonus_ia.py`,
  `ejemplos_semanticos/bonus_ia_demo.md`, `README_ENTREGA4.md`.
- **Modificados:** `server.py` (flag `usar_ia_semantica`, enriquecimiento
  semántico, caché de módulo, endpoint `/ping_ia_semantica`, prints de
  arranque); `diamondlang.html` (checkbox + `pingIASemantica` + badge de
  origen en las sugerencias); `PLAN_ENTREGA4.md` (esta sección).

### Decisiones y limitaciones

1. **Duplicación deliberada de `_fragmento_codigo`.** Se duplicó (en vez de
   importar de `sugerencias_ia.py`) para que los dos módulos de IA sean
   independientes. **Deuda futura propuesta:** extraer un `ia_comun.py` con
   el cliente, el builder de fragmento y la política de caché compartidos.
   No se hizo en esta etapa para no tocar la IA sintáctica que ya funciona.
2. **Caché de módulo en `server.py`** (no por-request): dentro de una
   sesión del server, dos análisis con el mismo `(regla, mensaje, lexema)`
   reusan la respuesta de Claude. Se borra al reiniciar el proceso.
3. **La IA puede alucinar sintaxis** que no existe en DiamondLang (visto en
   el demo). Por eso es Modalidad A: la detección y el veredicto son
   siempre de las reglas deterministas; la IA solo mejora el texto de ayuda.
4. **No se tocó `sugerencias_ia.py`** ni se rompió la IA sintáctica.

### Verificación de cierre

1. Tests de Etapas 1–8.5: **verdes** (sin regresión).
2. `test_etapa9_bonus_ia.py`: **pasa entero** con mocks, sin red.
3. `server.py` arranca, expone `/ping_ia_semantica`, y `/parsear` con
   `usar_ia_semantica=True` (API key real disponible en este entorno)
   devuelve la sugerencia enriquecida con `fuente_sugerencia='ia'`;
   con `False`, queda la local. Verificado vía test client.
4. Sin API key, el flujo es idéntico con sugerencias locales y el checkbox
   se deshabilita; nada crashea (cubierto por el caso A del test).
5. `README_ENTREGA4.md` creado: resumen, 5 reglas, arquitectura, ejecución,
   tests, demostración por regla y limitaciones.

---

## Etapa 10 — Ajustes de frontend (marca + selector de ejemplos semánticos)

Etapa puramente cosmética / de usabilidad para la sustentación. **No
toca** el analizador semántico, los parsers, el lexer, `tipos.py`,
`tabla_simbolos.py` ni el JSON de `/parsear`.

### Lo que cambió

1. **Marca actualizada a "Entrega 4" / "v4.0"** en los puntos visibles:
   - `diamondlang.html`: badge del logo (`v3.0` → `v4.0`).
   - `server.py`: docstring del header, `/ping` (`'DiamondLang server
     activo 💎 (Entrega 3)'` → `(Entrega 4)`) y el banner de arranque.
     Las menciones a "Entrega 3" que sobreviven están en comentarios de
     código (CSS/HTML/JS/Python) que describen el historial — esas
     **no** se cambian, conforme a la consigna.

2. **Selector de ejemplos de errores semánticos** en la pestaña
   ② Sintáctico. Es un control independiente del menú "📂 Ejemplos" de
   E3, que sigue con sus cinco entradas sintácticas intactas.

### Endpoint nuevo — `GET /ejemplos_semanticos`

Sirve la lista de `.dml` de `ejemplos_semanticos/` (22 archivos hoy) ya
preparada para el frontend. Cada item del JSON:

```json
{
  "archivo":   "01_decl_duplicada_variable.dml",
  "titulo":    "Declaración duplicada (variable)",
  "regla":     "DECL_DUPLICADA",
  "grupo":     "Regla 1 — Declaración duplicada",
  "contenido": "// Regla 1 — DECL_DUPLICADA ...\nfuncion principal() ..."
}
```

- El nombre, título, regla y grupo de cada archivo viven en un
  diccionario module-level `_MAPEO_EJEMPLOS_SEM` (verdad explícita,
  legible en el código).
- Si la carpeta `ejemplos_semanticos/` no existe, el endpoint devuelve
  `[]` (no crashea); si aparece un `.dml` nuevo no registrado, cae a un
  grupo `"Otros"` con título derivado del nombre — así el menú sigue
  reflejando la realidad de la carpeta.
- La carpeta se resuelve a partir de `Path(__file__).resolve().parent`,
  no del CWD, así el servidor funciona aunque se arranque desde otro
  directorio.

### Agrupación por regla (mapeo final, validado contra la carpeta real)

| Grupo                                | Archivos                                            |
|--------------------------------------|-----------------------------------------------------|
| Regla 1 — Declaración duplicada      | `01`, `02`                                          |
| Regla 2 — Uso no declarado           | `03`, `04`                                          |
| Regla 3 — Tipos en asignación        | `05`, `06`, `07`, `08*`, `09*`, `10`                |
| Regla 4 — Condición booleana         | `11`, `12`, `13*`, `14*`, `15`                      |
| Regla 5 — Llamadas a función         | `16`, `17`, `18`, `19*`, `20`, `21`, `22*`          |

(`*` = caso válido, marcado con "(válido)" en el título visible.)

### Frontend — `diamondlang.html`

- `<select id="ej-sem">` junto al "📂 Ejemplos" de E3, con el mismo
  estilo (`class="btn"`); el placeholder es "⬥ Ejemplos semánticos".
- Al cargar la página se llama una sola vez a
  `cargarMenuEjemplosSemanticos()`, que pega `GET /ejemplos_semanticos`
  y construye un `<optgroup>` por cada valor de `grupo` (orden de
  llegada, que coincide con el orden léxico de los archivos → bien
  numerados → Regla 1, 2, 3, 4, 5).
- Al seleccionar un item, `cargarEjemploSemantico()` vuelca el campo
  `contenido` en el editor `#ed2`, refresca los números de línea y
  dispara `parsear()` automáticamente, para que el panel semántico
  ámbar se llene de una vez. Luego resetea el `<select>` al placeholder
  para permitir elegir otro ejemplo sin tener que reseleccionar.
- Si el endpoint devuelve `[]` o falla la red, se muestra una única
  opción deshabilitada "No hay ejemplos disponibles" (la consigna lo
  pide explícitamente).

### Archivos modificados

- `server.py` — import de `pathlib.Path`, constante
  `_EJEMPLOS_SEM_DIR`, mapeo `_MAPEO_EJEMPLOS_SEM`, ruta
  `/ejemplos_semanticos`, banner/`/ping`/header actualizados a "Entrega 4".
- `diamondlang.html` — badge `v4.0`, nuevo `<select id="ej-sem">`,
  funciones JS `cargarMenuEjemplosSemanticos`/`cargarEjemploSemantico`,
  llamada en el arranque.
- `PLAN_ENTREGA4.md` — esta sección.

### Verificación de cierre

1. Tests de Etapas 1–9: **verdes** (corridos los 10 archivos
   `test_etapa*.py`; sin regresión, ningún assert tocaba la marca ni el
   nuevo endpoint).
2. Arranque del servidor muestra `Entrega 4` en el banner; `GET /ping`
   devuelve `(Entrega 4)`; `GET /ejemplos_semanticos` devuelve 22 items
   bien agrupados.
3. `POST /parsear` con el contenido de `01_decl_duplicada_variable.dml`
   produce `valido_semantico=False` con un `DECL_DUPLICADA` en línea 5
   col 12 (lo esperado); con `13_condicion_si_ok.dml` produce
   `valido_semantico=True` y `errores_semanticos=[]`.
4. `node --check` sobre el JS extraído del HTML: sintaxis OK; el menú
   de ejemplos sintácticos de E3 quedó intacto (mismo `<select id="ej2">`,
   mismas cinco opciones).

### Sorpresas / decisiones sobre la marcha

1. **Tres ejemplos que el enunciado mapeaba a su grupo no por su
   regla puntual sino por su "área temática"**, y los respeté así:
   - `10_cadena_concat_mixto.dml` ilustra `TIPO_OPERADOR` (no
     `TIPO_ASIGNACION`), pero el enunciado lo agrupa con Regla 3
     ("Tipos en asignación") porque conceptualmente cae en la familia
     de tipos. Lo dejé en Regla 3 con `regla: "TIPO_OPERADOR"` — así el
     título "Concatenar cadena con entero" queda en la sección
     correcta para la demo.
   - `15_condicion_cascada.dml` el header de archivo dice
     "USO_NO_DECLARADO en cascada", pero el enunciado lo cuenta como
     Regla 4 (es la *cascada* dentro de la condición). Quedó en Regla
     4 con `regla: "TIPO_CONDICION"`.
   - `21_llamada_cascada.dml` análogo: cascada de tipos dentro de una
     llamada, queda en Regla 5.
2. **Disparo automático de `parsear()` tras cargar el ejemplo.** El
   enunciado lo marca como opcional; lo dejé activado porque para la
   sustentación quita un click y la consigna lo lista como
   "deseable".
3. **No se tocó ningún `.dml`.** Los títulos legibles se construyen en
   `server.py`, no en los archivos.

---

## Estado de cierre del proyecto

| Etapa | Contenido | Estado |
|-------|-----------|--------|
| 0 | Reconocimiento + decisiones aprobadas | completa |
| 1 | Unificar `NodoArbol` + posición línea/columna | completa |
| 2 | Infraestructura (TablaSimbolos, ErrorSemantico, esqueleto) | completa |
| 3 | Reglas 1 y 2 (DECL_DUPLICADA, USO_NO_DECLARADO) | completa |
| 4 | Sistema de tipos (`tipos.py`) | completa |
| 5 | Regla 3 (TIPO_ASIGNACION, TIPO_VOID_EN_VARIABLE) | completa |
| 6 | Regla 4 (TIPO_CONDICION) | completa |
| 7 | Regla 5 (LLAMADA_ARIDAD / _TIPO / _NO_FUNCION) | completa |
| 8 | Integración `/parsear` + frontend + sugerencias locales | completa |
| 8.5 | Análisis semántico parcial (F.11) | completa |
| 9 | Bonus IA semántica (Modalidad A) | completa |
| 10 | Marca Entrega 4 + selector de ejemplos semánticos | completa |

Implementación terminada. Pendiente (fuera de código): documento PDF y
sustentación.
