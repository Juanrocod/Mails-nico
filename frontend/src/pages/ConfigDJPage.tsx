// frontend/src/pages/ConfigDJPage.tsx
import { useState, useEffect, useRef } from 'react'
import { AlertTriangle, Plus, Trash2 } from 'lucide-react'
import { Textarea } from '../components/ui/textarea'
import { Button } from '../components/ui/button'
import { useConfigDJ, useGuardarConfigDJ } from '../hooks/useSession'
import type { CampoRegla, OperadorRegla, ConfigDJ } from '../types/domain'

const CAMPOS: { value: CampoRegla; label: string }[] = [
  { value: 'operacion', label: 'Operación' },
  { value: 'operador', label: 'Operador' },
  { value: 'origen', label: 'Origen' },
  { value: 'estado', label: 'Estado' },
  { value: 'moneda', label: 'Moneda' },
  { value: 'instrumento', label: 'Instrumento' },
  { value: 'cantidad', label: 'Cantidad' },
  { value: 'precio', label: 'Precio' },
  { value: 'monto', label: 'Monto' },
  { value: 'cantidad_operada', label: 'Cantidad Operada' },
  { value: 'precio_operado', label: 'Precio Operado' },
  { value: 'requiere_conformidad', label: 'Requiere Conformidad' },
]

const OPERADORES: { value: OperadorRegla; label: string }[] = [
  { value: '>=', label: '>=' },
  { value: '<=', label: '<=' },
  { value: '>', label: '>' },
  { value: '<', label: '<' },
  { value: '=', label: '=' },
  { value: '!=', label: '!=' },
]

const DJ_VARIABLES = [
  '{cliente_nombre}',
  '{cuenta_comitente}',
  '{cuenta_cotapartista}',
  '{operacion}',
  '{instrumento}',
  '{cantidad}',
  '{precio}',
  '{monto}',
  '{moneda}',
  '{fecha_operacion}',
  '{fecha_liquidacion}',
  '{estado}',
  '{asesor}',
  '{operador}',
  '{origen}',
  '{id_orden}',
]

const REGLA_VACIA: { campo: CampoRegla; operador: OperadorRegla; valor: string } = { campo: 'cantidad', operador: '>=', valor: '' }

function reglasIguales(
  a: { campo: CampoRegla; operador: OperadorRegla; valor: string }[],
  b: { campo: CampoRegla; operador: OperadorRegla; valor: string }[]
): boolean {
  if (a.length !== b.length) return false
  return a.every(
    (r, i) => r.campo === b[i].campo && r.operador === b[i].operador && r.valor === b[i].valor
  )
}

