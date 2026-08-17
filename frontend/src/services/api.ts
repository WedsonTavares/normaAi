import type { ApiErrorBody, HealthResponse } from '../types/api'

// A barra final é removida para que `${API_URL}${path}` nunca gere "//".
const API_URL = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/+$/, '')

/** Erro vindo da API, já com mensagem pronta para exibir ao usuário. */
export class ApiError extends Error {
  status: number
  code: string

  constructor(message: string, status: number, code: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

function isApiErrorBody(body: unknown): body is ApiErrorBody {
  if (typeof body !== 'object' || body === null || !('error' in body)) return false
  const error = (body as { error: unknown }).error
  return typeof error === 'object' && error !== null && 'message' in error && 'code' in error
}

async function request<T>(path: string): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`)
  } catch {
    throw new ApiError('Não foi possível conectar ao servidor.', 0, 'network_error')
  }

  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null)
    if (isApiErrorBody(body)) {
      throw new ApiError(body.error.message, response.status, body.error.code)
    }
    throw new ApiError('Erro inesperado ao consultar o servidor.', response.status, 'unknown_error')
  }

  return (await response.json()) as T
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/health')
}
