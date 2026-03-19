# Guía de Configuración de Recuperación de Contraseña

## Resumen de Implementación

El sistema de recuperación de contraseña está completamente implementado con las siguientes características:

- Flujo de recuperación de contraseña mediante email
- Tokens seguros con expiración de 1 hora
- Emails HTML profesionales enviados desde support@saptiva.com
- Validación de contraseñas (mínimo 8 caracteres)
- Interfaz de usuario completa en español

## Arquitectura

### Backend (FastAPI)

1. **Modelo de Datos** (`apps/api/src/models/password_reset.py`):
   - `PasswordResetToken`: Almacena tokens con expiración y estado
   - Tokens generados con `secrets.token_urlsafe(32)`
   - Auto-expiración después de 1 hora

2. **Servicio de Email** (`apps/api/src/services/email_service.py`):
   - `EmailService`: Maneja el envío de emails vía Gmail SMTP
   - Templates HTML profesionales
   - Fallback a texto plano

3. **Endpoints** (`apps/api/src/routers/auth.py`):
   - `POST /api/auth/forgot-password`: Solicita reset de contraseña
   - `POST /api/auth/reset-password`: Restablece la contraseña

4. **Schemas** (`apps/api/src/schemas/auth.py`):
   - `ForgotPasswordRequest/Response`
   - `ResetPasswordRequest/Response`

### Frontend (Next.js 14)

1. **Páginas**:
   - `/forgot-password`: Formulario para solicitar recuperación
   - `/reset-password`: Formulario para establecer nueva contraseña
   - Componente `LoginForm`: Enlace "¿Olvidaste tu contraseña?"

## Configuración Requerida

### 1. Variables de Entorno (`envs/.env`)

Ya se han agregado las siguientes variables al archivo `.env`:

```bash
# ========================================
# EMAIL / PASSWORD RESET
# ========================================
# SMTP Configuration for sending emails via Gmail
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=support@saptiva.com
# IMPORTANT: Use Gmail App Password, not your regular password
# Generate at: https://myaccount.google.com/apppasswords
SMTP_PASSWORD=your-gmail-app-password-here
SMTP_FROM_EMAIL=support@saptiva.com
# Base URL for password reset links (frontend URL)
PASSWORD_RESET_URL_BASE=http://localhost:3000
```

### 2. Generar App Password de Gmail

**IMPORTANTE**: No uses la contraseña regular de Gmail. Debes generar una "App Password":

#### Pasos para generar App Password:

1. Ve a tu cuenta de Google: https://myaccount.google.com
2. En el menú izquierdo, selecciona "Seguridad"
3. En "Cómo inicias sesión en Google", selecciona "Verificación en dos pasos"
   - Si no está activada, actívala primero
4. En la parte inferior, selecciona "Contraseñas de aplicaciones"
5. Selecciona "Correo" y "Otro (nombre personalizado)"
6. Nombre sugerido: "Saptiva OctaviOS Password Reset"
7. Haz clic en "Generar"
8. Copia la contraseña de 16 caracteres generada
9. Pega esta contraseña en `SMTP_PASSWORD` en tu archivo `.env`

#### Ejemplo de App Password:
```
abcd efgh ijkl mnop
```

### 3. Configurar Cuenta support@saptiva.com

Asegúrate de que:
- La cuenta `support@saptiva.com` existe y tienes acceso
- La verificación en dos pasos está activada
- Has generado una App Password específica para esta aplicación

### 4. Actualizar URL Base (Producción)

Para producción, cambia `PASSWORD_RESET_URL_BASE` a tu dominio real:

```bash
# Desarrollo
PASSWORD_RESET_URL_BASE=http://localhost:3000

# Producción
PASSWORD_RESET_URL_BASE=https://octavios.saptiva.com
```

## Flujo de Usuario

### 1. Solicitar Recuperación

1. Usuario hace clic en "¿Olvidaste tu contraseña?" en `/login`
2. Navega a `/forgot-password`
3. Ingresa su email
4. Sistema:
   - Verifica si el email existe en la BD
   - Invalida tokens anteriores del usuario
   - Crea nuevo token con expiración de 1 hora
   - Envía email con enlace de recuperación
   - Siempre muestra mensaje de éxito (previene enumeración de emails)

### 2. Restablecer Contraseña

1. Usuario recibe email con enlace: `http://localhost:3000/reset-password?token=<token>`
2. Hace clic en el enlace
3. Navega a `/reset-password` con token en URL
4. Ingresa nueva contraseña (mínimo 8 caracteres)
5. Confirma contraseña
6. Sistema:
   - Valida token (existencia, expiración, no usado)
   - Actualiza contraseña del usuario (hash con Argon2)
   - Marca token como usado
   - Redirige a `/login` automáticamente

