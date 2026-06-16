// frontend/src/pages/FiltradaPage.tsx
import { useState } from 'react'
import { Skeleton } from '../components/ui/skeleton'
import { Button } from '../components/ui/button'
import MinutaCard from '../components/minutas/MinutaCard'
import MinutaDrawer from '../components/minutas/MinutaDrawer'
import { useMinutas } from '../hooks/useMinutas'
import { useAgregarFiltrada, useAgregarTodasFiltradas } from '../hooks/useSession'
import type { Minuta } from '../types/domain'

export default function FiltradaPage() {
  const { data, isLoading, isError } = useMinutas('FILTRADA')
  const agregarFiltrada = useAgregarFiltrada()
  const agregarTodas = useAgregarTodasFiltradas()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const selectedMinuta: Minuta | null = data?.items.find((m) => m.id === selectedId) ?? null

  const minutas = data?.items ?? []

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <div className="flex items-baseline justify-between gap-3">
        <div className="flex items-baseline gap-3">
          <h2 className="text-xl font-semibold text-slate-900">Órdenes Filtradas</h2>
          {data && (
            <span className="text-sm text-slate-400">
              {data.total} {data.total === 1 ? 'orden' : 'órdenes'}
            </span>
          )}
        </div>
        <Button
          onClick={() => agregarTodas.mutate(undefined)}
          disabled={minutas.length === 0 || agregarTodas.isPending}
        >
          {agregarTodas.isPending ? 'Agregando…' : 'Agregar todas'}
        </Button>
      </div>

      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full rounded-lg" />
          ))}
        </div>
      )}

      {isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3">
          <p className="text-sm text-red-700">
            Error al cargar las órdenes filtradas. Verificá tu conexión e intentá de nuevo.
          </p>
        </div>
      )}

      {data && minutas.length === 0 && !isLoading && (
        <div className="text-center py-16">
          <p className="text-sm text-slate-400">No hay órdenes filtradas</p>
        </div>
      )}

      {data && minutas.length > 0 && (
        <div className="space-y-3">
          {minutas.map((minuta) => (
            <div key={minuta.id} className="flex items-center gap-3">
              <div className="flex-1 min-w-0">
                <MinutaCard
                  minuta={minuta}
                  onClick={() => setSelectedId(minuta.id)}
                />
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => agregarFiltrada.mutate(minuta.id)}
                disabled={agregarFiltrada.isPending}
                className="shrink-0"
              >
                Agregar
              </Button>
            </div>
          ))}
        </div>
      )}

      <MinutaDrawer
        minuta={selectedMinuta}
        onClose={() => setSelectedId(null)}
      />
    </div>
  )
}
