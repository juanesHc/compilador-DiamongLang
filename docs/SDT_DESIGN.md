# SDT_DESIGN.md — Diseño de la Traducción Dirigida por la Sintaxis
## DiamondLang → Julia (Entrega Final, Fase A)

> **Estado:** documento de diseño. **No hay código productivo todavía.**
> Esta especificación es autocontenida: con ella se puede implementar la
> Fase B (`sdt.py`) sin consultar nada más.
>
> **Lenguaje fuente:** DiamondLang (palabras clave en español, tipado estático).
> **Lenguaje destino:** Julia.
> **Entrada de la fase SDT:** el CST (árbol de parseo) de un programa que ya pasó
> las fases léxica, sintáctica **y** semántica **sin errores**.
> **Salida:** una cadena con código fuente Julia.

---

## 0. Fuente de verdad — la gramática y los tipos REALES del proyecto

Todo lo de abajo se verificó contra `gramatica.txt`, `lexer.py`,
`parser_recursivo.py`, `semantico.py`, `tipos.py`, `tabla_simbolos.py`,
`arbol.py` y los 22 ejemplos en `ejemplos_semanticos/`. **No se inventó
ninguna construcción.**

### 0.1 Lo que DiamondLang SÍ tiene (gramática LL(1) completa)

- Un programa es una lista de **declaraciones**; cada declaración es una
  **definición de función** *o* una **sentencia suelta** (`declaracion → def_funcion | sentencia`). → **Sí se permite código fuera de funciones.**
- Funciones con parámetros tipados y tipo de retorno **opcional**
  (`retornar tipo`, o nada).
- Tipos: `entero`, `real`, `cadena`, `booleano`, `vacio`.
- Declaración de variable con inicialización obligatoria: `tipo id <- expr`.
- Asignación: `id <- expr`.
- Llamada a función como sentencia: `id ( args )`.
- Condicional `si … entonces … [sino …] fin_si`.
- Bucle `mientras … hacer … fin_mientras`.
- Bucle `para id desde A hasta B [paso C] hacer … fin_para`.
- `retornar expresion` (**siempre con expresión** — ver §2).
- `escribir ( expresion )` — **un solo argumento** (ver §2).
- `leer ( IDENTIFICADOR )`.
- Expresiones con precedencia: `o` < `y` < relacionales < `+ -` < `* / %` < `**` < unario (`no`, `-`) < primaria.
- Literales: `ENTERO`, `REAL`, `CADENA` (comillas dobles **o** simples), `verdadero`, `falso`.
- Llamada a función como expresión: `id ( args )`.
- Agrupación con `( … )`.

### 0.2 Lo que NO tiene (aunque el lexer reserve las palabras)

- `clase`, `fin_clase`, `nuevo`, `este` son **palabras reservadas en el lexer
  pero NO existen en la gramática** → no se pueden parsear → **el SDT nunca las
  verá**. No se traducen.
- Operadores lexados pero **fuera de la gramática**: `^`, `++`, `--`, `=`
  (asignación es `<-`), y símbolos `{ } [ ] ; : .`. Un programa válido nunca los
  contiene, así que el SDT no los maneja.
- **No hay `retornar` sin expresión** (no existe el retorno vacío explícito).
- **No hay `escribir` multi-argumento** (la producción es `escribir ( expresion )`).

### 0.3 Reglas de tipo relevantes para traducir (de `tipos.py`)

| Operación | Resultado en DiamondLang | Consecuencia para Julia |
|---|---|---|
| `entero ⊕ entero` (`+ - * / %`) | **`entero`** | `/` entre enteros es **división entera** → Julia necesita `div(a,b)`, no `/` |
| `numérico ⊕ numérico` con algún `real` | `real` | Julia `/` está bien (da Float64) |
| `cadena + cadena` | `cadena` (concatenación) | Julia necesita `string(a,b)` / `*`, **no** `+` |
| `**` (potencia) | numérico | Julia usa `^` |
| relacionales | `booleano` | Julia: mismos símbolos |
| `y` / `o` / `no` | `booleano` | Julia: `&&` / `||` / `!` |

> **Hallazgo central (ver §2.A y §2.B):** los operadores `+` y `/` **no se
> pueden traducir solo con el árbol** — dependen del **tipo** de los operandos.
> El SDT **debe** consultar el motor de tipos (`tipos.tipo_de_expresion`).

### 0.4 Forma del CST (de `arbol.py` y los parsers)

- Cada no-terminal es un `NodoArbol(etiqueta, es_terminal=False)` con `hijos`.
- Cada **terminal** es un `NodoArbol(lexema, es_terminal=True)` — **guarda el
  lexema literal** (`"factorial"`, `"<-"`, `'"hola"'` con comillas, `"42"`), no
  el tipo de token.
- Las producciones recursivas auxiliares llevan apóstrofo en el recursivo
  (`bloque'`, `expr_or'`) y `_prima` en el predictivo. **`arbol.etiqueta_normalizada()`** las unifica a `_prima`.
- El parser recursivo envuelve la raíz en un `programa` extra: usar
  **`arbol.raiz_logica()`** para obtener la raíz real.
- Helpers disponibles y reutilizables: `hijo_por_etiqueta`, `hijos_por_etiqueta`,
  `primer_terminal`, `recolectar_terminales`, `etiqueta_normalizada`,
  `raiz_logica`, `extraer_expresiones_de_argumentos`.

---