export default function ConfigDJPage() {
  const { data, isLoading } = useConfigDJ()
  const guardar = useGuardarConfigDJ()
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const [activa, setActiva] = useState(false)
  const [incluirTexto, setIncluirTexto] = useState(false)
  const [textoAlerta, setTextoAlerta] = useState('')
  const [reglas, setReglas] = useState<{ campo: CampoRegla; operador: OperadorRegla; valor: string }[]>([])
  const [logica, setLogica] = useState<'AND' | 'OR'>('OR')
  const [activarSiRequiereConformidad, setActivarSiRequiereConformidad] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (data) {
      setActiva(data.activa)
      setIncluirTexto(data.incluir_texto_en_minuta)
      setTextoAlerta(data.texto_alerta)
      setReglas(data.reglas)
      setLogica(data.logica)
      setActivarSiRequiereConformidad(data.activar_si_requiere_conformidad)
    }
  }, [data])

  const modificado = data
    ? activa !== data.activa ||
      incluirTexto !== data.incluir_texto_en_minuta ||
      textoAlerta !== data.texto_alerta ||
      logica !== data.logica ||
      activarSiRequiereConformidad !== data.activar_si_requiere_conformidad ||
      !reglasIguales(reglas, data.reglas)
    : false

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

  function agregarRegla() {
    setReglas((prev) => [...prev, { ...REGLA_VACIA }])
    setSaved(false)
  }

  function eliminarRegla(idx: number) {
    setReglas((prev) => prev.filter((_, i) => i !== idx))
    setSaved(false)
  }

  function actualizarRegla(idx: number, campo: 'campo' | 'operador' | 'valor', valor: string) {
    setReglas((prev) =>
      prev.map((r, i) => (i === idx ? { ...r, [campo]: valor } : r))
    )
    setSaved(false)
  }

  async function handleGuardar() {
    try {
      await guardar.mutateAsync({
        activa,
        incluir_texto_en_minuta: incluirTexto,
        texto_alerta: textoAlerta,
        reglas,
        logica,
        activar_si_requiere_conformidad: activarSiRequiereConformidad,
      })
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch {
      // error silenciado
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Configuración DJ</h2>
        <p className="text-sm text-slate-500 mt-1">
          Define las condiciones bajo las cuales una operación requiere Declaración Jurada.
          La configuración se guarda en la base de datos y persiste entre sesiones.
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          <div className="h-10 bg-slate-100 rounded animate-pulse" />
          <div className="h-32 bg-slate-100 rounded animate-pulse" />
        </div>
      ) : (
        <div className="space-y-5">
          {/* Toggle DJ activa */}
          <div className="flex items-center gap-3 p-4 border border-slate-200 rounded-lg">
            <button
              type="button"
              role="switch"
              aria-checked={activa}
              onClick={() => { setActiva(!activa); setSaved(false) }}
              className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 ${
                activa ? 'bg-slate-800' : 'bg-slate-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  activa ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
            <div className="flex-1">
              <p className="text-sm font-medium text-slate-800">
                {activa ? 'DJ activa' : 'DJ inactiva'}
              </p>
              <p className="text-xs text-slate-500">
                {activa
                  ? 'Se evalúan las reglas en cada minuta generada'
                  : 'No se detecta ni avisa ninguna condición de DJ'}
              </p>
            </div>
            {activa && <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0" />}
          </div>

          {activa && (
            <>
              {/* Panel de reglas */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium text-slate-700">
                    Reglas de detección
                  </label>
                  <Button variant="outline" size="sm" onClick={agregarRegla}>
                    <Plus className="h-3.5 w-3.5 mr-1" />
                    Agregar regla
                  </Button>
                </div>

                {reglas.length === 0 && (
                  <p className="text-sm text-slate-400 italic">
                    Sin reglas — agregá al menos una para activar la detección.
                  </p>
                )}

                {reglas.map((regla, idx) => (
                  <div key={idx} className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <select
                      value={regla.campo}
                      onChange={(e) => actualizarRegla(idx, 'campo', e.target.value)}
                      className="text-sm border border-slate-200 rounded px-2 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-slate-400"
                    >
                      {CAMPOS.map((c) => (
                        <option key={c.value} value={c.value}>{c.label}</option>
                      ))}
                    </select>
                    <select
                      value={regla.operador}
                      onChange={(e) => actualizarRegla(idx, 'operador', e.target.value)}
                      className="text-sm border border-slate-200 rounded px-2 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-slate-400 w-16"
                    >
                      {OPERADORES.map((o) => (
                        <option key={o.value} value={o.value}>{o.label}</option>
                      ))}
                    </select>
                    <input
                      type="text"
                      value={regla.valor}
                      onChange={(e) => actualizarRegla(idx, 'valor', e.target.value)}
                      placeholder="valor"
                      className="flex-1 text-sm border border-slate-200 rounded px-2 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-slate-400"
                    />
                    <button
                      type="button"
                      onClick={() => eliminarRegla(idx)}
                      className="p-1.5 text-slate-400 hover:text-red-500 transition-colors"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}

                {/* Selector de lógica — solo visible cuando hay más de una regla */}
                {reglas.length > 1 && (
                  <div className="flex items-center gap-3 pt-1">
                    <span className="text-xs text-slate-500">Lógica entre reglas:</span>
                    <div className="flex gap-2">
                      {(['OR', 'AND'] as const).map((l) => (
                        <button
                          key={l}
                          type="button"
                          onClick={() => { setLogica(l); setSaved(false) }}
                          className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                            logica === l
                              ? 'bg-slate-800 text-white border-slate-800'
                              : 'bg-white text-slate-600 border-slate-300 hover:border-slate-400'
                          }`}
                        >
                          {l === 'OR' ? 'OR — alguna regla' : 'AND — todas las reglas'}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Toggle activar DJ si requiere conformidad */}
              <div className="flex items-center gap-3 p-4 border border-slate-200 rounded-lg">
                <button
                  type="button"
                  role="switch"
                  aria-checked={activarSiRequiereConformidad}
                  onClick={() => { setActivarSiRequiereConformidad(!activarSiRequiereConformidad); setSaved(false) }}
                  className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 ${
                    activarSiRequiereConformidad ? 'bg-slate-800' : 'bg-slate-200'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      activarSiRequiereConformidad ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
                <div className="flex-1">
                  <p className="text-sm font-medium text-slate-800">
                    {activarSiRequiereConformidad ? 'DJ automática si RequiereConformidad = 1' : 'No activar DJ automáticamente'}
                  </p>
                  <p className="text-xs text-slate-500">
                    {activarSiRequiereConformidad
                      ? 'Se activa la DJ automáticamente cuando la plataforma indica que la operación requiere conformidad'
                      : 'La DJ solo se activa según las reglas configuradas arriba'}
                  </p>
                </div>
              </div>

              {/* Toggle incluir texto en minuta */}
              <div className="flex items-center gap-3 p-4 border border-slate-200 rounded-lg">
                <button
                  type="button"
                  role="switch"
                  aria-checked={incluirTexto}
                  onClick={() => { setIncluirTexto(!incluirTexto); setSaved(false) }}
                  className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 ${
                    incluirTexto ? 'bg-slate-800' : 'bg-slate-200'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      incluirTexto ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
                <div className="flex-1">
                  <p className="text-sm font-medium text-slate-800">
                    {incluirTexto ? 'Incluir texto en la minuta' : 'Solo aviso visual (⚠)'}
                  </p>
                  <p className="text-xs text-slate-500">
                    {incluirTexto
                      ? 'El texto de alerta se agrega al cuerpo de la minuta — Middle Office puede copiar todo en un paso'
                      : 'La minuta muestra ⚠ "Requiere DJ" pero Middle Office adjunta el documento DJ manualmente'}
                  </p>
                </div>
              </div>

              {/* Textarea texto de alerta — solo si incluirTexto */}
              {incluirTexto && (
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-700 flex items-center gap-1.5">
                    <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
                    Texto de alerta DJ
                  </label>
                  <p className="text-xs text-slate-500">
                    Podés usar las mismas variables que en la plantilla. Hacé clic en un botón para insertar en la posición del cursor.
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {DJ_VARIABLES.map((v) => (
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
                    rows={8}
                    className="font-mono text-sm resize-none"
                    placeholder="Ej: El cliente {cliente_nombre} debe presentar Declaración Jurada por operación de {cantidad} títulos de {instrumento}..."
                  />
                </div>
              )}
            </>
          )}
        </div>
      )}

      <div className="flex items-center gap-3">
        <Button
          onClick={handleGuardar}
          disabled={guardar.isPending || !modificado}
        >
          {guardar.isPending ? 'Guardando...' : 'Guardar configuración'}
        </Button>
        {saved && (
          <span className="text-sm text-green-600">Guardado</span>
        )}
      </div>
    </div>
  )
}
