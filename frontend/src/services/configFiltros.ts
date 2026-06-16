// frontend/src/services/configFiltros.ts
import { api } from './api'
import type { ConfigFiltros } from '../types/domain'

export async function getConfigFiltros(): Promise<ConfigFiltros> {
  const res = await api.get<ConfigFiltros>('/config/filtros-minutas')
  return res.data
}

export async function patchConfigFiltros(config: ConfigFiltros): Promise<ConfigFiltros> {
  const res = await api.patch<ConfigFiltros>('/config/filtros-minutas', config)
  return res.data
}
