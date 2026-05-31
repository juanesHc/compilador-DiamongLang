---
name: Darcula Pro
colors:
  surface: '#17130d'
  surface-dim: '#17130d'
  surface-bright: '#3e3831'
  surface-container-lowest: '#120e08'
  surface-container-low: '#1f1b15'
  surface-container: '#241f19'
  surface-container-high: '#2e2923'
  surface-container-highest: '#39342d'
  on-surface: '#ebe1d7'
  on-surface-variant: '#d3c4b2'
  inverse-surface: '#ebe1d7'
  inverse-on-surface: '#353029'
  outline: '#9c8f7e'
  outline-variant: '#4f4537'
  surface-tint: '#f5bd65'
  primary: '#ffe9cc'
  on-primary: '#442c00'
  primary-container: '#ffc66d'
  on-primary-container: '#785100'
  inverse-primary: '#805600'
  secondary: '#9dccf2'
  on-secondary: '#00344e'
  secondary-container: '#174d6e'
  on-secondary-container: '#8fbee3'
  tertiary: '#cbf2ff'
  on-tertiary: '#003641'
  tertiary-container: '#84dcf5'
  on-tertiary-container: '#006173'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffddaf'
  primary-fixed-dim: '#f5bd65'
  on-primary-fixed: '#281800'
  on-primary-fixed-variant: '#614000'
  secondary-fixed: '#cae6ff'
  secondary-fixed-dim: '#9dccf2'
  on-secondary-fixed: '#001e30'
  on-secondary-fixed-variant: '#144b6b'
  tertiary-fixed: '#afecff'
  tertiary-fixed-dim: '#7bd3ec'
  on-tertiary-fixed: '#001f26'
  on-tertiary-fixed-variant: '#004e5d'
  background: '#17130d'
  on-background: '#ebe1d7'
  surface-variant: '#39342d'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
  code-md:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
  label-caps:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  gutter: 1px
  margin-sm: 8px
  margin-md: 16px
  panel-padding: 12px
---

## Brand & Style

This design system is engineered for deep focus, technical precision, and long-form cognitive tasks. Inspired by industry-standard integrated development environments, it prioritizes functional clarity over decorative flair. The aesthetic is rooted in **Corporate Minimalism** with a **Technical** edge, utilizing a low-contrast dark palette to reduce eye strain during extended sessions.

The target audience consists of software engineers, data scientists, and power users who require a predictable, stable, and unobtrusive interface. The emotional response should be one of "controlled efficiency"—a UI that recedes into the background, allowing the user's content and code to take center stage.

## Colors

The palette is strictly dark-mode, utilizing a range of charcoals and deep greys to create a hierarchical structure through tonal shifts rather than vibrant saturation. 

- **Primary Accent (#FFC66D):** A warm, high-visibility orange-yellow used sparingly for active states, primary actions, and critical focus indicators.
- **Surface Hierarchy:** The deepest shade (#2B2B2B) serves as the primary workspace background. Panels and toolbars use a slightly lighter grey (#3C3F41) to create visual separation.
- **Semantic Logic:** Success, Error, and Warning colors are desaturated to maintain the low-contrast philosophy, ensuring they communicate status without breaking the user's flow.

## Typography

The typography system differentiates between "UI Context" and "Data Context." 

- **Inter** is used for all navigational elements, menus, labels, and settings. It provides excellent legibility at the small scale required for dense, professional applications.
- **JetBrains Mono** is reserved for code blocks, terminal outputs, and data-heavy tables where character alignment and distinction (e.g., `0` vs `O`) are paramount.
- **Scale:** Sizes are intentionally compact (primarily 12px-13px) to maximize information density.

## Layout & Spacing

The layout follows a **Fixed-Panel Grid** model, common in IDEs. Content is divided into collapsible sidebars, bottom consoles, and a central editor area.

- **4px Spacing System:** All margins and paddings are multiples of 4px to maintain a tight, mathematical rhythm.
- **Thin Borders:** Layout sections are separated by 1px solid borders (#323232) rather than large gaps.
- **Density:** High information density is encouraged. Padding within lists and trees should be minimal (4px-8px) to allow for deep nested structures.

## Elevation & Depth

This design system avoids traditional drop shadows and physical lighting metaphors. Depth is communicated through **Tonal Layering**:

- **Level 0 (Main Workspace):** #2B2B2B (The furthest "back").
- **Level 1 (Panels & Toolbars):** #3C3F41 (Moves "forward").
- **Level 2 (Popovers & Context Menus):** #313335 (The "highest" layer, often paired with a 1px border of #4E5254 for definition).

When a shadow is strictly necessary for a floating modal, use a sharp, 4px blur with 40% opacity and no offset, ensuring it feels integrated rather than floating high above the surface.

## Shapes

The shape language is rigid and disciplined. All interactive elements use a **4px corner radius** (Soft). 

- **Standard Elements:** Buttons, inputs, and cards use the 0.25rem (4px) radius.
- **Container Elements:** Large panels and workspace areas should remain sharp (0px) at the screen edges to maximize screen real estate.
- **Tabs:** Active tabs use a squared-off bottom to physically connect with the panel they represent.

## Components

- **Buttons:** Primary buttons use a solid #FFC66D background with dark text. Secondary buttons use a ghost style with a #4E5254 border and #A9B7C6 text.
- **Input Fields:** Backgrounds should be darker than the surrounding panel (#2B2B2B). On focus, the border changes to the primary accent (#FFC66D) with no outer glow.
- **Lists & Trees:** Use #4E5254 for the hover state and #323232 for the selected state. The "active" indicator is a 2px vertical line of #FFC66D on the left edge.
- **Chips/Tags:** Small, rectangular with a 2px radius. Use #313335 background with a subtle border.
- **Tooltips:** Use the Level 2 surface (#313335) with #A9B7C6 text; no delay on hover for a responsive, technical feel.
- **Scrollbars:** Non-intrusive, slim tracks with #4E5254 thumbs that only brighten on hover.