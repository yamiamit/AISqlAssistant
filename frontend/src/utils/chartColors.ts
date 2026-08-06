// Validated categorical palette (fixed order — never cycled per-series identity,
// only reused round-robin here because pie slices in this app are always a
// small, capped cardinality). Light/dark steps from the shared dataviz palette.
export const CATEGORICAL_LIGHT = [
  "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948",
];
export const CATEGORICAL_DARK = [
  "#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767",
];

export const SINGLE_SERIES = { light: "#2a78d6", dark: "#3987e5" };
export const GRID_LINE = { light: "#e1e0d9", dark: "#2c2c2a" };
export const AXIS_INK = { light: "#898781", dark: "#898781" };

export function getCategoricalPalette(isDark: boolean) {
  return isDark ? CATEGORICAL_DARK : CATEGORICAL_LIGHT;
}
