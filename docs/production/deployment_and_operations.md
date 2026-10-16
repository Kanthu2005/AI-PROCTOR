# ProctorAI — Production Deployment & Operations Guide

This guide outlines the production deployment architecture, security hardening, multi-tenant database isolation, HTTPS reverse-proxy configuration, worker scaling, and health monitoring for **ProctorAI**.

---

## 1. System Architecture & Network Topology

```
                         [ Internet / Candidate / Recruiter ]
                                         │
                                  HTTPS (TLS 1.3)
                                  WSS (WebSockets)
                                         ▼
                     ┌────────────────────────────────────────┐
                     │   Reverse Proxy (Nginx / Caddy / ALB)  │
                     │  - TLS Termination                    │
                     │  - Preserves X-SafeExamBrowser-*       │
                     │  - Handles WebSocket Upgrades          │
                     │  - Rate Limiting & DDOS Mitigation     │
                     └───────────────────┬────────────────────┘
                                         │ Internal HTTP/WS (8000)
                                         ▼
                     ┌────────────────────────────────────────┐
                     │     FastAPI / Gunicorn Application     │
                     │  - 4+ Uvicorn Workers                  │
                     │  - Non-root user: proctorai            │
                     │  - Argon2id Password Verification      │
                     │  - Multi-tenant RBAC & IDOR Guards     │
                     └───────┬────────────────────────┬───────┘
                             │                        │
         PostgreSQL 15+      │                        │ Docker Socket (Restricted)
         (Least Privilege)   ▼                        ▼
     ┌────────────────────────────┐    ┌─────────────────────────────────┐
     │   PostgreSQL Database      │    │  Docker / Isolated Subprocess   │
     │ - Connection Pooling       │    │  Sandbox Boundary               │
     │ - Dedicated user & schema  │    │  - python:3.11-slim             │
     │ - SSL mode: verify-full    │    │  - Network: None                │
     │ - Automated WAL archiving  │    │  - Read-only rootfs, non-root   │
     └────────────────────────────┘    └─────────────────────────────────┘
```

---

## 2. HTTPS & Reverse Proxy Configuration

Production environments **must terminate TLS** and forward authenticated WebSockets and Safe Exam Browser verification headers intact.

### Nginx Production Configuration (`/etc/nginx/sites-available/proctorai.conf`)

```nginx
# Rate limiting zone for public endpoints
limit_req_zone $binary_remote_addr zone=proctorai_auth:10m rate=10r/m;
limit_req_zone $binary_remote_addr zone=proctorai_general:10m rate=60r/s;

upstream proctorai_backend {
    server 127.0.0.1:8000 fail_timeout=0;
    keepalive 32;
}

server {
    listen 80;
    server_name assessment.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name assessment.yourdomain.com;

    # TLS Certificates (Let's Encrypt / Cloudflare)
    ssl_certificate /etc/letsencrypt/live/assessment.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/assessment.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    # Security Headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Client Request Limits
    client_max_body_size 16M;

    # Proxy Headers & SEB Custom Header Preservation
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # CRITICAL: Preserve Safe Exam Browser Cryptographic Headers
    proxy_pass_request_headers on;
    proxy_set_header X-SafeExamBrowser-RequestHash $http_x_safeexambrowser_requesthash;
    proxy_set_header X-SafeExamBrowser-ConfigKeyHash $http_x_safeexambrowser_configkeyhash;

    # WebSockets Proxying (/ws & /api/v1/ws)
    location ~* ^/(api/v1/)?ws/ {
        proxy_pass http://proctorai_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    # Sensitive Auth Endpoints Rate Limiting
    location /api/v1/auth/login {
        limit_req zone=proctorai_auth burst=5 nodelay;
        proxy_pass http://proctorai_backend;
    }

    # Health Probes (No rate limiting for orchestrators)
    location /health {
        proxy_pass http://proctorai_backend;
        access_log off;
    }

    # General API Traffic
    location /api/ {
        limit_req zone=proctorai_general burst=30 nodelay;
        proxy_pass http://proctorai_backend;
    }

    # Frontend Single Page App Assets
    location / {
        root /var/www/proctorai-frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }
}
```

---

## 3. Production Environment Variables Reference

Create `/etc/proctorai/proctorai.env` (restricted with `chmod 600`):

| Variable | Recommended Production Value | Description |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `production` | Enables strict production guards, disables demo seeding. |
| `LOG_LEVEL` | `INFO` | Output log severity (`INFO` or `WARNING`). |
| `SECRET_KEY` | *(32+ char random hex)* | Cryptographic signing key for JWT session tokens. |
| `COOKIE_SECURE` | `True` | Forces `Secure; HttpOnly; SameSite=Lax` on session cookies. |
| `CSRF_PROTECTION_ENABLED` | `True` | Enforces double-submit CSRF cookie checks on state-changing requests. |
| `AUTH_RATE_LIMIT_PER_MINUTE`| `10` | Rejects brute-force password guessing attacks. |
| `DATABASE_URL` | `postgresql://proctor_app:...@pg.internal:5432/proctorai_prod?sslmode=verify-full` | Production PostgreSQL connection string. |
| `DB_POOL_SIZE` | `20` | Base SQLAlchemy connection pool per worker process. |
| `DB_MAX_OVERFLOW` | `40` | Burst connection allowance above pool size. |
| `DB_POOL_TIMEOUT` | `30` | Seconds to wait before timing out connection acquisition. |
| `USE_DOCKER_SANDBOX` | `True` | Executes untrusted candidate code in disposable Docker containers. |
| `INTERNAL_RUNNER_SECRET` | *(32+ char random)* | Authentication secret for the coding sandbox boundary. |
| `SANDBOX_MAX_MEMORY_MB` | `128` | Memory ceiling per coding sandbox container. |
| `CORS_ORIGINS` | `https://assessment.yourdomain.com` | Strict whitelist of allowed web application origins. |

---

## 4. Production Application Server Execution

Do **not** use `uvicorn --reload` in production. Run under **Gunicorn** managing multiple asynchronous Uvicorn worker processes:

```bash
# Production Startup Command (4 workers for 2 CPU cores)
exec gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 127.0.0.1:8000 \
  --timeout 120 \
  --keep-alive 5 \
  --max-requests 10000 \
  --max-requests-jitter 1000 \
  --access-logfile /var/log/proctorai/access.log \
  --error-logfile /var/log/proctorai/error.log \
  --capture-output
```

### Systemd Service Unit (`/etc/systemd/system/proctorai-backend.service`)

```ini
[Unit]
Description=ProctorAI Assessment & Proctoring Backend API
After=network.target postgresql.service

[Service]
Type=simple
User=proctorai
Group=proctorai
WorkingDirectory=/opt/proctorai/backend
EnvironmentFile=/etc/proctorai/proctorai.env
ExecStart=/opt/proctorai/backend/.venv/bin/gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000 \
    --timeout 120
Restart=always
RestartSec=5s
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

---

## 5. Kubernetes & Container Orchestration Probes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: proctorai-backend
spec:
  replicas: 3
  template:
    spec:
      containers:
        - name: backend
          image: proctorai/backend:latest
          ports:
            - containerPort: 8000
          livenessProbe:
            httpGet:
              path: /health/live
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 15
            timeoutSeconds: 3
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 8000
            initialDelaySeconds: 15
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 2
```
