// frontend/src/hooks/useMinutas.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchMinutas, editarTexto, marcarEnviado } from '../services/minutas'
import type { EstadoMinuta } from '../types/domain'

export function useMinutas(estado: EstadoMinuta) {
  return useQuery({
    queryKey: ['minutas', estado],
    queryFn: () => fetchMinutas(estado),
  })
}

export function useEditarTexto() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ minutaId, texto }: { minutaId: string; texto: string }) =>
      editarTexto(minutaId, texto),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['minutas', 'BORRADOR' as EstadoMinuta] })
    },
  })
}

export function useMarcarEnviado() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (minutaId: string) => marcarEnviado(minutaId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['minutas', 'BORRADOR' as EstadoMinuta] })
      qc.invalidateQueries({ queryKey: ['minutas', 'ENVIADO' as EstadoMinuta] })
    },
  })
}
