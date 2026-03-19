# Commit & PR Authorship

When this applies: all git commits and PRs.

## Policy
- **NO** `Co-Authored-By: Claude` in commits
- **NO** AI attribution in PRs
- All commits authored solely by user (git config)

## Format
```
<type>(<scope>): <description>

Implementación:
- <cambios concretos>

Logros:
- <resultados verificables>

Testing:
- <tests y resultados, ej: "21/21 passed">

Siguientes pasos:
- <pendiente o "Ninguno">
```

Types: feat | fix | docs | style | refactor | test | chore

## Example
```
fix(handler): add PE sin gobierno metric routing

Implementación:
- Agregar regex _PE_RE para detectar "pérdida esperada"
- Reescribir _detect_metric() con prioridad 3 capas

Logros:
- "pérdida esperada sin gobierno" rutea a pe_sg correctamente

Testing:
- 60/60 unit tests passed

Siguientes pasos:
- Validar E2E con backend en PROD
```
