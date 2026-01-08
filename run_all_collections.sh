#!/bin/bash

export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export DJANGO_SETTINGS_MODULE=config.settings
export CRON_MODE=true

cd /home/ubuntu/pricehub
source /home/ubuntu/pricehub/venv/bin/activate

echo "========================================" >> /home/ubuntu/pricehub/logs/all_collections.log
echo "시작 시간: $(date)" >> /home/ubuntu/pricehub/logs/all_collections.log
echo "========================================" >> /home/ubuntu/pricehub/logs/all_collections.log

# 1. 일반 최저가 수집
echo "" >> /home/ubuntu/pricehub/logs/all_collections.log
echo "📊 일반 최저가 수집 시작..." >> /home/ubuntu/pricehub/logs/all_collections.log
python /home/ubuntu/pricehub/collect_prices.py >> /home/ubuntu/pricehub/logs/all_collections.log 2>&1

# 2. TCG999 가격 수집
echo "" >> /home/ubuntu/pricehub/logs/all_collections.log
echo "🎯 TCG999 가격 수집 시작..." >> /home/ubuntu/pricehub/logs/all_collections.log
python /home/ubuntu/pricehub/collect_tcg999_prices.py >> /home/ubuntu/pricehub/logs/all_collections.log 2>&1

echo "" >> /home/ubuntu/pricehub/logs/all_collections.log
echo "========================================" >> /home/ubuntu/pricehub/logs/all_collections.log
echo "완료 시간: $(date)" >> /home/ubuntu/pricehub/logs/all_collections.log
echo "========================================" >> /home/ubuntu/pricehub/logs/all_collections.log
