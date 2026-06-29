module.exports = {
  apps: [{
    name: 'kick-downloader',
    cwd: '/root/kick-downloader',
    script: 'src/server.py',
    interpreter: '.venv/bin/python',
    env: {
      PORT: 8000,
      DOWNLOAD_DIR: '/opt/kick-downloader/downloads'
    },
    watch: false,
    max_memory_restart: '500M',
    error_file: 'logs/error.log',
    out_file: 'logs/output.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss',
    autorestart: true
  }]
};