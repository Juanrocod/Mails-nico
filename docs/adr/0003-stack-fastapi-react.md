# ADR-0003: Stack Python FastAPI + React

## Estado
Aceptado

## Contexto
Se evaluaron dos stacks principales para el desarrollo: .NET (C#) + React, alineado con el ecosistema Microsoft del broker, y Python FastAPI + React. El desarrollador principal es Claude Code (IA).

## Decisión
Python FastAPI para el backend, React para el frontend.

## Consecuencias
- **Positivo:** FastAPI permite desarrollo más rápido con menos boilerplate que .NET para este tipo de aplicación.
- **Positivo:** El ecosistema Python tiene excelentes librerías para procesamiento de Excel (openpyxl, pandas), generación de PDF y autenticación.
- **Positivo:** La integración con Microsoft Graph API (Fase 2) tiene SDK oficial para Python.
- **Neutro:** La integración con Azure es igual de completa desde Python que desde .NET.
- **Negativo:** Si el broker tiene equipos internos de .NET, el mantenimiento futuro puede requerir capacitación.
