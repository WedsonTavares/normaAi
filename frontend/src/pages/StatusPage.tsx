import { useEffect, useState } from 'react'

import { ApiError, getHealth } from '../services/api'
import type { HealthResponse } from '../types/api'

type State =
  | { kind: 'loading' }
  | { kind: 'error'; message: string }
  | { kind: 'ready'; health: HealthResponse }

export function StatusPage() {
  const [state, setState] = useState<State>({ kind: 'loading' })

  useEffect(() => {
    let active = true

    getHealth()
      .then((health) => {
        if (active) setState({ kind: 'ready', health })
      })
      .catch((error: unknown) => {
        if (!active) return
        const message =
          error instanceof ApiError ? error.message : 'Erro inesperado ao consultar o servidor.'
        setState({ kind: 'error', message })
      })

    return () => {
      active = false
    }
  }, [])

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center gap-6 p-6">
      <header>
        <h1 className="text-3xl font-semibold text-slate-900">NormaAI</h1>
        <p className="mt-1 text-slate-600">
          Leitura, indexação e análise de documentos normativos.
        </p>
      </header>

      <section
        aria-live="polite"
        className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
      >
        <h2 className="mb-3 text-sm font-medium tracking-wide text-slate-500 uppercase">
          Status do backend
        </h2>

        {state.kind === 'loading' && <p className="text-slate-600">Verificando conexão…</p>}

        {state.kind === 'error' && (
          <div className="rounded-md border border-red-200 bg-red-50 p-3">
            <p className="font-medium text-red-800">Backend indisponível</p>
            <p className="mt-1 text-sm text-red-700">{state.message}</p>
          </div>
        )}

        {state.kind === 'ready' && (
          <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
            <dt className="text-slate-500">Status</dt>
            <dd className="font-medium text-emerald-700">conectado</dd>

            <dt className="text-slate-500">Aplicação</dt>
            <dd className="text-slate-900">{state.health.app}</dd>

            <dt className="text-slate-500">Versão</dt>
            <dd className="text-slate-900">{state.health.version}</dd>

            <dt className="text-slate-500">Ambiente</dt>
            <dd className="text-slate-900">{state.health.environment}</dd>
          </dl>
        )}
      </section>
    </main>
  )
}
