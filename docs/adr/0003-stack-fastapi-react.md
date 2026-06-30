# ADR-0003: Stack Python FastAPI + React

## Estado
Aceptado

## Contexto
Se evaluaron dos stacks: Node.js + React (unificado en JS) y Python FastAPI + React. El proyecto parte de la base de Mails-finanzas que ya usa FastAPI + React.

## Decisión
Python FastAPI para el backend, React 18 + TypeScript para el frontend.

## Consecuencias
- **Positivo:** Reutiliza la base de código de Mails-finanzas (auth, excel parser, estructura de proyecto).
- **Positivo:** El ecosistema Python tiene excelentes librerías para Excel (openpyxl, pandas), email (smtplib, imaplib) y templates (Jinja2, premailer).
- **Positivo:** FastAPI soporta SSE y background tasks asyncio nativamente, necesarios para el progreso de envío y el IMAP Watcher.
- **Neutro:** React con shadcn/ui ya está configurado y probado en el proyecto base.
