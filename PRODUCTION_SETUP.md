# 🚀 Guía de Configuración de Producción - CopilotOS Bridge

Esta guía detalla los pasos para configurar y desplegar CopilotOS Bridge en un entorno de producción.

## 📋 Prerrequisitos

### Servidor
- **OS**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- **RAM**: Mínimo 4GB (recomendado 8GB+)
- **CPU**: 2+ cores
- **Almacenamiento**: 50GB+ disponible
- **Red**: Puertos 80, 443, 22 abiertos

### Software
- Docker 24.0+
- Docker Compose 2.0+
- Git
- Certificados SSL (Let's Encrypt recomendado)

## 🔧 Configuración Paso a Paso

### 1. Preparación del Servidor

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependencias
sudo apt install -y curl wget git htop

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Instalar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Reiniciar sesión para aplicar permisos de Docker
```

### 2. Clonar el Repositorio

```bash
# Crear directorio de producción
sudo mkdir -p /opt/copilotos-bridge
sudo chown $USER:$USER /opt/copilotos-bridge

# Clonar repositorio
cd /opt/copilotos-bridge
git clone https://github.com/jazielflo/copilotos-bridge .
git checkout main  # o la rama de producción
```

### 3. Configurar Variables de Entorno

```bash
# Copiar archivo de ejemplo
cp .env.production.example .env.production

# Editar configuración
nano .env.production
```

**Variables críticas a configurar:**

```bash
# Dominio
DOMAIN=tudominio.com
API_HOST=api.tudominio.com
FRONTEND_URL=https://tudominio.com

# Seguridad - GENERAR CLAVES SEGURAS
MONGODB_PASSWORD=TuPasswordMongoDBAltamenteSegura
REDIS_PASSWORD=TuPasswordRedisAltamenteSegura
JWT_SECRET_KEY=TuClaveJWTDe32CaracteresOmas12345
SECRET_KEY=TuClaveSecretaDe32CaracteresOmas12

# APIs
SAPTIVA_API_KEY=tu-api-key-de-saptiva
ALETHEIA_API_KEY=tu-api-key-de-aletheia
ALETHEIA_URL=https://tu-instancia-aletheia.com

# Monitoreo (opcional)
SENTRY_DSN=https://tu-dsn@sentry.io/proyecto
ANALYTICS_ID=tu-google-analytics-id
```

### 4. Configurar HTTPS con Let's Encrypt (Recomendado)

```bash
# Instalar certbot
sudo apt install -y certbot

# Generar certificados (detener servicios web primero)
sudo systemctl stop nginx apache2 2>/dev/null || true

sudo certbot certonly --standalone \
  -d tudominio.com \
  -d api.tudominio.com \
  --email tu-email@tudominio.com \
  --agree-tos \
  --non-interactive

# Copiar certificados para Docker
sudo mkdir -p /opt/copilotos-bridge/nginx/ssl
sudo cp /etc/letsencrypt/live/tudominio.com/fullchain.pem /opt/copilotos-bridge/nginx/ssl/
sudo cp /etc/letsencrypt/live/tudominio.com/privkey.pem /opt/copilotos-bridge/nginx/ssl/
sudo chown -R $USER:$USER /opt/copilotos-bridge/nginx/ssl/
```

### 5. Configurar Nginx (Proxy Reverso)

Crear `/opt/copilotos-bridge/nginx/nginx.prod.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream api {
        server api:8001;
    }

    upstream web {
        server web:3000;
    }

    # Redirigir HTTP a HTTPS
    server {
        listen 80;
        server_name tudominio.com api.tudominio.com;
        return 301 https://$server_name$request_uri;
    }

    # Frontend
    server {
        listen 443 ssl http2;
        server_name tudominio.com;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;

        location / {
            proxy_pass http://web;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }

    # API
    server {
        listen 443 ssl http2;
        server_name api.tudominio.com;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;

        location / {
            proxy_pass http://api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # Para SSE streaming
            proxy_buffering off;
            proxy_cache off;
        }
    }
}
```

### 6. Desplegar

```bash
# Ejecutar script de despliegue
cd /opt/copilotos-bridge
./scripts/deploy-prod.sh

# Para despliegue limpio (borra datos existentes)
./scripts/deploy-prod.sh --clean
```

### 7. Verificar Despliegue

```bash
# Verificar estado de servicios
docker-compose -f docker-compose.prod.yml ps

# Ver logs
docker-compose -f docker-compose.prod.yml logs -f

# Probar endpoints
curl https://api.tudominio.com/health
curl https://tudominio.com
```

## 🔒 Configuración de Seguridad

### Firewall
```bash
# Configurar UFW
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

### Renovación Automática de Certificados
```bash
# Agregar a crontab
echo "0 3 * * * certbot renew --quiet && docker-compose -f /opt/copilotos-bridge/docker-compose.prod.yml restart nginx" | sudo crontab -
```

### Backup Automático
El script de despliegue configura backups automáticos diarios. Personalizar si es necesario:

```bash
# Editar configuración de backup
sudo nano /opt/copilotos-bridge/scripts/backup.sh
```

## 📊 Monitoreo

### Logs
```bash
# Logs de aplicación
docker-compose -f docker-compose.prod.yml logs -f api

# Logs del sistema
sudo journalctl -u docker -f
```

### Métricas
- **Prometheus**: http://tudominio.com:9090
- **Grafana**: http://tudominio.com:3001 (admin/password configurado)

### Health Checks
- **API Health**: https://api.tudominio.com/health
- **Frontend**: https://tudominio.com

## 🔄 Mantenimiento

### Actualizar
```bash
cd /opt/copilotos-bridge
git pull origin main
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

### Backup Manual
```bash
./scripts/backup.sh
```

### Reiniciar Servicios
```bash
# Reiniciar todo
docker-compose -f docker-compose.prod.yml restart

# Reiniciar servicio específico
docker-compose -f docker-compose.prod.yml restart api
```

## 🚨 Troubleshooting

### Problema: API no responde
```bash
# Verificar logs
docker-compose -f docker-compose.prod.yml logs api

# Verificar conectividad a BD
docker-compose -f docker-compose.prod.yml exec api python -c "from motor.motor_asyncio import AsyncIOMotorClient; print('MongoDB OK')"
```

### Problema: Frontend no carga
```bash
# Verificar configuración
docker-compose -f docker-compose.prod.yml exec web env | grep NEXT_PUBLIC
```

### Problema: SSL
```bash
# Verificar certificados
sudo certbot certificates

# Renovar manualmente
sudo certbot renew
```

## 📞 Soporte

Para problemas adicionales:
1. Revisar logs detallados
2. Verificar configuración de variables de entorno
3. Consultar documentación específica de cada servicio
4. Contactar al equipo de desarrollo

---

**⚠️ Importante**: Mantén siempre backup de:
- Base de datos MongoDB
- Configuración de variables de entorno
- Certificados SSL
- Logs importantes