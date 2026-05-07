/** Thin fetch wrapper with JSON parsing and error handling. */
export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public body: unknown,
  ) {
    super(`${status} ${statusText}`)
    this.name = 'ApiError'
  }
}

export async function api<T = unknown>(url: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string>),
  }

  // Attach admin token if present
  const token = sessionStorage.getItem('admin-token')
  if (token) {
    headers['X-Admin-Token'] = token
  }

  const res = await fetch(url, { ...options, headers })
  if (!res.ok) {
    let body: unknown
    try {
      body = await res.json()
    } catch {
      body = await res.text()
    }
    throw new ApiError(res.status, res.statusText, body)
  }

  // Handle 204 No Content
  if (res.status === 204) {
    return undefined as T
  }

  return res.json() as Promise<T>
}
