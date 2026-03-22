  #!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "This will remove the local Evolution API session state and recreate it from scratch."
echo "Containers affected: evolution-api, evolution-postgres, evolution-redis"
echo "Volumes removed: evolution_instances, evolution_postgres_data, evolution_redis_data"
read -r -p "Continue? [y/N] " answer

if [[ ! "$answer" =~ ^[Yy]$ ]]; then
  echo "Aborted."
  exit 0
fi

docker compose stop evolution-api evolution-postgres evolution-redis
docker compose rm -f evolution-api evolution-postgres evolution-redis
docker volume rm \
  bot-compra_evolution_instances \
  bot-compra_evolution_postgres_data \
  bot-compra_evolution_redis_data 2>/dev/null || true
docker compose up -d evolution-postgres evolution-redis evolution-api

echo
echo "Evolution API reset completed."
echo "Open http://localhost:8080/manager/instance/list and create a fresh instance."
