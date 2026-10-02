# Deploy — verwijzers.slaapkliniek.be

Drie onderdelen, in deze volgorde. Alleen stap 2 (DNS) en de SSL-aanvraag in stap 3 zijn
handmatig; de rest doet `deploy.sh`.

## 1. Container op de Hetzner-server

```bash
ssh root@dedodedodo.be 'bash -s' < deploy.sh
```

Kloont naar `/data/verwijzers` (daarna `git pull`), bouwt het image (`--no-cache`, want de
pagina's worden in de build-stage gerenderd), start de container `verwijzers` op het netwerk van
Nginx Proxy Manager (`NPM_NETWORK` in `/data/verwijzers/.env`, automatisch geraden uit de
NPM-container) en controleert vanuit de container de titel en de CSP-header. De container
publiceert **geen** poort.

## 2. DNS (Gandi, LiveDNS)

| type | naam | waarde | TTL |
|---|---|---|---|
| A | `verwijzers` | `65.108.230.243` | 1800 |

Controle: `getent ahostsv4 verwijzers.slaapkliniek.be` moet het serveradres geven vóór stap 3
(Let's Encrypt doet een HTTP-01-challenge en heeft de DNS nodig).

## 3. Nginx Proxy Manager

Via de API (idempotent, wachtwoord alleen uit de omgeving):

```bash
ssh root@dedodedodo.be "cd /data/verwijzers && git pull -q && NPM_EMAIL=<admin-e-mail> NPM_PASSWORD='<wachtwoord>' bash npm_proxyhost.sh"
```

Of met de hand: Hosts → Proxy Hosts → Add Proxy Host:

| veld | waarde |
|---|---|
| Domain Names | `verwijzers.slaapkliniek.be` |
| Scheme | `http` |
| Forward Hostname / IP | `verwijzers` |
| Forward Port | `80` |
| Cache Assets | uit (de site zet zelf `Cache-Control`) |
| Block Common Exploits | aan |
| Websockets Support | uit |
| SSL → certificaat | Request a new SSL Certificate (Let's Encrypt) |
| Force SSL | aan |
| HTTP/2 Support | aan |
| HSTS Enabled | aan |

Geen custom locations; de CSP en overige headers komen uit de container zelf. Controle na
afloop: `curl -sI https://verwijzers.slaapkliniek.be/nl/aanvraag/ | grep -i "content-security\|cache-control"`
moet de strikte CSP en `no-store` tonen.

## Terugdraaien

```bash
ssh root@dedodedodo.be "cd /data/verwijzers && git checkout <vorige tag of commit> && docker compose build --no-cache && docker compose up -d"
```

De proxyhost in NPM verwijderen (of uitschakelen) haalt de site offline zonder de container aan te raken.

## 4. Domeinen (slaapstudie.* en etudedusommeil.*)

Sinds v0.2.0 **serveren** de twee drukwerkdomeinen de site zelf: `slaapstudie.be/` → `/nl/`,
`etudedusommeil.be/` → `/fr/` (canonical per taal uit `domeinen` in `config/site.json`). De
varianten met `www`, `.eu` en `.com` verwijzen met 301 naar het `.be`-domein van hun taal, met
behoud van het pad. `verwijzers.slaapkliniek.be` blijft werken. Alles zit in `nginx/default.conf`
(gekozen op de Host-header die NPM doorgeeft) en wordt in CI met `nginx -t` en
`tests/test_build.py` bewaakt.

**Gandi (LiveDNS), per domein — zes keer hetzelfde:**

| type | naam | waarde | TTL |
|---|---|---|---|
| A | `@` | `65.108.230.243` | 1800 |
| A | `www` | `65.108.230.243` | 1800 |

Verwijder Gandi's parkeerrecords (`www` CNAME naar `webredir.vip.gandi.net`, `@` naar
217.70.184.38). MX-, SPF- en DKIM-records mogen blijven.

**Nginx Proxy Manager — één proxyhost met twaalf namen** (bestaat sinds 30-09-2026):
`slaapstudie.{be,eu,com}`, `etudedusommeil.{be,eu,com}` en hun `www`-varianten → `http` →
`verwijzers` : `80`, één Let's Encrypt-certificaat voor alle namen, Force SSL, HTTP/2, HSTS.

Controle: `curl -sI https://slaapstudie.be/ | grep -i location` → `/nl/`;
`curl -sI https://www.slaapstudie.eu/aanvraag/ | grep -i location` →
`https://slaapstudie.be/aanvraag/`; `curl -s https://etudedusommeil.be/fr/ | grep canonical`.
