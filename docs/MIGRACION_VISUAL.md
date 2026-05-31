# MIGRACIÓN VISUAL — DiamondLang IDE (Etapa 11, Fase 1)

> **Estado:** análisis previo a la migración. **No se ha tocado código fuente.**
> Esta es la entrada que debes aprobar antes de pasar a la Fase 2.

---

## 0. Resumen ejecutivo

- **Colores hex únicos detectados (paleta consolidada):** **57** tokens nombrados en el `tailwind.config` de Stitch + **10** valores "ide-*"/sintaxis + **3** hex de estado (verde / ámbar / rojo) usados fuera de la paleta nombrada ⇒ **~70 valores distintos**, pero el núcleo operativo se reduce a **≈18 colores** que de verdad usan los componentes.
- **IDs y clases que el JS toca y que NO se pueden renombrar:** **49 IDs** distintos referenciados por `getElementById`/`document.querySelector` + **34 clases** que el JS añade/quita o filtra (`tab`, `active`, `pane`, `errores-panel`, `sem-panel`, `simbolos-panel`, `estado-analisis`, `error-log`, `ok-log`, `token-chip`, `tok-*`, `err-item`, `sem-item`, `badge-*`, `ll-*`, `traza-*`, `set-*`, `simbolos-table`, `s-cat`, `s-tipo`, `s-amb`, `empty`, `ia-toggle`, `disabled`). Lista completa en §3.
- **3 riesgos principales:**
  1. **Resaltado inline de líneas de error en el editor**: el mockup sintáctico lo muestra (línea con fondo ámbar y borde izquierdo). El editor actual es un `<textarea>` puro y *no* se puede resaltar una línea individual sin reemplazarlo (CodeMirror / Monaco / contenteditable con overlay). Riesgo alto.
  2. **Chatbot modal**: el backend tiene `/ping_ia` y `/ping_ia_semantica` *solo de diagnóstico*. **No existe** endpoint de "enviar pregunta libre". El mockup muestra además un selector Claude Haiku / Gemini Flash; **Gemini no está integrado en el backend** (solo `sugerencias_ia.py` con Anthropic). Hay que crear un endpoint nuevo, y posiblemente un adaptador Gemini.
  3. **Conflicto real en la paleta** (ver §2.A): el mockup de Fundación usa `primary = #FFC66D` y `background = #2B2B2B`. Los otros tres usan `primary = #ffe9cc` y `background = #17130d`. Hay que decidir qué interpretación se canoniza antes de tocar nada.
- **Sobre el plan de fases propuesto:** la estructura general (1 análisis → 2 tokens → 3 componentes → 4 LL(1)/sets → 5 chatbot → 6 highlight) **es correcta**, pero la Fase 3 se beneficia de partirse en sub-fases por **familia visual** (chrome global, paneles, listas, tablas), y la Fase 6 debe quedar marcada como **opcional / stretch** porque cambia un `<textarea>` por algo más capaz y arrastra cambios en gutter, autosave de Ln/Col, atajo Ctrl+Enter y JSON enviado al backend. Detalle en §5.

---

## 1. Inventario de mockups (Tarea 1)

Los cuatro mockups "revisados" comparten plantilla: HTML único + Tailwind CDN + `tailwind.config` inline + Google Fonts (Inter / JetBrains Mono / Material Symbols Outlined) + un bloque `<style>` con scrollbars y utilidades de panel.

| # | Carpeta | Pestaña/sección IDE | Líneas | Componentes extra | JS propio |
|---|---|---|---:|---|---|
| 1 | `diamondlang_fundaci_n_y_sistema_de_dise_o_revisado` | **Base / Design system** — header, tabs, banner offline, paneles de diagnóstico (verde/ámbar/rojo), botones, chips, paleta de estado | 345 | "Showcase" de tokens (swatches `#2B2B2B`, `#3C3F41`, `#FFC66D`) + barra lateral derecha de íconos (no aplicable al IDE real). Footer fijo con info Ln/Col/UTF-8. | Sí: `togglePanel()` para colapsar paneles de diagnóstico. |
| 2 | `diamondlang_ide_espacio_de_trabajo_l_xico_revisado` | **Pestaña Léxico** — Editor (TL), Tokens (TR), Tabla de Símbolos (full-width inferior) | 383 | Selector `EJEMPLOS` con dropdown (existe ya en el HTML viejo), header con avatar de usuario (no aplica), leyenda de colores de tokens al pie del panel de tokens, badge "128 TOKENS". | Solo `tailwind.config`. No hay JS de interacción. |
| 3 | `diamondlang_ide_espacio_de_trabajo_sint_ctico_revisado` | **Pestaña Sintáctico** — Editor (izq) con resaltado inline de líneas con error, panel derecho con árbol + banner de estado + errores sintácticos + errores semánticos + tabla de símbolos. Footer "Traza de pila" colapsable. | 412 | Tabs simulados en el editor ("Main.dl", "Lib.dl") — **no aplica** al proyecto. Resaltado inline de líneas 11–12 con fondo ámbar. Toggle "IA sintaxis" / "IA semántica" + badge "CLAUDE". Selector "Método predictivo". Panel inferior colapsable de Traza con tabla `Paso / Pila / Lookahead / Acción / Producción`. Textura `stardust.png` overlay (puramente cosmético, opcional). | Sí: handler que cambia opacidad al click (solo demo). |
| 4 | `diamondlang_ide_asistente_chatbot_revisado` | **Modal de Asistente IA** (encima de cualquier pestaña) | 367 | FAB flotante (botón redondo bottom-right), modal con header + selector de modelo (Claude Haiku / Gemini Flash) + cuerpo de conversación + input + estado vacío con sugerencias rápidas. Tabs de archivo (Main.dl/Lib.dl) — **no aplica**. Workspace de fondo con `grayscale-[0.5] opacity-30` para dim. | Sí: `toggleAssistant()` y listener de ESC para cerrar. |

**Observaciones globales:**
- Las cuatro páginas son auto-contenidas (incluyen su propio `tailwind.config`). No comparten un sistema de tokens externo.
- Ninguna usa frameworks adicionales (React, Vue). El frontend objetivo sigue siendo HTML+JS plano.
- La opsz del icon font varía (`opsz 20` en Fundación, `opsz 24` en los otros tres). Cosmético; resolvemos en Fase 2 fijando `opsz 24`.

---

## 2. Design tokens (Tarea 2)

### A) Paleta de colores

#### A.1 Tokens nombrados (todos los hex que aparecen en `tailwind.config.colors`)

Estos son los **57 colores nombrados** consolidados a través de los cuatro mockups (orden alfabético por slug):

| Token | Hex | Rol funcional (según nombre Stitch) |
|---|---|---|
| `background` | `#17130d` *(L,S,C)* / `#2B2B2B` *(F)* | Fondo global de body. **⚠ Conflicto** (ver §2.A.2). |
| `error` | `#ffb4ab` | Texto/línea de error (rosa-rojo claro sobre oscuro) |
| `error-container` | `#93000a` | Fondo de banner/badge de error |
| `inverse-on-surface` | `#353029` | Texto sobre `inverse-surface` |
| `inverse-primary` | `#805600` | Variante de primary en superficies claras |
| `inverse-surface` | `#ebe1d7` | Superficie clara para modal/overlay (en tema oscuro: poco usada) |
| `on-background` | `#ebe1d7` | Texto sobre `background` |
| `on-error` | `#690005` | Texto sobre `error` |
| `on-error-container` | `#ffdad6` | Texto sobre `error-container` |
| `on-primary` | `#442c00` | Texto sobre `primary` |
| `on-primary-container` | `#785100` | Texto sobre `primary-container` (cuerpo del botón ámbar) |
| `on-primary-fixed` | `#281800` | – |
| `on-primary-fixed-variant` | `#614000` | – |
| `on-secondary` | `#00344e` | Texto sobre `secondary` |
| `on-secondary-container` | `#8fbee3` | Texto sobre `secondary-container` |
| `on-secondary-fixed` | `#001e30` | – |
| `on-secondary-fixed-variant` | `#144b6b` | – |
| `on-surface` | `#ebe1d7` | Texto principal sobre `surface` |
| `on-surface-variant` | `#d3c4b2` | Texto secundario / muted |
| `on-tertiary` | `#003641` | – |
| `on-tertiary-container` | `#006173` | – |
| `on-tertiary-fixed` | `#001f26` | – |
| `on-tertiary-fixed-variant` | `#004e5d` | – |
| `outline` | `#9c8f7e` | Borde tenue |
| `outline-variant` | `#4f4537` | Borde técnico, divisores |
| `primary` | `#ffe9cc` *(L,S,C)* / `#FFC66D` *(F)* | **⚠ Conflicto** (ver §2.A.2). Acento del logo / botones primarios. |
| `primary-container` | `#ffc66d` *(L,S,C)* / `#FFC66D` *(F)* | El amarillo IntelliJ — **acento principal en todos los mockups**, fondo de botones "ANALIZAR" |
| `primary-fixed` | `#ffddaf` | Acento secundario cálido |
| `primary-fixed-dim` | `#f5bd65` | Variante ligeramente más oscura del acento |
| `secondary` | `#9dccf2` | Azul (texto de nodos del árbol, headers de tabla símbolos) |
| `secondary-container` | `#174d6e` | Fondo azul profundo (badge "EXPANDIR") |
| `secondary-fixed` | `#cae6ff` | – |
| `secondary-fixed-dim` | `#9dccf2` | – |
| `surface` | `#17130d` / `#120e08` *(según mockup, ver A.2)* | Superficie de header / top bar |
| `surface-bright` | `#3e3831` | Superficie ligeramente más clara |
| `surface-container` | `#241f19` | Surface "card" |
| `surface-container-high` | `#2e2923` | Surface con un step más |
| `surface-container-highest` | `#39342d` | Surface más alta (hover, thead) |
| `surface-container-low` | `#1f1b15` | Surface baja (panels secundarios) |
| `surface-container-lowest` | `#120e08` | Surface más baja (editor) |
| `surface-dim` | `#17130d` | = body en tema oscuro |
| `surface-tint` | `#FFC66D` *(F)* / `#f5bd65` *(L,S,C)* | Tinte para elevación (ligero conflicto, ver A.2) |
| `surface-variant` | `#39342d` | Surface alternativa (variant) |
| `tertiary` | `#cbf2ff` | Cian / acento terciario |
| `tertiary-container` | `#84dcf5` | Fondo cian profundo |
| `tertiary-fixed` | `#afecff` | – |
| `tertiary-fixed-dim` | `#7bd3ec` | – |

**Tokens extra solo en el mockup Léxico** (sintaxis JetBrains):
| `ide-bg` | `#2B2B2B` | Fondo del canvas del editor |
| `ide-panel` | `#3C3F41` | Surface del panel del editor |
| `ide-border` | `#323232` | Borde técnico del panel |
| `syntax-keyword` | `#CC7832` | Naranja IntelliJ — palabras clave |
| `syntax-number` | `#6897BB` | Azul — números |
| `syntax-id` | `#A9B7C6` | Gris-azulado — identificadores |

**Hex puntuales fuera de paleta nombrada** (`bg-[#...]` o style inline):
- `#4CAF50` — verde de estado "OK" (status dot, banner verde)
- `#FFC66D` — repetido inline como acento "warning ámbar"
- `#FF6B6B` — rojo claro de banner de error (Fundación)
- `#6B46C1` — púrpura del badge "CLAUDE" / "IA"
- `#6A8759` — verde JetBrains para cadenas literales
- `#606366` — gris JetBrains para números de línea del gutter
- `#4E5254` / `#5C5F61` / `#5E6264` — grises de scrollbar custom
- `#323232` — bordes oscuros (mismo `ide-border` repetido)

#### A.2 Conflictos detectados entre mockups

> Reportados explícitamente como pidió el brief.

| Token | Valor en Fundación | Valor en Léxico / Sintáctico / Chatbot | Decisión recomendada |
|---|---|---|---|
| `primary` | `#FFC66D` | `#ffe9cc` | **Usar `#ffe9cc`** (3 de 4 mockups, y los tres son vistas del IDE real). En los mockups L/S/C, el amarillo IntelliJ se obtiene de `primary-container = #ffc66d`. Mantener `#FFC66D` como alias secundario solo si rompe algo. |
| `background` | `#2B2B2B` | `#17130d` | **Usar `#17130d`** para el body global. `#2B2B2B` se reserva como **fondo del editor** (lo que en el mockup Léxico se llama `ide-bg`). Es coherente con cómo IntelliJ separa chrome (más oscuro) y editor (gris medio). |
| `surface` | `#17130d` | `#17130d` / `#120e08` (ambiguo en distintas vistas) | Mantener `#17130d` para superficies generales y `#120e08` para `surface-container-lowest` específicamente. |
| `surface-tint` | `#FFC66D` | `#f5bd65` | Usar `#f5bd65` (consistente con `primary-fixed-dim`). |
| `borderRadius.DEFAULT` | `0.125rem` | `0.125rem` | Sin conflicto (2 px). |
| `borderRadius.full` | `0.75rem` | `0.75rem` | Sin conflicto. Nota: este valor **no es** "completamente redondo"; Stitch lo redefine. Pillado: cualquier uso de `rounded-full` en el mockup no sale circular salvo que se sobreescriba inline. |

#### A.3 Núcleo operativo (la paleta que de verdad usa la UI)

De los 70+ valores, los que aparecen una y otra vez en las clases reales:

```
Chrome / surfaces:  #17130d  #1f1b15  #241f19  #2e2923  #39342d  #3C3F41
Editor:             #2B2B2B  #323232  #606366
Texto:              #ebe1d7  #d3c4b2  #9c8f7e  #4f4537
Acento IntelliJ:    #ffc66d  (primary-container) ← el "amarillo de la marca"
Acento crema:       #ffe9cc  (primary)           ← texto sobre superficies oscuras
Error:              #ffb4ab  (texto)             #93000a (container)  #ffdad6 (texto sobre container)
Sintaxis:           #CC7832  #6897BB  #A9B7C6  #6A8759
Verde estado:       #4CAF50
Cian secundario:    #9dccf2  #cbf2ff  #174d6e  #84dcf5
```

### B) Tipografías

Las cuatro páginas importan exactamente lo mismo (con orden distinto y con/sin pesos extra):

```
Inter            wght 400, 500, 600, 700     — UI text
JetBrains Mono   wght 400, 500                — código + chips/badges monoespaciados
Material Symbols Outlined  FILL 0..1, wght 100..700  — íconos
```

Confirmado: **Inter + JetBrains Mono + Material Symbols Outlined**. El frontend actual usa `Syne` (UI) y `Space Mono` (código). En Fase 2 se reemplazan completos.

Tamaños tipográficos (consistentes entre mockups):

| Token | Tamaño / line-height / peso |
|---|---|
| `headline-lg` | 24 px / 32 px / 600, letter -0.01em |
| `headline-md` | 18 px / 24 px / 600 |
| `body-md` | 13 px / 20 px / 400 |
| `body-sm` | 12 px / 18 px / 400 |
| `code-md` | 13 px / 20 px / 400 (JetBrains Mono) |
| `code-sm` | 12 px / 18 px / 400 (JetBrains Mono) |
| `label-caps` | 11 px / 16 px / 700, letter 0.05em, **uppercase** |

### C) Espaciado, radios, sombras

**Spacing tokens** (consistentes):
```
unit            4 px
margin-sm       8 px
margin-md       16 px
panel-padding   12 px
gutter          1 px
toolbar-height  48 px   (solo Léxico)
container-padding 24 px (solo Léxico)
```

**Border radius:**
```
DEFAULT  0.125rem  (2 px)
lg       0.25rem   (4 px)
xl       0.5rem    (8 px)
full     0.75rem   (12 px)   ⚠ no es circular
```

**Clases Tailwind más repetidas** (catálogo rápido):
- Paddings: `p-2`, `p-4`, `px-panel-padding`, `px-3`, `px-4`, `py-1`, `py-1.5`, `py-2`, `py-0.5`, `p-margin-md` (16 px), `p-margin-sm` (8 px)
- Gaps: `gap-2`, `gap-3`, `gap-4`, `gap-margin-sm` (8), `gap-margin-md` (16), `gap-gutter` (1)
- Rounded: `rounded` (=DEFAULT, 2 px), `rounded-lg` (4 px), `rounded-sm`, `rounded-md`, `rounded-full`, `rounded-2xl`
- Shadows: `shadow-sm`, `shadow-lg`, `shadow-xl`, `shadow-2xl`. Sombras inline puntuales: `shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.1)]` en el footer del Léxico.

