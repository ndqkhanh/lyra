/**
 * 12 Built-in Color Themes — Plan 32 with exact hex palettes.
 *
 * Each theme provides a complete color palette suitable for terminal-rendered
 * UI with semantic role mapping (background, foreground, accent, status, diff).
 */

export interface ThemePreset {
  id: string
  name: string
  variant: 'dark' | 'light' | 'midnight'
  palette: ThemePalette
}

export interface ThemePalette {
  background: string
  foreground: string
  cursor: string
  selection: string
  surface0: string
  surface1: string
  surface2: string
  text: string
  subtext0: string
  subtext1: string
  comment: string
  accent: string
  red: string
  green: string
  yellow: string
  blue: string
  purple: string
  cyan: string
  orange: string
  statusBg: string
  statusFg: string
  statusError: string
  statusWarning: string
  statusSuccess: string
}

export const THEME_PRESETS: Record<string, ThemePreset> = {
  catppuccin_mocha: {
    id: 'catppuccin_mocha',
    name: 'Catppuccin Mocha',
    variant: 'dark',
    palette: {
      background: '#1E1E2E',
      foreground: '#CDD6F4',
      cursor: '#F5E0DC',
      selection: '#585B70',
      surface0: '#313244',
      surface1: '#45475A',
      surface2: '#585B70',
      text: '#CDD6F4',
      subtext0: '#A6ADC8',
      subtext1: '#BAC2DE',
      comment: '#6C7086',
      accent: '#CBA6F7',
      red: '#F38BA8',
      green: '#A6E3A1',
      yellow: '#F9E2AF',
      blue: '#89B4FA',
      purple: '#CBA6F7',
      cyan: '#94E2D5',
      orange: '#FAB387',
      statusBg: '#1E1E2E',
      statusFg: '#CDD6F4',
      statusError: '#F38BA8',
      statusWarning: '#F9E2AF',
      statusSuccess: '#A6E3A1',
    },
  },

  tokyo_night_storm: {
    id: 'tokyo_night_storm',
    name: 'Tokyo Night Storm',
    variant: 'dark',
    palette: {
      background: '#24283B',
      foreground: '#C0CAF5',
      cursor: '#C0CAF5',
      selection: '#364A82',
      surface0: '#1F2335',
      surface1: '#292E42',
      surface2: '#3B4261',
      text: '#C0CAF5',
      subtext0: '#A9B1D6',
      subtext1: '#9AA5CE',
      comment: '#565F89',
      accent: '#7AA2F7',
      red: '#F7768E',
      green: '#9ECE6A',
      yellow: '#E0AF68',
      blue: '#7AA2F7',
      purple: '#BB9AF7',
      cyan: '#7DCFFF',
      orange: '#FF9E64',
      statusBg: '#24283B',
      statusFg: '#C0CAF5',
      statusError: '#F7768E',
      statusWarning: '#E0AF68',
      statusSuccess: '#9ECE6A',
    },
  },

  nord: {
    id: 'nord',
    name: 'Nord',
    variant: 'dark',
    palette: {
      background: '#2E3440',
      foreground: '#D8DEE9',
      cursor: '#D8DEE9',
      selection: '#434C5E',
      surface0: '#3B4252',
      surface1: '#434C5E',
      surface2: '#4C566A',
      text: '#D8DEE9',
      subtext0: '#E5E9F0',
      subtext1: '#ECEFF4',
      comment: '#616E88',
      accent: '#88C0D0',
      red: '#BF616A',
      green: '#A3BE8C',
      yellow: '#EBCB8B',
      blue: '#81A1C1',
      purple: '#B48EAD',
      cyan: '#88C0D0',
      orange: '#D08770',
      statusBg: '#2E3440',
      statusFg: '#D8DEE9',
      statusError: '#BF616A',
      statusWarning: '#EBCB8B',
      statusSuccess: '#A3BE8C',
    },
  },

  dracula: {
    id: 'dracula',
    name: 'Dracula',
    variant: 'dark',
    palette: {
      background: '#282A36',
      foreground: '#F8F8F2',
      cursor: '#F8F8F2',
      selection: '#44475A',
      surface0: '#21222C',
      surface1: '#343746',
      surface2: '#44475A',
      text: '#F8F8F2',
      subtext0: '#BFBFBF',
      subtext1: '#D3D3D3',
      comment: '#6272A4',
      accent: '#BD93F9',
      red: '#FF5555',
      green: '#50FA7B',
      yellow: '#F1FA8C',
      blue: '#8BE9FD',
      purple: '#BD93F9',
      cyan: '#8BE9FD',
      orange: '#FFB86C',
      statusBg: '#282A36',
      statusFg: '#F8F8F2',
      statusError: '#FF5555',
      statusWarning: '#F1FA8C',
      statusSuccess: '#50FA7B',
    },
  },

  one_dark: {
    id: 'one_dark',
    name: 'One Dark',
    variant: 'dark',
    palette: {
      background: '#282C34',
      foreground: '#ABB2BF',
      cursor: '#528BFF',
      selection: '#3E4452',
      surface0: '#21252B',
      surface1: '#2C313A',
      surface2: '#3E4452',
      text: '#ABB2BF',
      subtext0: '#828997',
      subtext1: '#9DA5B4',
      comment: '#5C6370',
      accent: '#61AFEF',
      red: '#E06C75',
      green: '#98C379',
      yellow: '#E5C07B',
      blue: '#61AFEF',
      purple: '#C678DD',
      cyan: '#56B6C2',
      orange: '#D19A66',
      statusBg: '#282C34',
      statusFg: '#ABB2BF',
      statusError: '#E06C75',
      statusWarning: '#E5C07B',
      statusSuccess: '#98C379',
    },
  },

  gruvbox_dark_medium: {
    id: 'gruvbox_dark_medium',
    name: 'Gruvbox Dark Medium',
    variant: 'dark',
    palette: {
      background: '#282828',
      foreground: '#D5C4A1',
      cursor: '#D5C4A1',
      selection: '#504945',
      surface0: '#1D2021',
      surface1: '#3C3836',
      surface2: '#504945',
      text: '#D5C4A1',
      subtext0: '#BDAE93',
      subtext1: '#C9B99A',
      comment: '#928374',
      accent: '#D3869B',
      red: '#FB4934',
      green: '#B8BB26',
      yellow: '#FABD2F',
      blue: '#83A598',
      purple: '#D3869B',
      cyan: '#8EC07C',
      orange: '#FE8019',
      statusBg: '#282828',
      statusFg: '#D5C4A1',
      statusError: '#FB4934',
      statusWarning: '#FABD2F',
      statusSuccess: '#B8BB26',
    },
  },

  selenized_dark: {
    id: 'selenized_dark',
    name: 'Selenized Dark',
    variant: 'dark',
    palette: {
      background: '#103C48',
      foreground: '#ADBCBC',
      cursor: '#ADBCBC',
      selection: '#2D5B6A',
      surface0: '#0D353F',
      surface1: '#184956',
      surface2: '#2D5B6A',
      text: '#ADBCBC',
      subtext0: '#8DA0A0',
      subtext1: '#9BAEAE',
      comment: '#72898F',
      accent: '#4695F7',
      red: '#FA5750',
      green: '#75B938',
      yellow: '#DBB32D',
      blue: '#4695F7',
      purple: '#AF5AD2',
      cyan: '#41C7B9',
      orange: '#ED8649',
      statusBg: '#103C48',
      statusFg: '#ADBCBC',
      statusError: '#FA5750',
      statusWarning: '#DBB32D',
      statusSuccess: '#75B938',
    },
  },

  everforest_dark: {
    id: 'everforest_dark',
    name: 'Everforest Dark',
    variant: 'dark',
    palette: {
      background: '#2D353B',
      foreground: '#D3C6AA',
      cursor: '#D3C6AA',
      selection: '#425047',
      surface0: '#232A2E',
      surface1: '#343F44',
      surface2: '#425047',
      text: '#D3C6AA',
      subtext0: '#9DA9A0',
      subtext1: '#B6C0B9',
      comment: '#7A8478',
      accent: '#D699B6',
      red: '#E67E80',
      green: '#A7C080',
      yellow: '#DBBC7F',
      blue: '#7FBBB3',
      purple: '#D699B6',
      cyan: '#83C092',
      orange: '#E69875',
      statusBg: '#2D353B',
      statusFg: '#D3C6AA',
      statusError: '#E67E80',
      statusWarning: '#DBBC7F',
      statusSuccess: '#A7C080',
    },
  },

  ayu_dark: {
    id: 'ayu_dark',
    name: 'Ayu Dark',
    variant: 'dark',
    palette: {
      background: '#0A0E14',
      foreground: '#B3B1AD',
      cursor: '#FFCC66',
      selection: '#273747',
      surface0: '#0D1117',
      surface1: '#131721',
      surface2: '#1F2B38',
      text: '#B3B1AD',
      subtext0: '#7A828E',
      subtext1: '#8A919E',
      comment: '#626A73',
      accent: '#FFCC66',
      red: '#F07178',
      green: '#B8CC52',
      yellow: '#FFCC66',
      blue: '#59C2FF',
      purple: '#D2A6FF',
      cyan: '#95E6CB',
      orange: '#FF8F40',
      statusBg: '#0A0E14',
      statusFg: '#B3B1AD',
      statusError: '#F07178',
      statusWarning: '#FFCC66',
      statusSuccess: '#B8CC52',
    },
  },

  rose_pine_moon: {
    id: 'rose_pine_moon',
    name: 'Rose Pine Moon',
    variant: 'dark',
    palette: {
      background: '#232136',
      foreground: '#E0DEF4',
      cursor: '#E0DEF4',
      selection: '#433C59',
      surface0: '#2A2740',
      surface1: '#35304D',
      surface2: '#433C59',
      text: '#E0DEF4',
      subtext0: '#908CAA',
      subtext1: '#B8B4D0',
      comment: '#6E6A86',
      accent: '#C4A7E7',
      red: '#EB6F92',
      green: '#A3D4A6',
      yellow: '#F6C177',
      blue: '#9CCFD8',
      purple: '#C4A7E7',
      cyan: '#9CCFD8',
      orange: '#F6C177',
      statusBg: '#232136',
      statusFg: '#E0DEF4',
      statusError: '#EB6F92',
      statusWarning: '#F6C177',
      statusSuccess: '#A3D4A6',
    },
  },

  silk_circuit_neon: {
    id: 'silk_circuit_neon',
    name: 'Silk Circuit Neon',
    variant: 'dark',
    palette: {
      background: '#0B0F17',
      foreground: '#E0E7FF',
      cursor: '#00F0FF',
      selection: '#1A2340',
      surface0: '#0E1320',
      surface1: '#151C30',
      surface2: '#1A2340',
      text: '#E0E7FF',
      subtext0: '#7B8CBC',
      subtext1: '#A0AFDB',
      comment: '#4B5A8C',
      accent: '#00F0FF',
      red: '#FF3E6C',
      green: '#00E676',
      yellow: '#FFEA00',
      blue: '#448AFF',
      purple: '#D500F9',
      cyan: '#00F0FF',
      orange: '#FF6D00',
      statusBg: '#0B0F17',
      statusFg: '#E0E7FF',
      statusError: '#FF3E6C',
      statusWarning: '#FFEA00',
      statusSuccess: '#00E676',
    },
  },

  sentry_sentinel_dark: {
    id: 'sentry_sentinel_dark',
    name: 'Sentry Sentinel Dark',
    variant: 'dark',
    palette: {
      background: '#0C0F14',
      foreground: '#DEE3EA',
      cursor: '#FF5E5B',
      selection: '#232C38',
      surface0: '#10151C',
      surface1: '#181E27',
      surface2: '#232C38',
      text: '#DEE3EA',
      subtext0: '#7E8DA0',
      subtext1: '#A3B1C2',
      comment: '#515D6E',
      accent: '#FF5E5B',
      red: '#FF5E5B',
      green: '#3ECF8E',
      yellow: '#FFC857',
      blue: '#5B9BD5',
      purple: '#B084EB',
      cyan: '#3DD6D0',
      orange: '#FF8C42',
      statusBg: '#0C0F14',
      statusFg: '#DEE3EA',
      statusError: '#FF5E5B',
      statusWarning: '#FFC857',
      statusSuccess: '#3ECF8E',
    },
  },
}

/** Theme IDs in display order. */
export const THEME_ORDER: string[] = [
  'catppuccin_mocha',
  'tokyo_night_storm',
  'nord',
  'dracula',
  'one_dark',
  'gruvbox_dark_medium',
  'selenized_dark',
  'everforest_dark',
  'ayu_dark',
  'rose_pine_moon',
  'silk_circuit_neon',
  'sentry_sentinel_dark',
]

/** Look up a theme preset by ID. */
export function getThemePreset(id: string): ThemePreset | undefined {
  return THEME_PRESETS[id]
}

/** Get the default theme (Dracula — matches existing colors.ts). */
export function getDefaultTheme(): ThemePreset {
  return THEME_PRESETS.dracula
}
