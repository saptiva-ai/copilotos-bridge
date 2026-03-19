# Agents Parking

Agents inactivos (sin uso en 2+ semanas) se mueven aquí para reducir delegación accidental.

## Comandos

```bash
# Parkear un agente
mv .claude/agents/<agent>.md .claude/agents_parking/

# Reactivar un agente
mv .claude/agents_parking/<agent>.md .claude/agents/
```

## Reglas

- NO eliminar agentes parkeados
- Revisar antes de crear nuevos agentes
- Ver `.claude/rules/60_agent_hygiene.md` para detalles
