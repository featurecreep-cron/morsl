export interface ThemeEntry {
  label: string
  accentColor: string
  mode: 'dark' | 'light'
  family: string
}

export const THEME_REGISTRY: Record<string, ThemeEntry> = {
  honey: { label: 'Honey', accentColor: '#d4a847', mode: 'dark', family: 'material' },
  espresso: { label: 'Espresso', accentColor: '#7ec8e3', mode: 'dark', family: 'glass' },
  cobalt: { label: 'Cobalt', accentColor: '#2a9fd6', mode: 'dark', family: 'glass' },
  'cast-iron': { label: 'Cast Iron', accentColor: '#7a8b9a', mode: 'dark', family: 'material' },
  ember: { label: 'Ember', accentColor: '#e07840', mode: 'dark', family: 'material' },
  moss: { label: 'Moss', accentColor: '#4db866', mode: 'dark', family: 'glass' },
  porcelain: { label: 'Porcelain', accentColor: '#4a90d9', mode: 'light', family: 'structured' },
  sage: { label: 'Sage', accentColor: '#6b8f71', mode: 'light', family: 'soft' },
  rhubarb: { label: 'Rhubarb', accentColor: '#c4717a', mode: 'light', family: 'soft' },
  fig: { label: 'Fig', accentColor: '#8b7ec8', mode: 'light', family: 'soft' },
  'sea-salt': { label: 'Sea Salt', accentColor: '#2d7d9a', mode: 'light', family: 'glass' },
  sand: { label: 'Sand', accentColor: '#a08060', mode: 'light', family: 'soft' },
  terracotta: { label: 'Terracotta', accentColor: '#c4704b', mode: 'light', family: 'structured' },
  pewter: { label: 'Pewter', accentColor: '#5a6577', mode: 'light', family: 'structured' },
  paprika: { label: 'Paprika', accentColor: '#c86830', mode: 'light', family: 'structured' },
  basil: { label: 'Basil', accentColor: '#3d7a5f', mode: 'light', family: 'soft' },
}
