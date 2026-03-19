# MongoDB Full Backup

Backup completo de la base de datos `octavios` de PROD (invex.saptiva.com).

- **Fecha**: 2026-02-16
- **Fuente**: PROD server (octavios-chat-bajaware_invex-mongodb)
- **Formato**: mongodump --gzip

## Colecciones

| Coleccion | Documentos | Tamano |
|-----------|-----------|--------|
| history_events | 412 | 220 KB |
| messages | 342 | 130 KB |
| artifacts | 93 | 100 KB |
| documents | 5 | 95 KB |
| chat_sessions | 91 | 51 KB |
| users | 10 | 1.5 KB |
| deep_research_tasks | 0 | - |
| evidence | 0 | - |
| password_reset_tokens | 0 | - |
| research_sources | 0 | - |
| review_jobs | 0 | - |
| system_settings | 0 | - |
| tasks | 0 | - |
| validation_reports | 0 | - |

**Total**: 953 documentos, ~692 KB comprimido

## Restore en un nuevo servidor

```bash
# 1. Copiar backup al contenedor mongo
docker cp scripts/backups/mongodb/octavios <CONTAINER>:/tmp/restore/octavios

# 2. Restaurar (--drop reemplaza colecciones existentes)
docker exec <CONTAINER> mongorestore \
  --uri='mongodb://<USER>:<PASS>@localhost:27017/?authSource=admin' \
  --drop \
  --gzip \
  /tmp/restore/

# 3. Verificar
docker exec <CONTAINER> mongosh '<URI>' --quiet \
  --eval "db.getCollectionNames().forEach(c => print(c + ': ' + db[c].countDocuments()))"
```
