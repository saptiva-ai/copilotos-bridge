# TASK: Evolución Multiagente BankAdvisor

**Status**: `PLANNED`
**Priority**: `HIGH`
**Estimated Effort**: 6 weeks

---

## Summary

Diseñar e implementar una arquitectura multiagente segura para BankAdvisor que:
1. Responda consultas desde MVs como fuente primaria, con fallback a base completa
2. Utilice Weaviate para almacenar pares Q&A y permitir búsqueda vectorial
3. Ejecute código en un sandbox seguro con validación de inputs y rate limiting

## Acceptance Criteria

- [ ] Colecciones Weaviate `QA_Pairs_Banking` y `SQL_Examples` creadas
- [ ] Pipeline de generación de Q&A funcional (>500 pares iniciales)
- [ ] Estrategia MV-First implementada en todos los handlers
- [ ] Sandbox de ejecución con todas las protecciones activas
- [ ] Rate limiting configurado (100/user, 500/agent, 10k/global)
- [ ] Tests E2E multiagente pasando
- [ ] Métricas de hit rate y performance monitoreadas

## Technical Context

### Current State
- 15+ handlers especializados
- Weaviate solo para ontología (`Ontology_Term_V2`)
- Sin estrategia explícita de fallback MV→DB
- Sin sandbox para ejecución de código dinámico

### Target State
- Orchestrator multiagente
- Weaviate con Q&A cache + ontología + SQL examples
- MV-First strategy con métricas de fallback
- Sandbox seguro con AST validation + rate limiting

## Dependencies

- Weaviate 1.24+ con `text2vec-transformers`
- PostgreSQL con MVs actualizados
- Python 3.11+

## Related Files

- `plugins/bank-advisor-private/src/bankadvisor/`
- `docs/kanban/multiagent-evolution/plan.md`

## Timeline

| Phase | Duration | Status |
|-------|----------|--------|
| 1. Infraestructura Weaviate | 1 week | `TODO` |
| 2. MV-First Strategy | 1 week | `TODO` |
| 3. Secure Sandbox | 1.5 weeks | `TODO` |
| 4. Multi-Agent Integration | 1.5 weeks | `TODO` |
| 5. Monitoring & Optimization | 1 week | `TODO` |

---

## Notes

- Plan detallado en `plan.md`
- Seguir flujo: Explore → Plan → Code → Test → Review → Docs