## 1. Mapeo de construcciones DiamondLang → Julia

Para cada construcción: sintaxis DiamondLang, equivalente Julia, y notas.

### (a) Programa completo (lista de declaraciones)
```
funcion f() hacer … fin_funcion
funcion principal() hacer … fin_funcion
```
```julia
function f()
    …
end

function principal()
    …
end

principal()   # ← solo si existe una función llamada 'principal'
```
**Notas:** las declaraciones se emiten en orden de aparición, separadas por una
línea en blanco. Si existe una función `principal`, se añade al final una
llamada `principal()` para que el programa “corra” (ver §2.10).

### (b) Declaración de función con retorno
```
funcion factorial(entero n) retornar entero hacer … fin_funcion
```
```julia
function factorial(n::Int)::Int
    …
end
```

### (c) Declaración de función sin retorno (vacio / sin `retornar tipo`)
```
funcion saludar(cadena nombre) hacer … fin_funcion      # tipo_retorno_opt → ε
funcion log(cadena m) retornar vacio hacer … fin_funcion
```
```julia
function saludar(nombre::String)
    …
end

function log(m::String)
    …                # 'vacio' → sin anotación de retorno (Julia devuelve nothing)
end
```
**Notas:** `vacio` como tipo de retorno → **se omite** la anotación `::…`
(Julia ya devuelve `nothing`). Una función sin `retornar tipo` tampoco lleva
anotación.

### (d) Parámetros tipados
```
funcion g(entero n, real x, cadena s, booleano b) …
```
```julia
function g(n::Int, x::Float64, s::String, b::Bool)
```
**Notas:** se emiten anotaciones de tipo (decisión §2.2). Lista vacía →
`function g()`.

### (e) Bloque `hacer … fin_funcion`
El cuerpo de la función va entre `hacer` y `fin_funcion`; en Julia es el cuerpo
entre la cabecera y `end`, indentado un nivel (4 espacios).

### (f) Declaración de variable con asignación
```
entero x <- 10
real    y <- 3.14
cadena  s <- "hola"
```
```julia
x::Int = 10        # variante anotada (ver §2.2, opción recomendada)
y::Float64 = 3.14
s::String = "hola"
```
**Notas:** Julia admite `local x::Int = 10` dentro de funciones. La anotación es
opcional; ver §2.2 para la decisión (anotar vs. no anotar). Recomendado: anotar.

### (g) Asignación a variable existente
```
x <- x + 1
```
```julia
x = x + 1
```

### (h) Sentencia `si / sino / fin_si`
```
si cond entonces
    A
sino
    B
fin_si
```
```julia
if cond
    A
else
    B
end
```
Sin `sino`: se omite el bloque `else`. Anidamiento `sino` + `si` se traduce como
`if`/`else`/`if` anidado (Julia tiene `elseif`, pero la gramática produce un
`si` anidado dentro del `sino`, así que se emite `else` + `if` anidado; opcional
optimizar a `elseif`, ver §2 nota).

### (i) Sentencia `mientras`
```
mientras cond hacer
    A
fin_mientras
```
```julia
while cond
    A
end
```

### (j) Sentencia `para`
```
para i desde 1 hasta 10 paso 2 hacer
    A
fin_para
```
```julia
for i in 1:2:10
    A
end
```
**Notas:** Julia usa rangos `inicio:paso:fin`. Sin `paso` →
`for i in inicio:fin` (paso implícito 1). El identificador del bucle no se
declara con tipo (Julia lo infiere del rango). **Caso borde:** si `paso` es
negativo o las expresiones son `real`, `inicio:paso:fin` sigue siendo válido en
Julia. Ningún ejemplo del proyecto usa `para`; se diseñará un caso en
`prueba_valida.dml`.

### (k) Sentencia `retornar`
```
retornar n * 2
```
```julia
return n * 2
```
**Notas:** **siempre** lleva expresión (la gramática no permite `retornar` solo).

### (l) Llamada a función como sentencia
```
imprimir(x)
```
```julia
imprimir(x)
```

### (m) Sentencia `escribir` (UN argumento)
```
escribir(mensaje)
escribir(x + y)
```
```julia
println(mensaje)
println(x + y)
```
**Notas:** `escribir` recibe **exactamente una** expresión → `println(expr)`.
No hay variante multi-argumento (ver §2.5).

### (n) Sentencia `leer`
```
leer(edad)        # 'edad' declarada antes como 'entero'
```
```julia
edad = parse(Int, readline())
```
**Notas:** el `Tipo` de parseo se resuelve por el **tipo declarado** de la
variable (ver §2.5). `cadena` → `edad = readline()` (sin `parse`).

### (o) Expresiones aritméticas: `+ - * / % **`
```
a + b      a - b      a * b      a / b      a % b      a ** b
```
```julia
a + b      a - b      a * b      (depende)   a % b      a ^ b
```
**Notas:**
- `**` → **`^`** (potencia en Julia).
- `/` → `/` si algún operando es `real`; **`div(a, b)`** si ambos son `entero`
  (división entera, ver §2.B).
- `+` → `+` si numérico; **`string(a, b)`** si cadenas (ver §2.A).
- `%` → `%` (resto; semántica equivalente).

### (p) Expresiones lógicas: `y o no`
```
a y b      a o b      no a
```
```julia
a && b     a || b     !a
```
**Notas:** se usan los operadores **de cortocircuito** `&&` / `||` (lógicos),
nunca `&` / `|` (bit a bit). Ver §2.8.

