# CLAUDE.md

Claude Code가 이 저장소에서 작업할 때 따라야 하는 지침.

## 커밋 시 CHANGELOG.md 갱신

사용자가 최종적으로 커밋을 요청하면, 커밋에 포함되는 변경사항을 `CHANGELOG.md`에 반드시 기록한다.

1. `CHANGELOG.md` 최상단(가장 최근 버전) 항목을 확인한다.
2. 이번 커밋 내용에 맞춰 버전을 올린다 ([Semantic Versioning](https://semver.org/lang/ko/) 기준, 0.x 단계):
   - 새 기능 추가 → MINOR 버전 (`0.1.0` → `0.2.0`)
   - 버그 수정 / 보안 수정 / 문서·설정 정리 → PATCH 버전 (`0.1.0` → `0.1.1`)
   - 기존 동작을 깨는 변경 → MAJOR 버전 (`0.x.x` → `1.0.0`), 애매하면 사용자에게 먼저 확인
3. 새 버전 섹션을 파일 최상단(기존 항목들 위)에 추가한다. 날짜는 `YYYY-MM-DD`.
4. 기존 항목의 스타일을 따른다 — [Keep a Changelog](https://keepachangelog.com/ko/1.0.0/) 형식,
   `### Added` / `### Fixed` / `### Security` / `### Known Issues` 등으로 구분.
   한 줄 요약 + 필요하면 이유(왜 바꿨는지)를 짧게.
5. `git commit` 시 `CHANGELOG.md`도 함께 스테이징해서 같은 커밋에 포함한다.
6. 커밋 메시지 요약 정도로 너무 상세하게 쓰지 않는다 — 사용자나 나중에 코드를 보는 사람이
   "무엇이 왜 바뀌었는지" 빠르게 파악할 수 있는 수준이면 충분하다.
7. **git 태그(`git tag`)는 `dev`에서 커밋할 때마다 만들지 않는다** — `master`로 병합해
   실제 release가 되는 시점에만 태그를 단다. `dev`에서는 CHANGELOG.md 버전만 올려둔다.

버전이 애매하거나(사소한 수정인지 새 기능인지 판단이 안 설 때) 사용자에게 먼저 물어보고 진행한다.

## 브랜치 전략

- `master` — 최종 release 브랜치. **서버(운영 환경)는 항상 `master`에서만 pull 받는다.**
  직접 실험적인 커밋을 쌓거나 검증 안 된 변경을 바로 올리지 않는다.
- `dev` — 로컬 작업/테스트용 브랜치. 새 기능·리팩토링 작업은 기본적으로 여기서 진행한다.
- 작업 흐름: `dev`에서 작업 → 충분히 확인됐을 때 사용자 승인 하에 `dev`를 `master`로 병합.
  병합 시점에 CHANGELOG.md 버전도 함께 갱신한다 (위 규칙 참고).
- `master`에 대한 `push`(특히 origin으로) 는 서버가 바로 pull 받는 대상이므로,
  사용자가 명시적으로 병합/배포를 요청했을 때만 수행한다. 다른 모든 git 작업과 마찬가지로
  브랜치를 삭제하거나 강제로 이력을 바꾸는 작업은 하지 않는다.

## 배포 환경 (서버)

- AWS EC2(Ubuntu), `~/pricehub`에 저장소가 체크아웃되어 있고 `master` 브랜치만 pull 받는다.
- 프로세스 관리는 pm2 (`pm2 list`에서 이름 `django-app`). 재시작: `pm2 restart django-app`.
- gunicorn `-w 4`(워커 4개)로 `0.0.0.0:8000`에 바인딩, nginx가 80번 포트에서 리버스 프록시.
- **아직 도메인/TLS 미적용, HTTP로만 서비스 중.** `.env`의 `USE_HTTPS`는 도메인+인증서를
  붙이기 전까지 켜면 안 됨 — 켜면 `SECURE_SSL_REDIRECT`가 없는 HTTPS로 강제 리다이렉트해서
  사이트가 먹통이 된다. 나중에 도메인 적용되면 `USE_HTTPS=True` 추가할 것.
- `staticfiles/`(collectstatic 산출물), `django_cache/`(rate limit용 파일 캐시), `logs/`(에러 로그)는
  전부 런타임에 자동 생성되는 산출물이라 git에 커밋하지 않는다(`.gitignore` 처리됨) —
  실수로 다시 add하지 말 것.
- 공유 캐시(rate limit 등)가 필요하면 Redis 등 별도 인프라가 서버에 없으므로
  `FileBasedCache`(파일시스템 기반, 워커 간 공유됨) 사용을 우선 고려한다.
- `master` 병합 후 서버 배포 절차:
  ```bash
  cd ~/pricehub && source venv/bin/activate
  git pull origin master
  pip install -r requirements.txt
  python manage.py collectstatic --noinput
  python manage.py migrate
  pm2 restart django-app
  ```