**Bordes y separadores:**
- `border border-outline-variant` (#4f4537)
- `border border-ide-border` (#323232)
- `border-b border-outline-variant` para separadores horizontales del header/tabs

### D) Componentes recurrentes — receta Tailwind

**Panel / Card (el contenedor base):**
```html
<section class="bg-ide-panel rounded border border-ide-border flex flex-col overflow-hidden shadow-sm group hover:border-primary/20 transition-colors">
  <!-- header del panel: -->
  <div class="h-10 px-4 bg-[#323232] border-b border-ide-border flex justify-between items-center shrink-0">
    <div class="flex items-center gap-2">
      <span class="material-symbols-outlined ...">code</span>
      <span class="text-body-sm font-semibold tracking-tight uppercase text-on-surface-variant">TÍTULO</span>
    </div>
    <span class="bg-[#2B2B2B] text-[10px] px-2 py-0.5 rounded-full border border-ide-border font-bold text-secondary">CONTADOR</span>
  </div>
  <!-- cuerpo: -->
  <div class="flex-1 overflow-auto custom-scrollbar p-4 bg-[#2B2B2B]"> ... </div>
  <!-- footer del panel (opcional): -->
  <div class="h-9 px-6 border-t border-ide-border flex items-center bg-[#3C3F41] shrink-0"> ... </div>
</section>
```

**Botón primario (el amarillo de "ANALIZAR"):**
```html
<button class="bg-primary-container text-on-primary-container px-4 py-1.5 rounded-sm font-label-caps text-label-caps flex items-center gap-2 hover:brightness-110 transition-all active:scale-[0.98]">
  <svg class="w-4 h-4">...</svg>
  ANALIZAR
</button>
```

**Botón secundario (border, ghost):**
```html
<button class="border border-outline-variant text-on-surface font-label-caps text-label-caps px-4 py-2 rounded hover:bg-surface-variant transition-colors">
  SECUNDARIO
</button>
```

**Botón ghost / texto:**
```html
<button class="p-2 hover:bg-surface-variant rounded transition-all text-on-surface-variant flex items-center gap-2">
  <span class="text-label-caps font-label-caps">Limpiar</span>
  <svg class="w-5 h-5">...</svg>
</button>
```

**Badge / chip de regla (la pieza "DECL_DUPLICATED"):**
```html
<span class="bg-surface-variant text-on-surface font-mono-jetbrains text-code-sm px-2 py-1 rounded-sm border border-outline-variant">
  TYPE_MISMATCH
</span>
```

**Token chip (chip de léxico):**
```html
<span class="font-code-sm px-2 py-0.5 rounded border border-[COLOR]/30 bg-[COLOR]/10 text-[COLOR]">
  funcion
</span>
```
Donde `COLOR` cambia por tipo de token:
- `#CC7832` palabra clave
- `slate-500` identificador
- `amber-500` paréntesis/símbolo
- `#6897BB` número
- `rose-400` operador
- `red-500` error

**Banner de estado (banner ámbar "Sintaxis OK, pero hay errores semánticos"):**
```html
<div class="bg-primary-container/10 border-b border-primary-container/30 px-panel-padding py-2 flex items-center gap-2">
  <svg class="w-4 h-4 text-primary-container">...</svg>
  <span class="text-[11px] font-bold text-primary-container uppercase tracking-wider">Sintaxis OK, pero hay errores semánticos</span>
</div>
```
Para variantes: cambiar `primary-container` por `error` (rojo) o `#4CAF50` (verde).

**Ítem de lista de errores (semánticos):**
```html
<div class="p-panel-padding bg-surface-container-low border-l-4 border-primary-container flex flex-col gap-2">
  <div class="flex items-center justify-between">
    <div class="flex items-center gap-2">
      <span class="w-5 h-5 flex items-center justify-center bg-primary-container text-on-primary-container rounded-full text-[10px] font-bold">1</span>
      <span class="bg-surface-variant border border-outline-variant text-on-surface-variant text-[10px] px-1.5 py-0.5 rounded font-code-sm uppercase">TIPO_ASIGNACIÓN</span>
      <span class="text-on-surface-variant text-[11px]">línea 11, col 12</span>
    </div>
    <div class="flex items-center bg-[#6B46C1] text-white text-[9px] px-1.5 py-0.5 rounded font-bold gap-1">
      <svg>...</svg> IA
    </div>
  </div>
  <div class="flex items-center gap-2 text-on-surface text-[12px]">...</div>
  <div class="bg-surface-container-highest p-2 rounded border border-outline-variant/30 text-[11px] text-on-surface-variant">
    <!-- sugerencia / hint -->
  </div>
</div>
```

**Fila de tabla (Tabla de Símbolos):**
```html
<tr class="border-b border-ide-border/30 hover:bg-[#323232] transition-colors">
  <td class="px-6 py-3 text-[#606366]">001</td>
  <td class="px-6 py-3 font-medium">funcion</td>
  <td class="px-6 py-3"><span class="px-2 py-0.5 rounded border border-[#CC7832]/30 bg-[#CC7832]/10 text-[#CC7832]">PALABRA CLAVE</span></td>
  <td class="px-6 py-3 text-center">1</td>
  <td class="px-6 py-3 text-center">1</td>
</tr>
```

---

## 3. Mapeo HTML viejo ↔ mockups nuevos (Tarea 3)

### 3.A Tabla de correspondencia

| Bloque HTML actual | Mockup que lo reemplaza | Cambio visual |
|---|---|---|
| `<header>` (líneas 275–281) — logo 💎 + status-dot + status-text | Header de Fundación + variante Léxico (con `DiamondLang` en `font-headline-md` + chip "SERVIDOR ACTIVO") | **Medio** |
| `<div class="tabs">` (288–293) — pestañas Léxico/Sintáctico/Tabla LL(1)/PRIMERO–SIGUIENTE | Tab strip de Fundación / nav del Sintáctico (con íconos Material Symbols) | **Medio** |
| `.offline-banner` (283–286) | Banner offline de Fundación con `bg-error-container text-on-error-container` y botón "Reconectar" | **Medio** (mantener flujo de `status-dot` JS) |
| `#pane-lexico` (298–356) — Editor + Tokens + Tabla Símbolos | **Mockup Léxico completo** (3 paneles: editor TL, tokens TR, tabla full-width abajo) | **Alto** (rediseño de chrome de cada panel + leyenda al pie) |
| `#pane-sintactico` (359–453) — Editor + Árbol + paneles de errores + traza | **Mockup Sintáctico** (editor izq, sidebar derecho apilado, traza colapsable abajo) | **Alto** |
| `#pane-tabla` (455–466) — Tabla LL(1) | *No hay mockup* — aplicar lenguaje visual nuevo (panel + thead + cell-filled/empty con tokens nuevos) | **Bajo** (estructura intacta, solo colores y tipografía) |
| `#pane-sets` (470–483) — PRIMERO / SIGUIENTE | *No hay mockup* — aplicar lenguaje visual nuevo (grid 2 columnas, chips de tokens) | **Bajo** |
| *(no existe)* | **Modal del Chatbot** + FAB | **Nuevo completo** (HTML+CSS+JS+backend) |
| `.errores-panel` (rojo) (409–416) — lista de errores sintácticos | Panel "ERRORES SINTÁCTICOS (N)" del mockup Sintáctico con `text-error` y header colapsable | **Alto** (cambia layout interno del ítem) |
| `.sem-panel` (ámbar) (418–425) — lista de errores semánticos | Panel "ERRORES SEMÁNTICOS (N)" del mockup Sintáctico, ítems con `border-l-4 border-primary-container` | **Alto** |
| `.simbolos-panel` (teal) (427–437) — tabla de símbolos semánticos | Panel "TABLA DE SÍMBOLOS" del mockup Sintáctico | **Alto** |
| `.estado-analisis` (402) — banner combinado de estado | Banner ámbar/verde/rojo del Sintáctico (`bg-primary-container/10 border-b border-primary-container/30`) | **Medio** |
| `#traza-panel` (440–449) — traza de pila | Footer colapsable del mockup Sintáctico ("TRAZA DE PILA — Método predictivo (248 pasos)") | **Medio** |
| Controles (309–319, 369–397) — botones, selects, toggles IA | Botones primarios + secundarios + toggles ámbar del mockup Sintáctico | **Alto** |

### 3.B IDs y clases protegidas (NO renombrar)

> El JS los consulta directamente. Cambiarlos rompe el frontend.

**IDs referenciados por `getElementById(...)`** — 49 distintos:

```
status-dot           status-text         offline-banner
pane-lexico          pane-sintactico     pane-tabla        pane-sets
ed1                  ed2                 ln1               ln2
cur1                 cur2
btn-lex              btn-parse           sp1               sp2
ej1                  ej2                 ej-sem            metodo-sel
usar-ia              usar-ia-sem
ia-toggle-label      ia-sem-toggle-label
tokens-display       tok-count           tabla-lex
err-lex              ok-lex              stats-lex
s-total              s-kw                s-id              s-err
arbol-wrap           arbol-metodo        err-sint          ok-sint
errores-panel        errores-list        errores-count
sem-panel            sem-list            sem-count
simbolos-panel       simbolos-body       simbolos-count
estado-analisis
traza-panel          traza-body          traza-count
ll-container
primero-wrap         siguiente-wrap
```

**Clases manipuladas por el JS** (con `classList.add/remove`, asignaciones a `.className`, o reescritura completa del HTML que las contiene) — 34 distintas:

```
tab              active            pane
online           offline
errores-panel    sem-panel         simbolos-panel
error-log        ok-log
estado-analisis  estado-ok         estado-sem        estado-sint     estado-bad   show
empty            empty-icon
token-chip       tok-KEYWORD       tok-TIPO          tok-IDENTIFICADOR
tok-ENTERO       tok-REAL          tok-CADENA        tok-OPERADOR    tok-SIMBOLO
tok-BOOLEANO     tok-ERROR         tok-COMENTARIO
err-item         err-num           err-loc           err-source      local   ia
err-found        err-expected      err-suggestion
sem-item         sem-num           sem-rule          sem-loc         sem-lex
sem-msg          sem-suggestion    sem-source        nopos
ll-table         ll-cell-filled    ll-cell-empty    ll-nt
traza-match      traza-expand      traza-error      traza-accept
traza-sync       traza-insert     traza-discard
badge-match     badge-expand     badge-error      badge-accept
badge-sync      badge-insert     badge-discard    badge-pop
set-row         set-nt           set-vals         set-val         set-val-t       set-val-e
simbolos-table  s-cat            s-tipo           s-amb
ia-toggle       disabled
```

**Atributos `data-*` que el JS lee/escribe:**
- `data-fila`, `data-columna` en `.err-item` y `.sem-item` — usados por `resaltarEnEditor(fila, columna)` para llevar el cursor del textarea al error.
- `data-type` en `.token-chip` — solo cosmético (lo lee el CSS via `::after`), no JS.

**Estrategia segura:** las clases `tok-*`, `traza-*`, `badge-*`, `set-val-*`, `s-*`, `estado-*`, `err-*`, `sem-*` se **conservan** como hooks JS, y se redefinen sus estilos en el `<style>` con los nuevos tokens (o se les añaden clases Tailwind extra al renderizar). Las clases puramente decorativas (`.panel`, `.panel-hdr`, `.pdot`, `.controls`, `.editor-wrap`, `.legend`, `.stats-bar`, etc.) se pueden **complementar** con utilidades Tailwind o reescribir en CSS apuntando a los nuevos tokens.

---

## 4. Riesgos (Tarea 4)

### Riesgo 1 — Resaltado inline de líneas de error en el editor  **[ALTO]**

El mockup Sintáctico muestra las líneas 11 y 12 con fondo ámbar y borde izquierdo de color (`amber-error-bg border-l-4 border-primary-container`). El mockup Chatbot también pinta las líneas 11 y 12 con un borde rojo abajo.

**Problema:** el editor actual es un `<textarea id="ed1">` / `<textarea id="ed2">`. Un `<textarea>` **no permite** resaltar líneas individuales por dentro: es texto plano, sin marcado interno posible.

**Opciones (de menor a mayor cambio):**

- **(A) Fingirlo con un overlay (`<div>` posicionado absoluto detrás del textarea)** — un `<pre>` con el mismo texto y el mismo line-height detrás del textarea, sincronizando scroll. Es la técnica más usada para "monaco-lite". Requiere:
  - Reescribir el HTML del editor envolviendo textarea + overlay en un wrapper relativo.
  - Mantener `ed.scrollTop` ↔ overlay sincronizados (ya hay un `scroll` listener parecido en línea 1181).
  - Reaplicar overlay en cada keystroke del textarea (un setter en `input`).
  - **No rompe** los IDs (`ed1`, `ed2`, `ln1`, `ln2`).
- **(B) Reemplazar el textarea por `<div contenteditable>`** (lo que hace el mockup Léxico). Rompe el JS: `ed.value`, `ed.scrollTop`, `ed.selectionStart`, `keydown` para Ctrl+Enter y tabulación. Habría que reescribir todos los puntos que tocan el editor.
- **(C) Integrar CodeMirror 6 o Monaco** (vía CDN). Sin bundler. Cambio grande pero gana resaltado real de sintaxis + decoración de líneas + atajos. Es lo "correcto" pero rompe varios callbacks.

**Recomendación:** dejarlo para una **fase opcional final**, e implementarlo con la opción **(A) overlay** como primera elección. CodeMirror/Monaco solo si el usuario lo pide explícitamente.

### Riesgo 2 — Chatbot modal  **[ALTO]**

El mockup Chatbot supone:
1. Modal flotante con conversación (varios turnos).
2. Selector de modelo Claude Haiku ↔ Gemini Flash.
3. Botón "Enviar" + cierre con ESC.
4. FAB de invocación.
5. Workspace de fondo con dim.

**Estado del backend:**
- `/ping_ia` (GET) → solo dice si Claude está disponible (lee `info_ia()` de `sugerencias_ia.py`).
- `/ping_ia_semantica` (GET) → diagnóstico equivalente para IA semántica.
- `/analizar` y `/parsear` → aceptan `usar_ia` / `usar_ia_semantica`, pero llaman a Claude internamente como parte del análisis. **No hay endpoint para enviar una pregunta libre.**

**Hace falta:**
- **Endpoint nuevo** `/chat` (POST) que reciba `{ "mensaje": str, "modelo": "claude"|"gemini", "contexto"?: ... }` y devuelva `{ "respuesta": str, "modelo": "..." }`. Probablemente reuse `Anthropic` ya cargado en `sugerencias_ia.py`.
- **Adaptador Gemini** (opcional) si se quiere honrar el selector de modelo del mockup. Si no, la pestaña Gemini se deja deshabilitada con un tooltip "Próximamente".
- **Almacenamiento de historial** en cliente (sessionStorage o estado en memoria) — el backend puede ser stateless.

**Recomendación:** implementarlo como fase aparte (Fase 5 del plan), separando frontend (modal + FAB + JS) de backend (endpoint + posible Gemini). Si Gemini sobra, **dejarlo deshabilitado** y entregar solo Claude.

### Riesgo 3 — Conflictos de paleta entre mockups  **[MEDIO]**

Ver §2.A.2. Sin una decisión canónica, distintos componentes pueden quedar con valores incompatibles. **Decisión propuesta:**
- `primary` = `#ffe9cc` (cream)
- `primary-container` = `#ffc66d` (amarillo IntelliJ — el acento real)
- `background` = `#17130d` (chrome global, oscuro cálido)
- `ide-bg` = `#2B2B2B` (fondo de editor, gris Darcula)
- `ide-panel` = `#3C3F41` (surface del editor)
- `ide-border` = `#323232`

### Riesgo 4 — Tabs simulados en mockup Chatbot ("Main.dl", "Lib.dl")  **[BAJO]**

Los mockups Chatbot y partes del Sintáctico muestran tabs de archivo encima del editor. **El proyecto no es multi-archivo**. Ignorar este componente al migrar.

### Riesgo 5 — `borderRadius.full = 0.75rem` (no circular)  **[BAJO]**

Cualquier uso de `rounded-full` en el HTML migrado producirá radio de 12 px, no un círculo. Si necesitamos un círculo de verdad (avatar, FAB, dot de status), hay que usar inline `style="border-radius:50%"` o una utilidad Tailwind arbitraria `rounded-[9999px]`.

### Riesgo 6 — Textura `stardust.png` overlay (Sintáctico)  **[BAJO]**

El mockup Sintáctico añade un `<div>` con textura de ruido (`opacity 0.03 mix-blend-overlay`). Es cosmético. **No incluir** en la migración: añade un request externo y no aporta a la funcionalidad.

### Riesgo 7 — `tailwind.config` via CDN no compila `@apply`  **[BAJO]**

Tailwind por CDN soporta el bloque `tailwind.config = { ... }` para extender tokens, pero las utilidades se generan **just-in-time** observando el HTML. Si una clase se genera **dinámicamente** en JS (p.ej. `className="tok-" + tipo`), Tailwind por CDN puede no detectarla. Solución: dejar las clases sintaxis-aware (`tok-KEYWORD`, `tok-TIPO`, etc.) definidas en un bloque `<style>` propio con los hex finales, sin pedirle a Tailwind que las genere. Las clases de "chrome" sí se generan con CDN sin problema.

### Riesgo 8 — Fuentes vs FOUT  **[BAJO]**

Cambiar de Syne/Space Mono a Inter/JetBrains Mono puede causar un parpadeo (FOUT). Mitigable con `&display=swap` que ya está en el link de fuentes de los mockups.

---

## 5. Plan de fases definitivo (Tarea 5)

> Crítica primero, plan después.

### Crítica del plan propuesto inicialmente

La propuesta original (Fase 1 análisis → 2 base → 3 componentes → 4 LL(1) y sets → 5 chatbot → 6 highlight) **está bien estructurada**. Observaciones:

- **Fase 3 está muy ancha.** "Refactor componente por componente" abarca: chrome (header/tabs/banner), 4 paneles distintos, 3 tipos de listas (errores sint, errores sem, símbolos), 2 tablas (símbolos, traza), 1 panel de árbol, todos los botones y toggles. Hacerlo en una sola fase implica un commit gigante en el que es fácil romper algo silenciosamente. **Propuesta:** partir en 3a (chrome global), 3b (pestaña Léxico), 3c (pestaña Sintáctico) — cada uno con su commit y su verificación funcional.
- **Fase 5 debería partirse** entre frontend (modal + FAB + JS, golpeando solo `/ping_ia`) y backend (endpoint `/chat`). Si Gemini queda fuera, declararlo explícito.
- **Fase 6 debe quedar marcada como OPCIONAL / STRETCH** y, si se hace, con la opción A (overlay), no con CodeMirror, salvo solicitud expresa.
- **No hay fase de cierre.** Conviene añadir una fase final ligera para: borrar variables `--accent`, `--accent2`, etc. obsoletas; quitar Space Mono / Syne del `<link>`; comprobar que ningún CSS dead-code quedó suelto.

### Plan de fases definitivo

#### **Fase 1 — Análisis y reporte**  *(esta fase, en curso)*

- **Cambia:** nada de código.
- **Preserva:** todo intacto.
- **Verificar:** el documento `MIGRACION_VISUAL.md` cubre tokens, mapeo, riesgos y plan.
- **Commit:** `docs: migracion visual — analisis fase 1`

#### **Fase 2 — Importar Tailwind + fuentes + tokens base**

- **Cambia:**
  - Añadir en `<head>`: `<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries">`.
  - Añadir `<link>` a Google Fonts (Inter, JetBrains Mono, Material Symbols Outlined).
  - Añadir `<script id="tailwind-config">` con la paleta consolidada (decisión §2.A.2), spacing, borderRadius, fontFamily, fontSize.
  - Sustituir las variables `:root` por las nuevas (mantener nombres `--accent`, etc. mapeados a los hex nuevos para minimizar cambios en CSS existente):
    ```
    --bg → #17130d
    --surface → #1f1b15
    --surface2 → #241f19
    --border → #4f4537
    --accent → #ffc66d         (era #7c6af7)
    --accent2 → #ffb4ab        (rojo claro, era rosa)
    --accent3 → #4CAF50        (verde, era teal)
    --accent4 → #f5bd65        (amarillo, era amarillo distinto)
    --text → #ebe1d7
    --muted → #d3c4b2
    --tok-kw → #CC7832         (paleta sintaxis JetBrains)
    --tok-type → #6897BB
    --tok-id → #A9B7C6
    --tok-num → #6897BB
    --tok-str → #6A8759
    --tok-op → #CC7832
    --tok-err → #ffb4ab
    --tok-cmt → #808080
    ```
  - Cambiar `font-family: 'Syne'` → `'Inter'`, y `'Space Mono'` → `'JetBrains Mono'` en el CSS.
- **Preserva:** estructura DOM completa, IDs, clases, JS, lógica.
- **Verificar:**
  - La página carga sin errores 404 en network.
  - Las pestañas siguen cambiando (`switchTab`).
  - `/ping` sigue marcando online/offline.
  - Análisis léxico y sintáctico funcionan con un ejemplo.
  - El look ya es "cálido marrón con acentos amarillos" en vez de "morado/rosa", aunque desordenado.
- **Commit:** `style: importar tailwind cdn + paleta intellij + fuentes inter/jetbrains`

#### **Fase 3a — Chrome global (header, tabs, banner offline, footer)**

- **Cambia:**
  - `<header>`: reescribir interior con logo SVG diamante + título `Diamond` + `Lang` (acento) + badge `v4.0` + status-dot (mantener `id="status-dot"`, `id="status-text"`). Aplicar clases Tailwind.
  - `<div class="tabs">`: añadir íconos Material Symbols a cada tab (`code`, `account_tree`, `grid_on`, `list`). Conservar `class="tab"` y `onclick`.
  - `.offline-banner`: convertir a banner ámbar/rojo con ícono `cloud_off` y botón "Reconectar" (que llama al chequeo existente).
  - (Opcional) añadir footer fijo con `Línea X, Columna Y` (los mockups lo muestran, el proyecto ya calcula el `cur1`/`cur2`).
- **Preserva:** IDs, clases JS, lógica de tabs (`switchTab`).
- **Verificar:** las 4 pestañas siguen alternándose y el indicador de servidor sigue parpadeando online/offline.
- **Commit:** `style: chrome global (header, tabs, banner) con tokens nuevos`

#### **Fase 3b — Pestaña Léxico**

- **Cambia:** rediseño visual de `#pane-lexico`:
  - Panel del Editor con cabecera, botón primario "ANALIZAR LÉXICO", botón "EJEMPLOS" con dropdown, botón ghost de limpiar.
  - Panel de Tokens con badge contador y leyenda al pie (la leyenda ya existe; restilizarla).
  - Panel inferior de Tabla de Símbolos full-width con thead estilizado y filas con hover.
  - Stats bar al pie.
- **Preserva:** IDs (`ed1`, `ln1`, `tokens-display`, `tabla-lex`, `s-total`, `s-kw`, `s-id`, `s-err`, `btn-lex`, `tok-count`, `err-lex`, `ok-lex`, `stats-lex`, `ej1`). Clases hook (`token-chip`, `tok-*`, `empty`).
- **Verificar:** analizar un ejemplo → tokens aparecen, leyenda visible, tabla se llena, stats se actualizan. Verificar también clear/limpiar.
- **Commit:** `style: pestana lexico — editor, tokens, tabla simbolos`

#### **Fase 3c — Pestaña Sintáctico (incluye paneles de errores, traza, banner de estado)**

- **Cambia:** rediseño visual completo de `#pane-sintactico`:
  - Editor con toolbar (botón "ANALIZAR", selector método, toggles IA con badge "CLAUDE", botón ghost EJEMPLOS y LIMPIAR).
  - Panel derecho con árbol (mantener `arbol-wrap` para SVG Graphviz).
  - Banner de estado (`estado-analisis`) → fondo ámbar con `border-l-4` y texto en mayúsculas.
  - Panel "ERRORES SINTÁCTICOS (N)" colapsable.
  - Panel "ERRORES SEMÁNTICOS (N)" colapsable con ítems en formato del mockup (chip de regla + badge IA/local + sugerencia con borde).
  - Panel "TABLA DE SÍMBOLOS" con thead estilizado.
  - Footer "TRAZA DE PILA — Método predictivo (N pasos)" colapsable.
- **Preserva:** todos los IDs (`ed2`, `ln2`, `arbol-wrap`, `errores-panel`, `sem-panel`, `simbolos-panel`, `traza-body`, `estado-analisis`, etc.). **Importante:** los items de error son construidos por JS con `innerHTML` (ver líneas 693–741); hay que ajustar el template literal del JS para que emita las clases nuevas. Esto sí es un cambio mínimo de JS pero **NO** cambia los IDs ni el contrato con el backend.
- **Verificar:** analizar un ejemplo con error sintáctico, con error semántico, y uno limpio. Confirmar que el banner cambia y los paneles se muestran correctamente. Click en un error sigue moviendo el cursor.
- **Commit:** `style: pestana sintactico — arbol, errores, semantica, traza`

#### **Fase 4 — Pestañas Tabla LL(1) y PRIMERO/SIGUIENTE**

- **Cambia:** aplicar el lenguaje visual nuevo a `#pane-tabla` (tabla LL(1)) y `#pane-sets` (conjuntos). Sin mockup de referencia: mismo header/panel que las otras pestañas, tabla con thead estilo IntelliJ, chips de terminales/no-terminales con colores `secondary` y `primary-container`.
- **Preserva:** `ll-container`, `primero-wrap`, `siguiente-wrap`. Todas las clases `ll-*`, `set-*`.
- **Verificar:** ambas pestañas siguen cargando datos del endpoint `/tabla_ll`.
- **Commit:** `style: pestanas tabla ll(1) y primero/siguiente`

#### **Fase 5a — Chatbot frontend (modal + FAB)**

- **Cambia:**
  - HTML nuevo: FAB `<button id="chatbot-fab">` posicionado bottom-right (no en la raíz del proyecto, **en `diamondlang.html`**).
  - Modal `<div id="chatbot-modal">` con header, selector Claude/Gemini (Gemini deshabilitado por ahora), área de mensajes, textarea, botón Enviar.
  - JS nuevo para `toggleChatbot()`, ESC para cerrar, envío de mensaje (por ahora hace un `fetch('/chat', ...)`; si el endpoint no existe todavía, muestra "Próximamente").
- **Preserva:** todo lo demás.
- **Verificar:** se abre/cierra el modal, ESC funciona, el textarea acepta input. Sin backend aún, el botón Enviar muestra un mensaje de "Chat en construcción".
- **Commit:** `feat: chatbot modal y fab (sin backend aun)`

#### **Fase 5b — Chatbot backend (endpoint `/chat`)**

- **Cambia:** en `server.py` añadir `@app.route('/chat', methods=['POST'])`. Recibe `{ "mensaje": str, "modelo": "claude" }`. Llama a Anthropic con un prompt de sistema "Eres un asistente de DiamondLang...". Devuelve `{ "respuesta": str, "modelo": "claude-haiku" }`.
- **Preserva:** endpoints existentes.
- **Verificar:** abrir chatbot, enviar pregunta, recibir respuesta de Claude.
- **Commit:** `feat: endpoint /chat para asistente diamondlang`

#### **Fase 6 — [OPCIONAL] Resaltado inline de líneas de error**

- **Cambia:** implementar la **opción A (overlay)**: un `<pre id="ed2-overlay">` posicionado absoluto detrás del textarea, sincronizado en scroll, con líneas que coincidan con `data-fila` de los errores actualmente listados. Cuando hay error en la fila N, esa línea del overlay tiene `bg-primary-container/10 border-l-4 border-primary-container`.
- **Preserva:** textarea, IDs, JS principal.
- **Verificar:** introducir un error en línea 12, ver línea 12 resaltada. Scrollear el editor: el overlay scrollea sincronizado.
- **Commit:** `feat: overlay de resaltado inline de errores en editor sintactico`

#### **Fase 7 — Limpieza final**

- **Cambia:** borrar variables CSS `--accent2`, `--accent3`, `--accent4`, `--glow`, `--tok-bool`, `--tok-sym`, `--tok-cmt` si quedaron huérfanas. Quitar links de Space Mono / Syne. Borrar reglas CSS de selectores no usados. Reorganizar el bloque `<style>` por secciones.
- **Preserva:** funcionalidad.
- **Verificar:** repaso completo de las 4 pestañas + chatbot, ningún warning en consola.
- **Commit:** `chore: limpieza de css y fuentes obsoletas`

---

## Apéndice — Endpoints actuales del backend

| Ruta | Método | Propósito |
|---|---|---|
| `/ping` | GET | Diagnóstico, devuelve string "DiamondLang server activo" |
| `/ping_ia` | GET | Diagnóstico bonus IA sintáctica (Claude) |
| `/ping_ia_semantica` | GET | Diagnóstico bonus IA semántica (Claude) |
| `/analizar` | POST | Análisis léxico — `{ codigo }` → `{ tokens, errores, estadisticas }` |
| `/parsear` | POST | Análisis sintáctico + semántico — `{ codigo, metodo, usar_ia, usar_ia_semantica, max_errores }` → `{ valido, errores, error, nodos, traza, metodo, valido_semantico, errores_semanticos, simbolos }` |
| `/tabla_ll` | GET | Devuelve tabla LL(1) y conjuntos PRIMERO/SIGUIENTE |
| `/ejemplos_semanticos` | GET | Lista de `.dml` en `ejemplos_semanticos/` |
| **`/chat`** *(no existe, propuesto para Fase 5b)* | POST | `{ mensaje, modelo }` → `{ respuesta, modelo }` |

---

---

## Fase 2 — Tokens globales  *(ejecutada)*

> **Estado:** completada. Solo se tocó `diamondlang.html` (más backup `diamondlang.html.bak`). DOM, JavaScript, `server.py` y el resto del backend intactos.

### 2.1 Cambios en el `<head>`

1. **Tailwind CDN** (con plugins, idéntico a los mockups):
   ```html
   <script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
   ```
2. **Google Fonts** combinadas en un solo `<link>` (Inter + JetBrains Mono + Material Symbols Outlined, `display=swap` para mitigar FOUT — Riesgo 8):
   ```html
   <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">
   ```
   > El `<link>` viejo de **Space Mono + Syne se conservó** (Tarea 2 dice "agregar sin quitar"; su retiro es Fase 7). Esto además mantiene renderizando las 4 referencias a `'Space Mono'` que viven dentro del JS (ver edge case 2.5).
3. **`<script id="tailwind-config">`** antes de `</head>`: base = `tailwind.config` del mockup *fundación revisado* (fuente de verdad), con los overrides §2.A.2 y las extensiones `ide-*` / `syntax-*` / `toolbar-height` / `container-padding` del mockup Léxico añadidas para que las clases Tailwind de fases 3a-3c no se rompan.
   - `colors`: 53 tokens. Overrides aplicados: `primary #FFC66D→#ffe9cc`, `background #2B2B2B→#17130d`, `surface-tint #FFC66D→#f5bd65`. `primary-container` se dejó en `#ffc66d` (amarillo IntelliJ, el acento real).
   - `borderRadius`: `DEFAULT 0.125rem`, `lg 0.25rem`, `xl 0.5rem`, `full 0.75rem` (⚠ `full` no es circular — Riesgo 5).
   - `spacing`: `gutter 1px`, `unit 4px`, `margin-sm 8px`, `margin-md 16px`, `panel-padding 12px`, `toolbar-height 48px`, `container-padding 24px`.
   - `fontFamily` / `fontSize`: tokens `headline-*`, `body-*`, `code-*`, `label-caps` replicados (Inter para UI, JetBrains Mono para `code-*`).
   - `darkMode: "class"` (igual que los mockups). **No** se añadió `class="dark"` al `<html>` en esta fase para respetar "no tocar DOM"; sin uso de variantes `dark:` todavía no afecta. Si una fase posterior usa `dark:`, habrá que añadirlo entonces.
4. **Mini-estilo Material Symbols** al inicio del `<style>`:
   ```css
   .material-symbols-outlined { font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24; }
   ```
   (Se unificó `opsz 24`, descartando el `opsz 20` del mockup fundación, como se anticipó en §1.)

### 2.2 Mapeo final de variables `:root` (nombres conservados, solo cambia el valor)

| Variable | Antes | Ahora | Justificación |
|---|---|---|---|
| `--bg` | `#0a0a0f` | `#17130d` | `background` global canónico (§2.A.2). |
| `--surface` | `#12121a` | `#1f1b15` | `surface-container-low` del mockup (header/tabs). |
| `--surface2` | `#1a1a26` | `#241f19` | `surface-container` (siguiente nivel de elevación). |
| `--border` | `#2a2a3e` | `#4f4537` | `outline-variant` (bordes/divisores técnicos). |
| `--accent` | `#7c6af7` | `#ffc66d` | `primary-container` = amarillo IntelliJ, acento de marca. |
| `--accent2` | `#f75d8c` | `#ffb4ab` | `error` (rosa-rojo claro): acento secundario / error. |
| `--accent3` | `#4df7c8` | `#4CAF50` | verde de estado "OK" de los mockups (status dot, banner verde). |
| `--accent4` | `#f7c84d` | `#f5bd65` | `primary-fixed-dim` / `surface-tint`: ámbar de warning semántico. |
| `--text` | `#e8e8f0` | `#ebe1d7` | `on-surface`: texto principal. |
| `--muted` | `#6b6b8a` | `#d3c4b2` | `on-surface-variant`: texto secundario. |
| `--glow` | `rgba(124,106,247,0.25)` | `rgba(255,198,109,0.25)` | glow del nuevo `primary` (#ffc66d) a baja opacidad. |
| `--tok-kw` | `#c084fc` | `#CC7832` | `syntax-keyword` JetBrains (naranja). |
| `--tok-type` | `#60a5fa` | `#6897BB` | `syntax-number` azul — Darcula no separa tipo; se reusa el azul. |
| `--tok-id` | `#e8e8f0` | `#A9B7C6` | `syntax-id` JetBrains (gris-azulado). |
| `--tok-num` | `#f7c84d` | `#6897BB` | `syntax-number` JetBrains (azul). |
| `--tok-str` | `#4df7c8` | `#6A8759` | verde JetBrains para cadenas literales. |
| `--tok-op` | `#f75d8c` | `#CC7832` | naranja JetBrains; Darcula colorea operadores como keyword. |
| `--tok-sym` | `#fb923c` | `#A9B7C6` | **sin equivalente directo** en mockups → gris-azulado de identificador (Darcula, el más cercano). |
| `--tok-bool` | `#a78bfa` | `#CC7832` | booleanos son palabra clave en Darcula → naranja. |
| `--tok-err` | `#ef4444` | `#ffb4ab` | `error` consistente con la paleta de errores. |
| `--tok-cmt` | `#4b5563` | `#808080` | gris de comentarios IntelliJ Darcula. |

> Nota: los fondos translúcidos de los chips `.tok-*` (`background:rgba(...)`/`border-color:rgba(...)`) siguen con los **valores rgba antiguos** porque están hardcodeados, no usan las variables. Como `color` sí usa la variable, los chips ya muestran el texto en la paleta nueva; el refinamiento de sus fondos es Fase 3b. No rompe nada.

### 2.3 Tipografía global

- `body`: `'Syne'` → **`'Inter'`**.
- 26 reglas CSS dentro de `<style>`: `'Space Mono'` → **`'JetBrains Mono'`** (reemplazo acotado a las líneas del bloque `<style>` con `sed`, sin tocar el `<script>`). Tamaños, line-heights y weights **sin cambios** (como pide la Tarea 4).

### 2.4 Verificación funcional (estática)

- **JS byte-idéntico**: `diff` del bloque `<script>…` entre `.bak` y el archivo migrado → sin diferencias.
- **49 IDs protegidos**: todos presentes (0 faltantes).
- **78 clases/tokens-hook protegidos** (`tab`, `tok-*`, `traza-*`, `badge-*`, `set-*`, `s-*`, `estado-*`, `err-*`, `sem-*`, etc.): todos presentes.
- **`data-fila` / `data-columna` / `data-type`**: presentes.
- **4 pestañas y 4 panes**: `switchTab('lexico'|'sintactico'|'tabla'|'sets')` y `#pane-*` intactos.
- **`tailwind.config` válido**: parsea en node, 53 colores, overrides confirmados.
- **Tests etapas 1–9**: 10/10 OK (no podían verse afectados — solo cambió HTML/CSS — pero se corrieron antes y después).
- `server.py` y el backend no se tocaron (solo HTML); el endpoint `/parsear` sigue devolviendo el JSON completo.

### 2.5 Edge cases / decisiones sobre la marcha

1. **`--tok-sym` sin equivalente Stitch.** Los mockups solo definen `syntax-keyword/number/id`. Se mapeó a `#A9B7C6` (gris-azulado de identificador en Darcula) por ser el más cercano. Documentado para revisión en Fase 3b.
2. **4 referencias a `'Space Mono'` dentro del JS** (líneas ~353, 559, 572, 740: estilos inline en template literals de la traza, gutter del árbol, tabla de tokens y celda de pila). Por la regla "no tocar JS" **se dejaron como están**; siguen renderizando porque el `<link>` viejo de Space Mono se conservó. Quedan para unificar cuando se editen esos templates en Fase 3b/3c (o limpieza en Fase 7).
3. **`darkMode:"class"` sin `class="dark"` en `<html>`** — explicado en 2.1.3.
4. **Spacing ampliado** con `toolbar-height`/`container-padding` (del mockup Léxico, no del de fundación) para anticipar Fase 3b sin sorpresas.
5. **`<link>` de fuentes viejas conservado** intencionalmente (Tarea 2 = "agregar sin quitar"); su retiro corresponde a Fase 7.

---

**Fase 2 cerrada y aprobada por el usuario.**

---

## Fase 3a — Chrome global  *(ejecutada)*

> **Estado:** completada. Solo se tocó `diamondlang.html` (chrome) + backup `diamondlang.html.bak` (estado Fase 2). Contenido de las 4 panes, `<script>` JS, `<head>` (Tailwind/fuentes/config), `server.py` y backend: **intactos**.

### 3a.0 Hallazgo clave que condicionó el diseño

`switchTab()` ejecuta `t.className = 'tab' + (...' active')` y `setStatus()` ejecuta `offline-banner.className = 'offline-banner ' + (...'visible')` y `status-dot.className = 'status-dot ...'`. **Reescriben el `className` completo**, así que cualquier clase Tailwind puesta directamente sobre `.tab`, `#offline-banner` o `#status-dot` se borraría en el primer ping/switch. → Esos tres elementos se siguen gobernando por **reglas CSS** (`.tab`, `.tab.active`, `.offline-banner`, `.offline-banner.visible`, `.status-dot.online/.offline`); los **íconos Material Symbols se añadieron como hijos** (los hijos sí sobreviven al reset de className). Header y footer son estáticos → ahí sí se usó Tailwind libremente.

### 3a.1 Qué cambió

**Header** (`header{}` CSS + HTML interno con Tailwind):
- Altura fija 48px (≈ `h-12` del mockup), fondo `--surface2` (#241f19 = surface-container), borde inferior sutil, sin el `backdrop-filter`/translúcido anterior.
- Emoji 💎 → **SVG diamante monocromo** (los 3 paths del mockup) en acento amarillo `--accent` (#ffc66d).
- "Diamond" (`text-headline-md`, peso regular, `text-on-surface`) + "**Lang**" (bold, amarillo `--accent`).
- Badge `v4.0` estilo pill: `bg-surface-variant text-on-surface-variant`, monoespaciado (`font-mono-jetbrains`), 10px.
- Divisor vertical (`h-4 w-px`) entre logo y estado, como el mockup.
- Estado servidor: `#status-dot` + `#status-text` conservados; dot verde online (`--accent3` #4CAF50) / "rojo" offline (`--accent2` #ffb4ab, token error) con glow.

**Tab bar** (`.tabs` / `.tab` CSS + íconos hijos):
- 4 tabs horizontales, altura 40px (`h-10`), gap 16px, alineadas al inicio, fondo `--surface` (#1f1b15 = surface-container-low, como el `nav` del mockup).
- Se reemplazaron los prefijos ①②③④ por **íconos Material Symbols** (`code`, `account_tree`, `grid_on`, `list`) + label. Los nombres de pestaña NO cambian.
- Tipografía Inter, weight 500, uppercase, `letter-spacing 0.05em`.
- Activa: texto amarillo `--accent` + `border-bottom: 2px` amarillo. Inactivas: `--muted`. Hover: `--text`.

**Banner offline** (`.offline-banner` CSS + ícono hijo):
- Fondo rojo `#93000a` (error-container), texto `#ffdad6` (on-error-container), ícono `cloud_off`, monoespaciado, centrado. `display:flex` solo con `.visible` (lo aplica `setStatus`).

**Footer / status bar** (NUEVO DOM, antes de `<script>`):
- `<footer id="fs-bar">` fijo abajo, altura 24px (`h-6`), fondo `--surface2`, borde superior. Izquierda: "DiamondLang v4.0 · Entrega 4". Derecha: "UTF-8" y "Espacios: 4".
- IDs nuevos con prefijo `fs-`: **`fs-bar`, `fs-project`, `fs-encoding`, `fs-indent`** (sin colisión con los 49 existentes).

### 3a.2 IDs nuevos creados
`fs-bar`, `fs-project`, `fs-encoding`, `fs-indent` (footer status bar, solo visual).

### 3a.3 Decisiones tomadas sobre la marcha

1. **Acento del logo = amarillo `--accent` (#ffc66d), no `text-primary` (#ffe9cc crema) del mockup.** El brief pidió explícitamente "acento amarillo IntelliJ" para el ícono y "Lang"; prevalece sobre el `text-primary` del mockup de fundación.
2. **Altura de `.pane` ajustada** de `calc(100vh - 105px)` a `calc(100vh - 112px)` (header 48 + tabs 40 + footer fijo 24) para que el footer fijo no tape el contenido inferior de las panes. Es un ajuste de layout/chrome, no del contenido de las panes. *(Edge case: con el banner offline visible, el contenido se desplaza ~31px y puede haber un leve overflow inferior solo en estado offline — mismo comportamiento tolerado que el diseño original.)*
3. **Footer estático (sin JS).** No se cableó "Línea/Columna" en vivo (eso requeriría JS nuevo, prohibido en esta fase); los indicadores de cursor reales siguen en `#cur1`/`#cur2` dentro de las panes. Se omitió un "Línea 1, Columna 1" fijo para no mostrar un número engañoso que nunca cambia; en su lugar el footer muestra datos verídicos (proyecto, encoding, indentación).
4. **Footer `position:fixed`** en vez de reestructurar `<body>` a flex column → cambio mínimo y de bajo riesgo.
5. **Reglas CSS `.logo`, `.logo .lang`, `.badge` eliminadas** (ya no se usan; el header se reconstruyó). `class="server-status"` se conserva en el HTML pero ahora se estiliza con utilidades Tailwind (su regla CSS también se retiró). Sin huérfanos referenciados por JS.
6. **Íconos Material Symbols** se dejaron con el `opsz 24` global de Fase 2; tamaño afinado por contexto vía CSS (`.tab .material-symbols-outlined{16px}`, `.offline-banner .material-symbols-outlined{18px}`).

### 3a.4 Verificación (estática)
- **JS byte-idéntico** (`diff` del bloque `<script>` bak vs actual = sin diferencias).
- **49 IDs** presentes (0 faltantes) + **4 IDs `fs-` nuevos**.
- **78 clases/hooks** presentes (0 faltantes).
- **4 tabs** con sus `onclick="switchTab(...)"` intactos; orden y nombres sin cambios.
- Emoji 💎 del **logo** eliminado; quedan 2 ocurrencias fuera de alcance (el `<title>` del documento y un string de ejemplo `.dml` dentro del JS — no son chrome).
- **Tests etapas 1–9: 10/10 OK** antes y después.

### 3a.5 Qué quedó imperfecto (se ajusta en fases posteriores)
- El **interior de las 4 panes sigue con el chrome viejo** (paneles `.panel`/`.panel-hdr`, botones, chips) — Fases 3b/3c/4.
- Los hooks `.badge-*`, `.tok-*`, `.traza-*` aún usan rgba de la paleta vieja (morado/rosa) en sus fondos hardcodeados — se migran al tocar sus paneles.
- El footer no refleja cursor en vivo (decisión 3a.3.3).

---

**Fase 3a cerrada y aprobada por el usuario.**

---

## Fase 3b — Pestaña Léxico  *(ejecutada)*

> **Estado:** completada. Solo se tocó `diamondlang.html` (HTML de `#pane-lexico` + CSS asociado) + backup `diamondlang.html.bak` (estado Fase 3a). `<script>` JS, chrome global, `<head>`, panes Sintáctico/Tabla/Sets, `server.py` y backend: **intactos** (verificado por `diff`).

### 3b.0 Hallazgo de scoping (decisivo)

Varias clases que el JS toca o que aparecen en `#pane-lexico` **son compartidas con `#pane-sintactico`** (que se refina en 3c): `.error-log`/`.ok-log` (también en `#err-sint`/`#ok-sint`), `.panel`/`.panel-hdr`/`.pdot`/`.grid-2`/`.empty`/`.empty-icon`. Si se redefinen globalmente, se rompería el aspecto de Sintáctico antes de tiempo. → **Todo el refinamiento se scopeó bajo `#pane-lexico`** (overrides de mayor especificidad). Excepción: `.token-chip` y las 10 `.tok-*` son **exclusivas de Léxico**, así que se actualizaron globalmente (era además lo pedido en Tarea 3).

Además se respetó el **hallazgo de Fase 3a**: `limpiar()` y `renderErrLog()` reescriben `className` completo de `.error-log`/`.ok-log` → su estilo vive en CSS (`#pane-lexico .error-log/.ok-log`), nunca en clases Tailwind directas. Lo dinámico (`renderTokens`, `renderTablaLex`, `renderStatsLex`) inyecta `innerHTML` con estilos inline que **no se tocaron**.

### 3b.1 Qué se refinó

- **Estructura/paneles:** el grid 2×2 se conserva (`.lex-grid`, columnas `1fr 1fr`, filas `3fr/2fr`, gap 16px, padding 16px). Cada panel pasó de `.panel`/`.panel-hdr` (con `.pdot`) a **panel card del mockup** (`.lex-panel`: `bg #3C3F41`, borde `#323232`, `rounded`, hover borde ámbar; `.lex-hdr`: barra de 40px `bg #323232` con ícono Material Symbols + título uppercase + contador a la derecha).
- **Íconos:** `.pdot`/◇ reemplazados por Material Symbols — `description` (editor, ámbar), `format_list_bulleted` (tokens, azul), `table_chart` (tabla, cian). El emoji 📂 del select → texto "Ejemplos".
- **Editor:** `#ed1`/`#ln1` conservados; fondo `#2B2B2B`, gutter `#606366`, texto `#A9B7C6`, caret ámbar, selección ámbar translúcido. `#cur1` en JetBrains Mono muted.
- **Controles:** botón "Analizar léxico" (`#btn-lex`) → primario ámbar (`bg --accent`, texto `#442c00`) con ícono `play_arrow`; select "Ejemplos" (`#ej1`) → estilo dropdown del mockup con flecha SVG; botón limpiar → ghost con ícono `close`. **IDs y handlers `onclick`/`onchange` intactos.** El spinner `#sp1` recoloreado a ámbar.
- **Chips de token (Tarea 3):** las 10 `.tok-*` ahora usan el patrón Stitch `bg 10% / borde 30%` sobre los hex de sintaxis `--tok-*` de Fase 2 (#CC7832, #6897BB, #A9B7C6, #6A8759, #ffb4ab, #808080). El tooltip `::after` (de `data-type`) se mantiene, ahora sobre `surface2`/`border` (paleta nueva). La transición `translateY(-1px)` en hover se conserva.
- **Leyenda:** franja horizontal al pie del panel de tokens; squares 10px `rounded-sm`, texto Inter 0.56rem bold uppercase muted. Etiquetas pasadas a Capitalización ("Palabra clave", "Tipo", "Número", "Cadena", "Operador", "Error").
- **Tabla de símbolos:** `thead` `bg #323232` con celdas Inter small-caps muted; filas JetBrains Mono con hover `#323232`; padding generoso (`10px 24px` / `8px 24px`). La celda **Tipo de token** sigue armada por el JS con estilo inline (respetado). Cabeceras renombradas a "Tipo de token"/"Columna" (texto visible, no IDs).
- **error-log/ok-log:** recoloreados (rojo error-container translúcido / verde #4CAF50 translúcido) con padding alineado a la tabla. Las clases `.active` (añadidas/quitadas por JS) **no se tocaron**.
- **Stats bar:** barra de 36px `bg #3C3F41`, JetBrains Mono, separación entre stats; `.stat-val` en ámbar `--accent`; `#s-err` conserva su inline `color:var(--tok-err)` (rojo).

### 3b.2 Tailwind vs CSS plano (decisiones por conflicto con JS)

- **CSS plano scopeado** para: `.error-log`/`.ok-log` (JS reescribe className), tabla `th/td/thead` (selectores de elemento globales — se overridean solo dentro de `#pane-lexico`), `.tok-*`/`.token-chip` (generados dinámicamente; Tailwind CDN-JIT no los garantiza), `.empty-icon`, stats, leyenda, editor.
- **Clases nuevas con prefijo `lex-`** (`.lex-grid`, `.lex-panel`, `.lex-hdr`, `.lex-controls`, `.lex-btn-primary`, `.lex-select`, `.lex-btn-ghost`) en vez de Tailwind directo, para no chocar con las reglas globales `.panel`/`.controls`/`.btn` que siguen sirviendo a Sintáctico.

### 3b.3 Edge cases

1. **`◇` lo hardcodea el JS** (`renderTokens`/`limpiar`). No se puede tocar el JS → se ocultó el glifo con `#pane-lexico .empty-icon{font-size:0}` y se dibuja el ícono `data_object` vía `::after` con la fuente Material Symbols. Scopeado a Léxico (otras panes mantienen su ◇).
2. **`⚠`/`✓` los antepone el JS** en `renderErrLog`. Para no duplicar, **no** se añadió otro ícono Material Symbols al inicio de los logs; solo se refinó color/padding. (El brief lo dejaba como "si encaja".)
3. **`#s-err` siempre en rojo** (inline `var(--tok-err)`): incluso con 0 errores el "0" se ve rojo. Cambiarlo a condicional requeriría JS (prohibido). Se dejó como stat siempre rojo-codificada; imperfección menor.
4. **Contador de la tabla de símbolos:** el mockup muestra "32 Entradas", pero no existe elemento JS que lo alimente y no se permite JS nuevo → se omitió (el total ya aparece en la stats bar). `#tok-count` sí existe y se estiliza como pill; con `:empty{display:none}` no muestra una pastilla vacía antes del primer análisis.
5. **`.grid-2` compartida:** se sustituyó por `.lex-grid` propia en el HTML de Léxico para no alterar la `.grid-2` global de Sintáctico.

### 3b.4 Verificación (estática)
- **JS byte-idéntico** (`diff` del bloque `<script>` = sin diferencias).
- **17 IDs de Léxico** presentes; **handlers** `analizarLexico()`/`cargarEjemplo(...)`/`limpiar(...)` intactos.
- **Hooks** `.error-log`/`.ok-log` (2 c/u: léxico+sintáctico), 10 `.tok-*`, `.stat-val` (×4), `.token-chip`, `.empty`/`.empty-icon` presentes.
- **Panes Sintáctico, Tabla LL(1) y Sets: HTML byte-idéntico** al de Fase 3a.
- **Tests etapas 1–9: 10/10 OK.**

### 3b.5 Qué quedó imperfecto
- El editor sigue siendo `<textarea>` (sin resaltado de sintaxis real dentro del editor; el mockup muestra un contenteditable coloreado) — fuera de alcance; el resaltado inline es Fase 6.
- `#s-err` rojo permanente (3b.3.3).
- Sin contador "N entradas" en la tabla (3b.3.4).
- El resto de pestañas (Sintáctico/Tabla/Sets) siguen con estética previa — Fases 3c y 4.

---

**Fase 3b cerrada y aprobada por el usuario.**

---

## Fase 3c — Pestaña Sintáctico  *(ejecutada)*

> **Estado:** completada. Solo se tocó `diamondlang.html` (HTML de `#pane-sintactico` + su CSS) + backup `diamondlang.html.bak` (estado Fase 3b). `<script>` JS, chrome global, `<head>`, panes Léxico/Tabla/Sets, `server.py` y backend: **intactos** (verificado por `diff`).

### 3c.1 Qué se refinó
- **Chrome de paneles:** grid 2×2 + traza full-width abajo conservado. `.panel`/`.panel-hdr`/`.pdot` → clases nuevas `syn-panel`/`syn-hdr`/`syn-hdr-title` (panel card `#3C3F41`, header `#323232` con ícono Material Symbols + título uppercase + indicador a la derecha). Íconos: `edit_note` (editor), `account_tree` (árbol), `terminal` (traza), `report` (errores sint), `error` (errores sem), `table_chart` (símbolos).
- **Editor:** `#ed2`/`#ln2` conservados; fondo `#2B2B2B`, gutter `#606366`, texto `#A9B7C6`, caret/selección ámbar. `#cur2` en JetBrains Mono muted.
- **Toolbar:** botón "Analizar" (`#btn-parse`) primario ámbar con `play_arrow`; selects `#metodo-sel`/`#ej2`/`#ej-sem` con estilo dropdown del mockup (flecha SVG); botón limpiar ghost con `close`. **IDs, `onchange`/`onclick` y todos los `<option>`/values intactos.**
- **Toggles de IA → switches modernos:** `#usar-ia`/`#usar-ia-sem` (checkbox nativo) ocultos con `opacity:0;position:absolute`; se añadió un `<span class="syn-switch">` hermano dibujado por CSS (track + knob), encendido con `input:checked + .syn-switch`. Las labels conservan `id`/`class="ia-toggle"` y la lógica `.disabled` (que `pingIA*` añade/quita por `classList`) sigue atenuando el switch. Badge "Claude" cosmético añadido.
- **Banner de estado** (`#estado-analisis`, 4 variantes): rediseñado con `border-left:4px` + fondo translúcido + texto uppercase. `estado-ok` verde `#4CAF50`, `estado-sem` ámbar `--accent`, `estado-sint` naranja `#CC7832`, `estado-bad` rojo `#ffb4ab`. La clase `.show` sigue controlando `display:flex`.
- **Panel errores sintácticos (rojo):** header `report` + items `.err-item` con `border-l-3` rojo, `.err-num` pill rojo, `.err-source.local` gris / `.err-source.ia` púrpura `#6B46C1`, sugerencia en cian. Click→`resaltarEnEditor` preservado (data-fila/columna intactos).
- **Panel errores semánticos (ámbar):** header `error` + items con `border-l-4` ámbar, `.sem-num` pill ámbar, `.sem-rule` **chip rosa** (`#ffb4ab`), `.sem-source` pill, `.sem-msg` y `.sem-suggestion` (sugerencia en caja con borde; variante `.ia` en lila). Click preservado.
- **Tabla de símbolos semánticos (teal):** header `table_chart` cian; thead small-caps; filas con hover; `.s-cat` azul, `.s-tipo` azul medio, `.s-amb` cian.
- **Traza de pila:** tabla con thead IDE; los **8 badges** recoloreados y diferenciados — MATCH verde, EXPAND azul, SYNC amarillo, INSERT azul claro, DESCARTA naranja, POP lavanda `#b39ddb`, ERROR rojo, ACEPTAR verde brillante (bold). Tints de fila por tipo de acción.

### 3c.2 Decisiones de scope / conflictos resueltos
- **Regla de oro aplicada:** todo el CSS nuevo vive bajo `#pane-sintactico`. Las clases compartidas con Léxico (`.editor-wrap`, `.line-nums`, `textarea`, `.empty`, `.spinner`, `.error-log`, `.ok-log`, `.grid-2`→`syn-grid`, `.panel`/`.controls`/`.btn`→`syn-*`) se recrearon scopeadas, sin tocar las globales (que ya sirven a Léxico y a otras pestañas).
- Las clases **exclusivas** del Sintáctico (errores/sem/simbolos/estado/traza/badge/err/sem/s-cat/ia-toggle) también se scoparon a `#pane-sintactico` (recomendación del brief, aunque no aparezcan en otras panes) para no sorprender en Fase 4.
- **Hallazgo crítico respetado:** todos los elementos cuyo `className` reescribe el JS (`errores-panel`, `sem-panel`, `simbolos-panel`, `estado-analisis`, `error-log`, `ok-log`) se estilizan **solo por CSS** (clase fija + variante `.active`/`.show`), nunca con Tailwind directo. Los toggles usan `classList` (no reescritura) → seguros.

### 3c.3 Trucos / emojis hardcoded del JS
1. **Banner de estado:** `renderBannerEstado` arma el texto con `textContent` incluyendo el glifo `✓`/`⬥`/`⚠`/`✗`. Como es `textContent` (no `innerHTML`) y no se puede tocar el JS, **se conservó el glifo** como "ícono" del banner; el color/borde por estado los pone el CSS. No se añadió Material Symbol extra para no duplicar.
2. **Empty del árbol:** el `🌳` estático del HTML inicial **sí** se reemplazó por Material Symbol `account_tree` (es markup propio). Pero `renderArbol` regenera el empty con `✓`/`✗` vía `innerHTML` (JS) — esos glifos se mantienen (no se aplicó el truco `::after` de Léxico aquí, porque el mismo `.empty-icon` sirve para estados ✓/✗ y forzar un ícono fijo sería incorrecto).
3. **Sugerencias semánticas:** `renderErroresSemanticos` antepone `✨`/`💡` al texto de la sugerencia y `✨ IA`/`local` en la fuente (JS). Se conservaron; solo se estilizaron los contenedores (`.sem-suggestion`, `.sem-source`).

### 3c.4 Edge cases
- **Árbol SVG con colores viejos:** `renderArbol` genera el SVG con hex hardcodeados (fondo `#0a0a0f`, nodos `#7c6af7`/`#c084fc` morados, terminales `#4df7c8`, errores `#ef4444`, aristas `#3a3a5e`) y un `style="background:#0a0a0f"` inline en el `<svg>`. Como **no se puede tocar el JS**, el dibujo del árbol mantiene la paleta antigua morada sobre fondo casi negro, aunque el contenedor `.arbol-wrap` ya es `#2B2B2B`. Es la imperfección más visible de esta fase; su arreglo requeriría editar `renderArbol`/`dibujarNodos` (fuera de alcance).
- **`.err-num`/`.sem-num` muestran `[N]` con corchetes** (los pone el JS) en vez del número desnudo del mockup; se estilizaron como pills (no círculos) para que `[1]` quepa bien.
- **Traza:** la celda de pila conserva su `font-family:'Space Mono'` inline (uno de los 4 restos en JS de Fase 2); rendea porque el `<link>` viejo sigue cargado. Se unifica en Fase 7.

### 3c.5 Verificación (estática)
- **JS byte-idéntico** (`diff` del bloque `<script>` = sin diferencias).
- **Todos los IDs de Sintáctico** presentes; **handlers** `parsear()`/`cargarEjemplo('ed2','ej2',…)`/`cargarEjemploSemantico()`/`limpiarSint()` y todos los `<option>`/values intactos.
- **Hooks** (`errores-panel`, `sem-panel`, `simbolos-panel`, `estado-analisis`, `traza-table`, `ia-toggle`, `err-item`, `sem-rule`, `s-cat`, `badge-*`) presentes.
- **Panes Léxico, Tabla LL(1) y Sets: HTML byte-idéntico** al de Fase 3b.
- **Tests etapas 1–9: 10/10 OK.**

### 3c.6 Qué quedó imperfecto
- **Colores del árbol SVG** siguen en paleta vieja (3c.4) — requiere tocar JS.
- `[N]` con corchetes en los badges numéricos (3c.4).
- El banner usa el glifo del JS como ícono (3c.3.1).
- Pestañas Tabla LL(1) y PRIMERO/SIGUIENTE siguen con estética previa — Fase 4.

---

**Fase 3c cerrada y aprobada por el usuario.**

---

## Mini-fase — Migración de paleta del árbol SVG  *(ejecutada, excepción aprobada)*

> **Estado:** completada. Excepción aprobada para tocar **solo** los strings de color dentro de `renderArbol()` (las funciones internas `dibujarAristas`/`dibujarNodos`). Backup `diamondlang.html.bak` = estado post-3c.

**Decisión:** **hex hardcodeados** (no `getComputedStyle`). Motivo: mantiene el cambio confinado exactamente a los strings de color (cumple el alcance estricto "solo líneas con color"), sin añadir líneas de lógica ni riesgo de que `getComputedStyle` devuelva `rgb()` en formato distinto. El árbol queda coherente con el contenedor `.arbol-wrap` (que en 3c quedó en `#2B2B2B`).

**Mapeo viejo → nuevo aplicado** (10 hex, en 7 pares de líneas):

| Elemento | Viejo | Nuevo | Razón |
|---|---|---|---|
| Fondo del `<svg>` | `#0a0a0f` | `#2B2B2B` | ide-bg, igual que `.arbol-wrap`/editor (sin rectángulo negro dentro del panel) |
| Edges (`<line>`) | `#3a3a5e` | `#4f4537` | outline-variant (`--border`), gris cálido suave |
| Marker de flecha (defs) | `#3a3a5e` | `#4f4537` | mismo gris de los edges |
| ε (epsilon) texto | `#4b5563` | `#d3c4b2` | on-surface-variant (`--muted`) |
| No-terminal: fill elipse | `#1f1a3a` | `#3C3F41` | ide-panel (surface elevado) |
| No-terminal: stroke elipse | `#7c6af7` | `#ffc66d` | `--accent` (amarillo IntelliJ) — adiós morado |
| No-terminal: texto | `#c084fc` | `#ffc66d` | `--accent` |
| Terminal válido: fill rect | `#1e3a2a` | `#1f3322` | verde oscuro cálido |
| Terminal válido: stroke | `#4df7c8` | `#4CAF50` | `--accent3` (verde OK) |
| Terminal válido: texto | `#4df7c8` | `#4CAF50` | `--accent3` |
| Terminal error: fill rect | `#3a1d1d` | `#3a1414` | rojo oscuro |
| Terminal error: stroke | `#ef4444` | `#ffb4ab` | rojo de `.estado-bad`/`.tok-ERROR` |
| Terminal error: texto | `#ef4444` | `#ffb4ab` | mismo rojo |

**Colores fuera del mapeo del brief:** ninguno nuevo. El brief listaba todos; los únicos "no listados explícitos" eran los fondos oscuros de terminales (`#1e3a2a`/`#3a1d1d`), que mapeé con criterio (verde/rojo oscuros cálidos `#1f3322`/`#3a1414`).

**Verificación:**
- `diff` bak vs actual = **solo 7 pares de líneas, todas strings de color** del SVG. Coordenadas, `rx`/`ry`, `width`/`height`, `stroke-width`, `stroke-dasharray`, `font-size` y la lógica (`calcularPosiciones`, BFS, tamaños) **intactas**. Firmas de funciones sin cambios.
- 0 ocurrencias de cualquiera de los 10 hex viejos en todo el archivo.
- **Tests etapas 1–9: 10/10 OK.**

---

**Mini-fase del árbol cerrada y aprobada por el usuario.**

---

## Fase 4 — Pestañas Tabla LL(1) y PRIMERO/SIGUIENTE  *(ejecutada)*

> **Estado:** completada. Solo se tocó `diamondlang.html` (HTML de `#pane-tabla`
> y `#pane-sets` + su CSS) + backup `diamondlang.html.bak` (estado post mini-fase
> del árbol). `<script>` JS, chrome global, `<head>`, panes Léxico/Sintáctico,
> `server.py` y backend: **intactos** (verificado por `diff`).
>
> Sin mockup de Stitch para estas dos pestañas (no entraron en el rediseño): el
> criterio fue replicar el lenguaje visual ya establecido en Léxico/Sintáctico
> (panel card IDE `#3C3F41` / borde `#323232`, header de 40px `#323232` con
> Material Symbol + título Inter small-caps, datos técnicos en JetBrains Mono,
> acento amarillo IntelliJ `--accent` #ffc66d para no-terminales).

### 4.0 Hallazgo de scoping (decisivo)

Las clases `.panel`, `.panel-hdr`, `.pdot`, `.grid-2`, `.empty`, `.empty-icon`
son **globales y compartidas** con Léxico y Sintáctico (que ya están cerradas).
Redefinirlas a nivel global rompería esas pestañas. → **Todo el refinamiento se
scopeó bajo `#pane-tabla` y `#pane-sets`** mediante overrides de mayor
especificidad (`#pane-tabla .panel`, `#pane-sets .panel-hdr`, etc.). No se
renombró ninguna clase en el HTML (estructura del DOM intacta), así que los
overrides scopeados son la única vía: ganan por especificidad de ID frente a la
regla global de clase.

Las clases-hook que el JS inyecta (`ll-table`, `ll-nt`, `ll-cell-filled`,
`ll-cell-empty`, `set-row`, `set-nt`, `set-vals`, `set-val`, `set-val-t`,
`set-val-e`) **solo se usan dentro de estas dos panes**, así que los bloques CSS
globales previos (`.ll-*` en la sección "TABLA LL", `.set-*`/`.sets-wrap` en
"SETS PANEL") se **reescribieron scopeados** en su lugar — 0 reglas `.ll-`/`.set-`
quedan sin prefijo de pane. El JS no se tocó: `renderTablaLL`/`renderSets`
inyectan `innerHTML` con esas clases y el CSS scopeado las captura igual.

### 4.1 Qué se refinó — #pane-tabla (Tabla LL(1))

- **Layout:** `#pane-tabla{padding:16px}` para enmarcar el panel único con el
  mismo aire que el grid de 16px de Léxico/Sintáctico (`box-sizing:border-box`
  global evita overflow).
- **Panel:** `.panel` → card IDE `#3C3F41` / borde `#323232` / `rounded` /
  sombra sutil / hover borde ámbar.
- **Header (`.panel-hdr`):** barra de 40px `#323232`; `.pdot` (ámbar) →
  Material Symbol **`grid_on`** en `--accent`; título envuelto en `.ll-hdr-title`
  (Inter 600, uppercase, `--muted`).
- **Botón "↻ Cargar":** el `↻` textual + inline-style se reemplazaron por un
  botón ghost del mockup `.ll-reload` (borde `#323232`, Inter 700 uppercase,
  Material Symbol **`refresh`**, hover fondo `#39342d` + borde ámbar). Conserva
  `class="btn btn-ghost"` (los overrides scopeados ganan por especificidad de ID)
  y el `onclick="cargarTablaLL()"`.
- **Matriz `.ll-table`:**
  * `th` (encabezados): fondo surface elevado `#323232`, texto Inter small-caps
    `--muted`, sticky-top (z-index 2) para que la cabecera no desaparezca al
    scrollear.
  * `.ll-nt` (cabeceras de fila): fondo `#39342d`, texto **amarillo `--accent`**
    (antes era `--tok-kw` naranja), sticky-left.
  * `.ll-cell-filled`: fondo de acento suave `rgba(255,198,109,0.1)`, texto
    `--accent` (antes morado `rgba(124,106,247,…)`).
  * `.ll-cell-empty`: guion `—` en `--border` (muted), centrado.
  * Bordes `rgba(50,50,50,0.5)`, coherentes con el resto.
- **Estado vacío:** el `📊` (markup estático propio, no emitido por JS) se
  reemplazó **directamente** por un Material Symbol `grid_on` (mismo criterio que
  el `🌳→account_tree` de Fase 3c). Sizing vía `.empty-icon{font-size:0}` +
  `.empty-icon .material-symbols-outlined{2.6rem;opacity .25}`.

### 4.2 Qué se refinó — #pane-sets (PRIMERO / SIGUIENTE)

- **Layout:** `#pane-sets .grid-2{gap:16px;padding:16px;background:transparent}`
  (la global usa `gap:1px;background:var(--border)`); dos panel-cards paralelos.
- **Paneles y headers:** mismo tratamiento IDE que Tabla. `.pdot` →
  Material Symbols **`forward`** (PRIMERO) y **`arrow_forward`** (SIGUIENTE), con
  acento sutil distinto por cabecera: verde `--accent3` para PRIMERO, azul
  `#9dccf2` para SIGUIENTE (clases `.set-hdr-primero`/`.set-hdr-siguiente`).
- **Filas:** `.set-nt` → **amarillo `--accent`** (antes `--tok-kw` naranja);
  `.set-vals` JetBrains Mono; separadores `rgba(50,50,50,0.5)`.
- **Chips:**
  * `.set-val-t` (terminal normal): tono **cálido sutil** — fondo
    `#39342d` (surface-variant), texto `--muted`, borde `#4f4537`
    (outline-variant). Antes era verde translúcido.
  * `.set-val-e` (ε y $): tono **más destacado** — ámbar
    `rgba(255,198,109,0.12)` / texto `--accent` / borde ámbar 35%, `font-weight:700`.
    Antes era amarillo `--accent4` más apagado.
- **Estado vacío:** el `◇` (markup estático ×2) se reemplazó directamente por
  Material Symbol **`trending_flat`**.

### 4.3 Decisiones de scope / trucos CSS

- **Overrides scopeados sobre clases globales** (no clases nuevas prefijadas tipo
  `lex-`/`syn-`): el brief pidió mantener la **estructura HTML intacta**, así que
  no se renombró `.panel`/`.panel-hdr` en el markup. La técnica fue subir la
  especificidad con el ID del pane. El único añadido al markup fueron clases
  *complementarias* en los `<span>` de título (`.ll-hdr-title`,
  `.set-hdr-title`+modificador) y en el botón (`.ll-reload`), todas decorativas
  y no tocadas por JS.
- **Material Symbols por reemplazo directo en markup** (no el truco `::after` de
  Léxico): los glifos `📊`/`◇` viven en HTML estático, no los emite el JS, así
  que se sustituyeron por `<span class="material-symbols-outlined">` directamente
  — más limpio que ocultar+`::after`. El truco `::after` solo es necesario cuando
  el JS hardcodea el glifo (caso Léxico).
- **`.panel-hdr` scopeado** resetea `text-transform`/`letter-spacing` de la regla
  global (que era uppercase + 1.5px para el viejo título mono); el título nuevo
  recibe su tipografía desde `.ll-hdr-title`/`.set-hdr-title`.
- **Sticky headers/columna preservados** (`th` top, `.ll-nt` left) con `z-index`
  explícito y fondos opacos para que la matriz gigante siga siendo navegable.

### 4.4 Edge cases

1. **Fallback de error de `cargarTablaLL`** emite `⚠` por `innerHTML` (JS,
   línea ~1177) dentro de un `.empty-icon` sin `<span>` Material Symbol. Por eso
   **NO** se usó el truco `font-size:0`+`::after` de Léxico aquí: zeroar el
   font-size del `.empty-icon` ocultaría también ese `⚠`. Como el ícono normal
   es un `<span class="material-symbols-outlined">` real, basta con estilar el
   span; el `⚠` del error sigue visible a 2.2rem (regla global). Sin regresión.
2. **Carga automática al entrar:** `switchTab` llama a `cargarTablaLL()` si la
   pane está vacía (líneas ~921-922), así que el estado empty con `grid_on`
   normalmente se ve solo un instante antes de poblarse la matriz. Se estilizó
   igual por correctitud.
3. **Truncado de producciones a 30 columnas / 18 chars** (lo hace `renderTablaLL`
   en JS): se mantiene; es comportamiento existente, no visual de esta fase.
4. **`.set-val` margen:** se subió de `1px 2px` a `2px` y padding a `2px 7px`
   para que los chips respiren como los del mockup; no afecta a JS.

### 4.5 Verificación (estática)

- **JS byte-idéntico** (`diff` del bloque `<script>` bak vs actual = sin
  diferencias).
- **5 IDs protegidos** presentes: `pane-tabla`, `ll-container`, `pane-sets`,
  `primero-wrap`, `siguiente-wrap`.
- **10 clases-hook** (`ll-table`, `ll-nt`, `ll-cell-filled`, `ll-cell-empty`,
  `set-row`, `set-nt`, `set-vals`, `set-val`, `set-val-t`, `set-val-e`)
  presentes y capturadas por reglas scopeadas.
- **`onclick="cargarTablaLL()"`** intacto (1 ocurrencia).
- **0 reglas `.ll-`/`.set-`/`.sets-wrap` globales** (sin prefijo de pane) — todo
  scopeado.
- **0 hex de la paleta vieja** (morado `124,106,247`, verde `77,247,200`,
  ámbar viejo `247,200,77`, borde `42,42,62`) en las CSS de tabla/sets.
- **Panes Léxico y Sintáctico: HTML byte-idéntico** al backup.
- **Tests etapas 1–9: 10/10 OK** antes y después.

### 4.6 Qué quedó imperfecto

- El `⚠` del fallback de error queda en `font-size:0` (4.4.1) — solo visible
  hipotéticamente con servidor caído; sin ícono Material Symbol porque el JS
  no lo emite como `<span>`.
- Sin contador de filas en los headers (no hay elemento JS que lo alimente y no
  se permite JS nuevo) — coherente con la decisión análoga de Fase 3b.

---

**Fase 4 cerrada y aprobada por el usuario.**

---

## Fase 5a — Chatbot frontend (modal + FAB)  *(ejecutada)*

> **Estado:** completada. Solo se tocó `diamondlang.html` (CSS + HTML + JS
> nuevos, todo aditivo) + backup `diamondlang.html.bak` (estado post Fase 4).
> `server.py` y el backend: **intactos**. **Sin endpoints nuevos** — respuestas
> simuladas; la integración real con Claude/Gemini es Fase 5b.
>
> **Cambio de naturaleza del proyecto:** a partir de aquí se escribe JS nuevo.
> La regla "no tocar el JS existente" se respetó en su forma fuerte: el diff
> `bak` vs actual es **puramente aditivo** (0 líneas eliminadas o modificadas;
> el bloque JS existente hasta `// ── Arranque ──` es byte-idéntico). No fue
> necesario modificar ninguna función existente para integrar el chatbot.

### 5a.1 Estructura añadida (HTML) e IDs nuevos

Tres bloques nuevos en `diamondlang.html`, todos con prefijo `chat-`:

1. **Trigger en el header** — `<button id="chat-header-trigger">` (ghost, Material
   Symbol `chat_bubble`) insertado **después** de `.server-status`, dentro del
   flex existente del header. No toca `#status-dot`/`#status-text` (que el JS
   reescribe vía `className`): es un hermano nuevo.
2. **FAB** — `<button id="chat-fab">` `position:fixed` abajo-derecha (bottom 40px
   para librar el footer `#fs-bar` de 24px), círculo amarillo accent, Material
   Symbol `chat_bubble` **relleno** (`FILL 1`), `z-index:900`.
3. **Modal** — `<div id="chat-modal">` (overlay `position:fixed; inset:0;
   z-index:1000`), con `.chat-card` dentro. Insertado entre `#fs-bar` y el
   `<script>` principal, así que sus elementos existen cuando corre el JS.

**IDs nuevos:** `chat-fab`, `chat-header-trigger`, `chat-modal`, `chat-title`,
`chat-model-selector`, `chat-close`, `chat-body`, `chat-input`, `chat-send`,
`chat-clear`.

**Clases nuevas (CSS):** `chat-card`, `chat-hdr`, `chat-hdr-left`,
`chat-hdr-icon`, `chat-hdr-title`, `chat-hdr-sub`, `chat-hdr-right`,
`chat-model-dot`, `chat-empty`, `chat-empty-icon`, `chat-empty-title`,
`chat-empty-text`, `chat-prompts`, `chat-prompt`, `chat-msg`, `chat-msg-user`,
`chat-msg-asst`, `chat-bubble`, `chat-msg-meta`, `chat-footer`, `chat-input-wrap`,
`chat-footer-bottom`, `chat-hint`, y el estado `.open` (siempre bajo `#chat-modal`).
Ninguna colisiona con los 49 IDs / 78 clases-hook protegidos (todas llevan
prefijo `chat-` o viven bajo `#chat-modal`).

Estructura interna del modal: **header** (icono `auto_awesome` + título/subtítulo
+ `#chat-model-selector` con dos pills Claude/Gemini + `#chat-close`) · **body**
`#chat-body` (renderizado por JS) · **footer** (`#chat-input` textarea +
`#chat-send` con `send` + `#chat-clear` con `delete` + hint de atajos).

### 5a.2 Funciones JS nuevas (sección `// ── CHATBOT (Fase 5a) ──`)

Estado en memoria: `let chatHistory = []` (`{role, text, model?}`) y
`let chatActiveModel = 'claude'`. Mapa `CHAT_MODEL_LABEL`.

| Función | Propósito |
|---|---|
| `openChat()` | Añade `.open`, pone `aria-hidden=false`, re-renderiza y enfoca el textarea. |
| `closeChat()` | Quita `.open`, `aria-hidden=true`. |
| `toggleChat()` | Alterna abierto/cerrado (usado por FAB y trigger del header). |
| `setChatModel(name)` | Cambia `chatActiveModel` y la pill activa (`'claude'`/`'gemini'`). |
| `renderChatBody()` | Pinta el `#chat-body`: estado vacío (icono + texto + 3 prompts) o las burbujas del historial; auto-scroll al final. |
| `addMessage(role, text, model)` | Agrega un mensaje a `chatHistory` y re-renderiza. El `model` solo se guarda para `assistant`. |
| `sendChat()` | Lee el textarea (ignora vacío), agrega el `user`, limpia el input, y tras 350 ms agrega la respuesta `assistant` con el modelo **congelado al momento del envío**. |
| `chatPlaceholderReply(prompt)` | Respuesta determinista: "regla" → las 5 reglas; "análisis" → el pipeline; "alcance"/"scope" → global vs local; resto → texto neutro. Todas anotan que en 5b vendrá del modelo real. |
| `clearChat()` | Vacía el historial, vuelve al estado vacío, limpia el input. |
| `useChatPrompt(btn)` | Vuelca el texto del chip al textarea y enfoca. |
| `escChat(s)` | Escape de HTML local (no se reusó el `esc()` existente para no acoplar secciones; mismo comportamiento). |

### 5a.3 Conexión con el resto de la app (atajos, focus, accesibilidad)

- **Apertura:** FAB (abajo-derecha) y `#chat-header-trigger` (header) llaman a
  `toggleChat()`.
- **Cierre:** `Esc` (listener `document` que solo actúa si `#chat-modal.open`),
  click en el backdrop (`mousedown` con `e.target === chatModalEl`, así un click
  dentro de la card no cierra), y el botón `#chat-close`.
- **Teclado del input:** `Enter` envía, `Shift+Enter` inserta nueva línea
  (comportamiento por defecto del textarea). Listener acotado a `#chat-input`.
- **Focus management:** al abrir, foco al textarea (tras 50 ms para que el
  display:flex ya esté aplicado); **focus trap** simple en `keydown`/`Tab` del
  modal que cicla entre el primer y último elemento enfocable.
- **ARIA:** `role="dialog"`, `aria-modal="true"`, `aria-labelledby="chat-title"`,
  `aria-hidden` sincronizado con el estado, `aria-label` en FAB/trigger/cerrar.
- **z-index:** FAB 900 (encima del contenido, debajo del backdrop); modal 1000
  (encima de todo). El `#chat-body` tiene `overflow-y:auto`, así que la
  conversación scrollea si crece sin afectar al resto de la página.
- **No se modificó ningún listener existente.** Los editores siguen con sus
  `keydown` (Ctrl+Enter / Tab); el nuevo `Escape` global es independiente.

### 5a.4 Paleta y coherencia visual

Reutiliza las variables `:root` (`--accent` #ffc66d, `--text`, `--muted`,
`--border`, `--accent2`) más literales del mockup para las superficies elevadas
(`#241f19` card/body, `#2e2923` header/footer/burbuja-asistente, `#120e08`
input/selector, `#39342d` hover). Burbuja de usuario y botones primarios:
`var(--accent)` con texto `#442c00` (misma convención que los botones de
Léxico/Sintáctico). Dots de modelo: Claude `#CC7832` (naranja), Gemini `#9dccf2`
(azul). Tipografía Inter para todo el UI del chat.

### 5a.5 Decisiones tomadas sobre la marcha

1. **Un solo modal con render dinámico**, no los dos `<div>` separados
   (`active-assistant`/`empty-assistant`) del mockup. El brief pedía
   `renderChatBody()` que pinta vacío o mensajes → un único `#chat-body` es más
   limpio y evita estado duplicado.
2. **`chat_bubble` para ambos disparadores** (no `chat_bubble_outline`): en
   Material Symbols el contorno se logra con `FILL 0` (default global), así que
   el trigger del header sale en outline y el FAB se rellena con `FILL 1`. Evita
   depender de un nombre de glifo que podría no existir en la fuente Symbols.
3. **Texto oscuro `#442c00`** sobre el amarillo (no el `on-primary-container`
   #785100 del mockup) para igualar la convención ya usada en los botones
   primarios de las fases anteriores.
4. **Modelo congelado al enviar** (`modelAtSend`): si el usuario cambia de modelo
   mientras "responde" el placeholder, el badge refleja el modelo vigente en el
   envío, no el nuevo. Cambiar el modelo afecta a los **mensajes futuros**, como
   pide el criterio.
5. **Respuesta simulada con `setTimeout(350 ms)`** para que se sienta como una
   respuesta entrante y no instantánea (sigue siendo <1 s).
6. **FAB a `bottom:40px`** (el mockup usa 48px) para no solaparse con el footer
   fijo `#fs-bar` de 24px que añadió la Fase 3a.

### 5a.6 Verificación

- **Diff `bak` vs actual: puramente aditivo** (0 líneas removidas/modificadas);
  bloque JS existente byte-idéntico hasta `// ── Arranque ──`.
- **Sintaxis JS** del archivo completo: `node --check` OK.
- **Harness de lógica con DOM mock (21/21 asserts):** render vacío con 3 prompts,
  envío usuario+asistente, placeholders por keyword (regla/análisis/alcance/
  neutro), badge del modelo correcto, cambio de modelo congelado al enviar,
  `clearChat`, `open/close` + `aria-hidden`, y envío vacío como no-op.
- **10 IDs nuevos** presentes; **IDs protegidos** intactos.
- **Tests etapas 1–9: 10/10 OK.**
- **4 pestañas:** sin regresión (cambios aditivos, JS existente intacto).

### 5a.7 Pendiente explícito para Fase 5b

- **Backend:** crear `POST /chat` en `server.py` (`{mensaje, modelo}` →
  `{respuesta, modelo}`); reemplazar `chatPlaceholderReply` por un `fetch` real.
- **Gemini:** decidir si se integra un adaptador o se deja la pill deshabilitada
  con tooltip "Próximamente".
- **Streaming / estados de carga:** mostrar un indicador "escribiendo…" mientras
  llega la respuesta real (ahora es un `setTimeout` fijo).
- **Persistencia opcional** del historial (sessionStorage) si se desea.

### 5a.8 Qué quedó por pulir (honesto)

- Las burbujas del asistente renderizan **texto plano** (con saltos de línea via
  `white-space:pre-wrap`); el mockup muestra `code`/negritas/cajas de "Opciones".
  Como las respuestas reales de 5b serán texto/markdown, se dejó simple en 5a
  (no se parseó markdown todavía).
- No hay **timestamp** ("Tú • 10:42 AM") en las burbujas de usuario como el
  mockup; se omitió para no introducir formato de hora en esta fase.
- El **focus trap** es básico (primer/último enfocable); suficiente para el
  modal pero no contempla elementos que cambian de orden dinámicamente.

---

**Fase 5a cerrada y aprobada por el usuario.**

---

## Fase 5b — Chatbot backend y migración a multi-modelo  *(ejecutada)*

> **Estado:** completada. Primera fase que toca **backend** y **código IA**.
> Regla respetada: el JS y los endpoints existentes siguen funcionando igual;
> todo lo nuevo se **añade**. El único módulo IA preexistente que se reescribió
> es `sugerencias_ia.py` (migración Claude→Gemini), conservando su contrato
> público. `sugerencias_ia_semantica.py` quedó **intacto** (sigue en Claude).

### 5b.0 Decisión de arquitectura: dos clientes simétricos

Se extrajeron **dos wrappers autocontenidos** con el mismo contrato
(`disponible()`, `info()`, `responder(prompt, system, timeout, cache)`):

- **`cliente_gemini.py`** (nuevo) — SDK moderno `google.genai`. Modelo
  `gemini-2.5-flash`. Usa `GOOGLE_API_KEY` (o alias `GEMINI_API_KEY`).
- **`cliente_anthropic.py`** (nuevo) — SDK `anthropic`. Modelo
  `claude-haiku-4-5`. Usa `ANTHROPIC_API_KEY`.

Ambos calcan el patrón de `sugerencias_ia*.py`: **importación perezosa** del
SDK (la app arranca aunque falte la librería), carga del `.env` con ruta
absoluta, caché en memoria por `(system, prompt)`, timeout y fallback a `None`
ante cualquier fallo. Tener clientes simétricos hace que `/chat` despache a
cualquiera de los dos sin ramas especiales (un dict `modelo → (cliente,
etiqueta)`).

> Aunque el entregable listaba solo `cliente_gemini.py`, se creó también
> `cliente_anthropic.py` (la opción "o un cliente_anthropic.py si decides
> extraerlo" del brief): deja `/chat` simétrico y testeable sin acoplarse al
> módulo de sugerencias semánticas.

### 5b.1 Backend (`server.py`)

- **`GET /ping_chat`** → `{claude_disponible, gemini_disponible, modelos[]}`.
- **`POST /chat`** → recibe `{mensaje, modelo, historial}`, devuelve
  `{respuesta, modelo_usado, error}`. Despacha al cliente del `modelo`.
  - `system` fijo: *"Eres un asistente para el compilador DiamondLang, un
    lenguaje imperativo en español con tipado estático. Responde de forma
    concisa, en español…"*.
  - **Historial**: se aplanan los últimos **10** mensajes a un transcript
    `Usuario:/Asistente:` + el mensaje nuevo, y se manda como `contents`/`prompt`
    con el `system` aparte. (Decisión: aplanar en vez de pasar la lista
    estructurada, para que Claude y Gemini reciban EXACTAMENTE el mismo prompt
    y el wrapper `responder(prompt, system)` sea idéntico para ambos.)
  - **Modelo sin key** → 200 con `error` claro
    (`"Modelo 'gemini' no disponible: define GOOGLE_API_KEY…"`). Body inválido
    (mensaje vacío / modelo desconocido) → **400**. Errores del SDK capturados
    → `error` no nulo, nunca una excepción al cliente. Timeout 15 s.

### 5b.2 Migración `sugerencias_ia.py` (sintáctico) → Gemini

- Internamente ahora llama a `cliente_gemini.responder(prompt, system=…)` en
  vez de a Anthropic. El **rol** pasó a `SYSTEM_SINTACTICO` (system_instruction)
  y `construir_prompt()` devuelve solo los datos del caso. Se añadió a las
  instrucciones *"máximo 2 frases, sin markdown ni listas"* porque Gemini
  tiende a ser más verboso/estructurado que Claude.
- **Contrato público intacto**: `disponible()`, `info()`,
  `sugerencia_ia(error, codigo_fuente, cache=None)`, `construir_prompt`,
  `limpiar_cache`. Se añadió el parámetro **opcional** `cache=None` (paridad con
  el módulo semántico); `server.py` sigue llamando con 2 argumentos sin cambios.
- `info()` mantiene las claves que lee el frontend (`disponible`, `modelo`,
  `libreria_instalada`) pero `modelo` ahora es **"Gemini Flash"** (+ clave extra
  `proveedor:'google'`, ignorada por el frontend). Así `/ping_ia` sigue con el
  mismo schema y `pingIA()` no necesitó cambios de lógica.
- **`gemini-2.5-flash` y el "thinking":** el cliente fija
  `ThinkingConfig(thinking_budget=0)`. Sin esto, con un `max_output_tokens`
  bajo el modelo podría gastar todo el presupuesto "pensando" y devolver texto
  vacío. Desactivar thinking lo hace rápido y conciso (lo que queremos).

### 5b.3 Frontend del chatbot (`diamondlang.html`)

- **`sendChat()` ahora es `async`** y hace `fetch('/chat')` con
  `{mensaje, modelo, historial}` (los últimos 10, **sin** el mensaje nuevo —
  ese va en `mensaje`). Reemplaza el placeholder de 5a.
- **Indicador "escribiendo…"**: burbuja temporal (`#chat-typing-row`, 3 puntos
  animados) que **no** se persiste en `chatHistory`; se elimina al llegar la
  respuesta.
- **Errores**: si `data.error`, burbuja de asistente discreta
  (`.chat-bubble.chat-err`, cursiva rojiza) con el mensaje.
- **Fallbacks graciosos**:
  - *Red caída* (fetch lanza) → placeholder local + *"(sin conexión al
    servidor — respuesta local)"*.
  - *Sin ninguna key* (`/ping_chat` dice ambos `false`) → **modo placeholder**:
    `sendChat` ni siquiera llama a `/chat`, responde local con un hint para
    configurar las keys. Así se cumple la verificación #5 (sin keys, el chatbot
    sigue "vivo" con los placeholders de 5a).
- **`pingChat()`** al cargar: atenúa (`.chat-model-disabled`, opacity .45,
  `disabled`, tooltip) la pill del modelo sin key, y si el modelo activo quedó
  deshabilitado salta al disponible. `setChatModel()` ignora modelos
  deshabilitados.
- **Modelo congelado al enviar** (heredado de 5a): el badge del mensaje refleja
  el modelo del momento del envío.

### 5b.4 IDs/clases nuevos del frontend

- IDs: `chat-typing-row` (transitorio).
- Clases: `chat-model-disabled`, `chat-bubble.chat-err`, `chat-typing`.
- Badges del toolbar sintáctico: el `<span>` "Claude" cosmético único se
  sustituyó por **dos** badges por toggle — `syn-prov-gemini` ("Gemini", junto a
  *IA sintaxis*) y `syn-prov-claude` ("Claude", junto a *IA semántica*) — porque
  ahora cada toggle usa un proveedor distinto. (El brief permitía cambiarlo
  estáticamente; se hizo per-toggle para no mentir sobre la semántica, que sigue
  en Claude.) Tooltips de los toggles actualizados (sintaxis → "API de Gemini").

### 5b.5 Tests

- **`test_etapa11_chat.py` (nuevo, 10 casos, sin red):** mockea los SDK
  (`cliente_gemini._genai`/`_genai_types` y `cliente_anthropic.Anthropic`).
  Cubre `/chat` claude/gemini canned, gemini no disponible→error,
  `/ping_chat` (claude/gemini/ambos/ninguno), validación de body, e inclusión
  del historial en el prompt; además la migración de `sugerencias_ia.py`
  (no-disponible→None, canned, cache, y `/parsear` con `usar_ia=True` →
  `fuente='ia'` en recursivo y predictivo).
- **`test_etapa9_bonus_ia.py` NO se modificó.** Hallazgo: pese a su nombre,
  ese test cubre la IA **semántica** (`sugerencias_ia_semantica.py`), que sigue
  en Claude. La instrucción del brief ("actualizar etapa9 porque la sintáctica
  ahora es Gemini") partía de que etapa9 cubría la sintáctica; no es el caso. La
  cobertura del cambio de cliente sintáctico se añadió en etapa11 (su sitio
  natural, ya que **no existía** ningún test previo de `sugerencias_ia.py`). Se
  verificó que etapa9 sigue verde sin tocarlo.
- **Tests 1–9 verdes**; suite completa **11/11**.

### 5b.6 Demostración en este entorno (honesto)

- **`ANTHROPIC_API_KEY` real presente; `GOOGLE_API_KEY` ausente.** Por tanto:
  - **Claude EN VIVO**: `POST /chat {modelo:'claude'}` devolvió respuesta real
    de la API (incluida una llamada con historial que entendió "¿Y la Regla 4?"
    en contexto). `/ping_chat` → `claude_disponible:true, gemini_disponible:false`.
  - **Gemini**: no se pudo llamar en vivo (sin key); se verificó por **mock**
    (test b) y se demostró el **camino de error real** en vivo (`modelo:'gemini'`
    → `"…no disponible: define GOOGLE_API_KEY…"`).
- Consecuencia esperada de la migración en este entorno: la **IA sintáctica**
  queda **deshabilitada** (necesita Google key), mientras la **IA semántica**
  sigue activa (Claude). Documentado en README.

### 5b.7 Decisiones / sorpresas

1. **`cliente_anthropic.py` extra** (ver 5b.0): no estaba en la lista del
   entregable pero el brief lo permitía; simetría > minimalismo aquí.
2. **Prompt aplanado** para el historial (5b.1): mismo prompt para ambos
   modelos; el wrapper `responder` no necesita saber de roles.
3. **`thinking_budget=0`** en Gemini (5b.2): sorpresa técnica del 2.5-flash que
   habría devuelto texto vacío con tokens bajos.
4. **Badge per-toggle** (5b.4): la decisión "estática" del brief se refinó a dos
   badges para no etiquetar como "Gemini" algo que sigue siendo Claude.
5. **etapa9 intacto** (5b.5): se priorizó la corrección (no romper un test que
   cubre un módulo no migrado) sobre la letra del brief, documentándolo.
6. **`google-genai` se instaló** en el venv del entorno (red disponible);
   `requirements.txt` lo fija con import perezoso, así que su ausencia no
   rompería el arranque.

---

**Fase 5b cerrada — esperando aprobación explícita del usuario para pasar a Fase 6.**

---

## Fase 6 — Resaltado inline en el editor  *(ejecutada)*

Penúltima fase del rediseño. Cuando el analizador detecta errores con
posición (fila), esas líneas se resaltan **dentro del editor Sintáctico**
(`#ed2` / `#ln2`): fondo rojo suave para errores **sintácticos**, fondo
ámbar para **semánticos**, más un ícono Material Symbol en el gutter junto
al número de línea. El editor de Léxico (`#ed1` / `#ln1`) **no** recibe este
tratamiento (sus errores se reportan distinto) y queda intacto.

### Decisiones técnicas (aprobadas)
- Resaltado **por línea completa** (no el lexema). Rojo = sintáctico, ámbar
  = semántico. Si una línea tiene ambos, el **fondo prioriza el sintáctico**
  (más grave) pero el gutter muestra **ambos íconos**.
- Técnica: **overlay `<div>` detrás del textarea**, sincronizado por scroll.
- Gutter enriquecido con marcadores Material Symbols.

### Estructura del overlay
Nuevo elemento dentro de `.editor-wrap` del pane Sintáctico, **antes** del
textarea en el DOM:

```html
<div class="editor-wrap">
  <div class="line-nums" id="ln2"> … filas .ln-row … </div>
  <div id="ed2-overlay" class="editor-overlay"></div>   <!-- Fase 6 -->
  <textarea id="ed2" …></textarea>
</div>
```

- `.editor-overlay`: `position:absolute; top/right/bottom:0; pointer-events:none;
  overflow:hidden; z-index:1`. Métricas de fuente **idénticas** al textarea
  (`JetBrains Mono`, `0.78rem`, `line-height:1.7`, `padding:12px 0`). El
  `left` se fija **dinámicamente por JS** (= ancho del gutter, `ln.offsetWidth`)
  para alinear las bandas con el texto sin pisar la canaleta.
- Contenido: una pila de `.ovl-line`, una por línea, cada una de alto
  `calc(0.78rem * 1.7)` (exactamente la altura de una línea del textarea).
  - `.ovl-sint` → `background rgba(188,63,60,.16)` + borde izq
    `inset 3px rgba(188,63,60,.85)` (rojo `#bc3f3c` del mockup).
  - `.ovl-sem` → `background rgba(245,189,101,.12)` + borde izq
    `inset 3px rgba(245,189,101,.7)` (ámbar `#f5bd65 ~12%`).
- El textarea pasó a `background:transparent` (antes era `#2B2B2B`; ver
  trampa #4) y `z-index:2`; el gutter a `position:relative; z-index:2` para
  pintar opaco **por encima** del overlay y taparlo bajo la canaleta.

### Estructura del gutter enriquecido
`#ln2` deja de ser texto plano con `<br>` y pasa a una lista de filas:

```html
<div class="ln-row">
  <span class="material-symbols-outlined ln-ic ln-ic-sint">cancel</span>
  <span class="material-symbols-outlined ln-ic ln-ic-sem">warning_amber</span>
  <span class="ln-num">12</span>
</div>
```

- `.ln-row`: `flex; align-items:center; justify-content:flex-end; gap:3px;
  height:calc(0.78rem * 1.7)`. El alto fijo **iguala** la línea del textarea
  (antes el gutter usaba `line-height` con `0.76rem`, ~0.5px más corto por
  línea → derivaba en archivos largos; ahora queda exacto).
- `.ln-num` (número, color muted), `.ln-ic-sint` (rojo `#bc3f3c`),
  `.ln-ic-sem` (ámbar `var(--accent4)`). Línea limpia = solo el número.

### Funciones JS nuevas / modificadas
- **`renderOverlayErrores(erroresSint, erroresSem)`** *(nueva)* — firma:
  recibe los dos arrays de errores. Construye `Set` de filas por tipo
  (semánticos con `fila > 0`), repinta `#ed2-overlay` (una banda por línea,
  sint prioriza sobre sem) y reconstruye `#ln2` con los íconos. Al final
  ajusta `ovl.style.left = ln.offsetWidth` y refleja el scroll actual del
  textarea.
- **`updateLN(edId, lnId)`** *(modificada, misma firma)* — si `lnId === 'ln2'`
  genera la estructura `.ln-row` (números, **sin** íconos = estado limpio);
  si es `'ln1'` mantiene el `"1<br>2<br>…"` clásico. Cero regresión en Léxico.
- **`limpiarSint()`** *(modificada)* — añade `renderOverlayErrores([], [])`
  para vaciar overlay y gutter.
- **`parsear()`** *(modificada)* — al final llama
  `renderOverlayErrores(data.errores||[], data.errores_semanticos||[])`.
- **Listeners de `#ed2`** *(modificados)* — el handler `scroll` ahora también
  sincroniza `ovl.scrollTop`/`ovl.scrollLeft`; el handler `input` limpia el
  overlay (`ovl.innerHTML=''`) además de `updateLN`.

### Trampas técnicas encontradas y cómo se resolvieron
1. **Wrap de líneas largas** — el textarea ya tenía `white-space:pre;
   overflow:auto`, así que cada línea lógica = 1 línea visual. El overlay usa
   `white-space:pre` igual. Sin desincronización por wrap.
2. **Métricas de fuente idénticas** — overlay y textarea comparten
   `font-family/size/line-height/padding-top`. El alto de cada `.ovl-line` y
   `.ln-row` es `calc(0.78rem * 1.7)`, exactamente la línea del textarea.
3. **Scroll sincronizado** — se extendió el listener `scroll` existente para
   empujar `scrollTop`/`scrollLeft` al overlay además del gutter.
4. **Textarea NO era transparente** — el brief asumía `background:transparent`,
   pero `#pane-sintactico textarea` lo sobreescribía a `#2B2B2B`. Se cambió a
   `transparent` (la `.editor-wrap` aporta el fondo oscuro) para que el overlay
   se vea detrás. **Esta fue la corrección clave.**
5. **`pointer-events:none`** en el overlay → no intercepta clicks ni selección;
   el textarea sigue siendo el único elemento interactivo.
6. **Alineación horizontal / z-index** — el overlay abarca toda `.editor-wrap`,
   pero se le fija `left = ancho del gutter` por JS y el gutter se pinta con
   `z-index` superior y fondo opaco, de modo que ninguna banda se cuela bajo la
   canaleta y el borde-acento izquierdo queda justo en el inicio del texto.

### Cuándo se borra el overlay
- **Al editar** (`input` en `#ed2`): al primer cambio del usuario las
  posiciones de error dejan de ser confiables → se vacía el overlay y
  `updateLN` reconstruye el gutter sin íconos.
- **Al limpiar** (`limpiarSint`): `renderOverlayErrores([], [])`.
- **Al re-analizar** (`parsear`): se repinta con las filas nuevas.

### Limitaciones conocidas
- El borde-acento izquierdo de las bandas no se desplaza con el scroll
  **horizontal** (las bandas son full-width; el sync horizontal solo mueve el
  contenido si hay overflow). Es un detalle menor: el tinte de línea sigue
  correcto verticalmente, que es lo que importa.
- Pulsar **Tab** invoca `updateLN` (limpia íconos del gutter) pero no dispara
  `input`, así que las bandas del overlay sobreviven a un Tab aislado. Caso
  borde de bajo impacto; cualquier tecla normal sí limpia todo.
  **→ Resuelto en Fase 7 (tarea C6).**
- No hay scroll-to-error automático (fuera de alcance de la fase).

---

**Fase 6 cerrada y aprobada.**

---

## Fase 7 — Limpieza final  *(ejecutada)*

Última fase del rediseño. **Sin features nuevas, sin refactor.** Cierra las
imperfecciones cosméticas que las fases anteriores marcaron como fuera de su
alcance estricto, y hace la verificación final del proyecto para sustentación.
Principio de la fase: *mínimo cambio para máximo pulido* — cada tarea toca de
una a tres líneas.

### Tareas cosméticas resueltas

| # | Deuda de | Estado | Cambio |
|---|----------|--------|--------|
| **C1** | Fase 3b | hecha | `#s-err` ya no es rojo fijo: era `style="color:var(--tok-err)"` hardcoded. Se quitó el inline-style, se añadió la regla CSS `#pane-lexico #s-err.s-err-active{color:var(--tok-err);}` y `renderStatsLex` hace `errEl.classList.toggle('s-err-active', errores.length>0)`. Con 0 errores el contador queda en color neutro; sólo se pinta rojo cuando hay errores. |
| **C2** | Fase 3c | hecha | Badges numéricos sin corchetes. En `renderErroresSintacticos` y `renderErroresSemanticos` el template pasó de `[${e.indice}]` a `${e.indice}`. El badge circular (CSS `.err-num` / `.sem-num`, `border-radius:9999px`) ya daba la forma; los corchetes sobraban. |
| **C3** | Fase 3c | hecha | Banner de estado con Material Symbols. `renderBannerEstado` pasó de `el.textContent = '✓ …'` (glifos Unicode) a `el.innerHTML = '<span class="material-symbols-outlined">'+ic+'</span>'+esc(txt)`, con `ic` ∈ {`check_circle`, `warning`, `error`, `cancel`} según los 4 estados. El color lo hereda el ícono por `currentColor` de cada variante (`estado-ok/sem/sint/bad`). CSS nuevo: `.estado-analisis .material-symbols-outlined{font-size:18px;}` (el banner ya era `display:flex; gap:8px; align-items:center`, así que ícono y texto quedan alineados y espaciados). |
| **C4** | Fase 3c | hecha | Sugerencias semánticas sin emojis. En `renderErroresSemanticos` los prefijos `✨`/`💡` se reemplazaron por Material Symbols `auto_awesome` (IA) y `lightbulb` (local), tanto en la pill de fuente (`.sem-source.ia`) como en la caja de sugerencia (`.sem-suggestion`). Se añadió CSS de tamaño/alineación para los íconos inline (`.sem-src-ic` 13px, `.sug-ic` 15px, con `vertical-align` y `margin-right`) porque la clase base `.material-symbols-outlined` no fija `font-size` y, sin regla propia, heredaban el tamaño diminuto de la pill (~8px). |
| **C5** | Fase 3a | hecha (variante) | Footer Ln/Col en vivo. El footer `#fs-bar` **no** tenía un span de posición (la decisión de Fase 3a fue no añadirlo); se añadió `<span id="fs-cursor">Ln 1, Col 1</span>` en `.fs-right` y el listener `keyup` de `#ed1`/`#ed2` ahora actualiza `#fs-cursor` además de `#cur1`/`#cur2`. El footer sigue la posición del cursor de la pestaña activa. |
| **C6** | Fase 6 | hecha | Tab aislado borraba el gutter pero dejaba las bandas del overlay. En el handler `keydown` de Tab (que ya llamaba a `updateLN`) se añadió `if(ovl)ovl.innerHTML=''` — exactamente la misma limpieza que hace el listener `input`. Cierra la limitación documentada al final de la Fase 6. |

### Funciones JS modificadas (todas conservan su firma)

| Función / bloque | Cambio | Tarea |
|---|---|---|
| `renderStatsLex(stats, errores)` | +2 líneas: `const errEl=…` y `errEl.classList.toggle('s-err-active', …)` | C1 |
| `renderErroresSintacticos(errores)` | `[${e.indice}]` → `${e.indice}` (1 línea) | C2 |
| `renderErroresSemanticos(errores)` | `[${e.indice}]` → `${e.indice}`; emojis → Material Symbols en pill y sugerencia | C2, C4 |
| `renderBannerEstado(valido, validoSem)` | `let cls,txt` → `let cls,ic,txt`; `textContent` → `innerHTML` con `<span>` icon | C3 |
| Listener `keyup` de `#ed1`/`#ed2` | +1 línea: actualiza `#fs-cursor` | C5 |
| Listener `keydown` (rama Tab) de `#ed2` | +`if(ovl)ovl.innerHTML=''` | C6 |

Cambios de marcado/CSS asociados (no-JS): inline-style quitado en `#s-err`,
nuevas reglas CSS para `.s-err-active`, los íconos del banner y los íconos
inline de la sugerencia semántica, y el nuevo `<span id="fs-cursor">` en el
footer.

### Verificación

- **Tests:** los 11 (`etapa1`–`etapa9`, `etapa8_5`, `etapa11`) corren verdes
  tras los cambios. Fase 7 sólo toca frontend (`diamondlang.html`), así que
  no podía afectarlos; se corrieron igual como red de seguridad.
- **Código muerto:** barrido de variables CSS → **0 sin uso** (`var(--x)`
  referenciado para cada `--x:` definido). **0** funciones JS comentadas.
- **Archivos sueltos:** sólo `diamondlang.html.bak` (red de seguridad,
  estado post-Fase 6). Sin `.tmp`/`.orig`/`~`.

### Nada que rediseñar — deuda futura anotada (no tocada en F7)

- El borde-acento izquierdo de las bandas del overlay no sigue el scroll
  **horizontal** (heredado de Fase 6; impacto mínimo).
- No hay scroll-to-error automático al hacer click en un error.
- El `#fs-cursor` del footer se actualiza en `keyup`; un movimiento de cursor
  hecho **sólo con el mouse** (click) no dispara `keyup`, así que el footer se
  refresca al siguiente tecleo. Los indicadores por-pestaña `#cur1`/`#cur2`
  tienen el mismo comportamiento histórico; se dejó consistente a propósito.

Ninguna de estas afecta la funcionalidad; quedan como mejoras opcionales
post-entrega.

---

## Estado final del proyecto

Cierre de la migración visual completa (Fases 1 → 7). El IDE está
visualmente unificado al estilo IntelliJ cálido y todas las deudas
cosméticas documentadas están saldadas.

### Features funcionales

**Compilador (backend, intacto durante toda la migración):**
- **Análisis léxico** con posiciones (línea/columna) y estadísticas por
  categoría de token.
- **Dos parsers** sobre la misma gramática: **recursivo descendente** y
  **predictivo LL(1)** (con tabla LL(1) generada y conjuntos
  PRIMERO/SIGUIENTE).
- **Recuperación de errores sintácticos** (modo pánico) con reporte de
  token encontrado / esperado / no-terminal.
- **Análisis semántico** (visitor sobre el CST) con **5 reglas**:
  declaración duplicada, uso no declarado, compatibilidad de tipos en
  asignación, condición booleana, y aridad/tipos en llamadas; más
  `TIPO_OPERADOR` transversal con supresión de cascada.
- **Tabla de símbolos** con ámbitos (global + función) y **motor de tipos**
  con promoción `entero → real`.
- **Análisis parcial** (F.11): con errores sintácticos, analiza las zonas
  limpias del árbol y salta sólo las sentencias rotas.

**Bonus IA (aditivo, opcional, dos proveedores):**
- Sugerencias **sintácticas** con **Gemini Flash** (`GOOGLE_API_KEY`).
- Sugerencias **semánticas** con **Claude Haiku** (`ANTHROPIC_API_KEY`).
- **Chatbot** asistente modal con **selector de modelo** (Claude / Gemini),
  que atenúa la pill del modelo sin API key.
- Todo degrada con gracia: sin keys, sugerencias locales y chatbot con
  respuestas locales de prueba.

**Frontend / IDE visual (resultado de la migración):**
- Paleta IntelliJ Darcula cálida unificada vía tokens CSS en las **6
  pestañas** (Léxico, Sintáctico, Tabla LL(1), PRIMERO/SIGUIENTE, + chrome).
- **Resaltado inline** de líneas con error dentro del editor Sintáctico
  (overlay + gutter con íconos Material Symbols; rojo sintáctico, ámbar
  semántico).
- **Selector de ejemplos** semánticos por regla (carga `ejemplos_semanticos/`).
- Banner de estado combinado, paneles de errores sintácticos/semánticos,
  tabla de símbolos, traza de pila, mini-árbol SVG migrado.
- Resaltado de token al hacer click en un error; footer status-bar con
  posición de cursor viva (C5).
- Íconos Material Symbols coherentes en toda la app (chrome, botones,
  banners, sugerencias).

### Archivos clave creados durante la migración visual

| Archivo | Rol |
|---|---|
| `cliente_gemini.py` | Cliente Gemini Flash (Fase 5b): IA sintáctica + chatbot Gemini, import perezoso. |
| `cliente_anthropic.py` | Cliente Claude Haiku para el chatbot (`/chat`). |
| `test_etapa11_chat.py` | Tests del chatbot (`/chat`, `/ping_chat`) y de la migración de IA sintáctica a Gemini (SDK mockeado). |
| `MIGRACION_VISUAL.md` | Este documento: bitácora completa de las 11 secciones de la migración. |
| `diamondlang.html.bak` | Red de seguridad: backup del HTML en estado post-Fase 6. |

(`sugerencias_ia.py` y `sugerencias_ia_semantica.py` son de la Entrega 4
previa; en Fase 5b `sugerencias_ia.py` migró de Claude a Gemini vía
`cliente_gemini.py`.)

### Tests existentes y cobertura

Los suites son ejecutables directos (sin pytest ni red); cada uno ejercita
**ambos parsers** y verifica número exacto de errores, regla, posición y
lexema.

| Test | Cobertura |
|---|---|
| `test_etapa1_posiciones.py` | Posición línea/columna en el CST |
| `test_etapa2_infraestructura.py` | `TablaSimbolos` + helpers de `arbol.py` |
| `test_etapa3_reglas_1_2.py` | `DECL_DUPLICADA`, `USO_NO_DECLARADO` |
| `test_etapa4_tipos.py` | Motor de tipos (`compatible`, `unificar`, inferencia) |
| `test_etapa5_regla_3.py` | `TIPO_ASIGNACION`, `TIPO_VOID_EN_VARIABLE` |
| `test_etapa6_regla_4.py` | `TIPO_CONDICION` |
| `test_etapa7_regla_5.py` | `LLAMADA_ARIDAD` / `_TIPO` / `_NO_FUNCION` |
| `test_etapa8_endpoint.py` | `/parsear` con claves semánticas |
| `test_etapa8_5_analisis_parcial.py` | Análisis parcial (F.11) |
| `test_etapa9_bonus_ia.py` | Bonus IA semántica (Claude, mockeado) |
| `test_etapa11_chat.py` | Chatbot + IA sintáctica Gemini (mockeado) |
| `test_etapa12_sdt.py` | Traducción a Julia (SDT) + endpoint `/traducir` |

> Nota: `test_etapa11_chat.py` fue **regenerado** a partir del código real (la
> copia original se había perdido; el respaldo disponible era anterior a la Fase
> 5b). Cubre la misma funcionalidad con los SDK mockeados.

### Métricas de la migración

- **`diamondlang.html`:** 2 138 líneas / ~120 KB al cierre de Fase 7.
- **Backup `diamondlang.html.bak`** (estado post-Fase 6): 2 125 líneas /
  ~119 KB. Fase 7 añadió **+13 líneas netas** (CSS de íconos, span del
  footer, una clase y seis ediciones de una a tres líneas). *Nota:* no se
  conserva un backup pre-migración (el HTML no está versionado en git), así
  que la única referencia disponible es el backup post-Fase 6.
- **Hooks preservados:** ~73 IDs únicos en el marcado y **44** `getElementById`
  distintos en el JS — el contrato JS↔DOM se mantuvo intacto durante las 7
  fases (principio rector de la migración: cambiar el *valor* visual, nunca
  los *nombres* hook ni el contrato con el backend).
- **Backend:** **0 líneas** modificadas en `server.py`, lexer, parsers,
  semántico ni módulos del compilador a lo largo de toda la migración.

---

## Mejora — Paneles colapsables  *(post-Fase 7)*

Tarea independiente posterior al cierre de la migración. Cada panel de las
**4 pestañas** recibe un **chevron** en su cabecera que colapsa/expande el
cuerpo del panel (solo la barra de cabecera queda visible). Es **puramente
visual**: ortogonal a la lógica `.active` de los paneles dinámicos. Sin resize
por drag, sin maximizar, sin persistencia (al recargar, todo expandido).

### Sorpresa clave: las clases NO son uniformes

El plan asumía `.panel`/`.panel-hdr` en todas partes. **No es así.** El
inventario real de cabeceras por pestaña:

| Pestaña | Paneles (cabecera real) |
|---|---|
| **Léxico** (`#pane-lexico`) | Editor, Tokens, Tabla de símbolos → **`.lex-hdr`** (×3) |
| **Sintáctico** (`#pane-sintactico`) | Editor, Árbol, Traza → **`.syn-hdr`** (×3); Errores sint. → **`.errores-hdr`**; Errores sem. → **`.sem-hdr`**; Tabla símbolos → **`.simbolos-hdr`** |
| **Tabla LL(1)** (`#pane-tabla`) | Panel único → **`.panel-hdr`** |
| **PRIMERO/SIGUIENTE** (`#pane-sets`) | PRIMERO, SIGUIENTE → **`.panel-hdr`** (×2) |

**12 cabeceras** en total reciben chevron. El selector usado:
`.lex-hdr, .syn-hdr, .panel-hdr, .errores-hdr, .sem-hdr, .simbolos-hdr`.

### Implementación

- **JS** — `setupCollapsibles()` (llamada una vez en el arranque, junto a
  `ping`, `cargarMenu…`): por cada cabecera añade un `<span>` Material Symbol
  `expand_more`, marca la cabecera con `.collapsible-hdr`, y engancha un click
  que hace `panel.classList.toggle('panel-collapsed')` sobre `hdr.parentElement`.
  El click se ignora si cae en un control interactivo
  (`button, input, select, textarea, a`). Guard `dataset.collapsibleReady`
  para idempotencia.
- **CSS** — el colapso se basa **solo en `.panel-collapsed`** (no en una clase
  marcador del panel), para que **sobreviva al re-render** de los paneles
  dinámicos que reescriben su `className`:
  ```css
  .panel-collapsed > :not(.collapsible-hdr):not(.errores-panel):not(.sem-panel):not(.simbolos-panel){display:none !important;}
  .panel-collapsed > .collapsible-hdr .panel-chevron{transform:rotate(-90deg);}
  ```
  El chevron `expand_more` (▼ expandido) rota a ► al colapsar.

### Decisiones / edge cases verificados

1. **Paneles dinámicos ortogonales.** `.errores-panel`/`.sem-panel`/
   `.simbolos-panel` conservan su lógica `.active` (mostrar/ocultar según haya
   errores). El colapso solo oculta su *cuerpo* (la lista), no la cabecera. Si
   el panel está oculto (sin `.active`), el chevron tampoco se ve.
2. **`!important` necesario.** Los cuerpos como `#stats-lex` usan `display`
   inline controlado por JS, y `.errores-panel.active` tiene alta
   especificidad; sin `!important` el colapso no ganaría.
3. **Árbol con paneles anidados.** Los paneles de errores están *dentro* del
   `.syn-panel` del árbol. La exclusión `:not(.errores-panel):not(.sem-panel):not(.simbolos-panel)`
   hace que colapsar "Árbol sintáctico" oculte **solo el árbol** (y banner/logs),
   dejando los paneles de errores intactos con su propio chevron.
4. **Click en controles.** El botón "Cargar" de Tabla LL(1) y los selects no
   colapsan (exclusión por `closest`). Contadores (`#tok-count`, `#cur1/2`) y el
   título sí colapsan (son decoración).
5. **Chevron a la derecha.** `margin-left:auto` en cabeceras flex. En las dos
   cabeceras con pista "Click para resaltar" (que ya usa `margin-left:auto`) el
   chevron y la pista comparten el lado derecho — diferencia cosmética menor,
   aceptada.

Verificado con simulación DOM de la función real (14 checks: chevron único por
cabecera, toggle por click, exclusión de botones, colapso independiente del
panel anidado, idempotencia) y tests 1–9 + 11 verdes.

---

# Fase C — Pestaña Traducción (SDT → Julia)

Quinta pestaña del frontend (`⑤ Traducción`). Muestra el código Julia
generado por la fase SDT (Fase B, endpoint `POST /traducir`) cuando el
análisis es válido. **Disparo automático** desde la pestaña Sintáctico: no
hay botón manual de "traducir". **Sin syntax highlighting**: el Julia se
muestra monoespaciado (JetBrains Mono) con la paleta IDE neutral.
**Side-by-side**: DiamondLang fuente a la izquierda, Julia generado a la
derecha.

## Estructura del nuevo pane (`#pane-traduccion`)

```
#pane-traduccion  (padding 16px, flex-column; oculto salvo .active)
├── #tr-empty  .tr-empty      ← estado vacío explicativo (ícono translate + texto)
└── #tr-content .tr-content   ← card IDE (#3C3F41 / borde #323232), display:none por defecto
    ├── #tr-header .panel-hdr .tr-header
    │     ├── «● Traducción a Julia»
    │     └── #tr-meta          ← "generada el <fecha local>"
    ├── .controls .tr-controls
    │     ├── #tr-btn-download  .btn .btn-primary  → descargarJulia()
    │     ├── #tr-btn-copy      .btn .btn-ghost    → copiarJulia()
    │     └── #tr-stats         ← "N líneas · N funciones"
    └── .grid-2 (1fr 1fr)
          ├── .tr-code-panel → .panel-hdr .tr-code-hdr + <pre> #tr-src-code  (DiamondLang)
          └── .tr-code-panel → .panel-hdr .tr-code-hdr + <pre> #tr-jl-code   (Julia)
```

Todos los IDs y clases nuevos llevan prefijo `tr-` para no colisionar con
los 49 IDs / 78 clases-hook previos. El `<pre> .tr-code-body` usa
`white-space:pre` (sin wrap), `overflow:auto`, fondo `#2B2B2B` (ide-bg),
`line-height:1.7`. Reutiliza `.panel-hdr` y `.pdot` globales. El toast
`.tr-toast` es global (anclado al `<body>`, `position:fixed`).

## Funciones JS nuevas (bloque `// ── PESTAÑA TRADUCCIÓN (Fase C) ──`)

| Función | Propósito |
|---|---|
| `lanzarTraduccion(codigoFuente, metodo)` | `async`. Llama a `/traducir`; si `data.ok`, guarda `{julia, fuente, fecha}` en `traduccionActual` y `renderTraduccion()`; si no (o error de red), `null` + `renderTraduccionVacio()`. |
| `renderTraduccion()` | Pinta el side-by-side, el `#tr-meta` (`fecha.toLocaleString()`) y `#tr-stats` (líneas no vacías + `^function ` del Julia). |
| `renderTraduccionVacio()` | Muestra `#tr-empty`, oculta `#tr-content`. |
| `descargarJulia()` | `Blob` `text/x-julia` → descarga `programa.jl`. |
| `copiarJulia()` | `async`. `navigator.clipboard.writeText` + toast. |
| `mostrarToast(mensaje)` | Crea/reutiliza `#tr-toast`, lo muestra 2 s. |

Estado global: `let traduccionActual = null; // {julia, fuente, fecha} | null`.

## Modificaciones a funciones existentes (las dos únicas)

1. **`parsear()`** — tras `renderBannerEstado(...)`:
   ```js
   if (data.valido && data.valido_semantico) lanzarTraduccion(codigo, metodo);
   else { traduccionActual = null; renderTraduccionVacio(); }
   ```
   La traducción solo se dispara con análisis válido (sintáctico **y**
   semántico). El SDT del backend además vuelve a validar las 3 fases, así
   que la guardia es defensa en profundidad.

2. **`limpiarSint()`** — al final: `traduccionActual = null; renderTraduccionVacio();`
   para que limpiar el editor descarte la traducción.

3. **`switchTab()`** — se extiende el array de nombres a
   `['lexico','sintactico','tabla','sets','traduccion']` (cambio mecánico,
   ningún caso especial).

## Edge cases manejados

- **Programa con error sintáctico/semántico** → `parsear()` no dispara la
  traducción; pestaña en estado vacío. (Verificado: `parentesis_sin_cerrar.dml`
  → `fase_fallida=sintactica`; `05_tipo_asignacion_decl.dml` → `fase_fallida=semantica`.)
- **Editor vacío** → `parsear()` retorna temprano; `lanzarTraduccion` además
  ignora `codigo` en blanco.
- **Limpiar editor** → traducción descartada, vuelve al vacío.
- **Re-análisis** → `traduccionActual` se sobrescribe y la pestaña se
  repinta con el nuevo resultado (o vacío si pasó a inválido).
- **Servidor offline / error de red** → `catch` deja la pestaña vacía sin
  romper el resto del análisis.
- **Portapapeles bloqueado** (sin permiso/HTTP) → toast `✗ Error al copiar`.

Verificado: endpoint `/traducir` real (factorial → Julia correcto; dos
programas con error → `ok:false`), `node --check` del script completo, y los
12 archivos de test verdes (etapas 1–9 + 11 + 12).

---

## Fase D — Bonus IA validación (Modalidad C)

Capa **opcional** sobre la pestaña Traducción: envía el código Julia ya
generado por el SDT a **Claude Haiku** (`claude-haiku-4-5`) para validarlo y
sugerir optimizaciones idiomáticas. Es el bonus de la Entrega Final
(*Bonus Opcional*, Modalidad C: validación + optimización). El compilador
sigue traduciendo a Julia sin la IA: si no hay `ANTHROPIC_API_KEY`, el botón
queda deshabilitado con tooltip y nada más cambia.

### Cambios por archivo

| Archivo | Cambio |
|---|---|
| `server.py` | Endpoint `POST /validar_julia`; constantes `SYSTEM_VALIDAR_JULIA` y `_prompt_validar_julia()` (prompt literal, visible para sustentación); `_parsear_respuesta_julia()` (regex ```` ```json ```` + `json.loads`, con fallback a `raw`). **No** toca `/traducir` ni el SDT. |
| `diamondlang.html` | Panel `#tr-ia-panel` en `#pane-traduccion` (tras el side-by-side); JS `solicitarAnalisisIA()` / `renderAnalisisIA()` / `mostrarErrorIA()` / `resetPanelIA()`; CSS scopeado `.tr-ia-*`; `pingChat()` deshabilita `#tr-ia-btn` con tooltip si Claude no está disponible. |
| `test_etapa13_validacion_ia.py` | **Nuevo.** Endpoint con `cliente_anthropic` mockeado: JSON válido, JSON sin cercas, texto sin JSON (→`raw`), IA no disponible (`ok=false`), sin `julia` (400), respuesta `None`/timeout. |
| `README_ENTREGA4.md` | Sección "Bonus IA — Modalidad C" con la modalidad, el prompt literal y el ejemplo completo (DiamondLang → Julia → respuesta real de Claude). |
| `diamondlang.html.bak` | Backup en estado post-Fase C (sin el panel IA). |

### Separación de responsabilidades (requisito del enunciado)

La IA es **una capa adicional**: `/traducir` y `sdt.py` quedan sin tocar; la
pestaña Traducción muestra DiamondLang ↔ Julia, descarga y copia con
independencia de si la IA está disponible. Solo el panel "Análisis con IA"
depende de Anthropic. Tres modos degradados sin error: sin API key
(`ok=false` + botón deshabilitado), respuesta sin JSON (`ok=true` + `raw`), y
timeout/`None` (`ok=false` con mensaje legible).

### Material Symbols nuevos

`auto_awesome` (cabecera panel), `auto_fix_high` (botón), `verified`
(Validación), `error_outline` (Problemas), `tips_and_updates`
(Optimizaciones). Todos de la misma fuente ya cargada, renderizan como ícono.

### Verificación

- **13/13 archivos de test verdes** (etapas 1–9 + 11 + 12 + 13).
  `test_etapa13_validacion_ia.py`: 22 checks, 0 fallos.
- **Demo real ejecutada** (con `ANTHROPIC_API_KEY`): factorial DiamondLang →
  Julia → respuesta real de Claude Haiku, estructurada en validación +
  problemas + optimizaciones. Documentada en `README_ENTREGA4.md`.

---

**FIN DEL DOCUMENTO — migración visual (Fases 1 → 7) + mejoras posteriores + Fase C (pestaña Traducción) + Fase D (bonus IA validación).**
