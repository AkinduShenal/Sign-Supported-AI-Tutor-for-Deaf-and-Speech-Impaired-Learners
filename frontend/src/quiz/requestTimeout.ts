export async function withQuizTimeout<T>(
  request: (signal: AbortSignal) => Promise<T>,
  signal?: AbortSignal,
  timeoutMs = 15000,
): Promise<T> {
  const timeout = AbortSignal.timeout(timeoutMs)
  const requestSignal = signal ? AbortSignal.any([signal, timeout]) : timeout
  try {
    return await request(requestSignal)
  } catch (error) {
    if (timeout.aborted && !signal?.aborted) {
      throw new Error('Quiz request timed out. Ask the researcher to check the backend and database connection, then reload.')
    }
    throw error
  }
}
