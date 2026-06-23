import { useState, useEffect, useRef } from 'react'
import { AlertTriangle, Plus, Trash2, ChevronDown } from 'lucide-react'
import { Textarea } from '../components/ui/textarea'
import { Input } from '../components/ui/input'
import { Button } from '../components/ui/button'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '../components/ui/collapsible'
import { useConfigDJList, useCrearConfigDJ, useActualizarConfigDJ, useEliminarConfigDJ } from '../hooks/useSession'
import type { ConfigDJ, CampoRegla, OperadorRegla } from '../types/domain'

const CAMPOS: { value: CampoRegla; label: string }[] = [
  { value: 'operacion',            label: 'Operación' },
  { value: 'operador',             label: 'Operador' },
  { value: 'origen',               label: 'Origen' },
  { value: 'estado',               label: 'Estado' },
  { value: 'moneda',               label: 'Moneda' },
  { value: 'instrumento',          label: 'Instrumento' },
  { value: 'cantidad',             label: 'Cantidad' },
  { value: 'precio',               label: 'Precio' },
  { value: 'monto',                label: 'Monto' },
  { value: 'cantidad_operada',     label: 'Cantidad Operada' },
  { value: 'precio_operado',       label: 'Precio Operado' },
  { value: 'requiere_conformidad', label: 'Requiere Conformidad' },
]

const OPERADORES: { value: OperadorRegla; label: string }[] = [
  { value: '>=', label: '>=' },
  { value: '<=', label: '<=' },
  { value: '>',  label: '>'  },
  { value: '<',  label: '<'  },
  { value: '=',  label: '='  },
  { value: '!=', label: '!=' },
]

const DJ_VARIABLES = [
  '{cliente_nombre}', '{cuenta_comitente}', '{cuenta_cotapartista}',
  '{operacion}', '{instrumento}', '{cantidad}', '{precio}', '{monto}',
  '{moneda}', '{fecha_operacion}', '{fecha_liquidacion}', '{estado}',
  '{asesor}', '{operador}', '{origen}', '{id_orden}',
]

const REGLA_VACIA: { campo: CampoRegla; operador: OperadorRegla; valor: string } = {
  campo: 'cantidad', operador: '>=', valor: '',
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: () => void }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={onChange}
      className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 ${
        checked ? 'bg-slate-800' : 'bg-slate-200'
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
          checked ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
    </button>
  )
}

interface DJPanelProps {
  dj: ConfigDJ
  defaultOpen?: boolean
}

