# Bonus IA (Modalidad A) — Demo end-to-end

Demostración del enriquecimiento de un **error semántico** con IA (Claude),
como pide el enunciado del bonus: código fuente, error original, sugerencia
local y sugerencia enriquecida por la IA, con una comparación.

> Generado en vivo con `ANTHROPIC_API_KEY` configurada, modelo
> `claude-haiku-4-5`, vía `sugerencias_ia_semantica.sugerencia_ia_semantica`.
> Si la API no está disponible, el sistema cae a la **sugerencia local** y
> todo sigue funcionando (el bonus es aditivo, no obligatorio).

---

## 1. Código fuente DiamondLang (error semántico intencional)

```
funcion area(real radio) retornar real
hacer
    retornar 3.14 * radio * radio
fin_funcion

funcion principal() retornar entero
hacer
    entero resultado <- area(5)
    retornar resultado
fin_funcion
```

La función `area` retorna `real`, pero en `principal` su resultado se asigna
a una variable declarada `entero`. La promoción válida es `entero → real`,
**no** `real → entero`, así que la asignación es un error de tipos.

## 2. Error original (tal como lo reporta el analizador)

| Campo | Valor |
|-------|-------|
| Regla | `TIPO_ASIGNACION` |
| Mensaje | No se puede asignar un valor de tipo 'real' a una variable de tipo 'entero'. |
| Posición | línea 8, columna 12 |
| Lexema | `resultado` |
| Contexto | `tipo_declarado=entero · tipo_recibido=real · identificador=resultado` |

(0 errores sintácticos; 1 error semántico.)

## 3. Sugerencia local (`sugerencias_semanticas.py`)

> No puedes asignar un valor de tipo 'real' a una variable de tipo 'entero'.
> Considera cambiar el tipo de la variable o convertir el valor.

## 4. Sugerencia enriquecida por Claude (real)

> El problema es que la función `area(5)` devuelve un valor `real`
> (probablemente porque calcula un área con decimales), pero estás
> intentando guardarlo en una variable `entero`. Cambia la declaración a
> `real resultado <- area(5)` o, si necesitas un entero, convierte el
> resultado con algo como `entero resultado <- entero(area(5))`.
> Probablemente declaraste `resultado` como `entero` sin revisar qué tipo
> devuelve la función `area`.

## 5. Comparación: ¿qué valor agrega la IA?

- **Aprovecha el contexto del programa, no solo del error.** La sugerencia
  local solo conoce los tipos (`real` vs `entero`). La IA, al recibir el
  fragmento de código alrededor del error, **infiere la causa raíz**: la
  función `area` retorna `real` y por eso el resultado no cabe en un
  `entero`. La local no puede "ver" la firma de `area`.
- **Propone una corrección concreta y contextual**: `real resultado <-
  area(5)`, usando el nombre real de la variable y la llamada real.
- **Hipotetiza el error humano** ("declaraste `resultado` como `entero`
  sin revisar qué devuelve `area`"), que es justo lo que pedía el enunciado.
- **Limitación observada:** la IA propuso `entero(area(5))` como conversión
  explícita, una construcción que **no existe** en la gramática actual de
  DiamondLang. Es una pequeña alucinación de sintaxis; el consejo central
  (cambiar el tipo de la variable a `real`) sí es correcto y aplicable.
  Por eso la IA es una **capa aditiva** sobre las reglas clásicas, no un
  sustituto: la detección y el veredicto siguen viniendo del analizador
  determinista (Modalidad A).

---

### Cómo reproducirlo

1. `export ANTHROPIC_API_KEY=...` (o ponerla en `.env`) y `pip install anthropic`.
2. `python server.py`
3. Abrir `diamondlang.html`, pestaña **② Sintáctico**.
4. Pegar el código de arriba, marcar el checkbox **"IA semántica"** y
   analizar.
5. El panel ámbar de errores semánticos muestra la sugerencia con un badge
   violeta **✨ IA**. Sin el checkbox (o sin API key), muestra la local con
   badge gris.
