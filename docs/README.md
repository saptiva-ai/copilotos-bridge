# 📚 Copilotos Bridge Documentation

Recopilación actualizada de guías, procedimientos y evidencias para Copilotos Bridge.

---

## 📋 Post-Mortems & Bug Fixes
- **[Auto-Titling Fix (2025-10-07)](post-mortem-auto-titling-fix.md)** - Solución del sistema de auto-generación de títulos con IA
  - Root cause: Detección incorrecta de conversaciones nuevas por timing de reconciliación optimista
  - Solución: Detección basada en `messages.length === 0`
  - Resultado: 100% de conversaciones con títulos generados por IA ✅

## 🚀 Guías Iniciales
- [Quick Start Guide](guides/QUICK_START.md)
- [Credentials Reference](guides/CREDENTIALS.md)

## 🚢 Deploy & Operaciones
- [Quick Deployment Cheatsheet](QUICK-DEPLOY.md)
- [Secure Production Deployment Guide](DEPLOYMENT.md)
- [Deployment Playbook](deployment/README.md)
- [Setup](setup/PRODUCTION_SETUP.md) · [Checklist](setup/PRODUCTION_CHECKLIST.md) · [Docker Compose Notes](setup/DEPLOYMENT.md)
- Archivos de entorno de ejemplo: [`setup/.env.production.example`](setup/.env.production.example), [`setup/.env.staging.example`](setup/.env.staging.example)

## 🏗️ Arquitectura y Flujos
- Diagramas y flujos LLM: [`arquitectura/`](arquitectura/)
- Casos de corrección UX/overlay: [`bugfixes/UI-OVL-001.yaml`](bugfixes/UI-OVL-001.yaml)

## 🔍 Evidencias y QA
- Evidencias funcionales: [`evidencias/`](evidencias/)
- Planes/manuales de prueba: [`testing/`](testing/)

## 🔄 CI/CD y Entrega
- Guías de pipeline empresarial y despliegues automatizados: [`ci-cd/`](ci-cd/)
- Documentación detallada de scripts de despliegue: [`../scripts/README-DEPLOY.md`](../scripts/README-DEPLOY.md)

## 🗂️ Archivo Histórico
Los documentos legacy y reportes de releases se movieron a [`archive/`](archive/), por ejemplo:
- [DEPLOYMENT-BEST-PRACTICES.md](archive/DEPLOYMENT-BEST-PRACTICES.md)
- [DEPLOYMENT-READY-v1.2.1.md](archive/DEPLOYMENT-READY-v1.2.1.md)
- [DEPLOYMENT-TAR-GUIDE.md](archive/DEPLOYMENT-TAR-GUIDE.md)
- [QUICKSTART-DEPLOY.md](archive/QUICKSTART-DEPLOY.md)
- [BACKLOG_RECONCILIADO.md](archive/BACKLOG_RECONCILIADO.md)

Revisa esta carpeta cuando necesites contexto histórico o notas de releases anteriores.

## 📌 Otros Recursos
- Registro de cambios: [CHANGELOG.md](CHANGELOG.md)
- Makefile con comandos clave: [`../Makefile`](../Makefile) (usa `make help`)
