import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useLocation } from 'react-router-dom'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { useAuth } from '../hooks/useAuth'

interface FormValues {
  username: string
  password: string
}

export default function LoginPage() {
  const { handleLogin } = useAuth()
  const location = useLocation()
  const passwordReset = (location.state as any)?.passwordReset === true
  const [error, setError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    formState: { isSubmitting, errors },
  } = useForm<FormValues>()

  async function onSubmit(data: FormValues) {
    try {
      setError(null)
      await handleLogin(data.username, data.password)
    } catch {
      setError('Credenciales inválidas. Verificá tu usuario y contraseña.')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center space-y-1">
          <h1 className="text-2xl font-semibold text-slate-900">Gestión de Minutas</h1>
          <p className="text-sm text-slate-500">Ingresá con tus credenciales</p>
        </div>

        <form
          onSubmit={handleSubmit(onSubmit)}
          className="space-y-4 bg-white p-6 rounded-lg border border-slate-200 shadow-sm"
        >
          <div className="space-y-1.5">
            <label htmlFor="username" className="text-sm font-medium text-slate-700">
              Usuario
            </label>
            <Input
              id="username"
              {...register('username', { required: 'El usuario es obligatorio' })}
              placeholder="usuario"
              autoComplete="username"
            />
            {errors.username && (
              <p className="text-xs text-red-600">{errors.username.message}</p>
            )}
          </div>

          <div className="space-y-1.5">
            <label htmlFor="password" className="text-sm font-medium text-slate-700">
              Contraseña
            </label>
            <Input
              id="password"
              {...register('password', { required: 'La contraseña es obligatoria' })}
              type="password"
              placeholder="••••••••"
              autoComplete="current-password"
            />
            {errors.password && (
              <p className="text-xs text-red-600">{errors.password.message}</p>
            )}
          </div>

          {passwordReset && (
            <p className="text-sm text-green-700 bg-green-50 rounded px-3 py-2">
              Contraseña actualizada. Ingresá con tu nueva contraseña.
            </p>
          )}

          {error && (
            <p role="alert" className="text-sm text-red-600 bg-red-50 rounded px-3 py-2">
              {error}
            </p>
          )}

          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? 'Ingresando...' : 'Ingresar'}
          </Button>

          <p className="text-center text-xs text-slate-400">
            ¿Olvidaste tu contraseña? Contactá a tu administrador.
          </p>
        </form>
      </div>
    </div>
  )
}
