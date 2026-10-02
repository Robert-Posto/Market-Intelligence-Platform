import { theme, type ThemeConfig } from 'antd'

/**
 * Tema MIP peste Ant Design: aceeași paletă ca aplicația veche (fildeș cald +
 * vișiniu), cu varianta întunecată după setarea sistemului, cum făcea și
 * `prefers-color-scheme` din CSS-ul vechi. Culorile stau și ca variabile CSS
 * în global.css, pentru elementele care nu sunt componente AntD.
 */
const LUMINOS = {
  bg: '#f5f1ec', surface: '#fffdfa', ink: '#2a1f22', muted: '#6e615d', line: '#e3dad0', line2: '#d6cabd',
  warn: '#98550b', ok: '#2b7044', accent: '#7a1e2c', accentTint: '#f5e8e6', onAccent: '#fffdfa',
}
const INTUNECAT = {
  bg: '#1b1517', surface: '#251d1f', ink: '#efe6e2', muted: '#b4a5a0', line: '#3a2e30', line2: '#4a3b3d',
  warn: '#e3a95a', ok: '#7fcb97', accent: '#e7a3ab', accentTint: '#3b2428', onAccent: '#2a1216',
}

export function temaMip(intunecat: boolean): ThemeConfig {
  const c = intunecat ? INTUNECAT : LUMINOS
  return {
    algorithm: intunecat ? theme.darkAlgorithm : theme.defaultAlgorithm,
    token: {
      colorPrimary: c.accent,
      colorInfo: c.accent,
      colorLink: c.accent,
      colorSuccess: c.ok,
      colorWarning: c.warn,
      colorText: c.ink,
      colorTextSecondary: c.muted,
      colorTextTertiary: c.muted,
      colorBgLayout: c.bg,
      colorBgContainer: c.surface,
      colorBgElevated: c.surface,
      colorBorder: c.line2,
      colorBorderSecondary: c.line,
      colorTextLightSolid: c.onAccent,
      borderRadius: 8,
      fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
      fontFamilyCode: "'IBM Plex Mono', monospace",
      fontSize: 13,
    },
    components: {
      Table: {
        headerBg: c.surface,
        headerColor: c.muted,
        headerSplitColor: 'transparent',
        headerSortActiveBg: c.surface,
        headerSortHoverBg: c.surface,
        bodySortBg: 'transparent',
        rowHoverBg: c.accentTint,
        cellPaddingBlock: 7,
        cellPaddingInline: 9,
        cellFontSize: 13,
        borderColor: c.line,
      },
      Drawer: { paddingLG: 22 },
      Collapse: { headerPadding: '0 0 10px 0', contentPadding: '0', headerBg: 'transparent' },
      Segmented: { itemSelectedBg: c.accent, itemSelectedColor: c.onAccent, trackBg: c.surface },
      Tag: { defaultBg: 'transparent' },
    },
  }
}
