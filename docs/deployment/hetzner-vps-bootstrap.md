# Hetzner VPS Bootstrap For Phase 1 Caddy Layout

This runbook starts from the current assumed state:

- Hetzner VPS is provisioned
- Ubuntu packages are updated
- the server has already been rebooted
- you can SSH in as `admin`

It follows the architecture in [vps-phase1-caddy.md](./vps-phase1-caddy.md): one VPS, one shared Caddy proxy, one Compose project per app, and a shared `edge` Docker network.

## Goal

Prepare the host so it is ready for:

- `/srv/proxy` for the shared Caddy stack
- `/srv/blogit` for this repo
- `/srv/tystar` for the public site
- `/srv/eatit` for the EatIt app

## Before You Start

Keep **two SSH sessions** open while changing SSH access. Do not close the original `admin` session until you have verified that the new deploy user can log in with SSH keys and run `sudo`.

## 1. Create A Deploy User

This runbook uses `deploy` as the day-to-day operator account.

```bash
adduser deploy
usermod -aG sudo deploy
mkdir -p /home/deploy/.ssh
cp /home/admin/.ssh/authorized_keys /home/deploy/.ssh/authorized_keys
chown -R deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys
```

Verify from a **new terminal on your machine**:

```bash
ssh deploy@your_server_ip
sudo whoami
```

Expected result: `sudo whoami` prints `root`.

## 2. Harden SSH

Once the `deploy` login works, disable password auth and direct root SSH login.

Open the SSH daemon config:

```bash
sudoedit /etc/ssh/sshd_config
```

Ensure these settings are present:

```text
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
ChallengeResponseAuthentication no
UsePAM yes
```

Validate and reload:

```bash
sudo sshd -t
sudo systemctl reload ssh
```

Verify you can still log in as `deploy` before closing the original session.

## 3. Enable The Firewall

Allow SSH, HTTP, and HTTPS only.

```bash
sudo apt-get update
sudo apt-get install -y ufw
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```

Expected open ports:

- `22/tcp`
- `80/tcp`
- `443/tcp`

## 4. Install Docker And Compose

Install Docker Engine and the Compose plugin from Docker's Ubuntu repository:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker deploy
```

Open a fresh SSH session as `deploy`, then verify:

```bash
docker --version
docker compose version
docker ps
```

## 5. Create The VPS Directory Layout

Create the base structure described in the phase-1 deployment doc.

```bash
sudo mkdir -p /srv/proxy
sudo mkdir -p /srv/blogit
sudo mkdir -p /srv/tystar
sudo mkdir -p /srv/eatit
sudo chown -R deploy:deploy /srv/proxy /srv/blogit /srv/tystar /srv/eatit
```

Optional next-level structure:

```bash
mkdir -p /srv/proxy/data /srv/proxy/config
mkdir -p /srv/blogit/{logs,uploads}
mkdir -p /srv/tystar/{logs,uploads}
mkdir -p /srv/eatit/{logs,uploads}
```

## 6. Create The Shared Docker Network

Create the `edge` network once. Every app stack and the proxy stack will join it.

```bash
docker network create edge
docker network ls | grep edge
```

## 7. Install The Shared Proxy Files

Copy the tracked proxy files from this repo into `/srv/proxy`:

- [proxy/docker-compose.yml](../../proxy/docker-compose.yml)
- [proxy/Caddyfile](../../proxy/Caddyfile)

Recommended target names on the server:

- `/srv/proxy/docker-compose.yml`
- `/srv/proxy/Caddyfile`
- `/srv/proxy/.env`

Suggested `.env`:

```env
CADDY_ACME_EMAIL=you@example.com
```

## 8. Point DNS Before Requesting Public TLS

Before you expect Caddy to issue Let's Encrypt certificates, create these DNS records and point them to the VPS public IPv4 address:

- `tystar.cz`
- `www.tystar.cz`
- `blog-it.tystar.cz`
- `eat-it.tystar.cz`

Check from your own machine:

```bash
dig +short tystar.cz
dig +short www.tystar.cz
dig +short blog-it.tystar.cz
dig +short eat-it.tystar.cz
```

All should resolve to the VPS public IP before you rely on automatic public TLS.

## 9. Start Caddy

From `/srv/proxy`:

```bash
cd /srv/proxy
docker compose up -d
docker compose ps
docker compose logs --tail=100
```

Expected result:

- the `caddy` container is `Up`
- ports `80` and `443` are bound on the host
- logs show certificate issuance attempts after DNS is ready

## 10. Smoke-Test The Proxy Layer

Verify the listening ports on the server:

```bash
sudo ss -tulpn | grep -E ':80|:443'
```

Check externally:

```bash
curl -I https://tystar.cz
curl -I https://blog-it.tystar.cz
curl -I https://eat-it.tystar.cz
```

At this stage, placeholder responses are fine. The goal is to verify:

- DNS reaches the VPS
- Caddy answers on HTTPS
- certificates are issued successfully

## 11. What Comes Next

Once the shared host and proxy are working, move to the first real app stack:

1. Build the Blogit production frontend image.
2. Add `/srv/blogit/docker-compose.production.yml`.
3. Clone this repo into `/srv/blogit`.
4. Attach Blogit services to the `edge` network.
5. Replace the placeholder `blog-it.tystar.cz` response in Caddy with `reverse_proxy` rules for:
   - `blogit_frontend:80`
   - `blogit_backend:8000`

That gives you one working vertical slice before repeating the pattern for `tystar` and `eatit`.

## Out Of Scope

- CI/CD automation
- backups and restore drills
- centralized logs and metrics
- managed Postgres migration
- blue/green or multi-node deployments
