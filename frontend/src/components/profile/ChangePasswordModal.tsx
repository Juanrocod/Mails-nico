import { useState } from 'react'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { changePassword } from '../../services/auth'

interface Props {
  open: boolean
  onClose: () => void
}

export default function ChangePasswordModal({ open, onClose }: Props) {
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)

  function reset() {
    setOldPassword('')
    setNewPassword('')
    setConfirmPassword('')
    setError('')
    setSuccess(false)
  }

  function handleClose() {
    reset()
    onClose()
  }

  function validatePassword(p: string): string | null {
    if (p.length < 8) return 'La contraseña debe tener al menos 8 caracteres'
    if (!/[A-Z]/.test(p)) return 'La contraseña debe tener al menos una mayúscula'
    if (!/[0-9]/.test(p)) return 'La contraseña debe tener al menos un número'
    return null
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    const pwError = validatePassword(newPassword)
    if (pwError) { setError(pwError); return }
    if (newPassword !== confirmPassword) {
      setError('Las contraseñas nuevas no coinciden')
      return
    }
    setLoading(true)
    try {
      await changePassword(oldPassword, newPassword)
      setSuccess(true)
    } catch (err: any) {
      if (err?.response?.status === 401) {
        setError('La contraseña actual es incorrecta')
      } else {
        setError('Error al cambiar la contraseña')
      }
    } finally {
      setLoading(false)
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-lg border border-slate-200 p-6 w-full max-w-sm space-y-4">
        <h2 className="text-base font-semibold text-slate-900">Cambiar contraseña</h2>

        {success ? (
          <div className="space-y-4">
            <p className="text-sm text-green-700 bg-green-50 border border-green-200 rounded-md px-3 py-2">
              Contraseña actualizada correctamente.
            </p>
            <Button className="w-full" onClick={handleClose}>Cerrar</Button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-600">Contraseña actual</label>
              <Input
                type="password"
                value={oldPassword}
                onChange={(e) => setOldPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-600">Nueva contraseña</label>
              <Input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="mínimo 8 caracteres"
                required
                autoComplete="new-password"
              />
              <p className="text-xs text-slate-400 mt-1">
                Mínimo 8 caracteres, una mayúscula y un número.
              </p>
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-600">Confirmar nueva contraseña</label>
              <Input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                autoComplete="new-password"
              />
            </div>
            {error && <p className="text-xs text-red-600">{error}</p>}
            <div className="flex gap-2 pt-1">
              <Button type="button" variant="outline" className="flex-1" onClick={handleClose} disabled={loading}>
                Cancelar
              </Button>
              <Button type="submit" className="flex-1" disabled={loading}>
                {loading ? 'Guardando...' : 'Guardar'}
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
