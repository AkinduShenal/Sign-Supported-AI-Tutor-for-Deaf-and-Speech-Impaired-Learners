// Matches the application tokens in index.css and the Quiz assessment panels.
// Keep numeric colours for Phaser and derive CSS strings for canvas text.
export const GAME_THEME = {
  color: {
    page: 0xf6f7fb,
    surface: 0xffffff,
    surfaceSoft: 0xf9faff,
    primary: 0x5b4ae8,
    primaryHover: 0x4938cc,
    primarySoft: 0xeeebff,
    primaryText: 0x3424a8,
    text: 0x1f2440,
    muted: 0x68708c,
    border: 0xe2e5ef,
    borderStrong: 0xcdd2df,
    track: 0xeceef5,
    success: 0x18794e,
    successSoft: 0xeaf8f0,
    error: 0xb3261e,
    errorSoft: 0xfff0ee,
    gold: 0xb07d00,
    goldSoft: 0xfff8df,
    shadow: 0x1f2440,
    operation: { add: 0xeaf8f0, subtract: 0xfff4e8, multiply: 0xeef3ff, divide: 0xf9eff8 },
  },
  radius: { panel: 24, card: 20, tile: 14, button: 13, badge: 10 },
  space: { xs: 6, sm: 12, md: 20, lg: 28, xl: 40 },
  font: { title: 32, subtitle: 18, body: 17, caption: 15, equation: 36, operation: 27 },
  control: { height: 60, compactHeight: 68, minPhysicalHeight: 44 },
  // maxDesktopZoom allows full screen to fill a 1080p display; text is
  // re-rasterised at the new zoom on resize (resharpenSceneText in gameUi.ts).
  render: { maxPixelRatio: 2, maxTextResolution: 3, maxDesktopZoom: 1.5 },
  // Soft game-world backdrop colours (gameBackdrop.ts). Light enough that
  // dark text placed directly on them keeps strong contrast.
  backdrop: {
    hub: { top: 0xd9d3ff, bottom: 0xf4f1ff, hill: 0xc9c0f7, hillFar: 0xe1dcfb },
    balance: { top: 0xd6e4ff, bottom: 0xf3f6ff, hill: 0xc3d3f7, hillFar: 0xdde7fb },
    gym: { top: 0xcfeaff, bottom: 0xf1f9ff, hill: 0xbfe3c9, hillFar: 0xd9efdf },
  },
  confetti: [0x5b4ae8, 0xf5b301, 0x18a35e, 0xff6b6b, 0x3bb6ff, 0xff9f1c],
} as const

export const cssColor = (value: number): string => `#${value.toString(16).padStart(6, '0')}`

export function renderPixelRatio(value: number): number {
  return Math.min(GAME_THEME.render.maxPixelRatio, Math.max(1, Number.isFinite(value) ? value : 1))
}

export function textResolution(cameraZoom: number): number {
  // Include the small existing equation/reward pop without making every texture huge.
  return Math.min(GAME_THEME.render.maxTextResolution, Math.max(1, cameraZoom * 1.15))
}
