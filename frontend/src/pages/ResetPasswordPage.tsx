import { useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { resetPassword } from '../services/auth'

interface Rule { label: string; ok: boolean }

function getPasswordRules(p: string): Rule[] {
  return [
    { label: 'Al menos 8 caracteres', ok: p.length >= 8 },
    { label: 'Una letra mayúscula (A-Z)', ok: /[A-Z]/.test(p) },
    { label: 'Un número (0-9)', ok: /[0-9]/.test(p) },
    { label: 'Un carácter especial (!@#$...)', ok: /[^a-zA-Z0-9]/.test(p) },
  ]
}

export default function ResetPasswordPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const token = params.get('token') ?? ''

  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [serverError, setServerError] = useState('')
  const [loading, setLoading] = useState(false)
  const [touched, setTouched] = useState(false)

  const rules = getPasswordRules(password)
  const passwordValid = rules.every(r => r.ok)
  const passwordsMatch = password === confirmPassword
  const confirmTouched = confirmPassword.length > 0

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="max-w-sm w-full text-center space-y-2">
          <p className="text-slate-700 font-medium">Link inválido</p>
          <p className="text-sm text-slate-500">
            Necesitás un link de reset válido. Pedíselo al administrador.
          </p>
        </div>
      </div>
    )
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setTouched(true)
    setServerError('')
    if (!passwordValid || !passwordsMatch) return
    setLoading(true)
    try {
      await resetPassword(token, password)
      navigate('/login', { state: { passwordReset: true } })
    } catch (err: any) {
      const status = err?.response?.status
      if (status === 400) {
        setServerError('El link de reset es inválido o ya expiró. Pedile al administrador un nuevo link.')
      } else if (status === 422) {
        setServerError('La contraseña no cumple los requisitos de seguridad del servidor.')
      } else if (status === 429) {
        setServerError('Demasiados intentos. Esperá un minuto y volvé a intentar.')
      } else {
        setServerError(`Error inesperado (código ${status ?? 'sin respuesta'}). Intentá de nuevo.`)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="max-w-sm w-full bg-white rounded-xl shadow-sm border border-slate-200 p-8 space-y-6">
        <div>
          <p className="text-sm font-semibold text-slate-900">Gestión de Minutas</p>
          <h1 className="text-xl font-semibold text-slate-900 mt-3">Nueva contraseña</h1>
          <p className="text-sm text-slate-500 mt-1">
            Tu Authenticator no cambia — solo actualizás la contraseña.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-slate-700">Nueva contraseña</label>
            <Input
              type="password"
              value={password}
              onChange={(e) => { setPassword(e.target.value); setTouched(false) }}
              placeholder="mínimo 8 caracteres"
              autoComplete="new-password"
            />
            {/* Indicadores de requisitos en tiempo real */}
            {(password.length > 0 || touched) && (
              <ul className="mt-2 space-y-1">
                {rules.map(r => (
                  <li key={r.label} className={`text-xs flex items-center gap-1.5 ${r.ok ? 'text-green-600' : 'text-red-500'}`}>
                    <span>{r.ok ? '✓' : '✗'}</span>
                    {r.label}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-medium text-slate-700">Confirmar contraseña</label>
            <Input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="repetí la contraseña"
              autoComplete="new-password"
            />
            {confirmTouched && !passwordsMatch && (
              <p className="text-xs text-red-500 mt-1">Las contraseñas no coinciden</p>
            )}
            {confirmTouched && passwordsMatch && confirmPassword.length > 0 && (
              <p className="text-xs text-green-600 mt-1">✓ Las contraseñas coinciden</p>
            )}
          </div>

          {serverError && (
            <p role="alert" className="text-sm text-red-600 bg-red-50 rounded px-3 py-2">
              {serverError}
            </p>
          )}

          <Button
            type="submit"
            className="w-full"
            disabled={loading}
          >
            {loading ? 'Guardando...' : 'Guardar contraseña'}
          </Button>
        </form>
      </div>
    </div>
  )
}
