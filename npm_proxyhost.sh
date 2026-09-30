#!/usr/bin/env bash
# npm_proxyhost.sh — maakt de proxyhost verwijzers.slaapkliniek.be aan in Nginx Proxy Manager
# via de API, met een nieuw Let's Encrypt-certificaat, Force SSL, HTTP/2 en HSTS (DEPLOY.md §3).
#
#   Op de server:   NPM_EMAIL=... NPM_PASSWORD=... bash npm_proxyhost.sh
#   Vanaf elders:   NPM_URL=https://... (of via ssh-tunnel naar :81)
#
# Idempotent: bestaat de host al, dan wordt hij niet dubbel aangemaakt. Het wachtwoord komt
# alleen uit de omgeving (nooit in git); de DNS moet al naar de server wijzen (HTTP-01).
set -euo pipefail
NPM_URL="${NPM_URL:-http://127.0.0.1:81}"
DOMEIN="${DOMEIN:-verwijzers.slaapkliniek.be}"
FORWARD_HOST="${FORWARD_HOST:-verwijzers}"
FORWARD_PORT="${FORWARD_PORT:-80}"
: "${NPM_EMAIL:?zet NPM_EMAIL}"; : "${NPM_PASSWORD:?zet NPM_PASSWORD}"
LE_EMAIL="${LE_EMAIL:-$NPM_EMAIL}"

TOKEN=$(curl -sf -X POST "$NPM_URL/api/tokens" -H 'Content-Type: application/json' \
  -d "$(python3 -c 'import json,os;print(json.dumps({"identity":os.environ["NPM_EMAIL"],"secret":os.environ["NPM_PASSWORD"]}))')" \
  | python3 -c 'import json,sys;print(json.load(sys.stdin)["token"])')
auth=(-H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json')

if curl -sf "${auth[@]}" "$NPM_URL/api/nginx/proxy-hosts" | python3 -c "
import json,sys; hs=json.load(sys.stdin); d='$DOMEIN'
m=[h for h in hs if d in h.get('domain_names',[])]
print('bestaat al: id', m[0]['id'], 'cert', m[0].get('certificate_id')) if m else sys.exit(1)"; then
  exit 0
fi

BODY=$(python3 - <<PY
import json, os
print(json.dumps({
  "domain_names": [os.environ["DOMEIN"]],
  "forward_scheme": "http", "forward_host": os.environ["FORWARD_HOST"], "forward_port": int(os.environ["FORWARD_PORT"]),
  "certificate_id": "new", "ssl_forced": True, "hsts_enabled": True, "hsts_subdomains": False, "http2_support": True,
  "block_exploits": True, "caching_enabled": False, "allow_websocket_upgrade": False,
  "access_list_id": "0", "advanced_config": "", "locations": [],
  "meta": {"letsencrypt_email": os.environ["LE_EMAIL"], "letsencrypt_agree": True, "dns_challenge": False}
}))
PY
)
export DOMEIN FORWARD_HOST FORWARD_PORT LE_EMAIL
curl -sf "${auth[@]}" -X POST "$NPM_URL/api/nginx/proxy-hosts" -d "$BODY" \
  | python3 -c 'import json,sys;h=json.load(sys.stdin);print("aangemaakt: id", h["id"], "domeinen", h["domain_names"], "cert", h.get("certificate_id"))'
echo "controle: curl -sI https://$DOMEIN/nl/aanvraag/ | grep -i 'content-security\|cache-control\|strict-transport'"
