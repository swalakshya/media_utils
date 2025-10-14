# Docker Deployment Guide

This guide explains how to build and run the Media Utils application using Docker.

## Prerequisites

- Docker installed (version 20.10 or later)
- Docker Compose installed (version 1.29 or later)

## Quick Start

### Option 1: Using Docker Compose (Recommended)

```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

Access the application at: http://localhost:8000

### Option 2: Using Docker directly

```bash
# Build the image
docker build -t media-utils .

# Run the container
docker run -d \
  --name media-utils \
  -p 8000:8000 \
  --restart unless-stopped \
  media-utils

# View logs
docker logs -f media-utils

# Stop the container
docker stop media-utils
docker rm media-utils
```

## Configuration

### Environment Variables

You can customize the application using environment variables:

```bash
docker-compose up -d \
  -e PYTHONUNBUFFERED=1
```

### Resource Limits

Adjust CPU and memory limits in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '4.0'      # Max CPUs (adjust based on your system)
      memory: 2G       # Max memory
    reservations:
      cpus: '2.0'      # Minimum CPUs
      memory: 1G       # Minimum memory
```

### Persistent Storage

By default, Docker volumes are used for uploads and outputs:

```bash
# View volumes
docker volume ls

# Backup a volume
docker run --rm -v media-uploads:/data -v $(pwd):/backup alpine tar czf /backup/uploads-backup.tar.gz /data

# Restore a volume
docker run --rm -v media-uploads:/data -v $(pwd):/backup alpine tar xzf /backup/uploads-backup.tar.gz -C /
```

## Accessing the Application

- **Frontend UI**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **API Health Check**: http://localhost:8000/api/

## API Endpoints

- `POST /api/pdf/ocr/async` - Start PDF OCR processing
- `GET /api/pdf/ocr/stream/{job_id}` - Stream progress updates (SSE)
- `POST /api/pdf/ocr/cancel/{job_id}` - Cancel a running job
- `GET /api/pdf/download/{job_id}` - Download processed PDF

## Supported Languages

The Docker image includes Tesseract language packs for:
- Hindi (hin)
- Gujarati (guj)
- English (eng)
- Marathi (mar)
- Tamil (tam)
- Telugu (tel)

## Development

To rebuild the image after code changes:

```bash
# Rebuild and restart
docker-compose up -d --build

# Or with Docker directly
docker build -t media-utils .
docker stop media-utils && docker rm media-utils
docker run -d --name media-utils -p 8000:8000 media-utils
```

## Troubleshooting

### Container won't start

Check logs:
```bash
docker-compose logs media-utils
# or
docker logs media-utils
```

### Out of memory errors

Increase memory limit in `docker-compose.yml` or add swap space.

### OCR processing is slow

- Increase CPU limits in `docker-compose.yml`
- The application uses half available cores by default
- Check if Docker has enough resources allocated (Docker Desktop settings)

### Port already in use

Change the port mapping in `docker-compose.yml`:
```yaml
ports:
  - "8080:8000"  # Use port 8080 instead
```

Then access at: http://localhost:8080

## Production Deployment

For production, consider:

1. **Use a reverse proxy** (nginx/Traefik) for HTTPS
2. **Set up monitoring** (Prometheus, Grafana)
3. **Configure log rotation**
4. **Set resource limits** appropriately
5. **Use Docker secrets** for sensitive data
6. **Enable health checks** in your orchestrator

Example nginx configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # For SSE support
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
    }
}
```

## Cleanup

Remove all containers, volumes, and images:

```bash
# Stop and remove containers
docker-compose down -v

# Remove image
docker rmi media-utils

# Clean up all unused Docker resources
docker system prune -a
```