### (q) Comparaciones: `== != < <= > >=`
```
a == b   a != b   a < b   a <= b   a > b   a >= b
```
```julia
a == b   a != b   a < b   a <= b   a > b   a >= b
```
(idénticos en Julia, también sobre cadenas y booleanos).

### (r) Concatenación de cadenas (`+` sobre cadenas)
```
"Hola, " + nombre
```
```julia
string("Hola, ", nombre)
```
**Notas:** ver §2.A. Se elige `string(...)` por robustez (mezclas ilegales ya
las bloqueó la semántica).

### (s) Literales
```
42          3.14         "texto"        'texto'        verdadero   falso
```
```julia
42          3.14         "texto"        "texto"        true        false
```
**Notas:** `verdadero/falso` → `true/false`. Cadenas con **comillas simples** de
DiamondLang → **comillas dobles** en Julia (Julia reserva `'x'` para `Char`).
Hay que **re-encomillar**: quitar las comillas del lexema y volver a emitir con
`"`. Cuidar el escape de comillas dobles internas.

### (t) Variables / identificadores
```
miVariable     contador     área     niño
```
```julia
miVariable     contador     área     niño
```
**Notas:** se emiten **tal cual**, con tildes/ñ. Julia soporta Unicode en
identificadores (ver §2.1).

### (u) Llamada a función como expresión
```
1 + factorial(n - 1)
```
```julia
1 + factorial(n - 1)
```

### (v) Paréntesis de agrupación
```
(a + b) * c
```
```julia
(a + b) * c
```

### (w) Operador unario menos
```
-x        -(a + b)
```
```julia
-x        -(a + b)
```
(`no` unario → `!`, ya cubierto en (p).)

### (x) Comentarios
DiamondLang admite `// línea` y `/* bloque */`, **pero el parser los descarta
antes de construir el árbol** (`tokens = [t for t in tokens_raw if t.tipo !=
'COMENTARIO']`). → **El CST no contiene comentarios** → el SDT **no puede
preservarlos**. El Julia generado no llevará los comentarios del fuente (salvo
el encabezado generado, §2.12). *Se documenta como limitación aceptada.*

---

## 2. Decisiones de diseño no triviales

### 2.A ⚠ Concatenación `+`: requiere el tipo de los operandos  **(decisión clave)**
El árbol solo dice “`+`”. Pero `+` puede ser **suma numérica** o
**concatenación de cadenas** (`tipos.unificar_aritmetico` permite
`cadena + cadena → cadena`). En Julia son operadores distintos (`+` vs `*` /
`string`). Las mezclas ilegales (`cadena + entero`) **ya son error semántico** y
no llegan al SDT, así que un `+` que llega es *o* numérico *o* de cadenas.
**Decisión:** en cada nodo de suma, el SDT consulta
`tipos.tipo_de_expresion(operando, tabla)`; si el tipo es `cadena`, emite
`string(izq, der)`; si es numérico, emite `izq + der`.
**Recomendación de emisión:** `string(a, b)` (más explícito y seguro que `a * b`
para sustentación).

### 2.B ⚠ División `/`: entera vs. real  **(decisión clave)**
DiamondLang tipa `entero / entero → entero` (división **entera**). En Julia
`5 / 2 == 2.5` (Float64) — **semántica distinta**. **Decisión:** si ambos
operandos son `entero`, emitir **`div(a, b)`** (división entera, equivalente a
`a ÷ b`); si alguno es `real`, emitir `a / b`. Requiere consultar el motor de
tipos igual que 2.A.

### 2.1 Identificadores con tildes/ñ
**Decisión:** emitir **tal cual**. Julia soporta identificadores Unicode
(`área`, `niño`, `contador`). No se normaliza a ASCII (perdería legibilidad y no
aporta nada).

### 2.2 Anotaciones de tipo
Julia es dinámico pero acepta `n::Int`. **Decisión: emitir anotaciones
explícitas** en parámetros, declaraciones de variable y retorno de función.
- **Pro:** preserva la información del análisis semántico, hace el Julia más
  legible para la sustentación, y deja en evidencia que el compilador “sabe” los
  tipos.
- **Contra:** más verboso; si la inferencia de DiamondLang y Julia difieren en
  algún borde, una anotación podría provocar un error de Julia que sin anotar no
  ocurriría. Riesgo bajo dado el sistema de tipos simple.
- **Mitigación:** para variables locales reasignadas, anotar **solo en la
  declaración** (`x::Int = 0`), nunca en las reasignaciones (`x = x + 1`).

### 2.3 Promoción `entero → real`
Implícita en DiamondLang y en Julia. **Decisión:** confiar en Julia, **no**
emitir `Float64(x)`. Ejemplo: `real a <- 5` → `a::Float64 = 5` (Julia promueve).
*Excepción a vigilar:* una variable `real` inicializada con literal entero queda
`a::Float64 = 5`; Julia acepta y convierte. OK.

### 2.4 Mapeo de tipos básicos
| DiamondLang | Julia |
|---|---|
| `entero` | `Int` |
| `real` | `Float64` |
| `cadena` | `String` |
| `booleano` | `Bool` |
| `vacio` | (sin anotación de retorno; conceptualmente `Nothing`) |

### 2.5 `escribir` / `leer`
- **`escribir(expr)` → `println(expr)`** (un solo argumento; no hay multi-arg en
  la gramática, así que el problema de espacios/comas no aplica).
