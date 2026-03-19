# Configuración de Variables de Entorno para Password Reset

## Resumen

Este documento describe la configuración de variables de entorno necesarias para el sistema de recuperación de contraseña en los diferentes ambientes (desarrollo y producción).

## Variables de Entorno Agregadas

Las siguientes variables han sido agregadas a todos los archivos de configuración:

```bash
# Email / Password Reset Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=support@saptiva.com
SMTP_PASSWORD=<gmail-app-password>
SMTP_FROM_EMAIL=support@saptiva.com
PASSWORD_RESET_URL_BASE=<environment-specific-url>
```

## Archivos Actualizados

### 1. Development (Activo)

**Archivo**: `envs/.env`

```bash
# ========================================
# EMAIL / PASSWORD RESET
# ========================================
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=support@saptiva.com
SMTP_PASSWORD=your-gmail-app-password-here
SMTP_FROM_EMAIL=support@saptiva.com
PASSWORD_RESET_URL_BASE=http://localhost:3000
```

**Estado**: ✓ Configurado
**Acción requerida**: Reemplazar `SMTP_PASSWORD` con App Password real

---

### 2. Development Template

**Archivo**: `apps/api/.env.example`

```bash
# ========================================
# EMAIL / PASSWORD RESET CONFIGURATION
# ========================================
# SMTP Configuration for sending password reset emails via Gmail
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=support@saptiva.com
# IMPORTANT: Use Gmail App Password, not your regular password
# Generate at: https://myaccount.google.com/apppasswords
SMTP_PASSWORD=your-gmail-app-password-here
SMTP_FROM_EMAIL=support@saptiva.com

# Base URL for password reset links (frontend URL)
# Development: http://localhost:3000
# Production: https://414.saptiva.com
PASSWORD_RESET_URL_BASE=http://localhost:3000
```

**Estado**: ✓ Actualizado
**Uso**: Template para nuevas instalaciones en desarrollo

---

### 3. Production Template

**Archivo**: `envs/.env.production.example`

```bash
# ============================================================================
# EMAIL / PASSWORD RESET CONFIGURATION
# ============================================================================
# SMTP Configuration for sending password reset emails via Gmail
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=support@saptiva.com
# IMPORTANT: Use Gmail App Password, not your regular password
# Generate at: https://myaccount.google.com/apppasswords
SMTP_PASSWORD=CHANGE_ME_GMAIL_APP_PASSWORD
SMTP_FROM_EMAIL=support@saptiva.com

# Base URL for password reset links (frontend URL)
# Production: Must be the actual domain where users access the frontend
PASSWORD_RESET_URL_BASE=https://414.saptiva.com
```

**Estado**: ✓ Actualizado
**URL de producción**: `https://414.saptiva.com`
**Acción requerida**: Copiar a `.env` en producción y configurar `SMTP_PASSWORD`

---

## Configuración por Ambiente

### Development

| Variable | Valor |
|----------|-------|
| `SMTP_HOST` | smtp.gmail.com |
| `SMTP_PORT` | 587 |
| `SMTP_USER` | support@saptiva.com |
| `SMTP_PASSWORD` | **[CONFIGURAR CON APP PASSWORD]** |
| `SMTP_FROM_EMAIL` | support@saptiva.com |
| `PASSWORD_RESET_URL_BASE` | http://localhost:3000 |

### Production

| Variable | Valor |
|----------|-------|
| `SMTP_HOST` | smtp.gmail.com |
| `SMTP_PORT` | 587 |
| `SMTP_USER` | support@saptiva.com |
| `SMTP_PASSWORD` | **[CONFIGURAR CON APP PASSWORD]** |
| `SMTP_FROM_EMAIL` | support@saptiva.com |
| `PASSWORD_RESET_URL_BASE` | https://414.saptiva.com |

---

## Pasos de Configuración

### Development (Local)

1. **Generar App Password de Gmail**:
   - Ve a https://myaccount.google.com/apppasswords
   - Crea nueva App Password para "Saptiva OctaviOS Dev"
   - Copia la contraseña de 16 caracteres

2. **Actualizar envs/.env**:
   ```bash
   SMTP_PASSWORD=abcd efgh ijkl mnop  # Tu App Password aquí
   ```

3. **Recargar variables de entorno**:
   ```bash
   make reload-env-service service=api
   ```

