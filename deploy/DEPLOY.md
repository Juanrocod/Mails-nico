# Deploy en Oracle Cloud — Guía paso a paso

## Prerequisitos

- Cuenta en Oracle Cloud (free tier)
- VM creada con Ubuntu 22.04, Shape VM.Standard.A1.Flex (ARM), 2 OCPU + 12GB RAM
- Archivo .key (SSH private key) descargado al crear la VM
- IP pública de la VM

## 1. Abrir puertos en Oracle Cloud

En la consola de Oracle Cloud:
1. Ir a Networking → Virtual Cloud Networks → tu VCN
2. Click en la subnet pública
3. Click en la Security List
4. Agregar Ingress Rules:

| Source CIDR | Protocol | Dest Port | Descripción |
|-------------|----------|-----------|-------------|
| 0.0.0.0/0   | TCP      | 80        | HTTP        |
| 0.0.0.0/0   | TCP      | 443       | HTTPS       |

## 2. Conectarse a la VM

```bash
# En Windows (PowerShell o Git Bash)
ssh -i "C:\ruta\a\tu\archivo.key" ubuntu@<IP_PUBLICA>
```

Si da error de permisos en el .key, en PowerShell:
```powershell
icacls "C:\ruta\a\tu\archivo.key" /inheritance:r /grant:r "$($env:USERNAME):(R)"
```

## 3. Ejecutar setup del servidor

Desde tu máquina local:
```bash
ssh -i key.pem ubuntu@<IP> 'bash -s' < deploy/setup-server.sh
```

O conectarte por SSH y correr los comandos manualmente.

## 4. Desconectarse y reconectarse

```bash
exit
ssh -i key.pem ubuntu@<IP>
```

## 5. Clonar el repo

```bash
git clone https://github.com/TU_USUARIO/Gestion-Mails.git
cd Gestion-Mails
```

## 6. Configurar variables de entorno

```bash
cp deploy/.env.production .env
nano .env
```

Generar las claves:
```bash
# SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(48))"

# ENCRYPTION_KEY
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copiar los valores generados al .env. Cambiar DB_PASSWORD por algo seguro.
Cambiar ALLOWED_ORIGINS por `http://<TU_IP_PUBLICA>`.

## 7. Levantar todo

```bash
docker compose up --build -d
```

Primera vez tarda ~3-5 minutos (descarga imágenes). Después:

```bash
# Verificar que los 3 containers estén corriendo
docker compose ps

# Correr migraciones
docker compose exec backend alembic upgrade head

# Crear primer usuario
docker compose exec backend python create_invite.py invite
```

## 8. Verificar

```bash
# Health check
curl http://localhost:8000/health
# Debe devolver: {"status":"ok","database":"ok"}

# Frontend
curl -I http://localhost
# Debe devolver: HTTP/1.1 200 OK
```

Abrir en el browser: `http://<IP_PUBLICA>`

## Comandos útiles

```bash
# Ver logs
docker compose logs -f

# Reiniciar todo
docker compose restart

# Actualizar con nuevo código
git pull
docker compose up --build -d

# Crear link de registro
docker compose exec backend python create_invite.py invite

# Crear link de reset de password
docker compose exec backend python create_invite.py reset --username middleoffice
```
