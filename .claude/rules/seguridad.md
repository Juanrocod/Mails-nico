---
paths:
  - "backend/app/core/security.py"
  - "backend/app/core/dependencies.py"
  - "backend/app/routers/auth.py"
  - "backend/app/services/auth.py"
  - "backend/app/services/config_service.py"
  - "frontend/src/services/api.ts"
---

## Autenticación

- JWT firmado con `SECRET_KEY` (mínimo 32 chars). Passwords con **bcrypt**. Sin 2FA (ADR 0004).
- Endpoints protegidos: `Depends(get_current_user)`.
- Login con **rate limiting** (slowapi / `limiter`) — no quitarlo.
- Tokens en el frontend viven en `localStorage` (accesible a JS → riesgo XSS). Aceptado en el
  MVP; si se endurece, mover a cookie httpOnly + CSRF.

## Credenciales de email

- Yahoo/Gmail app passwords se guardan **cifradas con Fernet** (`ENCRYPTION_KEY`) en
  `configuracion_sistema`. Nunca en texto plano, nunca en logs.
- `decrypt` puede tirar `InvalidToken` si la key cambió → capturar, no propagar a 500.
- Si `ENCRYPTION_KEY` cambia, las credenciales guardadas quedan ilegibles y hay que recargarlas.

## Transporte y headers

- Prod es HTTPS (Vercel + Render). SMTP/IMAP usan STARTTLS/SSL.
- `SecurityHeadersMiddleware`: `X-Content-Type-Options`, `X-Frame-Options: DENY`,
  `Referrer-Policy`, `Permissions-Policy`. No quitarlos.
- **CORS**: `ALLOWED_ORIGINS` explícito (coma-separado) + `allow_credentials=True`.
  Debe listar el/los origin(s) del frontend (Vercel), **sin barra final**. Nunca `*` con credenciales.

## Secretos

- `.env`, `.env.production` → **gitignored**, nunca commitear. Sólo `.env.example` con placeholders.
- Generar: `SECRET_KEY` = `secrets.token_urlsafe(48)`; `ENCRYPTION_KEY` = `Fernet.generate_key()`.
- Prod y dev usan claves distintas. Si un secreto se expone (logs, chat), **rotarlo**.

## Unsubscribe

- `GET /unsubscribe/{token}` usa token firmado (ver `test_security_unsubscribe_token`).
  No exponer IDs crudos; el token no debe ser adivinable.
