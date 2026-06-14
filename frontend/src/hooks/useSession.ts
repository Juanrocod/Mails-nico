// frontend/src/hooks/useSession.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchPlantilla, guardarPlantilla } from '../services/plantilla'
import { fetchConfigDJ, guardarConfigDJ } from '../services/configDJ'
import type { ConfigDJ } from '../types/domain'

export function usePlantilla() {
  return useQuery({
    queryKey: ['plantilla'],
    queryFn: fetchPlantilla,
  })
}

export function useGuardarPlantilla() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (texto: string) => guardarPlantilla(texto),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['plantilla'] })
    },
  })
}

export function useConfigDJ() {
  return useQuery({
    queryKey: ['config-dj'],
    queryFn: fetchConfigDJ,
  })
}

export function useGuardarConfigDJ() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (config: ConfigDJ) => guardarConfigDJ(config),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['config-dj'] })
    },
  })
}
