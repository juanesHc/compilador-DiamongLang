# DiamondLang 💎 — Entrega 3

Recuperación de errores sintácticos en modo pánico, sugerencias contextuales
en español y bonus de IA opcional sobre la API de Claude.

## Cambios respecto a la Entrega 2

| Componente             | Estado en E2                 | Estado en E3                                                  |
|------------------------|------------------------------|---------------------------------------------------------------|
| Reporte de errores     | un único string `error`      | lista `errores: [ErrorSintactico]` con índice, fila, columna, lexema, tipo, esperados, no-terminal y sugerencia |
| Comportamiento         | aborta al primer error       | continúa hasta agotar la entrada o `max_errores` (default 100) |
| Recursivo              | excepción/cortocircuito      | modo pánico con sincronización por no-terminal                 |
| Predictivo             | break en bucle único         | acciones SINCRONIZAR / INSERTAR / DESCARTAR / POP en la traza  |
| Sugerencias            | (ninguna)                    | reglas locales por `(no_terminal, esperado)` + fallback genérico |
| Bonus IA               | —                            | `sugerencias_ia.py` con cliente Claude opcional                |
| API `/parsear`         | `{valido, error, nodos}`     | `{valido, errores, error*, nodos, traza, metodo}` (`error` se mantiene como compatibilidad: primer error formateado) |
| Frontend               | error en banner único        | lista numerada con click → resaltar línea/columna en el editor |

### Archivos nuevos

- `errores.py` — dataclass `ErrorSintactico` y formateador.
- `recuperacion.py` — conjuntos de sincronización y `sincronizar()`.
- `sugerencias.py` — reglas locales y humanización de tokens.
- `sugerencias_ia.py` — cliente opcional de la API de Claude.
- `ejemplos_errores/` — 5 archivos `.dml` con errores documentados.
- `README_ENTREGA3.md` — este archivo.

## Estrategia de recuperación

Modo pánico clásico (Aho/Sethi/Ullman §4.1.4): ante un error en el no-terminal
`A` se descartan tokens hasta encontrar uno en `SIGUIENTE(A)` ∪ delimitadores
fuertes del lenguaje. Eso permite continuar el análisis en una posición
estructuralmente coherente.

### Conjuntos de sincronización

| Constante              | Contenido                                                       |
|------------------------|-----------------------------------------------------------------|
| `SYNC_GLOBAL`          | `fin_funcion, fin_si, fin_mientras, fin_para, fin_clase, sino, $` |
| `INICIOS_SENTENCIA`    | `si, mientras, para, retornar, leer, escribir, funcion, entero, real, cadena, booleano, vacio, IDENTIFICADOR` |
| `SYNC_SENTENCIA`       | `SYNC_GLOBAL ∪ INICIOS_SENTENCIA`                                |
| `SYNC_EXPRESION`       | derivado dinámicamente de `SIGUIENTE(expresion) ∪ SYNC_GLOBAL` (incluye `,`, `)`, `entonces`, `hacer`, `hasta`, `paso` …) |

Cada no-terminal usa `SIGUIENTE(no_terminal) ∪ SYNC_GLOBAL`, con la salvedad
de que los no-terminales del grupo *expresión* añaden `SYNC_EXPRESION`. Ver
`recuperacion.py:GRUPO_EXPRESION` para la lista completa.

### Acciones del parser predictivo

Sobre la pila explícita, los errores se manejan así:

- **`M[A, a]` vacío** (no-terminal en tope): si el lookahead `a` ya está en
  `SIGUIENTE(A) ∪ SYNC_GLOBAL`, se hace **POP** del no-terminal; en caso
  contrario se ejecuta **SINCRONIZAR** (descartar tokens hasta uno del
  conjunto). En ambos casos se registra el error.
- **Tope terminal sin match**: si el terminal pertenece a la lista de
  *cierres fuertes* (`fin_*, entonces, hacer, desde, hasta, ), <-`) se
  hace **INSERTAR** (pop del tope sin avanzar la entrada, asumiendo el
  olvido). En cualquier otro caso, **DESCARTAR** (avanzar el lookahead).
- **Pila vacía con tokens restantes**: error agregado y se descarta el
  resto de la entrada.

Las cuatro acciones nuevas aparecen en la columna *Acción* de la traza
con badges de color distinto (`SINC`, `INSERT`, `DESCARTA`, `POP`).

### Garantías

- **Terminación**: `$` está siempre en cualquier conjunto de sincronización;
  además ambos parsers tienen un detector de iteraciones improductivas
  (200 iteraciones sin avanzar la posición → aborto controlado).
- **Tope de errores**: parámetro `max_errores` (default 100) en el body de
  `/parsear` y en los constructores de los parsers.
- **No se introducen nuevos conflictos LL(1)**: la recuperación solo
  altera el comportamiento ante celdas vacías o desajustes; la tabla LL(1)
  generada por `tabla_ll.py` sigue teniendo 0 conflictos sobre 453 entradas.
- **Compatibilidad**: la respuesta JSON de `/parsear` mantiene el campo
  `error` (string del primer error) para no romper consumidores antiguos.

## Bonus IA — sugerencias enriquecidas con Claude

### Activación

```bash
# 1) Instalar todas las dependencias (incluye anthropic y python-dotenv)
pip install -r requirements.txt

# 2) Copiar la plantilla y pegar la API key real
cp .env.example .env
# editar .env y reemplazar el valor de ANTHROPIC_API_KEY

# 3) Arrancar el server
python server.py
```

Si todo está bien, en el arranque verás:

```
💎 Generando tabla LL(1)...
   Tabla lista: 453 entradas, 44 no-terminales
   Bonus IA: disponible
```