- **`leer(var)` → `var = parse(Tipo, readline())`**, con `Tipo` resuelto del
  tipo declarado de `var`:
  `entero→Int`, `real→Float64`, `booleano→Bool`, y `cadena → var = readline()`
  (sin `parse`). Requiere conocer el tipo de `var` (ver §4, entorno de tipos).

### 2.6 Concatenación de cadenas
Ver §2.A. **`string(a, b)`**. Alternativa idiomática `a * b` documentada pero no
elegida (menos clara en defensa).

### 2.7 Operadores lógicos
`y → &&`, `o → ||`, `no → !`.

### 2.8 AND/OR de cortocircuito vs. bit a bit
Se usan **`&&` / `||`** (lógicos de cortocircuito), **nunca** `&` / `|`
(bit a bit). Los operandos de `y`/`o` son siempre `booleano` (lo garantiza la
semántica), así que `&&`/`||` es correcto y idiomático.

### 2.9 Retorno de función
`retornar expr → return expr`. **No existe** la forma sin expresión, así que no
hay que manejar `return` pelado. (En funciones `vacio`, el cuerpo simplemente no
tiene `retornar`, o retorna una expresión cuyo valor se ignora.)

### 2.10 Estructura del programa emitido
`principal` **no** es palabra clave: es una función normal por convención (los
ejemplos la usan como punto de entrada). **Decisión:** tras emitir todas las
funciones, si existe una función llamada `principal` (aridad 0), emitir al final
`principal()` para que el archivo Julia ejecute algo. Si no existe, las
funciones quedan definidas pero no se invocan automáticamente. Las **sentencias
sueltas** de nivel superior (permitidas por la gramática) se emiten en su lugar,
a indentación 0.

### 2.11 Indentación
**4 espacios por nivel**, igual que el fuente. Cada `function`, `if`, `else`,
`while`, `for` incrementa el nivel para su cuerpo y lo decrementa al cerrar con
`end`.

### 2.12 Comentario inicial (header del archivo generado)
```julia
# Código Julia generado por DiamondLang Compiler v4.0
# Programa fuente: <nombre>.dml
# Fecha de generación: <ISO-8601>
```
La fecha se inyecta desde el llamador (el endpoint), no se calcula dentro del
SDT puro (mantiene a `sdt.py` determinista y testeable).

### 2.13 Programas sin funciones
La gramática **permite** sentencias fuera de funciones (`declaracion →
sentencia`). **Decisión:** soportarlo — las sentencias top-level se traducen a
código Julia top-level. (En la práctica los ejemplos siempre envuelven todo en
funciones, pero el SDT no debe romperse si recibe código suelto.)

### 2.14 `si/sino` anidado → ¿`elseif`?
La gramática genera `sino` con un `bloque` que puede contener otro `sent_si`. La
traducción directa produce `else` + `if` anidado (correcto y válido en Julia).
**Decisión:** emitir la forma directa (`else` / `if` anidado). *Optimización
opcional* a `elseif` queda fuera de alcance de Fase B (cosmética).

---

## 3. Tabla de gramática ampliada con acciones SDT

Notación de las acciones:
- `emit "..."` añade texto al buffer de salida.
- `T(X)` = “traducir el sub-árbol X” (llamada recursiva al visitor).
- `indent++ / indent--` ajusta el nivel; `nl` = salto de línea + sangría actual.
- `tipoJulia(t)` = mapeo de §2.4. `tipoExpr(E)` = `tipos.tipo_de_expresion(E, tabla)`.
- `lex(t)` = lexema del terminal `t`.

