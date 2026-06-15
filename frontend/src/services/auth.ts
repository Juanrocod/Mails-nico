import { api } from './api'
import type { LoginResponse, TokenResponse } from '../types/domain'

let pendingToken: string | null = null

export function setPendingToken(token: string): void {
  pendingToken = token
}

export function getPendingToken(): string | null {
  return pendingToken
}

export function clearPendingToken(): void {
  pendingToken = null
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const res = await api.post<LoginResponse>('/auth/login', { username, password })
  return res.data
}

export async function verifyTotp(pending_token: string, code: string): Promise<TokenResponse> {
  const res = await api.post<TokenResponse>('/auth/verify-totp', { pending_token, code })
  return res.data
}

export async function logout(): Promise<void> {
  await api.post('/auth/logout')
}

export async function register(
  token: string,
  username: string,
  password: string
): Promise<{ totp_uri: string; setup_token: string }> {
  const res = await api.post('/auth/register', { token, username, password })
  return res.data
}

export async function confirmRegister(
  setup_token: string,
  totp_code: string
): Promise<void> {
  await api.post('/auth/register/confirm', { setup_token, totp_code })
}

export async function resetPassword(token: string, password: string): Promise<void> {
  await api.post('/auth/reset-password', { token, password })
}

export async function changePassword(
  old_password: string,
  new_password: string
): Promise<void> {
  await api.post('/auth/change-password', { old_password, new_password })
}

export async function regenerateTotp(
  totp_code: string
): Promise<{ totp_uri: string }> {
  const res = await api.post('/auth/regenerate-totp', { totp_code })
  return res.data
}
