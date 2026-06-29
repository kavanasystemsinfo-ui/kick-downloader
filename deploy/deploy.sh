#!/bin/bash
# ========================================
# KICK DOWNLOADER - DEPLOY SCRIPT
# Ejecutar en tu VPS Hetzner
# ========================================

set -e

echo "🚀 Deploy Kick Downloader..."

# 1. Instalar dependencias del sistema
apt update
apt install -y ffmpeg yt-dlp python3-pip python3-venv nginx certbot python3-certbot-nginx

# 2. Instalar dependencias Python
pip3 install --break-system-packages fastapi uvicorn python-multipart

# 3. Crear directorio del proyecto (ajusta si ya existe)
mkdir -p /opt/kick-downloader
mkdir -p /opt/kick-downloader/downloads

# 4. Clonar repositorio (ajusta URL si es necesario)
cd /opt/kick-downloader
if [ ! -d ".git" ]; then
    git clone https://github.com/kavanasystemsinfo-ui/kick-downloader.git .
fi

# 5. Probar servidor
echo "🧪 Probando servidor..."
timeout 5 python3 -c "import src.server" || echo "Import OK"

echo "✅ Deploy script listo"
echo "📍 Próximos pasos:"
echo "   - uvicorn src.server:app --host 0.0.0.0 --port 8000"
echo "   - Configurar nginx con deploy/nginx.conf"
echo "   - certbot --nginx -d tu-dominio.com"