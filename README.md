# Kick Video Downloader - Automated Stream Capture

## 🎯 Objective
Backend API en VPS Hetzner que descargue videos de Kick.com

## 📁 Structure (TDD)
```
kick-downloader/
├── .clinerules          # TDD methodology
├── src/
│   ├── server.py        # FastAPI server
│   └── downloader.py    # Download logic con yt-dlp
├── tests/
│   ├── test_downloader.py
│   └── test_yt_dlp.py
├── deploy/
│   ├── kick-downloader.service  # Systemd unit
│   └── nginx.conf
└── requirements.txt
```

## 🔄 Arquitectura
```
APK móvil → POST /download → VPS (FastAPI + yt-dlp) → Kick.com
           ← Devuelve URL del archivo ←               
           ◄ Borra a 5 min ◄
```

## 🚀 Endpoints API
| Endpoint | Método | Body | Respuesta |
|----------|--------|------|-----------|
| `/health` | GET | - | `{"status": "ok"}` |
| `/download` | POST | `{"url": "...", "format": "mp4/mp3"}` | `{"file_url": "/files/xxx"}` |
| `/files/{filename}` | GET | - | Archivo para descarga |

## 📦 Deploy Commands
```bash
# En VPS Hetzner:
cd /opt
git clone https://github.com/kavanasystemsinfo-ui/kick-downloader.git
cd kick-downloader
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uv pip install fastapi uvicorn python-multipart yt-dlp

# Tests
python -m pytest tests/ -v

# Servir
uvicorn src.server:app --host 0.0.0.0 --port 8000
```