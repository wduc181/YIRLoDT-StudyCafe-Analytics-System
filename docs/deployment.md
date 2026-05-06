# VPS Deployment

Dung Docker Compose production:

```bash
cp env.prod.example env.prod
nano env.prod
docker compose --env-file env.prod -f docker-compose.prod.yml up -d --build
```

Frontend production duoc build thanh static file va serve qua Nginx container.
`VITE_API_BASE_URL` phai la domain HTTPS public vi Vite doc bien nay luc build.

Vi GPS tren mobile browser can secure context, hay dat reverse proxy HTTPS truoc
2 port noi bo:

- Frontend: `127.0.0.1:5173`
- Backend: `127.0.0.1:8088`

Vi du Caddy:

```caddyfile
studycafe.example.com {
    handle /api/* {
        reverse_proxy 127.0.0.1:8088
    }

    handle /docs* {
        reverse_proxy 127.0.0.1:8088
    }

    handle /openapi.json {
        reverse_proxy 127.0.0.1:8088
    }

    handle {
        reverse_proxy 127.0.0.1:5173
    }
}
```

Neu can nap mock data demo:

```bash
docker compose --env-file env.prod -f docker-compose.prod.yml --profile seed up mock-data
```

Kiem tra nhanh:

```bash
curl https://studycafe.example.com/
curl https://studycafe.example.com/api/cafes
```