| # | Producción | Acción SDT | Notas |
|---|---|---|---|
| 1 | `programa → declaracion programa` | `{ T(declaracion); T(programa) }` | lista; ver 1b |
| 1b | `programa → ε` | `{ }` | fin de lista; al cerrar el programa, si existe `principal/0` → `emit "\nprincipal()\n"` |
| 2 | `declaracion → def_funcion` | `{ T(def_funcion) }` | |
| 3 | `declaracion → sentencia` | `{ T(sentencia) }` | sentencia top-level (indent 0) |
| 4 | `def_funcion → funcion ID ( parametros ) tipo_retorno_opt hacer bloque fin_funcion` | `{ emit "function " lex(ID) "("; T(parametros); emit ")"; T(tipo_retorno_opt); emit nl; indent++; T(bloque); indent--; emit "end\n\n" }` | registra nombre/aridad para 1b |
| 5 | `tipo_retorno_opt → retornar tipo` | `{ if tipo≠vacio: emit "::" tipoJulia(tipo) }` | `vacio` → no emite |
| 6 | `tipo_retorno_opt → ε` | `{ }` | sin anotación |
| 7 | `parametros → param_lista` | `{ T(param_lista) }` | |
| 8 | `parametros → ε` | `{ }` | sin parámetros |
| 9 | `param_lista → tipo ID param_lista'` | `{ emit lex(ID) "::" tipoJulia(tipo); T(param_lista') }` | |
| 10 | `param_lista' → , tipo ID param_lista'` | `{ emit ", " lex(ID) "::" tipoJulia(tipo); T(param_lista') }` | separador |
| 11 | `param_lista' → ε` | `{ }` | |
| 12 | `tipo → entero\|real\|cadena\|booleano\|vacio` | `(valor para tipoJulia)` | no emite por sí solo |
| 13 | `bloque → sentencia bloque'` | `{ T(sentencia); T(bloque') }` | cada sentencia en su propia línea (`nl` antes) |
| 14 | `bloque' → sentencia bloque'` | `{ T(sentencia); T(bloque') }` | |
| 15 | `bloque' → ε` | `{ }` | |
| 16 | `sentencia → decl_variable` | `{ emit nl; T(decl_variable) }` | |
| 17 | `sentencia → sentencia_id` | `{ emit nl; T(sentencia_id) }` | asignación o llamada |
| 18 | `sentencia → sent_si \| sent_mientras \| sent_para \| sent_retornar \| sent_escribir \| sent_leer` | `{ emit nl; T(hijo) }` | despacho directo |
| 19 | `decl_variable → tipo ID <- expresion` | `{ emit lex(ID) "::" tipoJulia(tipo) " = "; T(expresion) }` | registra tipo de ID en el entorno (para `leer`) |
| 20 | `sentencia_id → ID sentencia_id_cola` | `{ recordar lex(ID); T(sentencia_id_cola) }` | la cola decide |
| 21 | `sentencia_id_cola → <- expresion` | `{ emit ID " = "; T(expresion) }` | asignación |
| 22 | `sentencia_id_cola → ( argumentos )` | `{ emit ID "("; T(argumentos); emit ")" }` | llamada-sentencia |
| 23 | `sent_si → si expresion entonces bloque rama_sino fin_si` | `{ emit "if "; T(expresion); indent++; T(bloque); indent--; T(rama_sino); emit nl "end" }` | |
| 24 | `rama_sino → sino bloque` | `{ emit nl "else"; indent++; T(bloque); indent-- }` | |
| 25 | `rama_sino → ε` | `{ }` | sin else |
| 26 | `sent_mientras → mientras expresion hacer bloque fin_mientras` | `{ emit "while "; T(expresion); indent++; T(bloque); indent--; emit nl "end" }` | |
| 27 | `sent_para → para ID desde E1 hasta E2 paso_opt hacer bloque fin_para` | `{ emit "for " lex(ID) " in "; T(E1); emit_paso(paso_opt); emit ":"; T(E2); indent++; T(bloque); indent--; emit nl "end" }` | rango `E1[:paso]:E2` (ver nota) |
| 28 | `paso_opt → paso expresion` | `{ emit ":"; T(expresion) }` inserto entre E1 y E2 | rango con paso |
| 29 | `paso_opt → ε` | `{ }` | paso 1 |
| 30 | `sent_retornar → retornar expresion` | `{ emit "return "; T(expresion) }` | |
| 31 | `sent_escribir → escribir ( expresion )` | `{ emit "println("; T(expresion); emit ")" }` | un argumento |
| 32 | `sent_leer → leer ( ID )` | `{ emit lex(ID) " = " parseExpr(tipoDe(ID)) }` | `parse(T, readline())`; cadena → `readline()` |
| 33 | `expresion → expr_or` | `{ T(expr_or) }` | |
| 34 | `expr_or → expr_and expr_or'` | `{ T(expr_and); T(expr_or') }` | |
| 35 | `expr_or' → o expr_and expr_or'` | `{ emit " || "; T(expr_and); T(expr_or') }` | |
| 36 | `expr_or' → ε` | `{ }` | |
| 37 | `expr_and → expr_rel expr_and'` | `{ T(expr_rel); T(expr_and') }` | |
| 38 | `expr_and' → y expr_rel expr_and'` | `{ emit " && "; T(expr_rel); T(expr_and') }` | |
| 39 | `expr_and' → ε` | `{ }` | |
| 40 | `expr_rel → expr_add expr_rel'` | `{ T(expr_add); T(expr_rel') }` | |
| 41 | `expr_rel' → op_rel expr_add` | `{ emit " " lex(op_rel) " "; T(expr_add) }` | `== != < > <= >=` idénticos |
| 42 | `expr_rel' → ε` | `{ }` | |
| 43 | `op_rel → == \| != \| < \| > \| <= \| >=` | `(valor literal)` | sin traducción |
| 44 | `expr_add → expr_mul expr_add'` | `{ T(expr_mul); T(expr_add') }` | |
| 45 | `expr_add' → + expr_mul expr_add'` | **si tipoExpr(contexto)=cadena:** envolver en `string(...)`; **si no:** `{ emit " + "; T(expr_mul); T(expr_add') }` | **ver §2.A** |
| 46 | `expr_add' → - expr_mul expr_add'` | `{ emit " - "; T(expr_mul); T(expr_add') }` | |
| 47 | `expr_add' → ε` | `{ }` | |
| 48 | `expr_mul → expr_pot expr_mul'` | `{ T(expr_pot); T(expr_mul') }` | |
| 49 | `expr_mul' → * expr_pot expr_mul'` | `{ emit " * "; T(expr_pot); T(expr_mul') }` | |
| 50 | `expr_mul' → / expr_pot expr_mul'` | **si ambos entero:** `emit " ÷ "` (o `div(...)`); **si no:** `emit " / "` | **ver §2.B** |
| 51 | `expr_mul' → % expr_pot expr_mul'` | `{ emit " % "; T(expr_pot); T(expr_mul') }` | |
| 52 | `expr_mul' → ε` | `{ }` | |
| 53 | `expr_pot → expr_unaria expr_pot'` | `{ T(expr_unaria); T(expr_pot') }` | |
| 54 | `expr_pot' → ** expr_pot` | `{ emit " ^ "; T(expr_pot) }` | `**` → `^` |
| 55 | `expr_pot' → ε` | `{ }` | |
| 56 | `expr_unaria → no expr_unaria` | `{ emit "!"; T(expr_unaria) }` | |
| 57 | `expr_unaria → - expr_unaria` | `{ emit "-"; T(expr_unaria) }` | unario menos |
| 58 | `expr_unaria → expr_primaria` | `{ T(expr_primaria) }` | |
| 59 | `expr_primaria → ENTERO` | `{ emit lex }` | tal cual |
| 60 | `expr_primaria → REAL` | `{ emit lex }` | tal cual |
| 61 | `expr_primaria → CADENA` | `{ emit reencomillar(lex) }` | `'..'`→`".."`, escapar |
| 62 | `expr_primaria → verdadero` | `{ emit "true" }` | |
| 63 | `expr_primaria → falso` | `{ emit "false" }` | |
| 64 | `expr_primaria → ID sufijo_id` | `{ emit lex(ID); T(sufijo_id) }` | variable o llamada |
| 65 | `expr_primaria → ( expresion )` | `{ emit "("; T(expresion); emit ")" }` | agrupación |
| 66 | `sufijo_id → ( argumentos )` | `{ emit "("; T(argumentos); emit ")" }` | llamada-expresión |
| 67 | `sufijo_id → ε` | `{ }` | era variable simple |
| 68 | `argumentos → arg_lista` | `{ T(arg_lista) }` | |
| 69 | `argumentos → ε` | `{ }` | sin argumentos |
| 70 | `arg_lista → expresion arg_lista'` | `{ T(expresion); T(arg_lista') }` | |
| 71 | `arg_lista' → , expresion arg_lista'` | `{ emit ", "; T(expresion); T(arg_lista') }` | |
| 72 | `arg_lista' → ε` | `{ }` | |