## Seguridad

### Medidas Implementadas:

1. **Prevención de Enumeración de Emails**:
   - Siempre devuelve mensaje de éxito, incluso si el email no existe
   - Logs internos para debugging sin exponer información al usuario

2. **Tokens Seguros**:
   - Generados con `secrets.token_urlsafe(32)` (256 bits de entropía)
   - Expiración automática después de 1 hora
   - Solo un uso permitido
   - Tokens anteriores invalidados al solicitar uno nuevo

3. **Hashing de Contraseñas**:
   - Argon2 para hashing (estándar de la industria)
   - Validación de longitud mínima (8 caracteres)

4. **Rate Limiting**:
   - Recomendado: Implementar rate limiting en `/auth/forgot-password`
   - Ejemplo: Máximo 3 solicitudes por email cada 15 minutos

## Testing Manual

### Prerrequisitos:
1. Configurar SMTP_PASSWORD con App Password válida
2. Tener un usuario registrado en la BD
3. Servicios levantados: `make dev`

### Pasos de Prueba:

```bash
# 1. Asegúrate de que los servicios estén corriendo
make dev

# 2. Verifica que las variables de entorno estén configuradas
make reload-env-service service=api

# 3. Prueba el flujo completo:
```

#### Test 1: Solicitar Recuperación (Email Válido)
1. Ve a http://localhost:3000/login
2. Haz clic en "¿Olvidaste tu contraseña?"
3. Ingresa un email registrado (ej: demo@example.com)
4. Haz clic en "Enviar enlace de recuperación"
5. Verifica que:
   - Aparece mensaje de éxito
   - Recibes email en la bandeja de entrada
   - El email tiene el formato correcto

#### Test 2: Solicitar Recuperación (Email Inválido)
1. Ingresa un email no registrado
2. Verifica que:
   - Aparece el mismo mensaje de éxito (prevención de enumeración)
   - No se envía email

#### Test 3: Restablecer Contraseña
1. Abre el email recibido
2. Haz clic en "Restablecer Contraseña"
3. Ingresa nueva contraseña (mínimo 8 caracteres)
4. Confirma la contraseña
5. Haz clic en "Restablecer contraseña"
6. Verifica que:
   - Aparece mensaje de éxito
   - Redirige automáticamente a `/login`
   - Puedes iniciar sesión con la nueva contraseña

#### Test 4: Token Expirado
1. Espera más de 1 hora después de solicitar recuperación
2. Intenta usar el enlace del email
3. Verifica que:
   - Muestra error: "Token de recuperación inválido o expirado"

#### Test 5: Token Reutilizado
1. Usa un token que ya fue utilizado
2. Verifica que:
   - Muestra error: "Token de recuperación inválido o expirado"

## Debugging

### Ver Logs del Servicio de Email:

```bash
# Ver logs en tiempo real
docker compose logs -f api

# Buscar errores de email
docker compose logs api | grep -i "email\|smtp"
```

### Errores Comunes:

#### 1. "SMTPAuthenticationError"
- **Causa**: Contraseña incorrecta o no es App Password
- **Solución**: Genera nueva App Password y actualiza `.env`

#### 2. "SMTPSenderRefused"
- **Causa**: Email remitente no autorizado
- **Solución**: Verifica que `SMTP_USER` sea el mismo que `SMTP_FROM_EMAIL`

#### 3. "TimeoutError"
- **Causa**: Firewall bloqueando puerto 587
- **Solución**: Verifica conexión de red o prueba puerto 465 (SSL)

#### 4. "Token de recuperación inválido"
- **Causa**: Token expirado, usado o no existe
- **Solución**: Solicita nuevo token de recuperación

## Mejoras Futuras (Opcional)

1. **Rate Limiting por IP**:
   - Prevenir abuso del endpoint `/forgot-password`
   - Implementar con Redis

2. **Templates Personalizables**:
   - Mover HTML del email a archivos de template
   - Permitir personalización sin cambiar código

3. **Notificación de Cambio de Contraseña**:
   - Enviar email confirmando cambio exitoso
   - Alertar al usuario si no fue él quien lo solicitó

4. **Múltiples Idiomas**:
   - Detectar idioma del navegador
   - Enviar emails en español/inglés según preferencia

5. **Historial de Cambios**:
   - Registrar cambios de contraseña en tabla de auditoría
   - Mostrar último cambio en perfil del usuario

## Contacto y Soporte

Para problemas o preguntas:
- Email: support@saptiva.com
- Documentación: `docs/guides/PASSWORD_RESET_SETUP.md`