function DJConfigPanel({ dj, defaultOpen = false }: DJPanelProps) {
  const actualizar = useActualizarConfigDJ()
  const eliminar = useEliminarConfigDJ()
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const [nombre, setNombre] = useState(dj.nombre)
  const [activa, setActiva] = useState(dj.activa)
  const [activarSiRC, setActivarSiRC] = useState(dj.activar_si_requiere_conformidad)
  const [reglas, setReglas] = useState(dj.reglas)
  const [logica, setLogica] = useState(dj.logica)
  const [incluirTexto, setIncluirTexto] = useState(dj.incluir_texto_en_minuta)
  const [textoAlerta, setTextoAlerta] = useState(dj.texto_alerta)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    setNombre(dj.nombre)
    setActiva(dj.activa)
    setActivarSiRC(dj.activar_si_requiere_conformidad)
    setReglas(dj.reglas)
    setLogica(dj.logica)
    setIncluirTexto(dj.incluir_texto_en_minuta)
    setTextoAlerta(dj.texto_alerta)
  }, [dj])

  function insertarVariable(variable: string) {
    const el = textareaRef.current
    if (!el) return
    const start = el.selectionStart
    const end = el.selectionEnd
    const nuevo = textoAlerta.slice(0, start) + variable + textoAlerta.slice(end)
    setTextoAlerta(nuevo)
    setSaved(false)
    requestAnimationFrame(() => {
      el.focus()
      const pos = start + variable.length
      el.setSelectionRange(pos, pos)
    })
  }

  async function handleGuardar() {
    if (!dj.id) return
    try {
      await actualizar.mutateAsync({
        id: dj.id,
        config: {
          nombre,
          activa,
          activar_si_requiere_conformidad: activarSiRC,
          reglas,
          logica,
          incluir_texto_en_minuta: incluirTexto,
          texto_alerta: textoAlerta,
        },
      })
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch { /* handled by TanStack Query */ }
  }

  async function handleEliminar() {
    if (!dj.id) return
    try {
      await eliminar.mutateAsync(dj.id)
    } catch { /* handled by TanStack Query */ }
  }

  const disabled = !activa

  return (
    <Collapsible defaultOpen={defaultOpen} className="border border-slate-200 rounded-lg overflow-hidden">
      <CollapsibleTrigger className="flex items-center justify-between w-full px-4 py-3 bg-white hover:bg-slate-50 transition-colors group">
        <div className="flex items-center gap-3">
          <div className={`h-2 w-2 rounded-full shrink-0 ${activa ? 'bg-green-500' : 'bg-slate-300'}`} />
          <span className="text-sm font-medium text-slate-800">{nombre || 'Sin nombre'}</span>
          {activa && <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />}
        </div>
        <ChevronDown className="h-4 w-4 text-slate-400 transition-transform group-data-[state=open]:rotate-180" />
      </CollapsibleTrigger>

      <CollapsibleContent>
        <div className="border-t border-slate-200 p-4 space-y-5">

          {/* Nombre */}
          <div className="space-y-1">
            <label className="text-xs font-medium text-slate-600">Nombre de la DJ</label>
            <Input
              value={nombre}
              onChange={(e) => { setNombre(e.target.value); setSaved(false) }}
              placeholder="Ej: DJ para operaciones mayores a $1M"
              className="text-sm"
            />
          </div>

          {/* Toggle activa */}
          <div className="flex items-center gap-3">
            <Toggle checked={activa} onChange={() => { setActiva(!activa); setSaved(false) }} />
            <div>
              <p className="text-sm font-medium text-slate-800">{activa ? 'Activa' : 'Desactivada'}</p>
              <p className="text-xs text-slate-500">
                {activa ? 'Se evalúa en cada upload' : 'No se evalúa'}
              </p>
            </div>
          </div>

          {/* Activacion automatica */}
          <div className={`transition-opacity ${disabled ? 'opacity-40 pointer-events-none' : ''}`}>
            <div className="flex items-center gap-3">
              <Toggle checked={activarSiRC} onChange={() => { setActivarSiRC(!activarSiRC); setSaved(false) }} />
              <div>
                <p className="text-sm font-medium text-slate-800">Activar si requiere conformidad</p>
                <p className="text-xs text-slate-500">DJ se dispara cuando RequiereConformidad = 1</p>
              </div>
            </div>
          </div>

          {/* Reglas */}
          <div className={`space-y-3 transition-opacity ${disabled ? 'opacity-40 pointer-events-none' : ''}`}>
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-slate-700">Condiciones</p>
              <Button variant="outline" size="sm" onClick={() => { setReglas(prev => [...prev, { ...REGLA_VACIA }]); setSaved(false) }}>
                <Plus className="h-3.5 w-3.5 mr-1" />
                Agregar regla
              </Button>
            </div>
            {reglas.length === 0 && (
              <p className="text-sm text-slate-400 italic text-center py-2">
                Sin reglas — solo activación automática.
              </p>
            )}
            {reglas.map((regla, idx) => (
              <div key={idx} className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg border border-slate-200">
                <select
                  value={regla.campo}
                  onChange={(e) => { setReglas(prev => prev.map((r, i) => i === idx ? { ...r, campo: e.target.value as CampoRegla } : r)); setSaved(false) }}
                  className="text-sm border border-slate-200 rounded px-2 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-slate-400"
                >
                  {CAMPOS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                </select>
                <select
                  value={regla.operador}
                  onChange={(e) => { setReglas(prev => prev.map((r, i) => i === idx ? { ...r, operador: e.target.value as OperadorRegla } : r)); setSaved(false) }}
                  className="text-sm border border-slate-200 rounded px-2 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-slate-400 w-16"
                >
                  {OPERADORES.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
                <input
                  type="text"
                  value={regla.valor}
                  onChange={(e) => { setReglas(prev => prev.map((r, i) => i === idx ? { ...r, valor: e.target.value } : r)); setSaved(false) }}
                  placeholder="valor"
                  className="flex-1 text-sm border border-slate-200 rounded px-2 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-slate-400"
                />
                <button
                  type="button"
                  onClick={() => { setReglas(prev => prev.filter((_, i) => i !== idx)); setSaved(false) }}
                  className="p-1.5 text-slate-400 hover:text-red-500 transition-colors"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
            {reglas.length > 1 && (
              <div className="flex items-center gap-3 pt-1">
                <span className="text-xs text-slate-500">Lógica:</span>
                <div className="flex gap-2">
                  {(['OR', 'AND'] as const).map(l => (
                    <button
                      key={l}
                      type="button"
                      onClick={() => { setLogica(l); setSaved(false) }}
                      className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                        logica === l ? 'bg-slate-800 text-white border-slate-800' : 'bg-white text-slate-600 border-slate-300 hover:border-slate-400'
                      }`}
                    >
                      {l === 'OR' ? 'Cualquiera (OR)' : 'Todas (AND)'}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Texto DJ */}
          <div className={`space-y-3 transition-opacity ${disabled ? 'opacity-40 pointer-events-none' : ''}`}>
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-slate-700">Texto en el mail</p>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">Incluir</span>
                <Toggle checked={incluirTexto} onChange={() => { setIncluirTexto(!incluirTexto); setSaved(false) }} />
              </div>
            </div>
            {incluirTexto && (
              <>
                <div className="flex flex-wrap gap-1.5">
                  {DJ_VARIABLES.map(v => (
                    <button
                      key={v}
                      type="button"
                      onClick={() => insertarVariable(v)}
                      className="px-2 py-0.5 text-xs font-mono bg-slate-100 hover:bg-slate-200 text-slate-700 rounded border border-slate-200 transition-colors"
                    >
                      {v}
                    </button>
                  ))}
                </div>
                <Textarea
                  ref={textareaRef}
                  value={textoAlerta}
                  onChange={(e) => { setTextoAlerta(e.target.value); setSaved(false) }}
                  rows={4}
                  className="font-mono text-sm resize-none"
                  placeholder="Ej: El cliente {cliente_nombre} debe presentar DJ..."
                />
              </>
            )}
          </div>

          {/* Acciones */}
          <div className="flex items-center gap-3 pt-2 border-t border-slate-100">
            <Button size="sm" onClick={handleGuardar} disabled={actualizar.isPending}>
              {actualizar.isPending ? 'Guardando...' : 'Guardar'}
            </Button>
            {saved && <span className="text-sm text-green-600">Guardado ✓</span>}
            <div className="flex-1" />
            <Button
              variant="ghost"
              size="sm"
              className="text-red-500 hover:text-red-700 hover:bg-red-50"
              onClick={handleEliminar}
              disabled={eliminar.isPending}
            >
              <Trash2 className="h-3.5 w-3.5 mr-1" />
              Eliminar
            </Button>
          </div>
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}

export default function ConfigDJPage() {
  const { data: djList, isLoading } = useConfigDJList()
  const crear = useCrearConfigDJ()
  const [newlyCreatedId, setNewlyCreatedId] = useState<number | null>(null)

  async function handleNuevaDJ() {
    try {
      const created = await crear.mutateAsync({
        nombre: '',
        activa: false,
        incluir_texto_en_minuta: false,
        texto_alerta: '',
        reglas: [],
        logica: 'OR',
        activar_si_requiere_conformidad: true,
      })
      setNewlyCreatedId(created.id ?? null)
    } catch { /* handled by TanStack Query */ }
  }

  return (
    <div className="max-w-2xl mx-auto pb-12">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Declaraciones Juradas</h2>
          <p className="text-sm text-slate-500 mt-1">
            Configurá las condiciones bajo las cuales una operación requiere DJ.
          </p>
        </div>
        <Button onClick={handleNuevaDJ} disabled={crear.isPending}>
          <Plus className="h-4 w-4 mr-1.5" />
          Nueva DJ
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          <div className="h-14 bg-slate-100 rounded-lg animate-pulse" />
          <div className="h-14 bg-slate-100 rounded-lg animate-pulse" />
        </div>
      ) : djList && djList.length === 0 ? (
        <div className="text-center py-16 border border-dashed border-slate-200 rounded-lg">
          <p className="text-sm text-slate-400">
            No hay declaraciones juradas configuradas.
          </p>
          <Button variant="outline" size="sm" className="mt-3" onClick={handleNuevaDJ}>
            <Plus className="h-3.5 w-3.5 mr-1" />
            Crear primera DJ
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          {djList?.map((dj) => (
            <DJConfigPanel
              key={dj.id}
              dj={dj}
              defaultOpen={dj.id === newlyCreatedId}
            />
          ))}
        </div>
      )}
    </div>
  )
}
