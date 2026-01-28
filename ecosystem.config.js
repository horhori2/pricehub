module.exports = {
  apps: [
    {
      name: 'django-app',
      script: 'venv/bin/gunicorn',  // 가상환경의 gunicorn 경로
      args: 'config.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120',
      cwd: '/home/ubuntu/pricehub',  // 실제 프로젝트 경로로 변경
      interpreter: 'none',  // gunicorn이 이미 Python을 사용하므로 none
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        DJANGO_SETTINGS_MODULE: 'config.settings',
        PYTHONPATH: '/home/ubuntu/pricehub',  // 실제 프로젝트 경로로 변경
      },
      error_file: '/home/ubuntu/logs/django-error.log',
      out_file: '/home/ubuntu/logs/django-out.log',
      log_file: '/home/ubuntu/logs/django-combined.log',
      time: true,
      merge_logs: true,
    }
  ]
};