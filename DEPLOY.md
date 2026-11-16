# Deploying ASoundJob

One Ubuntu 24.04 server runs everything:

| piece | how it runs | where |
| --- | --- | --- |
| Caddy | system service, handles HTTPS | `/etc/caddy/Caddyfile` (copy of `deploy/Caddyfile`) |
| API (FastAPI) | `asoundjob-api.service`, port 8000, local only | `/srv/asoundjob/api` |
| Website (SvelteKit) | `asoundjob-web.service`, port 3000, local only | `/srv/asoundjob/web` |
| Scrape | `asoundjob-scrape.timer`, nightly 03:00 New York time | `/srv/asoundjob/scraper` |
| Backup | `asoundjob-backup.timer`, daily 05:00, keeps 14 | `/var/lib/asoundjob/backups` |
| Company-list push | `asoundjob-seed-push.timer`, daily 05:30 | commits `data/audio_companies_final.json` to `main` |
| Database | SQLite (WAL mode) | `/var/lib/asoundjob/asoundjob.db` |
| Settings and secrets | read by every service | `/etc/asoundjob/asoundjob.env` |

Caddy sends `/api/*` to the API and everything else to the website. All of
these files are in `deploy/`.

**Company edits live on the server.** Admin → Companies writes
`data/audio_companies_final.json` on the server, and a daily job pushes it to
`main`. Before editing that file on your own machine, `git pull` first.

---

## Before you start

- [ ] The domain `asoundjob.com` is bought.
- [ ] A Hetzner Cloud server exists: Ubuntu 24.04, 4 GB RAM or more, your SSH
      key added, backups on, and a firewall allowing TCP 22, 80 and 443.
- [ ] In Namecheap → Advanced DNS, A records for `@` and `www` point to the
      server's IPv4 address, and the default parking records are deleted.

Check the DNS from your Mac. Both commands should print the server's IP:

```bash
dig +short asoundjob.com
```

```bash
dig +short www.asoundjob.com
```

In the steps below, replace `SERVER_IP` with the server's IPv4 address.

---

## 1. Log in

```bash
ssh root@SERVER_IP
```

Everything until step 7 runs **on the server** as root.

## 2. Base packages, swap and the app user

```bash
apt update && apt -y upgrade
```

```bash
apt install -y git sqlite3 curl ca-certificates gnupg debian-keyring debian-archive-keyring apt-transport-https
```

Add 2 GB of swap, a safety net for the scraper's browsers:

```bash
fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile && echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

Create the user the app runs as, and its folders:

```bash
useradd --system --create-home --home-dir /var/lib/asoundjob --shell /bin/bash asoundjob
```

```bash
mkdir -p /srv/asoundjob /etc/asoundjob && chown asoundjob:asoundjob /srv/asoundjob
```

## 3. Install uv (Python), Node 22 and Caddy

uv installs the exact Python version (3.9) the code is tested on:

```bash
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh
```

Node 22:

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && apt install -y nodejs
```

Caddy:

```bash
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
```

```bash
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
```

```bash
apt update && apt install -y caddy
```

## 4. GitHub deploy key and the code

Switch to the app user:

```bash
su - asoundjob
```

