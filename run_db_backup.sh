#!/bin/bash

# DB 백업 스크립트 — mysqldump로 매일 전체 백업 후 gzip 압축.
# 14일 넘은 백업은 자동 삭제(디스크 무한 증가 방지).
cd /home/ubuntu/pricehub

# 환경변수 로드 (DB 접속 정보)
if [ -f .env ]; then
    export $(grep -v '^#' .env | grep -v '^$' | xargs)
fi

BACKUP_DIR=/home/ubuntu/pricehub/backups
mkdir -p "$BACKUP_DIR"
mkdir -p logs

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/pricehub_${DATE}.sql.gz"

echo "========================================" >> logs/db_backup.log
echo "시작: $(date)" >> logs/db_backup.log

mysqldump -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" | gzip > "$BACKUP_FILE"

if [ $? -eq 0 ] && [ -s "$BACKUP_FILE" ]; then
    echo "완료: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))" >> logs/db_backup.log
else
    echo "실패: mysqldump 오류 (백업 파일 확인 필요)" >> logs/db_backup.log
    rm -f "$BACKUP_FILE"
fi

# 14일 넘은 백업 자동 삭제
find "$BACKUP_DIR" -name "pricehub_*.sql.gz" -mtime +14 -delete

echo "완료: $(date)" >> logs/db_backup.log
echo "========================================" >> logs/db_backup.log
