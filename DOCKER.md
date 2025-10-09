# 🐳 Docker Deployment Guide

Run FNIRSI FNB58 Monitor in a Docker container for easy deployment, consistent environments, and portability.

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd fnirsi-web-monitor

# Start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Access at http://localhost:5000
```

### Using Docker CLI

```bash
# Build the image
docker build -t fnb58-monitor .

# Run the container
docker run -d \
  --name fnb58-monitor \
  -p 5000:5000 \
  --device=/dev/bus/usb:/dev/bus/usb \
  --privileged \
  -v $(pwd)/sessions:/app/sessions \
  -v $(pwd)/exports:/app/exports \
  fnb58-monitor

# View logs
docker logs -f fnb58-monitor

# Stop the container
docker stop fnb58-monitor

# Remove the container
docker rm fnb58-monitor
```

---

## Configuration

### Environment Variables

Create a `.env` file or pass environment variables:

```bash
FLASK_ENV=production          # production or development
HOST=0.0.0.0                 # Server bind address
PORT=5000                    # Server port
BT_DEVICE_ADDRESS=XX:XX:XX   # Optional: Bluetooth device MAC address
SECRET_KEY=your-secret-key   # Optional: Flask secret key
```

### Docker Compose Configuration

Edit `docker-compose.yml` to customize:

```yaml
environment:
  - FLASK_ENV=production
  - PORT=5000
  - BT_DEVICE_ADDRESS=98:DA:B0:08:A1:82  # Your device MAC

ports:
  - "8080:5000"  # Change host port if 5000 is in use

volumes:
  - ./my-sessions:/app/sessions  # Custom session directory
  - ./my-exports:/app/exports    # Custom export directory
```

---

## USB Device Access

### Linux

#### Method 1: Device Passthrough (Recommended)

```bash
docker run -d \
  --device=/dev/bus/usb:/dev/bus/usb \
  --privileged \
  -p 5000:5000 \
  fnb58-monitor
```

#### Method 2: udev Rules (More Secure)

1. **Copy udev rules to host:**
```bash
sudo cp docker/99-fnirsi.rules /etc/udev/rules.d/
```

2. **Reload udev:**
```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

3. **Run container without --privileged:**
```bash
docker run -d \
  --device=/dev/bus/usb:/dev/bus/usb \
  -p 5000:5000 \
  fnb58-monitor
```

#### Find Device Path

```bash
# List all USB devices
lsusb

# Find FNIRSI device (Vendor ID: 0716)
lsusb | grep 0716

# Example output:
# Bus 001 Device 005: ID 0716:5030 FNIRSI FNB58

# Get device path
ls -la /dev/bus/usb/001/005
```

### macOS

Docker Desktop on macOS has limited USB passthrough support. **USB mode is NOT recommended.**

**Workaround:**
1. Run the Python app natively on macOS (not in Docker)
2. Or use Bluetooth mode in Docker (see below)

### Windows

USB passthrough requires **WSL 2** and **usbipd**:

1. **Install WSL 2:**
```powershell
wsl --install
```

2. **Install usbipd-win:**
   - Download from: https://github.com/dorssel/usbipd-win/releases

3. **Attach USB device to WSL:**
```powershell
# List devices
usbipd wsl list

# Attach FNIRSI device (replace <BUSID>)
usbipd wsl attach --busid <BUSID>
```

4. **Run Docker container:**
```bash
docker run -d \
  --device=/dev/bus/usb:/dev/bus/usb \
  --privileged \
  -p 5000:5000 \
  fnb58-monitor
```

---

## Bluetooth Support

### Linux

Bluetooth requires **host network mode**:

```bash
docker run -d \
  --name fnb58-monitor \
  --net=host \
  --privileged \
  -v $(pwd)/sessions:/app/sessions \
  -v $(pwd)/exports:/app/exports \
  -e BT_DEVICE_ADDRESS=98:DA:B0:08:A1:82 \
  fnb58-monitor
```

**docker-compose.yml:**
```yaml
services:
  fnb58-monitor:
    network_mode: host
    privileged: true
    environment:
      - BT_DEVICE_ADDRESS=98:DA:B0:08:A1:82
```

### macOS / Windows

Bluetooth in Docker is **NOT supported** on macOS/Windows due to Docker Desktop limitations.

**Workaround:** Run the Python app natively (not in Docker)

---

## Multi-Architecture Support

Build for multiple architectures (useful for Raspberry Pi):

```bash
# Enable buildx
docker buildx create --use

# Build for ARM64 (Raspberry Pi 4) and AMD64
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t yourusername/fnb58-monitor:latest \
  --push \
  .
```

### Raspberry Pi Deployment

```bash
# On Raspberry Pi (ARM64)
docker pull yourusername/fnb58-monitor:latest

docker run -d \
  --name fnb58-monitor \
  -p 5000:5000 \
  --device=/dev/bus/usb:/dev/bus/usb \
  --privileged \
  --restart unless-stopped \
  -v /home/pi/fnb58/sessions:/app/sessions \
  -v /home/pi/fnb58/exports:/app/exports \
  yourusername/fnb58-monitor:latest
```

