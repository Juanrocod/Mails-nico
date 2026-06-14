import axios from 'axios'

let accessToken: string | null = null
let refreshToken: string | null = null
let onUnauthenticated: (() => void) | null = null

export function setTokens(access: string, refresh: string): void {
  accessToken = access
  refreshToken = refresh
}

export function clearTokens(): void {
  accessToken = null
  refreshToken = null
}

export function getAccessToken(): string | null {
  return accessToken
}

export function setUnauthenticatedHandler(fn: () => void): void {
  onUnauthenticated = fn
}

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
})

api.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as typeof error.config & { _retry?: boolean }
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      refreshToken
    ) {
      originalRequest._retry = true
      try {
        const res = await axios.post(
          `${import.meta.env.VITE_API_URL}/auth/refresh`,
          { refresh_token: refreshToken }
        )
        setTokens(res.data.access_token, res.data.refresh_token)
        originalRequest.headers.Authorization = `Bearer ${res.data.access_token}`
        return api(originalRequest)
      } catch {
        clearTokens()
        onUnauthenticated?.()
        return Promise.reject(error)
      }
    }
    return Promise.reject(error)
  }
)
