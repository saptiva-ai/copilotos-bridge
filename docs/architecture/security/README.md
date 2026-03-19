# Seguridad

> Documentación de seguridad del proyecto.

## Índice

| Documento | Descripción |
|-----------|-------------|
| [SECURITY.md](SECURITY.md) | Políticas y prácticas de seguridad |
| [updates/](updates/) | Actualizaciones de seguridad |

## Prácticas de Seguridad

### SQL Injection Prevention (Bank Advisor)
El plugin Bank Advisor implementa 5 capas de validación SQL:
1. Keyword blacklist (no DDL/DML)
2. Table whitelist
3. Pattern detection
4. LIMIT enforcement
5. RLS ready

Ver [../context/BANK_ADVISOR.md](../context/BANK_ADVISOR.md) para detalles.

### Autenticación
- JWT con refresh tokens
- Redis blacklist para logout
- Scopes: `mcp:tools.*`, `mcp:admin.*`

### Secrets
- Variables sensibles en `envs/.env`
- Pre-commit hook para detección de secrets
- Nunca commitear `.env` con valores reales

## Reportar Vulnerabilidades

Contactar al equipo de seguridad antes de disclosure público.