---

## Troubleshooting

### "Permission denied" accessing USB device

**Linux:**
```bash
# Add your user to plugdev group
sudo usermod -a -G plugdev $USER

# Install udev rules
sudo cp docker/99-fnirsi.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger

# Reconnect the device
```

### "No FNIRSI device detected"

```bash
# Check if device is connected to host
lsusb | grep 0716

# Check if device is visible in container
docker exec -it fnb58-monitor lsusb

# Verify device permissions
docker exec -it fnb58-monitor ls -la /dev/bus/usb/001/
```

### Container fails to start

```bash
# Check logs
docker logs fnb58-monitor

# Check for port conflicts
sudo lsof -i :5000

# Remove and restart
docker rm -f fnb58-monitor
docker-compose up -d
```

### Bluetooth not working

```bash
# Check host Bluetooth
hciconfig

# Ensure container has host network
docker run --net=host --privileged ...

# Check Bluetooth in container
docker exec -it fnb58-monitor hciconfig
```

### Health check failing

```bash
# Check health status
docker inspect fnb58-monitor | grep -A 10 Health

# Manual health check
docker exec -it fnb58-monitor \
  python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:5000/api/status').read())"
```

---

## Data Persistence

### Sessions and Exports

Data is stored in Docker volumes:

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect fnb58_sessions

# Backup sessions
docker run --rm -v fnb58_sessions:/data -v $(pwd):/backup alpine \
  tar czf /backup/sessions-backup-$(date +%Y%m%d).tar.gz -C /data .

# Restore sessions
docker run --rm -v fnb58_sessions:/data -v $(pwd):/backup alpine \
  tar xzf /backup/sessions-backup-20250108.tar.gz -C /data
```

### Bind Mounts (Alternative)

Use host directories instead of volumes:

```yaml
volumes:
  - ./sessions:/app/sessions      # Sessions in current directory
  - ./exports:/app/exports        # Exports in current directory
```

---

## Production Deployment

### With Nginx Reverse Proxy

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  fnb58-monitor:
    build: .
    restart: unless-stopped
    expose:
      - "5000"
    devices:
      - /dev/bus/usb:/dev/bus/usb
    privileged: true
    volumes:
      - sessions:/app/sessions
      - exports:/app/exports

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - fnb58-monitor

volumes:
  sessions:
  exports:
```

**nginx.conf:**
```nginx
server {
    listen 80;
    server_name fnb58.yourdomain.com;

    location / {
        proxy_pass http://fnb58-monitor:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Auto-start on Boot

```bash
# Enable Docker to start on boot
sudo systemctl enable docker

# Set container restart policy
docker update --restart unless-stopped fnb58-monitor

# Or in docker-compose.yml:
services:
  fnb58-monitor:
    restart: unless-stopped
```

---

## Performance Tips

1. **Use bind mounts for development** (faster file access):
   ```yaml
   volumes:
     - ./:/app
   ```

2. **Use volumes for production** (better performance):
   ```yaml
   volumes:
     - sessions:/app/sessions
   ```

3. **Limit container resources**:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '0.5'
         memory: 512M
   ```

4. **Use multi-stage builds** (already implemented in Dockerfile)

---

## Security Best Practices

1. **Don't run as root** ✅ (Already configured in Dockerfile)

2. **Use read-only filesystem** (when possible):
   ```yaml
   read_only: true
   tmpfs:
     - /tmp
     - /app/sessions
     - /app/exports
   ```

3. **Drop unnecessary capabilities**:
   ```yaml
   cap_drop:
     - ALL
   cap_add:
     - CAP_NET_RAW  # For Bluetooth
   ```

4. **Use secrets for sensitive data**:
   ```yaml
   secrets:
     - secret_key
   environment:
     - SECRET_KEY_FILE=/run/secrets/secret_key
   ```

5. **Scan for vulnerabilities**:
   ```bash
   docker scan fnb58-monitor
   ```

---

## Updates

### Pull Latest Image

```bash
docker-compose pull
docker-compose up -d
```

### Rebuild After Changes

```bash
docker-compose build --no-cache
docker-compose up -d
```

---

## Monitoring

### View Logs

```bash
# Follow logs
docker-compose logs -f

# Last 100 lines
docker logs --tail 100 fnb58-monitor

# Since timestamp
docker logs --since 2025-01-08T10:00:00 fnb58-monitor
```

### Container Stats

```bash
# Real-time stats
docker stats fnb58-monitor

# Resource usage
docker inspect fnb58-monitor | grep -A 20 State
```

---

## Support

- **GitHub Issues**: Report bugs and request features
- **Documentation**: See README.md and CLAUDE.md
- **Community**: Share your Docker setups!

---

## License

MIT License - See LICENSE file for details
