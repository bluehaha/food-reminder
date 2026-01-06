# Deployment Guide

This guide explains how to deploy the Food Reminder application using Docker and GitHub Actions.

## Prerequisites

- Docker and Docker Compose installed locally
- GitHub repository with Actions enabled
- A VM with Docker installed for deployment
- SSH access to the VM

## Local Testing

### Build and Run with Docker

```bash
# Build the Docker image
docker build -t food-reminder:latest .

# Create config file if not exists
cp conf/config.example.yaml conf/config.yaml
# Edit conf/config.yaml with your settings

# Run the container
docker run --rm \
  -v $(pwd)/conf/config.yaml:/app/conf/config.yaml:ro \
  -v $(pwd)/state:/app/state \
  food-reminder:latest
```

### Using Docker Compose

```bash
# Ensure config file exists
cp conf/config.example.yaml conf/config.yaml
# Edit conf/config.yaml with your settings

# Start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

## VM Setup

### 1. Prepare the VM

SSH into your VM and set up the deployment directory:

```bash
# Create deployment directory
sudo mkdir -p /opt/food-reminder
sudo chown $USER:$USER /opt/food-reminder
cd /opt/food-reminder

# Create necessary subdirectories
mkdir -p conf state

# Create config file
cat > conf/config.yaml << 'EOF'
# Add your configuration here
products:
  - url: "https://www.wagashi.com.tw/product/example/"
    name: "Product Name"

slack:
  webhook_url: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
  username: "Food Availability Bot"
  icon_emoji: ":bento:"

state:
  file_path: "state/notifications.json"

timeout: 30
user_agent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
max_retries: 3
retry_delay: 2
EOF

# Edit the config with your actual values
nano conf/config.yaml
```

### 2. Set Up Cron for Periodic Checks

The container runs once and exits. Use cron to schedule periodic checks:

```bash
# Edit crontab
crontab -e

# Add this line to check every 30 minutes
*/30 * * * * cd /opt/food-reminder && docker run --rm -v $(pwd)/conf/config.yaml:/app/conf/config.yaml:ro -v $(pwd)/state:/app/state ghcr.io/YOUR_USERNAME/food-reminder:latest

# Or check every hour at minute 0
0 * * * * cd /opt/food-reminder && docker run --rm -v $(pwd)/conf/config.yaml:/app/conf/config.yaml:ro -v $(pwd)/state:/app/state ghcr.io/YOUR_USERNAME/food-reminder:latest
```

## GitHub Actions Setup

### Required Secrets

Configure these secrets in your GitHub repository (Settings → Secrets and variables → Actions):

| Secret | Description | Example |
|--------|-------------|---------|
| `VM_HOST` | VM hostname or IP address | `192.168.1.100` or `vm.example.com` |
| `VM_USERNAME` | SSH username | `ubuntu` or `deploy` |
| `VM_SSH_KEY` | Private SSH key for authentication | Contents of `~/.ssh/id_rsa` |
| `VM_SSH_PORT` | SSH port (optional, defaults to 22) | `22` |
| `VM_DEPLOY_PATH` | Deployment directory on VM (optional) | `/opt/food-reminder` |

### Generate SSH Key Pair

If you don't have an SSH key for deployment:

```bash
# On your local machine
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_actions

# Copy public key to VM
ssh-copy-id -i ~/.ssh/github_actions.pub user@your-vm-host

# Copy private key contents to GitHub secret
cat ~/.ssh/github_actions
# Copy the entire output to VM_SSH_KEY secret
```

### Workflow Triggers

The deployment workflow triggers on:
- Push to `main` or `master` branch
- Manual trigger via GitHub Actions UI (workflow_dispatch)

### Deployment Process

1. **Build**: Builds Docker image and pushes to GitHub Container Registry (ghcr.io)
2. **Deploy**: SSHs into VM and deploys the new image

## Image Registry

Images are published to GitHub Container Registry:
- Registry: `ghcr.io`
- Image: `ghcr.io/YOUR_USERNAME/food-reminder:latest`

### Manual Image Pull

```bash
# Login to GitHub Container Registry
echo YOUR_GITHUB_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin

# Pull the image
docker pull ghcr.io/YOUR_USERNAME/food-reminder:latest

# Run the image
docker run --rm \
  -v /opt/food-reminder/conf/config.yaml:/app/conf/config.yaml:ro \
  -v /opt/food-reminder/state:/app/state \
  ghcr.io/YOUR_USERNAME/food-reminder:latest
```

## Monitoring and Maintenance

### View Container Logs

```bash
# If using docker-compose
docker-compose logs -f

# If running manually
docker logs food-reminder

# View cron logs
grep CRON /var/log/syslog
```

### Check State File

```bash
# View notification state
cat state/notifications.json
```

### Clear Notification State

```bash
# Clear state for a specific product
docker run --rm \
  -v $(pwd)/conf/config.yaml:/app/conf/config.yaml:ro \
  -v $(pwd)/state:/app/state \
  ghcr.io/YOUR_USERNAME/food-reminder:latest \
  python scripts/check_availability.py --clear-state "PRODUCT_URL"
```

### Update Configuration

```bash
# Edit config on VM
cd /opt/food-reminder
nano conf/config.yaml

# Next scheduled run will use new config
```

## Troubleshooting

### Container Fails to Start

```bash
# Check logs
docker logs food-reminder

# Run interactively for debugging
docker run -it --rm \
  -v $(pwd)/conf/config.yaml:/app/conf/config.yaml:ro \
  -v $(pwd)/state:/app/state \
  --entrypoint /bin/bash \
  ghcr.io/YOUR_USERNAME/food-reminder:latest
```

### GitHub Actions Fails

1. Check Actions tab in GitHub for error messages
2. Verify all secrets are correctly configured
3. Test SSH connection manually:
   ```bash
   ssh -i ~/.ssh/github_actions user@vm-host
   ```

### Slack Notifications Not Received

1. Verify webhook URL in config.yaml
2. Check Slack app permissions
3. Run manually with verbose logging:
   ```bash
   docker run --rm \
     -v $(pwd)/conf/config.yaml:/app/conf/config.yaml:ro \
     -v $(pwd)/state:/app/state \
     ghcr.io/YOUR_USERNAME/food-reminder:latest \
     python scripts/check_availability.py -v
   ```

## Security Considerations

- Keep SSH private keys secure and never commit them
- Use read-only volume mount for config file (`:ro` flag)
- Regularly update the base image for security patches
- Use strong passwords/keys for SSH access
- Consider using SSH key with passphrase for additional security
- Rotate secrets periodically

## Advanced Configuration

### Custom Cron Schedule

```bash
# Every 15 minutes
*/15 * * * * cd /opt/food-reminder && docker run --rm -v $(pwd)/conf/config.yaml:/app/conf/config.yaml:ro -v $(pwd)/state:/app/state ghcr.io/YOUR_USERNAME/food-reminder:latest

# Twice daily at 9 AM and 6 PM
0 9,18 * * * cd /opt/food-reminder && docker run --rm -v $(pwd)/conf/config.yaml:/app/conf/config.yaml:ro -v $(pwd)/state:/app/state ghcr.io/YOUR_USERNAME/food-reminder:latest

# Weekdays only at 10 AM
0 10 * * 1-5 cd /opt/food-reminder && docker run --rm -v $(pwd)/conf/config.yaml:/app/conf/config.yaml:ro -v $(pwd)/state:/app/state ghcr.io/YOUR_USERNAME/food-reminder:latest
```

### Using Environment Variables

For sensitive configuration, use environment variables:

```bash
docker run --rm \
  -e SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL" \
  -v $(pwd)/state:/app/state \
  ghcr.io/YOUR_USERNAME/food-reminder:latest
```

Then modify the application to read from environment variables if preferred.