El archivo `.env` se carga con **ruta absoluta** (`Path(__file__).parent /
".env"`), por lo que funciona aunque ejecutes el server desde cualquier
directorio. Está listado en `.gitignore` para que la key no se comitee.
La plantilla `.env.example` SÍ se versiona, sin la key real.

En la interfaz, marcar el checkbox **Usar IA** junto al selector de método.
El frontend consulta `GET /ping_ia` al arrancar y deshabilita el checkbox si
no hay API key o no está la librería instalada.

Por cada error, el server invoca `sugerencias_ia.sugerencia_ia(error,
codigo)` que envía a Claude (modelo configurable, por defecto
`claude-haiku-4-5`) un prompt en español con:

- 5 líneas alrededor del error con un marcador `↑` apuntando a la columna,
- no-terminal en curso, tokens esperados, lexema encontrado,
- la sugerencia local como punto de partida.

Claude responde con un mensaje breve (máx. 2 frases) en lenguaje natural.
Si la API falla por cualquier razón (sin red, timeout de 10 s, error 5xx,
sin API key), `sugerencia_ia` retorna `None` y el sistema cae al texto
local sin romper el análisis. Hay cache en memoria por
`(no_terminal, esperados, lexema)` para no llamar dos veces a la API por
el mismo patrón en el mismo análisis.

## Ejemplos de salida

### `ejemplos_errores/errores_multiples_simples.dml`

```text
Error sintáctico [1] — línea 11, columna 14
  Encontrado : lexema='10' tipo=ENTERO
  Esperado   : <-
  ¿Quiso decir? : ¿Olvidó la asignación '<-' después de declarar la variable? Ejemplo: entero x <- 10

Error sintáctico [2] — línea 12, columna 5
  Encontrado : lexema='si' tipo=KEYWORD
  Esperado   : ENTERO | REAL | CADENA | verdadero | falso | IDENTIFICADOR | (
  ¿Quiso decir? : Se esperaba un valor (número, cadena, verdadero/falso), una variable, o una expresión entre paréntesis.

Error sintáctico [3] — línea 13, columna 9
  Encontrado : lexema='escribir' tipo=KEYWORD
  Esperado   : entonces
  ¿Quiso decir? : Falta la palabra clave 'entonces' después de la condición del 'si'.

Error sintáctico [4] — línea 14, columna 1
  Encontrado : lexema='fin_funcion' tipo=KEYWORD
  Esperado   : fin_si
  ¿Quiso decir? : Falta cerrar el bloque condicional con 'fin_si'.
```

### `ejemplos_errores/errores_en_funcion.dml`

```text
Error sintáctico [1] — línea 12, columna 23
  Encontrado : lexema='0' tipo=ENTERO
  Esperado   : <-
  ¿Quiso decir? : ¿Olvidó la asignación '<-' después de declarar la variable? Ejemplo: entero x <- 10

Error sintáctico [3] — línea 15, columna 9
  Encontrado : lexema='acumulador' tipo=IDENTIFICADOR
  Esperado   : hacer
  ¿Quiso decir? : Falta 'hacer' después de la condición del 'mientras'.

Error sintáctico [4] — línea 18, columna 24
  Encontrado : fin de archivo
  Esperado   : fin_funcion
  ¿Quiso decir? : Falta cerrar la función con 'fin_funcion'.
```

### `ejemplos_errores/bucle_para_incompleto.dml`

```text
Error sintáctico [1] — línea 11, columna 20
  Encontrado : lexema='hacer' tipo=KEYWORD
  Esperado   : hasta
  ¿Quiso decir? : Falta 'hasta' con el valor final del bucle 'para'.
```

(El parser recursivo añade aquí 1–2 errores satélite por la cascada de la
expresión inacabada; el predictivo reporta 2.)

## Cómo probar

```bash
# 1. Instalar dependencias (anthropic es opcional)
pip install -r requirements.txt

# 2. Ejecutar el servidor
python server.py

# 3. Abrir diamondlang.html en el navegador
# 4. Pegar uno de los archivos de ejemplos_errores/ en la pestaña Sintáctico
#    y presionar ▶ Analizar (o Ctrl+Enter)
```

Para probar todos los ejemplos en una sola pasada:

```bash
python -c "
from parser_recursivo import ParserRecursivo
from errores import formatear_lista
import glob
for ruta in sorted(glob.glob('ejemplos_errores/*.dml')):
    with open(ruta) as f: codigo = f.read()
    p = ParserRecursivo(codigo); p.analizar()
    print(f'═══ {ruta} ═══')
    print(formatear_lista(p.errores))
    print()
"
```

## Limitaciones conocidas

1. **Errores satélite**: el parser recursivo, al sincronizar dentro de
   una declaración de variable o expresión, puede emitir un error
   adicional en `expr_primaria` mientras se reposiciona. Es esperable en
   modo pánico; el primer error siempre identifica la causa real.
2. **Posición de EOF**: cuando el error ocurre al final del archivo se
   reporta como "fin de archivo" usando la fila/columna del último token
   más su longitud. No coincide exactamente con la del salto de línea
   final.
3. **Heurística de inserción del predictivo**: la lista
   `TERMINALES_INSERTABLES` está hardcodeada. Si el lenguaje crece, hay
   que actualizarla manualmente (decisión consciente: insertar ε
   demasiado liberal genera falsos positivos).
4. **Cache IA**: vive en memoria del proceso del server. Reiniciar el
   servidor la borra. Para trabajos largos puede convenir persistirla.
5. **Bucle de recuperación**: tras 200 iteraciones sin avance, ambos
   parsers abortan con un error sintético `(bucle de recuperación)`. No
   debería dispararse nunca con código razonable.
