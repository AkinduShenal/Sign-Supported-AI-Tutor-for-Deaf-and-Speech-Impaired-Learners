/** A named clip is usable only if present AND allowed by explicit review policy. */
export function selectPlayback(
  requested: string[], available: string[], validated: string[], prototypes: string[], allowPrototype: boolean,
) {
  const permitted = new Set([...validated, ...(allowPrototype ? prototypes : [])])
  // Preserve order and repetitions. Repeated digits/actions are not duplicates.
  return requested.map((name, sourceIndex) => ({ name, sourceIndex }))
    .filter(({ name }) => permitted.has(name) && available.includes(name))
}