> **Nota de implementación sobre §2.A/§2.B y las producciones recursivas de
> expresión:** como `+` y `/` viven en producciones `_prima` recursivas, lo más
> limpio NO es decidir el operador dentro de `expr_add'`/`expr_mul'`, sino
> **tipar el nodo `expresion`/`expr_add`/`expr_mul` completo** una vez con
> `tipos.tipo_de_expresion` y traducir la sub-expresión con conocimiento de su
> tipo. La tabla de arriba muestra la intención; la implementación real puede
> consolidar la decisión a nivel del nodo de expresión (ver §4).

---

## 4. Estrategia de implementación de `sdt.py`

**Patrón:** *visitor* sobre el CST, idéntico en estructura a `semantico.py`
(despacho por `getattr(self, f"_visit_{etiqueta_normalizada(nodo.etiqueta)}",
self._visit_generico)`).

**Estado interno del traductor:**
- `self._buffer: list[str]` — acumulador de fragmentos; al final
  `"".join(self._buffer)`.
- `self._indent: int` — nivel actual; `nl()` emite `"\n" + "    " * indent`.
- `self._tipos_local: dict[str, str]` — **entorno de tipos en la pasada**: a
  medida que el visitor ve `decl_variable` y parámetros, registra `nombre→tipo`.
  Se usa para `leer` (resolver `parse(Tipo,…)`) y para decidir `+`/`/`.
  Se apila/desapila por función (mini scope stack), reflejando el scoping de dos
  niveles de DiamondLang.
- `self._funciones: dict[str, aridad]` — para decidir si emitir `principal()`.
- `self.tabla` — la `TablaSimbolos`/lista de símbolos del análisis semántico,
  disponible como **fuente secundaria**; la fuente primaria es `_tipos_local`
  (porque tras el análisis los ámbitos de función ya están cerrados; ver §0.4 y
  el hallazgo de §“ambigüedades”).

**Tipado de expresiones:** se reutiliza `tipos.tipo_de_expresion(nodo, tabla)`
para resolver `+` (cadena vs numérico) y `/` (entero vs real). El SDT **no
reimplementa** la inferencia de tipos: la importa de `tipos.py`.

**Función pública:**
```python
def traducir(arbol, tabla_simbolos=None) -> str: ...
```
- **Pre-condición:** el árbol es sintáctica y semánticamente válido (sin
  errores). El SDT **no valida**: asume que las fases previas ya lo hicieron.
  Llamar primero a `raiz_logica(arbol)`.
- El header con fecha (§2.12) lo antepone el **llamador** (endpoint), pasando la
  fecha; `traducir` produce solo el cuerpo del programa (determinista → testeable
  con `assert salida == esperado`).

**Funciones del visitor (una por nodo relevante):**
`_visit_programa`, `_visit_def_funcion`, `_visit_parametros`,
`_visit_decl_variable`, `_visit_sentencia_id`, `_visit_sent_si`,
`_visit_sent_mientras`, `_visit_sent_para`, `_visit_sent_retornar`,
`_visit_sent_escribir`, `_visit_sent_leer`, `_visit_expresion` (y helpers de
expresión), y `_visit_generico` (desciende a los hijos). Los nodos puramente
estructurales (`declaracion`, `bloque`, `sentencia`) pueden caer en el genérico.

**Errores propios:** en teoría no debería haber ninguno (entrada validada). Si
el visitor topa un nodo inesperado (etiqueta sin handler, o `es_error=True`), la
estrategia es: registrar un `assert`/excepción `SDTError` con la etiqueta y la
posición, y abortar la traducción con un mensaje claro (nunca emitir Julia a
medias). Esto solo pasaría por un bug interno, no por entrada del usuario.