4. **Verificar configuración**:
   ```bash
   ./scripts/test_password_reset.sh demo@example.com
   ```

---

### Production (414.saptiva.com)

1. **Generar App Password de Gmail**:
   - Ve a https://myaccount.google.com/apppasswords
   - Crea nueva App Password para "Saptiva OctaviOS Production"
   - Copia la contraseña de 16 caracteres

2. **Conectar al servidor de producción**:
   ```bash
   ssh user@414.saptiva.com
   ```

3. **Actualizar archivo .env en producción**:
   ```bash
   cd /opt/octavios-bridge/envs
   nano .env
   ```

4. **Agregar configuración SMTP**:
   ```bash
   # EMAIL / PASSWORD RESET
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=support@saptiva.com
   SMTP_PASSWORD=<tu-app-password-aqui>
   SMTP_FROM_EMAIL=support@saptiva.com
   PASSWORD_RESET_URL_BASE=https://414.saptiva.com
   ```

5. **Reiniciar servicios**:
   ```bash
   cd /opt/octavios-bridge/infra
   docker compose down
   docker compose up -d
   ```

6. **Verificar logs**:
   ```bash
   docker compose logs -f api | grep -i "email\|smtp"
   ```

7. **Probar flujo completo**:
   - Ve a https://414.saptiva.com/login
   - Haz clic en "¿Olvidaste tu contraseña?"
   - Ingresa email de prueba
   - Verifica recepción del email

---

## Validación de Configuración

### Checklist Development

- [ ] `SMTP_PASSWORD` configurado en `envs/.env`
- [ ] `PASSWORD_RESET_URL_BASE=http://localhost:3000`
- [ ] Servicios reiniciados con `make reload-env-service service=api`
- [ ] Email de prueba enviado exitosamente
- [ ] Enlace de reset funciona correctamente

### Checklist Production

- [ ] `SMTP_PASSWORD` configurado en servidor de producción
- [ ] `PASSWORD_RESET_URL_BASE=https://414.saptiva.com`
- [ ] Servicios reiniciados en producción
- [ ] Email de prueba enviado exitosamente desde producción
- [ ] Enlace redirige a `https://414.saptiva.com/reset-password`
- [ ] SSL/HTTPS funcionando correctamente

---

## Troubleshooting

### Error: "SMTPAuthenticationError"

**Causa**: App Password incorrecta o inválida

**Solución**:
1. Verifica que usas App Password (no la contraseña regular)
2. Verifica que la App Password no tenga espacios
3. Genera nueva App Password y actualiza `.env`

### Error: "Password reset link points to localhost in production"

**Causa**: `PASSWORD_RESET_URL_BASE` no configurado correctamente

**Solución**:
```bash
# En producción debe ser:
PASSWORD_RESET_URL_BASE=https://414.saptiva.com

# NO debe ser:
PASSWORD_RESET_URL_BASE=http://localhost:3000
```

### Email no se envía en producción

**Solución**:
1. Verifica logs del contenedor API:
   ```bash
   docker compose logs api | grep -i smtp
   ```

2. Verifica conectividad SMTP:
   ```bash
   docker compose exec api ping smtp.gmail.com
   ```

3. Verifica que el puerto 587 no esté bloqueado por firewall

---

## Seguridad

### Gmail App Password

- ✓ Usar App Password específica para esta aplicación
- ✓ No compartir la App Password
- ✓ Rotar App Password cada 90 días
- ✓ Revocar App Password si se compromete
- ✓ Usar diferentes App Passwords para dev y prod

### Variables de Entorno

- ✓ Nunca commitear archivos `.env` con credenciales reales
- ✓ Los archivos `.env.example` deben contener solo placeholders
- ✓ Usar `CHANGE_ME_*` como prefijo para valores que deben cambiarse
- ✓ Documentar todas las variables en este archivo

---

## Referencias

- **Setup Guide**: `docs/guides/PASSWORD_RESET_SETUP.md`
- **Test Script**: `scripts/test_password_reset.sh`
- **Gmail App Passwords**: https://myaccount.google.com/apppasswords
- **Production Domain**: https://414.saptiva.com

---

## Changelog

- **2025-11-17**: Agregada configuración SMTP a todos los archivos .env
  - `envs/.env` (development)
  - `apps/api/.env.example` (development template)
  - `envs/.env.production.example` (production template)
  - URL de producción configurada: `https://414.saptiva.com`
