export const spacing = {
  none: 0,
  '2xs': 2,
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  '2xl': 24,
  '3xl': 32,
  '4xl': 40,
  '5xl': 48,
  '6xl': 64,
} as const;

/**
 * Border radius — paridade com a vitrine web:
 *   - sm (8)  → botões e chips (`btn-primary`, `loja.css:79`)
 *   - md (10) → inputs e search bar (`loja-search-form`, `loja.css:137`)
 *   - lg (14) → cards e blocos de seção (`loja-section-block`, `loja.css:175`)
 *   - xl (18) → bottom sheets (extensão suave)
 *   - 2xl (22) → modais cheios
 *   - full → pílulas (chips arredondados, badges)
 */
export const borderRadius = {
  none: 0,
  sm: 8,
  md: 10,
  lg: 14,
  xl: 18,
  '2xl': 22,
  full: 999,
} as const;

export const iconSize = {
  xs: 16,
  sm: 20,
  md: 24,
  lg: 28,
  xl: 32,
  '2xl': 40,
  '3xl': 48,
} as const;

export const hitSlop = {
  top: 8,
  bottom: 8,
  left: 8,
  right: 8,
} as const;

/**
 * Focus-ring acessível — paridade com `loja-header *:focus-visible`
 * (`loja.css:111-113`: `outline: 2px solid #C47A44; outline-offset: 2px`).
 * Cor real é resolvida via `colors.focusRing` no theme.
 */
export const focusRing = {
  width: 2,
  offset: 2,
} as const;

export type SpacingKey = keyof typeof spacing;