**Reutilización:** `arbol.py` (`hijo_por_etiqueta`, `primer_terminal`,
`recolectar_terminales`, `etiqueta_normalizada`, `raiz_logica`,
`extraer_expresiones_de_argumentos`) y `tipos.py` (`tipo_de_expresion`).

---

## 5. Los 3 archivos `.dml` de prueba obligatorios

Carpeta propuesta: `ejemplos_traduccion/`.

### (a) `prueba_valida.dml` — programa COMPLETO sin errores
**Objetivo:** ejercitar funciones + recursión + control de flujo + E/S + todos
los tipos, y producir Julia funcional.

Contenido conceptual:
- `funcion es_par(entero n) retornar booleano` → usa `%`, `==`, `retornar` booleano.
- `funcion factorial(entero n) retornar entero` → **recursión**, `si/sino`, `*`, `-`.
- `funcion suma_rango(entero a, entero b) retornar entero` → bucle **`para`** con
  `desde/hasta/paso`, acumulador, reasignación.
- `funcion saludo(cadena nombre) retornar cadena` → **concatenación** `"Hola, " + nombre`.
- `funcion promedio(real x, real y) retornar real` → `/` con reales (división real).
- `funcion principal()` (vacío de retorno) → declara variables de **cada tipo**
  (`entero`, `real`, `cadena`, `booleano`), llama a las otras funciones,
  `escribir(...)` de resultados, un `mientras` corto. (Opcional: un `leer(...)`
  comentado/aparte, porque `leer` requiere stdin; ver nota.)

**Resultado esperado:** el compilador genera un `.jl` que **corre en Julia** y
produce salida coherente. Ejercita: (b),(c),(d),(f),(g),(h),(i),(j),(k),(m),
operadores `+ - * / % ** == != < y o no`, recursión, todos los tipos, y el
auto-llamado `principal()`.
> **Nota `leer`:** como `leer` exige entrada interactiva, `prueba_valida.dml` lo
> incluirá de forma **demostrable pero no bloqueante** (p.ej. en una función
> aparte no invocada por `principal`, o documentando que esa parte requiere
> stdin), para que la verificación automática no se cuelgue.

### (b) `prueba_semantica.dml` — sintácticamente válido, ≥3 errores semánticos distintos
**Objetivo:** mostrar que la fase semántica detecta varios errores y que **NO se
genera Julia**.

Contenido conceptual (un error de cada tipo, mínimo 3):
1. **Uso de variable no declarada** (`USO_NO_DECLARADO`): usar `total` sin declararla.
2. **Tipo incompatible en asignación** (`TIPO_ASIGNACION`): `entero x <- "hola"`.
3. **Condición no booleana** (`TIPO_CONDICION`): `si x entonces …` con `x` entero.
4. *(extra opcional)* **Aridad de llamada** (`LLAMADA_ARIDAD`): llamar a una
   función de 2 parámetros con 3 argumentos.

**Resultado esperado:** el endpoint `/traducir` (Fase B) responde con la lista de
errores semánticos y `julia = null` / sin salida. El SDT **no se ejecuta**.

### (c) `prueba_sintactica.dml` — uno o más errores sintácticos
**Objetivo:** mostrar recuperación de errores y que **NO se genera Julia**.

Contenido conceptual:
- Falta `entonces` tras la condición de un `si`.
- Paréntesis sin cerrar en una llamada.
- Falta `fin_funcion`.

**Resultado esperado:** el parser reporta los errores (con modo pánico /
recuperación), `valido=false`, y el pipeline **no llega** al SDT. Sin salida Julia.

---

## 6. Plan de implementación (Fases B → E)

| Fase | Contenido | Entregable | Estimación |
|---|---|---|---|
| **B** | `sdt.py` (visitor + tipado), endpoint `POST /traducir`, tests unitarios (incluyendo los 3 `.dml`), validación de que el Julia generado corre. | `sdt.py`, ruta en `server.py`, `ejemplos_traduccion/`, tests. | **1.5–2 días** |
| **C** | Pestaña **Traducción** en el frontend (5ª pestaña): editor → botón Traducir → panel con el Julia generado, resaltado, botón copiar/descargar. Reusa el chrome existente. | cambios en `diamondlang.html`. | **1–1.5 días** |
| **D** | Bonus IA de **validación**: enviar el Julia generado a Claude/Gemini para una revisión de “¿esto es Julia idiomático/correcto?” y mostrar sugerencias (aditivo, opcional, degrada sin API key). | extensión de `sugerencias_ia*` + endpoint. | **0.5–1 día** |
| **E** | Documentación final: PDF de **gramática ampliada** (esta tabla §3), actualizar `README`, ejemplos, capturas, y `SDT_DESIGN.md` → estado “implementado”. | PDF, README, ejemplos. | **1 día** |

**Total objetivo:** **4.5–5.5 días** de trabajo (dentro del rango 5–6 pedido,
con margen).

**Orden recomendado:** B → C → E mínimo viable, y D si queda tiempo (es bonus).
La Fase B es la crítica; C y E dependen de ella; D es independiente y opcional.

---

## Apéndice — Ambigüedades de la gramática y construcciones difíciles

