module.exports = {
  apps: [
    {
      name: 'django-app',
      script: 'venv/bin/gunicorn',
      args: 'config.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120',
      cwd: '/home/ubuntu/pricehub',
      interpreter: 'none',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        DJANGO_SETTINGS_MODULE: 'config.settings',
        PYTHONPATH: '/home/ubuntu/pricehub',
      },
      error_file: '/home/ubuntu/logs/django-error.log',
      out_file: '/home/ubuntu/logs/django-out.log',
      log_file: '/home/ubuntu/logs/django-combined.log',
      time: true,
      merge_logs: true,
    }
  ]
};