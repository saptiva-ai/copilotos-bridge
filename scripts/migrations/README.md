# Migrations Scripts

Scripts de migraciones de datos y schema de base de datos.

## Scripts Disponibles

Data and schema migration scripts.

## Uso

```bash
# Ejecutar migración
python scripts/migrations/<migration_script>.py
```

## Buenas Prácticas

1. **Siempre hacer backup antes de migraciones**
   ```bash
   ./scripts/database/backup-mongodb.sh
   ```

2. **Probar primero en desarrollo**
   - Verificar que la migración funciona localmente
   - Revisar logs para errores

3. **Verificar después de migración**
   - Verificar que los datos están correctos
   - Verificar que los índices se crearon

---
**Ver también:** `../README.md` para más información
