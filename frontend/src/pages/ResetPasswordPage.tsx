import { useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { resetPassword } from '../services/auth'

export default function ResetPasswordPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const token = params.get('token') ?? ''

  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function validatePassword(p: string): string | null {
    if (p.length < 8) return 'La contraseña debe tener al menos 8 caracteres'
    if (!/[A-Z]/.test(p)) return 'La contraseña debe tener al menos una mayúscula'
    if (!/[0-9]/.test(p)) return 'La contraseña debe tener al menos un número'
    if (!/[^a-zA-Z0-9]/.test(p)) return 'La contraseña debe tener al menos un carácter especial (!@#$...)'
    return null
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    const pwError = validatePassword(password)
    if (pwError) { setError(pwError); return }
    if (password !== confirmPassword) {
      setError('Las contraseñas no coinciden')
      return
    }
    setLoading(true)
    try {
      await resetPassword(token, password)
      navigate('/login', { state: { passwordReset: true } })
    } catch (err: any) {
      if (err?.response?.status === 400) {
        setError('El link de reset es inválido o expiró. Pedile al administrador un nuevo link.')
      } else {
        setError('Error al cambiar la contraseña. Intentá de nuevo.')
      }
    } finally {
      setLoading(false)
    }
  }

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

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="max-w-sm w-full bg-white rounded-xl shadow-sm border border-slate-200 p-8 space-y-6">
        <div>
          <p className="text-sm font-semibold text-slate-900">Gestión de Minutas</p>
          <h1 className="text-xl font-semibold text-slate-900 mt-3">Nueva contraseña</h1>
          <p className="text-sm text-slate-500 mt-1">
            Tu Authenticator no cambia — solo actualizás tu contraseña.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-slate-700">Nueva contraseña</label>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="mínimo 8 caracteres"
              required
              autoComplete="new-password"
            />
            <p className="text-xs text-slate-400 mt-1">
              Mínimo 8 caracteres, una mayúscula, un número y un carácter especial (!@#$...).
            </p>
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-slate-700">Confirmar contraseña</label>
            <Input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="repetí la contraseña"
              required
              autoComplete="new-password"
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? 'Guardando...' : 'Guardar contraseña'}
          </Button>
        </form>
      </div>
    </div>
  )
}
