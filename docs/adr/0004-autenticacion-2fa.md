# ADR-0004: Autenticación con 2FA, sesiones con expiración y log de accesos

## Estado
Aceptado

## Contexto
El sistema maneja órdenes bursátiles con implicancias regulatorias (CNV). La seguridad de acceso es prioritaria. Se evaluaron: autenticación simple (usuario/contraseña), 2FA, y SSO corporativo.

## Decisión
Autenticación con usuario, contraseña y segundo factor (2FA via app autenticadora). Sesiones con expiración automática. Log de todos los accesos (usuario, IP, timestamp, éxito/fallo).

## Consecuencias
- **Positivo:** Protección ante accesos no autorizados incluso si una contraseña es comprometida.
- **Positivo:** El log de accesos es parte del Audit Trail requerido para compliance CNV.
- **Positivo:** Las sesiones con expiración minimizan el riesgo de sesiones abandonadas en terminales compartidas.
- **Neutro:** Si el broker adopta SSO corporativo (Azure AD / Microsoft 365) en el futuro, se puede reemplazar este mecanismo sin cambiar el resto del sistema.
