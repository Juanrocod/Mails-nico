# ADR-0004: Autenticación simple sin 2FA

## Estado
Aceptado

## Contexto
El proyecto base (Mails-finanzas) implementa autenticación con JWT + bcrypt + TOTP 2FA obligatorio, requerido por el contexto regulatorio CNV del broker. Este sistema no tiene esos requerimientos.

## Decisión
Autenticación con usuario + contraseña + JWT. Sin 2FA. Sin registro público. Un único usuario operario creado via seed script.

## Consecuencias
- **Positivo:** Setup inicial más simple para el cliente.
- **Positivo:** Elimina dependencia de pyotp, pantalla TwoFactor, gestión de TOTP secrets.
- **Negativo:** Menor seguridad ante acceso físico a la terminal. Mitigado por ser un sistema de uso personal del dueño, sin datos regulados.
- **Conservado:** JWT con expiración de 8 horas, bcrypt cost factor 12, rate limiting en login (5 intentos/min/IP), log de accesos.
