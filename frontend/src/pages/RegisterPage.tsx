import { useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { QRCodeSVG } from 'qrcode.react'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { register, confirmRegister } from '../services/auth'

type Step = 'form' | 'qr'

export default function RegisterPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const token = params.get('token') ?? ''

  const [step, setStep] = useState<Step>('form')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [totpUri, setTotpUri] = useState('')
  const [setupToken, setSetupToken] = useState('')
  const [totpCode, setTotpCode] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    if (password !== confirmPassword) {
      setError('Las contraseñas no coinciden')
      return
    }
    if (password.length < 8) {
      setError('La contraseña debe tener al menos 8 caracteres')
      return
    }
    setLoading(true)
    try {
      const data = await register(token, username, password)
      setTotpUri(data.totp_uri)
      setSetupToken(data.setup_token)
      setStep('qr')
    } catch (err: any) {
      if (err?.response?.status === 409) {
        setError('Ese nombre de usuario ya está en uso')
      } else if (err?.response?.status === 400) {
        setError('El link de registro es inválido o expiró')
      } else {
        setError(err?.response?.data?.detail ?? 'Error al registrarse')
      }
    } finally {
      setLoading(false)
    }
  }

  async function handleConfirm(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await confirmRegister(setupToken, totpCode)
      navigate('/login', { state: { registered: true } })
    } catch (err: any) {
      if (err?.response?.status === 401) {
        setError('Código incorrecto. Verificá que escaneaste el QR y que la hora de tu dispositivo es correcta.')
      } else {
        setError('Error al confirmar. Intentá de nuevo.')
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
            Necesitás un link de invitación válido para registrarte.
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
          <h1 className="text-xl font-semibold text-slate-900 mt-3">
            {step === 'form' ? 'Crear cuenta' : 'Configurar Authenticator'}
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            {step === 'form'
              ? 'Elegí tu usuario y contraseña.'
              : 'Escaneá el código QR con Google Authenticator o Authy, luego ingresá el código de 6 dígitos.'}
          </p>
        </div>

        {step === 'form' && (
          <form onSubmit={handleRegister} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">Usuario</label>
              <Input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="tu_usuario"
                required
                autoComplete="username"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">Contraseña</label>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="mínimo 8 caracteres"
                required
                autoComplete="new-password"
              />
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
              {loading ? 'Creando cuenta...' : 'Continuar'}
            </Button>
          </form>
        )}

        {step === 'qr' && (
          <form onSubmit={handleConfirm} className="space-y-5">
            <div className="flex justify-center">
              <div className="p-3 bg-white border border-slate-200 rounded-lg">
                <QRCodeSVG value={totpUri} size={180} />
              </div>
            </div>
            <p className="text-xs text-slate-500 text-center">
              Si no podés escanear el QR, copiá este código en tu app:
              <br />
              <span className="font-mono text-slate-700 break-all">
                {totpUri.split('secret=')[1]?.split('&')[0] ?? ''}
              </span>
            </p>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">
                Código del Authenticator (6 dígitos)
              </label>
              <Input
                type="text"
                inputMode="numeric"
                maxLength={6}
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
                placeholder="123456"
                required
                autoComplete="one-time-code"
              />
            </div>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <Button type="submit" className="w-full" disabled={loading || totpCode.length !== 6}>
              {loading ? 'Verificando...' : 'Confirmar y activar cuenta'}
            </Button>
          </form>
        )}
      </div>
    </div>
  )
}
