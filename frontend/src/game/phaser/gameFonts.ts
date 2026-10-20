import { GAME_FONTS } from './gameText'

// Phaser rasterises Text into a texture once, when it is created; a font
// that finishes loading later never reaches text already drawn. So the
// canvas boots only after the Game's bundled fonts (see PhaserGame.css) are
// ready — or after a short timeout, in which case the system fallback fonts
// in FONT_FAMILY are used and the game still starts.
export function loadGameFonts(timeoutMs = 3000): Promise<void> {
  if (typeof document === 'undefined' || !document.fonts) return Promise.resolve()
  const faces: Array<[string, string]> = [
    [`500 24px "${GAME_FONTS.rounded}"`, 'Ax0'],
    [`700 24px "${GAME_FONTS.rounded}"`, 'Ax0'],
    [`400 24px "${GAME_FONTS.sinhala}"`, 'අ'],
    [`700 24px "${GAME_FONTS.sinhala}"`, 'අ'],
  ]
  const loaded = Promise.all(faces.map(([font, sample]) => document.fonts.load(font, sample)))
    .then(() => undefined, () => undefined)
  const timeout = new Promise<void>((resolve) => { window.setTimeout(resolve, timeoutMs) })
  return Promise.race([loaded, timeout])
}
