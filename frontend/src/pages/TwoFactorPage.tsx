import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { useAuth } from '../hooks/useAuth'

interface FormValues {
  code: string
}

export default function TwoFactorPage() {
  const navigate = useNavigate()
  const { handleVerify2fa } = useAuth()
  const [error, setError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    formState: { isSubmitting, errors },
  } = useForm<FormValues>()

  async function onSubmit(data: FormValues) {
    try {
      setError(null)
      await handleVerify2fa(data.code)
    } catch {
      setError('Código inválido. Revisá tu aplicación de autenticación.')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center space-y-1">
          <h1 className="text-2xl font-semibold text-slate-900">Verificación 2FA</h1>
          <p className="text-sm text-slate-500">
            Ingresá el código de tu aplicación de autenticación
          </p>
        </div>

        <form
          onSubmit={handleSubmit(onSubmit)}
          className="space-y-4 bg-white p-6 rounded-lg border border-slate-200 shadow-sm"
        >
          <div className="space-y-1.5">
            <label htmlFor="code" className="text-sm font-medium text-slate-700">
              Código de 6 dígitos
            </label>
            <Input
              id="code"
              {...register('code', {
                required: 'El código es obligatorio',
                minLength: { value: 6, message: 'El código debe tener 6 dígitos' },
                maxLength: { value: 6, message: 'El código debe tener 6 dígitos' },
                pattern: { value: /^\d{6}$/, message: 'Solo se aceptan números' },
              })}
              placeholder="000000"
              inputMode="numeric"
              autoComplete="one-time-code"
              className="text-center text-xl tracking-[0.5em]"
              maxLength={6}
            />
            {errors.code && (
              <p className="text-xs text-red-600">{errors.code.message}</p>
            )}
          </div>

          {error && (
            <p role="alert" className="text-sm text-red-600 bg-red-50 rounded px-3 py-2">
              {error}
            </p>
          )}

          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? 'Verificando...' : 'Verificar'}
          </Button>

          <Button
            type="button"
            variant="ghost"
            className="w-full text-sm text-slate-500"
            onClick={() => navigate('/login')}
          >
            Volver al login
          </Button>
        </form>
      </div>
    </div>
  )
}
