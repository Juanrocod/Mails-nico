// frontend/src/pages/PlantillaPage.tsx
import { useState, useRef } from 'react'
import { Textarea } from '../components/ui/textarea'
import { Button } from '../components/ui/button'

const VARIABLES: { label: string; token: string }[] = [
  { label: 'Nombre cliente',    token: '{cliente_nombre}' },
  { label: 'Cta. comitente',   token: '{cuenta_comitente}' },
  { label: 'Cta. cotapartista',token: '{cuenta_cotapartista}' },
  { label: 'Nº orden',         token: '{id_orden}' },
  { label: 'Fecha operación',  token: '{fecha_operacion}' },
  { label: 'Fecha liquidación',token: '{fecha_liquidacion}' },
  { label: 'Operación',        token: '{operacion}' },
  { label: 'Instrumento',      token: '{instrumento}' },
  { label: 'Moneda',           token: '{moneda}' },
  { label: 'Cantidad',         token: '{cantidad}' },
  { label: 'Precio',           token: '{precio}' },
  { label: 'Monto',            token: '{monto}' },
  { label: 'Estado',           token: '{estado}' },
  { label: 'Asesor',           token: '{asesor}' },
]

export default function PlantillaPage() {
  const [texto, setTexto] = useState('')
  const [saved, setSaved] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  function insertarVariable(token: string) {
    const el = textareaRef.current
    if (!el) return
    const start = el.selectionStart ?? texto.length
    const end = el.selectionEnd ?? texto.length
    const next = texto.slice(0, start) + token + texto.slice(end)
    setTexto(next)
    setSaved(false)
    requestAnimationFrame(() => {
      el.focus()
      const pos = start + token.length
      el.setSelectionRange(pos, pos)
    })
  }

  async function handleGuardar() {
    // placeholder: guardar funcionalidad removida
  }

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Plantilla Estándar</h2>
        <p className="text-sm text-slate-500 mt-1">
          Texto del mail. Usá los botones para insertar variables que se reemplazan
          con los datos de cada operación al generar las minutas.
        </p>
      </div>

      {/* Botones de variables */}
      <div className="flex flex-wrap gap-1.5">
        {VARIABLES.map(({ label, token }) => (
          <button
            key={token}
            type="button"
            onClick={() => insertarVariable(token)}
            className="px-2 py-1 text-xs font-mono bg-slate-100 hover:bg-slate-200 text-slate-700 rounded border border-slate-200 transition-colors"
          >
            {label}
          </button>
        ))}
      </div>

      <Textarea
        ref={textareaRef}
        value={texto}
        onChange={(e) => { setTexto(e.target.value); setSaved(false) }}
        rows={18}
        className="font-mono text-sm resize-none"
        placeholder="Ingresá el texto de la plantilla estándar..."
      />

      <div className="flex items-center gap-3">
        <Button onClick={handleGuardar} disabled={true}>
          Guardar plantilla
        </Button>
        {saved && <span className="text-sm text-green-600">Guardado</span>}
      </div>
    </div>
  )
}
