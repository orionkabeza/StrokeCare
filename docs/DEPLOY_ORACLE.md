<!-- Owner: Orion Kabeza (DevOps) -->
# Deploy the pilot on Oracle Cloud Always Free

**Fictional demo data only.** No real patient data goes on this server until every BLOCKER in
`docs/OPEN_QUESTIONS.md` is closed (clinical reviewer, verified emergency numbers, consent text, ethics approval,
data-protection check, hosting decision for real health data). An Always Free VM has no managed database, no
guaranteed backups and no compliance claims, so it is a pilot and demo host, not a place for real health records.

What this sets up: one virtual machine running four containers from `docker-compose.prod.yml`: PostgreSQL 16 (no
public port), the app (Django + the plain-files web app), the alert worker, and Caddy, which gets a free HTTPS
certificate and is the only thing reachable from the internet.

## What was tested, and what was not

| Item | State |
|---|---|
| App with production settings (debug off) behind a proxy header: `/healthz`, `/`, `/js/main.js` return 200, an unknown host returns 400, plain HTTP is redirected to HTTPS | **Run**, natively on Windows against a local PostgreSQL |
| `docker-compose.prod.yml` parses and has the four services | **Run** (YAML load only) |
| `docker compose -f docker-compose.prod.yml up` on a real VM, Caddy certificate, Oracle firewall rules | **Not run.** Needs an Oracle account and a server. This guide is the checklist for that first run |

## 1. Create the account and the server

1. Sign up at oracle.com/cloud/free. You choose a **home region** once, and Always Free resources only exist in
   it. Closest to Rwanda is **South Africa (Johannesburg)**; check that it is listed as available when you sign up.
   Free-tier terms, shape availability and card checks change: read Oracle's current Always Free page first.
2. Create an instance: image **Ubuntu 24.04**, shape **VM.Standard.A1.Flex** (Arm, 2 OCPU and 12 GB RAM is plenty)
   or **VM.Standard.E2.1.Micro** (1 GB: tight, add swap). Arm capacity can be "out of capacity"; retry later or
   use the Micro. Add your SSH public key. Note the **public IP**.
3. In the instance's subnet **Security List** (or network security group) add ingress rules for TCP **80** and
   **443** from `0.0.0.0/0`. Keep 22 open only if you need it.

## 2. Open the server's own firewall (a common Oracle trap)

Oracle's Ubuntu images block ports in iptables as well as in the cloud rules. On the server:

```bash
sudo iptables -I INPUT 6 -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -p tcp --dport 443 -j ACCEPT
sudo apt-get install -y iptables-persistent && sudo netfilter-persistent save
```

## 3. Install Docker and get the code

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER && newgrp docker
git clone https://github.com/orionkabeza/StrokeCare.git && cd StrokeCare
```

## 4. Name and settings

- With a domain: point an `A` record at the public IP, and set `DOMAIN` to that name.
- Without one: use `<ip with dashes>.sslip.io`, for example `129-151-10-20.sslip.io`. It resolves to that IP and
  Caddy can get a certificate for it.

```bash
cp deploy/.env.prod.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # run twice: secret key, database password
nano .env     # DOMAIN, DJANGO_SECRET_KEY, POSTGRES_PASSWORD
chmod 600 .env
```

Leave `ALLOW_DEMO_DATA=0` unless this is the course demo. The compose file refuses to start if the secrets or
`DOMAIN` are empty.

## 5. Start it

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps          # db, web, worker, caddy all running; web "healthy"
curl -I https://YOUR-DOMAIN/healthz                    # 200 once Caddy has its certificate (about a minute)
```

The first start migrates the database and loads the draft reference data. Open `https://YOUR-DOMAIN/`.

Create an admin and any clinician accounts (only after checking a real licence):

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
docker compose -f docker-compose.prod.yml exec web python manage.py create_clinician <email> "<name>" --ref <licence> --verified
```

## 6. Backups (do this before relying on it)

The database lives in the `pgdata` Docker volume on one disk. A daily dump, copied off the server:

```bash
mkdir -p ~/backups
( crontab -l 2>/dev/null; echo '0 2 * * * cd ~/StrokeCare && docker compose -f docker-compose.prod.yml exec -T db pg_dump -U strokecare strokecare | gzip > ~/backups/strokecare-$(date +\%F).sql.gz && find ~/backups -mtime +14 -delete' ) | crontab -
```

Copy `~/backups` somewhere else too (Oracle Object Storage has a free allowance; or your laptop). **Test one
restore**: `gunzip -c file.sql.gz | docker compose -f docker-compose.prod.yml exec -T db psql -U strokecare strokecare`
into a fresh database.

## 7. Updating, logs, stopping

```bash
git pull && docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml down        # keeps the data; add -v to delete it
```

## Things to know

- **Idle reclaim:** Oracle may reclaim Always Free instances that stay idle for a long time. A busy pilot is
  fine; a forgotten one may disappear, which is another reason for off-server backups.
- **One server, one disk:** no failover. A reboot is fine (`restart: unless-stopped`); a lost disk is not.
- **Access:** whoever holds the SSH key and the Oracle account can read the database. Keep both to one or two
  named people, use SSH keys only, and never share `.env`.
- **Audit log:** after the first `migrate`, remove UPDATE and DELETE on `audit_auditlog` from the app's database
  role (see `docs/DEPLOYMENT.md`). The compose file uses the single `strokecare` database user, so this is not
  done automatically.
- **Scheduler:** the worker container runs the alert job every 15 minutes. If you use the GitHub scheduler
  instead, set `CRON_SECRET` here and as a GitHub secret.
