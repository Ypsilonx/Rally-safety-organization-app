# Nasazení na produkční server

Tenhle dokument popisuje nasazení na veřejně dostupný VPS s vlastní doménou
(scénář z bezpečnostního auditu — appka dostupná odkudkoliv na internetu).
Pro lokální vývoj viz `SETUP.md`.

## Architektura nasazení

```
Internet (HTTPS/WSS)
        │
        ▼
┌───────────────────┐
│  Caddy (80/443)    │  automatický TLS certifikát (Let's Encrypt)
│  - / → frontend/    │  statické soubory
│  - /api/* → :8000   │  reverse proxy
│  - /ws/*  → :8000   │  reverse proxy (websocket upgrade)
└───────────────────┘
        │ 127.0.0.1
        ▼
┌───────────────────┐
│  uvicorn :8000      │  poslouchá jen na localhost, ven není vystavený
│  backend.main:app   │
└───────────────────┘
```

Frontend i backend běží pod **stejnou doménou** — díky tomu `frontend/js/auth.js`
a `frontend/js/websocket.js` používají `window.location` a nepotřebují žádnou
build-time konfiguraci URL.

## Požadavky

- Linux VPS (Ubuntu/Debian), root/sudo přístup
- Doména ukazující A záznamem na IP serveru
- Nainstalovaný [uv](https://astral.sh/uv) a [Caddy](https://caddyserver.com/docs/install)
- Otevřené porty 80 a 443 (443 pro TLS, 80 pro ACME challenge + redirect)

## 1. Příprava aplikace

```bash
git clone <repo-url> /opt/rally-safety-app
cd /opt/rally-safety-app
uv sync --no-dev
cp .env.example .env
```

### Konfigurace `.env` — checklist před ostrým nasazením

- [ ] `DEBUG=False` (jinak je `/api/debug/pins` veřejně dostupné)
- [ ] `HOST=127.0.0.1` (uvicorn ať poslouchá jen pro Caddy, ne pro celý internet)
- [ ] `ALLOWED_ORIGINS=https://vase-domena.cz` (ne `*`)
- [ ] `VEDENI_PASSWORD_HASH=<vlastní hash>` — **vestavěné demo heslo `demo123`
      je veřejně známé ze zdrojového kódu.** Vygeneruj nové:
      ```bash
      uv run python -c "from backend.core.auth import hash_password; print(hash_password('nove-bezpecne-heslo'))"
      ```
      a vlož výstup do `.env`. Zapiš si heslo v plaintextu jinam (např.
      heslo manažer) — v `.env` je jen hash, plaintext hesla nikde neukládáme.
- [ ] `SESSION_EXPIRE_MINUTES` — 480 (8h) je rozumný default pro trvání
      jedné rally; uprav podle délky akce.

## 2. systemd služba pro backend

`/etc/systemd/system/rally-backend.service`:

```ini
[Unit]
Description=Rally Safety App backend
After=network.target

[Service]
Type=simple
User=rally
WorkingDirectory=/opt/rally-safety-app
ExecStart=/opt/rally-safety-app/.venv/bin/uvicorn backend.main:app \
    --host 127.0.0.1 --port 8000 \
    --proxy-headers --forwarded-allow-ips=127.0.0.1
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

`--proxy-headers --forwarded-allow-ips=127.0.0.1` je nutné, jinak backend
(a jeho rate limiter na loginu) vidí jako zdroj každého requestu jen loopback
Caddy, ne skutečnou IP klienta — omezení pokusů o login by pak sdílel jeden
"virtuální" útočník se všemi reálnými uživateli.

Spuštění a autostart po rebootu:

```bash
sudo useradd -r -s /usr/sbin/nologin rally  # pokud ještě neexistuje
sudo chown -R rally:rally /opt/rally-safety-app
sudo systemctl daemon-reload
sudo systemctl enable --now rally-backend
sudo systemctl status rally-backend
```

## 3. Caddy — reverse proxy + TLS

`/etc/caddy/Caddyfile`:

```
vase-domena.cz {
    root * /opt/rally-safety-app/frontend
    file_server

    handle /api/* {
        reverse_proxy 127.0.0.1:8000
    }

    handle /ws/* {
        reverse_proxy 127.0.0.1:8000
    }
}
```

Caddy websocket upgrade (Connection/Upgrade hlavičky) i TLS certifikát řeší
automaticky, není potřeba nic dalšího nastavovat.

```bash
sudo systemctl reload caddy
```

## 4. Firewall

Port 8000 nesmí být dostupný zvenku — poslouchá jen na `127.0.0.1`, takže
je to defaultně bezpečné, ale firewall to potvrdí i kdyby se `HOST` v `.env`
někdy omylem přepsal:

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 8000/tcp
sudo ufw enable
```

## 5. Zálohování dat

Appka nemá databázi — veškerý stav je v `data/*.json` (PINy, katalog lidí,
RZ kontext). Restart procesu je v pořádku (soubory přežijí), ale **ztráta
disku znamená ztrátu všech PINů a přiřazení**. Před každou akcí:

```bash
# Pravidelná záloha (např. cron každých 15 minut během závodu)
tar -czf /var/backups/rally-data-$(date +%Y%m%d-%H%M).tar.gz /opt/rally-safety-app/data
```

## 6. Aktualizace nasazené verze

```bash
cd /opt/rally-safety-app
git pull
uv sync --no-dev
sudo systemctl restart rally-backend
```

Restart backendu odhlásí všechny připojené vedení (session tokeny jsou jen
v paměti) — komisaři se svým PINem přihlásí znovu bez problému. Restart
plánuj mimo aktivní RZ, ne uprostřed provozu.

## Ověření po nasazení

```bash
curl -s https://vase-domena.cz/health
curl -s -o /dev/null -w "%{http_code}\n" https://vase-domena.cz/
```

A ručně v prohlížeči: přihlášení jako vedení i jako komisař, ověřit že se
zprávy v chatu doručují oběma směry (WebSocket přes `wss://`).