### Ambigüedades / hallazgos resueltos tentativamente
1. **`+` y `/` dependen del tipo** (no del árbol). *Resuelto:* el SDT consulta
   `tipos.tipo_de_expresion`. **Es la dependencia técnica más importante de la Fase B.**
2. **División entera vs. real.** `entero/entero → entero` en DiamondLang ≠ `/` de
   Julia. *Resuelto:* `div(a,b)`/`÷` para enteros, `/` para reales.
3. **`escribir` es de un solo argumento** (el brief asumía multi-arg). *Resuelto:*
   `println(expr)`, sin manejo de comas.
4. **No existe `retornar` vacío.** *Resuelto:* siempre `return expr`.
5. **Comentarios se pierden** antes del parser. *Resuelto:* no se traducen; se
   documenta como limitación.
6. **Cadenas con comillas simples** (`'…'`) son válidas en DiamondLang pero en
   Julia `'x'` es `Char`. *Resuelto:* re-encomillar a `"…"` y escapar comillas.
7. **Símbolo de programa permite código suelto** (`declaracion → sentencia`).
   *Resuelto:* se traduce a top-level Julia; `principal()` se autoinvoca si existe.
8. **Estado de la tabla de símbolos tras el análisis:** los ámbitos de función se
   cierran; la lista `simbolos` queda plana (con `ambito`). *Resuelto:* el SDT
   mantiene su **propio** entorno de tipos durante la pasada (fuente primaria) en
   vez de depender del estado final de la tabla.

### Construcciones que conviene DISCUTIR antes de Fase B
- **`leer` + verificación automática:** `leer` genera `readline()`, que bloquea
  esperando stdin. ¿Cómo lo probamos sin colgar los tests? Propuesta: en
  `prueba_valida.dml` mantener `leer` fuera del flujo que se ejecuta en CI, o
  alimentar stdin en el test. **Decisión pendiente de tu visto bueno.**
- **`÷` vs `div(a,b)`** para división entera: `÷` es más “bonito” (y Unicode, que
  ya usamos), `div(a,b)` es más explícito. Sugiero `div(a, b)` por claridad en
  defensa. **Confirmar preferencia.**
- **`string(a,b)` vs `a * b`** para concatenación: sugiero `string(...)`.
  **Confirmar preferencia.**
- **`si/sino` anidado → `elseif`:** dejarlo como `else`+`if` (simple) vs.
  optimizar a `elseif` (más idiomático). Sugiero dejarlo simple en Fase B.
- **Anotar variables locales reasignadas:** confirmar que anotamos solo en la
  declaración, no en reasignaciones (para no chocar con el tipado de Julia).

*Ninguna de estas bloquea el diseño; son afinaciones de criterio para Fase B.*

---

## Anexo — Notas de implementación (Fase B, `sdt.py`)

Estado: **implementado** en `sdt.py` + endpoint `/traducir` + `test_etapa12_sdt.py`
(42 casos verdes). Decisiones de criterio confirmadas por el usuario:

| Tema | Decisión Fase B implementada |
|---|---|
| Concatenación `+` de cadenas | operador **`*`** de Julia (`"a" * "b"`) |
| División `entero/entero` | operador **`÷`** (Unicode, da `Int`); `/` si hay `real` |
| `leer(var)` | `var = parse(Tipo, readline())`; `cadena` → `var = readline()` |
| `si/sino` con **un** `si` anidado | **se colapsa a `elseif`**; si el `sino` trae algo más, `else` con bloque |

### Desviaciones / hallazgos descubiertos al implementar (≠ diseño)

1. **La variable de un `para` DEBE pre-declararse.** El análisis semántico
   trata `para k …` como un **uso** de `k`, no como una declaración: un `para`
   cuya variable no se declaró antes produce `USO_NO_DECLARADO` y **no llega al
   SDT**. Por tanto, un `para` válido siempre va precedido de `entero k <- …`.
   → El SDT traduce `para` correctamente (`for k in a:paso:b`), pero **un
   `prueba_valida.dml` que use `para` debe declarar la variable antes**.
2. **Mismatch de scope del `for` de Julia (caveat).** En DiamondLang `para k`
   reutiliza la `k` externa (mismo símbolo); en Julia `for k in …` crea una `k`
   **local al bucle**. Si un programa lee `k` *después* del bucle, el valor
   diferiría. No afecta el uso normal (leer `k` dentro del bucle). Documentado
   como limitación.
3. **Palabras reservadas no pueden ser identificadores.** `y`, `o`, `no`, `si`,
   `para`, etc. son keywords; usarlas como nombre de variable es error
   sintáctico. (Relevante al diseñar ejemplos: evitar `y`/`o`/`no` como nombres.)
4. **Header determinista.** `traducir(arbol, tabla, fecha=None, con_header=True)`:
   la fecha la inyecta el endpoint (`/traducir` pasa `datetime.now()`); los tests
   usan `con_header=False` para comparaciones golden estables. (Coincide con la
   recomendación de §2.12.)
5. **Tipado de `+`/`÷` resuelto durante la traducción de la expresión.** Como se
   anticipó en §2.A/§2.B, `_traducir_expresion` devuelve `(codigo, tipo)` y la
   decisión de operador se toma con el tipo acumulado; se reusa
   `tipos.unificar_aritmetico` para no duplicar la inferencia.

Todo lo demás se implementó **según el diseño** (las 24 construcciones, las 72
producciones, el visitor agnóstico al parser vía `etiqueta_normalizada`, el
entorno de tipos propio del SDT, y la detección de `principal`).
