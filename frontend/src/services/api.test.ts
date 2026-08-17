import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError, getHealth } from './api'

function mockFetch(response: Response | Error) {
  const fetchMock = vi.fn(() =>
    response instanceof Error ? Promise.reject(response) : Promise.resolve(response),
  )
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('getHealth', () => {
  it('devolve o corpo quando a resposta é bem-sucedida', async () => {
    mockFetch(
      jsonResponse({ status: 'ok', app: 'NormaAI', version: '0.1.0', environment: 'test' }),
    )

    await expect(getHealth()).resolves.toEqual({
      status: 'ok',
      app: 'NormaAI',
      version: '0.1.0',
      environment: 'test',
    })
  })

  it('usa a mensagem do backend quando o erro vem no formato da API', async () => {
    mockFetch(jsonResponse({ error: { code: 'not_found', message: 'Recurso não encontrado.' } }, 404))

    await expect(getHealth()).rejects.toMatchObject({
      message: 'Recurso não encontrado.',
      status: 404,
      code: 'not_found',
    })
  })

  it('não quebra quando o erro vem em formato inesperado', async () => {
    mockFetch(new Response('<html>502 Bad Gateway</html>', { status: 502 }))

    const error = await getHealth().catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 502, code: 'unknown_error' })
  })

  it('transforma falha de rede em erro tratado', async () => {
    mockFetch(new TypeError('Failed to fetch'))

    await expect(getHealth()).rejects.toMatchObject({
      message: 'Não foi possível conectar ao servidor.',
      code: 'network_error',
      status: 0,
    })
  })
})
