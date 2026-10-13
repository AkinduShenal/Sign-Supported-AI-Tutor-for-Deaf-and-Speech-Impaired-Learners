export async function requestGameCsvDownload(
  apiBaseUrl: string,
  exportKey: string,
  request: typeof fetch = fetch,
): Promise<{ blob: Blob; filename: string }> {
  if (!exportKey.trim()) throw new Error('Enter the researcher export key.')
  const response = await request(`${apiBaseUrl.replace(/\/$/, '')}/game/exports/collection`, {
    headers: { Accept: 'application/zip', Authorization: `Bearer ${exportKey.trim()}` },
    cache: 'no-store',
    signal: AbortSignal.timeout(120000),
  })
  if (response.status === 401 || response.status === 403) {
    throw new Error('The researcher export key is missing or incorrect.')
  }
  if (response.status === 503) {
    throw new Error('CSV download is unavailable. Check the backend configuration and connection.')
  }
  if (!response.ok) throw new Error('CSV download failed. Please retry.')
  if (response.headers.get('Content-Type')?.split(';')[0].trim() !== 'application/zip') {
    throw new Error('The server did not return the CSV archive. Please retry.')
  }
  const blob = await response.blob()
  if (!blob.size) throw new Error('The server returned an empty download. Please retry.')
  const disposition = response.headers.get('Content-Disposition') ?? ''
  const filename = disposition.match(/filename="(game-collection-[0-9TZ-]+\.zip)"/)?.[1]
    ?? `game-collection-${new Date().toISOString().replace(/[:.]/g, '-')}.zip`
  return { blob, filename }
}
