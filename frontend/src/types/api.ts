export interface HealthResponse {
  status: 'ok'
  app: string
  version: string
  environment: string
}

/** Formato de erro devolvido pelo backend. */
export interface ApiErrorBody {
  error: {
    code: string
    message: string
  }
}
