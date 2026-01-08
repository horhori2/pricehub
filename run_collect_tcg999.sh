#!/bin/bash

export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export DJANGO_SETTINGS_MODULE=config.settings
export CRON_MODE=true

cd /home/ubuntu/pricehub
source /home/ubuntu/pricehub/venv/bin/activate
python /home/ubuntu/pricehub/collect_tcg999_prices.py >> /home/ubuntu/pricehub/logs/collect_tcg999.log 2>&1

echo "Completed at $(date)" >> /home/ubuntu/pricehub/logs/collect_tcg999.log
