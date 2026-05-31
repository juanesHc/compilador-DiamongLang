---
name: Technical Precision
colors:
  surface: '#0b1326'
  surface-dim: '#0b1326'
  surface-bright: '#31394d'
  surface-container-lowest: '#060e20'
  surface-container-low: '#131b2e'
  surface-container: '#171f33'
  surface-container-high: '#222a3d'
  surface-container-highest: '#2d3449'
  on-surface: '#dae2fd'
  on-surface-variant: '#c5c6cd'
  inverse-surface: '#dae2fd'
  inverse-on-surface: '#283044'
  outline: '#8f9097'
  outline-variant: '#45474c'
  surface-tint: '#bcc7de'
  primary: '#bcc7de'
  on-primary: '#263143'
  primary-container: '#1e293b'
  on-primary-container: '#8590a6'
  inverse-primary: '#545f73'
  secondary: '#6bd8cb'
  on-secondary: '#003732'
  secondary-container: '#29a195'
  on-secondary-container: '#00302b'
  tertiary: '#4edea3'
  on-tertiary: '#003824'
  tertiary-container: '#00301e'
  on-tertiary-container: '#00a472'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d8e3fb'
  primary-fixed-dim: '#bcc7de'
  on-primary-fixed: '#111c2d'
  on-primary-fixed-variant: '#3c475a'
  secondary-fixed: '#89f5e7'
  secondary-fixed-dim: '#6bd8cb'
  on-secondary-fixed: '#00201d'
  on-secondary-fixed-variant: '#005049'
  tertiary-fixed: '#6ffbbe'
  tertiary-fixed-dim: '#4edea3'
  on-tertiary-fixed: '#002113'
  on-tertiary-fixed-variant: '#005236'
  background: '#0b1326'
  on-background: '#dae2fd'
  surface-variant: '#2d3449'
typography:
  headline-lg:
    fontFamily: Geist
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Geist
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  body-md:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Geist
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  code-lg:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
  label-caps:
    fontFamily: Geist
    fontSize: 11px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  panel-gap: 1px
  container-padding: 1rem
  element-gap: 0.5rem
  sidebar-width: 260px
  toolbar-height: 48px
---

## Brand & Style
The design system is engineered for a high-performance IDE environment, prioritizing focus, structural clarity, and technical authority. It targets developers and students who require a distraction-free space for complex logic. 

The aesthetic sits at the intersection of **Corporate Modern** and **Minimalism**, drawing inspiration from high-end productivity tools. The visual language is defined by a "Diamond" motif—incorporating geometric precision, sharp execution, and a multi-faceted approach to information density. The mood is serious and structured, utilizing a "Dark/Dimmed" default state to reduce eye strain during long coding sessions, while maintaining high-contrast ratios for critical syntax feedback.

## Colors
The palette is rooted in deep, cool neutrals to provide a stable foundation for a multi-panel interface. 

- **Foundation:** The main UI chrome utilizes a deep Navy (`#0F172A`), while the primary workspace (Editor) is slightly lifted to a Slate Charcoal (`#1E293B`) to provide depth without harsh contrast.
- **Action & Info:** Teal (`#0D9488`) serves as the primary action color and for informational markers like the Symbol Table.
- **Status Semantic:** A strict traffic-light system is used for compiler feedback: Emerald for success, Amber for warnings/semantic issues, and Rose for syntax errors.
- **Borders:** Subtle Slate borders (`#334155`) define the geometry of the IDE without adding visual noise.

## Typography
The typography system uses a dual-font approach to distinguish between navigation and content.

- **UI Shell:** **Geist** is used for all menus, panel headers, and buttons. Its tight apertures and geometric construction mirror the "Diamond" theme’s precision.
- **Editor & Data:** **JetBrains Mono** is reserved for the code editor, terminal output, and symbol tables. It provides the necessary rhythmic spacing required for debugging and reading logic.
- **Hierarchy:** Use `label-caps` for panel titles (e.g., "EXPLORER", "DEBUG CONSOLE") to create a clear structural distinction from content.

## Layout & Spacing
The layout follows a **Fixed Grid** philosophy typical of IDEs, maximizing the utility of every pixel.

- **Panel Management:** The UI is divided into four primary zones: Sidebar (Left), Editor (Center), Console/Terminal (Bottom), and Inspector (Right). 
- **Gaps:** Use a 1px "border-gap" strategy for panel separation to create a seamless, monolithic look. 
- **Rhythm:** An 8px base unit governs all internal padding. 
- **Responsive Behavior:** On smaller viewports, the Sidebar and Inspector collapse into icon-only rails, while the Editor retains priority. 
- **The Diamond Grid:** Background textures for empty states or splash screens should utilize a subtle 45-degree dot grid or interlocking diamond outlines at 5% opacity.

## Elevation & Depth
This design system avoids traditional shadows in favor of **Tonal Layers** and **Crisp Outlines**.

- **Surface Tiers:** 
  - Level 0 (Base): `#0F172A` (Sidebar/Background)
  - Level 1 (Workspace): `#1E293B` (Editor/Main Panels)
  - Level 2 (Floating): `#1E293B` with a `#334155` 1px border (Modals/Popovers)
- **Active State:** Selected tabs or active line highlights in the editor should use a low-opacity Teal tint (`#0D94881A`) rather than a heavy shadow.
- **Depth:** Use 1px solid borders for all panel divisions to reinforce the "structured" and "technical" feel.

## Shapes
The shape language balances professional rigidity with modern approachability.

- **Corners:** A base radius of `0.5rem` (8px) is applied to buttons, input fields, and main containers. 
- **Tabs:** Top-level workspace tabs use "Soft" top corners (4px) to maintain a connection to the panel below.
- **Diamond Accents:** Checkboxes and status indicators may use a diamond shape (a square rotated 45 degrees) instead of standard circles to reinforce the brand identity.

## Components
- **Buttons:** Primary buttons use a solid Teal fill with white text. Secondary buttons use a Slate border with no fill.
- **Editor Tabs:** Active tabs feature a 2px Teal bottom border. Inactive tabs are semi-transparent.
- **Input Fields:** Use the Slate border (`#334155`) with a slightly darker background. On focus, the border transitions to Teal.
- **Status Chips:** Use high-saturation background tints with white text for errors (Rose) and successes (Emerald).
- **Collapsible Panels:** Headers should feature a chevron icon and use the `label-caps` type style. The header background should be slightly lighter than the panel content to denote interactivity.
- **Symbol Table:** A dense, striped list view using `code-sm` typography for high information density.