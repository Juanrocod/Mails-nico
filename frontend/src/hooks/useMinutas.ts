// frontend/src/hooks/useMinutas.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchMinutas, editarTexto, marcarEnviado } from '../services/minutas'
import type { EstadoMinuta, SessionMinutasResponse } from '../types/domain'

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
    onMutate: async ({ minutaId, texto }) => {
      await qc.cancelQueries({ queryKey: ['minutas', 'BORRADOR'] })
      const prev = qc.getQueryData<SessionMinutasResponse>(['minutas', 'BORRADOR'])
      if (prev) {
        qc.setQueryData<SessionMinutasResponse>(['minutas', 'BORRADOR'], {
          ...prev,
          items: prev.items.map(m =>
            m.id === minutaId ? { ...m, texto_minuta: texto, texto_editado: true } : m
          ),
        })
      }
      return { prev }
    },
    onError: (_err, _vars, context) => {
      if (context?.prev) qc.setQueryData(['minutas', 'BORRADOR'], context.prev)
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['minutas', 'BORRADOR'] })
    },
  })
}

export function useMarcarEnviado() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (minutaId: string) => marcarEnviado(minutaId),
    onMutate: async (minutaId) => {
      await qc.cancelQueries({ queryKey: ['minutas', 'BORRADOR'] })
      await qc.cancelQueries({ queryKey: ['minutas', 'ENVIADO'] })
      const prevBorr = qc.getQueryData<SessionMinutasResponse>(['minutas', 'BORRADOR'])
      const prevEnv = qc.getQueryData<SessionMinutasResponse>(['minutas', 'ENVIADO'])
      if (prevBorr) {
        const minuta = prevBorr.items.find(m => m.id === minutaId)
        qc.setQueryData<SessionMinutasResponse>(['minutas', 'BORRADOR'], {
          ...prevBorr,
          items: prevBorr.items.filter(m => m.id !== minutaId),
          total: prevBorr.total - 1,
        })
        if (minuta && prevEnv) {
          qc.setQueryData<SessionMinutasResponse>(['minutas', 'ENVIADO'], {
            ...prevEnv,
            items: [...prevEnv.items, { ...minuta, estado: 'ENVIADO' }],
            total: prevEnv.total + 1,
          })
        }
      }
      return { prevBorr, prevEnv }
    },
    onError: (_err, _vars, context) => {
      if (context?.prevBorr) qc.setQueryData(['minutas', 'BORRADOR'], context.prevBorr)
      if (context?.prevEnv) qc.setQueryData(['minutas', 'ENVIADO'], context.prevEnv)
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['minutas', 'BORRADOR'] })
      qc.invalidateQueries({ queryKey: ['minutas', 'ENVIADO'] })
    },
  })
}
