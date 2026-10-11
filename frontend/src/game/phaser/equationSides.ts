// Splits "x + 3 = 7" into its two sides for the balance scale's pans.
// Pure and Phaser-free so it can be unit-tested directly.
export function splitEquation(equation: string): [string, string] {
  const index = equation.indexOf('=')
  if (index < 0) return [equation.trim(), '']
  return [equation.slice(0, index).trim(), equation.slice(index + 1).trim()]
}
