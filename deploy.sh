#!/usr/bin/env bash
# deploy.sh — verwijzers.slaapkliniek.be op de Hetzner-server (naast YASAFlaskified, eigen map).
#
#   Vanaf de werkplek:  ssh root@dedodedodo.be 'bash -s' < deploy.sh
#   Op de server zelf:  bash /data/verwijzers/deploy.sh
#
# Idempotent: kloont bij de eerste keer, daarna git pull; bouwt het image opnieuw (--no-cache,
# want de build-stage rendert de pagina's) en start de container. Geen rsync, geen --delete.
set -euo pipefail

APP_DIR="${APP_DIR:-/data/verwijzers}"
REPO="${REPO:-https://github.com/bartromb/slaapkliniek-verwijzers.git}"
NPM_NETWORK="${NPM_NETWORK:-}"

step() { printf '\n\033[1;34m== %s\033[0m\n' "$*"; }

step "1/5 code"
if [ ! -d "$APP_DIR/.git" ]; then
  mkdir -p "$APP_DIR"
  git clone -q "$REPO" "$APP_DIR"
else
  git -C "$APP_DIR" pull -q --ff-only
fi
cd "$APP_DIR"
git log --oneline -1

step "2/5 NPM-netwerk"
if [ ! -f .env ]; then
  if [ -z "$NPM_NETWORK" ]; then
    # Raad het netwerk van Nginx Proxy Manager: het netwerk waar de NPM-container aan hangt.
    NPM_CID=$(docker ps --filter "ancestor=jc21/nginx-proxy-manager:latest" -q | head -1 || true)
    if [ -z "$NPM_CID" ]; then NPM_CID=$(docker ps --format '{{.ID}} {{.Image}}' | grep -i "proxy-manager" | awk '{print $1}' | head -1 || true); fi
    if [ -n "$NPM_CID" ]; then
      NPM_NETWORK=$(docker inspect "$NPM_CID" --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{"\n"}}{{end}}' | grep -v '^bridge$' | head -1)
    fi
  fi
  if [ -z "$NPM_NETWORK" ]; then
    echo "NPM-netwerk niet gevonden; zet NPM_NETWORK=<naam> (docker network ls) en draai opnieuw." >&2
    exit 1
  fi
  printf 'NPM_NETWORK=%s\n' "$NPM_NETWORK" > .env
fi
cat .env
docker network inspect "$(sed -n 's/^NPM_NETWORK=//p' .env)" >/dev/null

step "3/5 image bouwen"
docker compose build --no-cache

step "4/5 starten"
docker compose up -d
sleep 3
docker compose ps

step "5/5 controle vanuit de container"
docker compose exec -T verwijzers wget -q -O - http://127.0.0.1/nl/ | grep -o '<title>[^<]*</title>' | head -1
docker compose exec -T verwijzers wget -q -S -O /dev/null http://127.0.0.1/nl/aanvraag/ 2>&1 | grep -i "content-security-policy\|cache-control" | head -3
echo "klaar: koppel in Nginx Proxy Manager verwijzers.slaapkliniek.be -> verwijzers:80 (zie DEPLOY.md)"