Make a key that can push to this one repository only:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/github_deploy -N "" -C "asoundjob-server"
```

```bash
printf 'Host github.com\n  IdentityFile ~/.ssh/github_deploy\n  IdentitiesOnly yes\n' > ~/.ssh/config && ssh-keyscan github.com >> ~/.ssh/known_hosts
```

```bash
cat ~/.ssh/github_deploy.pub
```

Add the printed key on GitHub: the repository → **Settings → Deploy keys → Add
deploy key**. Title it `asoundjob-server`, paste the key, and **tick "Allow
write access"**. The write access lets the server push company edits.

Then clone:

```bash
git clone git@github.com:joshieyu/asoundjob.git /srv/asoundjob
```

## 5. Python, the scraper's browser and the website build

Still as `asoundjob`:

```bash
cd /srv/asoundjob && uv python install 3.9 && uv venv --python 3.9 venv
```

```bash
uv pip install --python venv/bin/python -r requirements.txt
```

```bash
venv/bin/python -m playwright install chromium
```

```bash
cd web && npm ci --no-audit --no-fund && npm run build && cd ..
```

Go back to root for the browser's system libraries:

```bash
exit
```

```bash
/srv/asoundjob/venv/bin/python -m playwright install-deps chromium
```

## 6. Settings and secrets

As root:

```bash
cp /srv/asoundjob/deploy/asoundjob.env.example /etc/asoundjob/asoundjob.env && chown root:asoundjob /etc/asoundjob/asoundjob.env && chmod 640 /etc/asoundjob/asoundjob.env
```

Generate the secret key that signs admin logins, and copy the output:

```bash
openssl rand -hex 32
```

Open the file:

```bash
nano /etc/asoundjob/asoundjob.env
```

Replace the three `CHANGE_ME` values:

- `ADMIN_USERNAME`: the name you'll log in with.
- `ADMIN_PASSWORD`: at least 12 characters. Use only letters, digits, `-` and
  `_` (no spaces, quotes or `$`), because the update script reads this file as
  shell. A password manager's generator works well.
- `ADMIN_SECRET_KEY`: the `openssl` output from above.

Save with Ctrl+O, Enter, then exit with Ctrl+X. The API refuses to start if
any of these is missing, too short or still a development default.

## 7. Copy your database up

**On your Mac**, from the repo folder, make a consistent copy. A plain file
copy can miss recent writes, because the database is in WAL mode.

```bash
sqlite3 asoundjob.db ".backup asoundjob-upload.db"
```

```bash
scp asoundjob-upload.db root@SERVER_IP:/var/lib/asoundjob/asoundjob.db
```

```bash
rm asoundjob-upload.db
```

**Back on the server** as root:

```bash
chown asoundjob:asoundjob /var/lib/asoundjob/asoundjob.db
```

```bash
sudo -u asoundjob -H bash -c 'cd /srv/asoundjob/scraper && set -a && . /etc/asoundjob/asoundjob.env && set +a && ../venv/bin/alembic upgrade head'
```

## 8. Start everything

```bash
cp /srv/asoundjob/deploy/systemd/* /etc/systemd/system/ && systemctl daemon-reload
```

```bash
systemctl enable --now asoundjob-api asoundjob-web asoundjob-scrape.timer asoundjob-backup.timer asoundjob-seed-push.timer
```

```bash
cp /srv/asoundjob/deploy/Caddyfile /etc/caddy/Caddyfile && systemctl reload caddy
```

Caddy fetches the HTTPS certificate on the first visit, which takes a few
seconds.

## 9. Check it

On the server:

```bash
systemctl --no-pager status asoundjob-api asoundjob-web caddy | grep -E "●|Active"
```

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://asoundjob.com/api/jobs/featured
```

That should print `200`. Then in a browser:

- [ ] `https://asoundjob.com` loads with jobs and a padlock.
- [ ] `https://www.asoundjob.com` redirects to `https://asoundjob.com`.
- [ ] A job page and a company page load.
- [ ] `https://asoundjob.com/admin` accepts the admin login from step 6.
- [ ] `https://asoundjob.com/robots.txt` mentions `https://asoundjob.com/sitemap.xml`.

Scrape one company to confirm the scraper works from the server (about a
minute):

```bash
sudo -u asoundjob -H bash -c 'cd /srv/asoundjob/scraper && set -a && . /etc/asoundjob/asoundjob.env && set +a && ../venv/bin/python -m scraper.main --company apple --skip-load'
```

```bash
systemctl list-timers 'asoundjob-*'
```

That lists when the next scrape, backup and push will run.

---

## Updating the site

After pushing new code to `main`:

```bash
ssh root@SERVER_IP
```

```bash
/srv/asoundjob/deploy/update.sh
```

It pushes any pending company edits, pulls `main`, updates Python packages,
runs database migrations, rebuilds the website, and restarts the API and the
website. An admin-started scrape that is running gets stopped by the restart;
the nightly one runs separately and is not affected.

## Day to day

Logs (Ctrl+C to stop following):

```bash
journalctl -u asoundjob-api -f
```

```bash
journalctl -u asoundjob-web -f
```

Last night's scrape:

```bash
journalctl -u asoundjob-scrape --since yesterday --no-pager | tail -40
```

Run a full scrape now (about 30 minutes; returns at once if one is already
running):

```bash
systemctl start --no-block asoundjob-scrape
```

Back up now, or push company edits now:

```bash
systemctl start asoundjob-backup
```

```bash
systemctl start asoundjob-seed-push
```

### Restoring a backup

```bash
systemctl stop asoundjob-api asoundjob-web
```

```bash
gunzip -c /var/lib/asoundjob/backups/asoundjob-YYYY-MM-DD.db.gz > /var/lib/asoundjob/asoundjob.db && rm -f /var/lib/asoundjob/asoundjob.db-wal /var/lib/asoundjob/asoundjob.db-shm && chown asoundjob:asoundjob /var/lib/asoundjob/asoundjob.db
```

```bash
systemctl start asoundjob-api asoundjob-web
```

Hetzner's server backups cover the whole machine as a second line.

### Getting the live database onto your Mac

```bash
ssh root@SERVER_IP 'sqlite3 /var/lib/asoundjob/asoundjob.db ".backup /tmp/live.db"' && scp root@SERVER_IP:/tmp/live.db ./asoundjob.db
```

Stop your local API first; this replaces your local copy.

## Things to know

- **Rate limits are kept in memory**, so the API runs with one worker. Keep
  `--workers 1` in `asoundjob-api.service`.
- **Some careers sites block data-centre traffic.** A company that scrapes fine
  from home may fail from the server. Admin → Company health shows which.
- **One scrape at a time.** The scraper takes `/srv/asoundjob/.scrape.lock`; a
  second start (timer, admin button or by hand) exits with code 75 and does
  nothing.
- **`ASOUNDJOB_ENV=production`** makes the API refuse development credentials.
