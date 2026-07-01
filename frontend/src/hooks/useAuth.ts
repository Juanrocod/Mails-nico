import { useNavigate } from 'react-router-dom'
import { login, logout as logoutApi } from '../services/auth'
import { getAccessToken } from '../services/api'

export function useAuth() {
  const navigate = useNavigate()

  async function handleLogin(username: string, password: string): Promise<void> {
    await login(username, password)
    navigate('/seguimiento/no-contestados')
  }

  async function handleLogout(): Promise<void> {
    try {
      await logoutApi()
    } catch {
      // continuar aunque falle la red — siempre limpiar estado local
    } finally {
      navigate('/login')
    }
  }

  function isAuthenticated(): boolean {
    return getAccessToken() !== null
  }

  return { handleLogin, handleLogout, isAuthenticated }
}
