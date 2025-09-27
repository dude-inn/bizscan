# BizScan Bot - Deployment Guide

## Overview

BizScan Bot now supports PostgreSQL database and includes a queuing system for managing API requests to Gamma and OFData services.

## Features Added

### 1. PPTX Generation
- Added PPTX generation support in `gamma_exporter.py`
- Users can choose between PDF and PPTX formats
- Handler already supports format selection

### 2. PostgreSQL Migration
- New `DatabaseService` with SQLAlchemy ORM
- Supports both SQLite (legacy) and PostgreSQL
- Automatic table creation and migrations
- Backward compatibility with existing SQLite setup

### 3. Queue System
- Rate limiting for Gamma API (5 requests/minute, 50/day)
- Rate limiting for OFData API (30 requests/minute, 1000/hour)
- Background workers for processing tasks
- Automatic cleanup of old tasks
- Configurable worker counts and limits

## Configuration

### Environment Variables

```bash
# Database
DATABASE_TYPE=postgresql
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=bizscan
POSTGRES_USER=bizscan
POSTGRES_PASSWORD=your_password

# Queue Settings
GAMMA_QUEUE_MAX_WORKERS=2
GAMMA_DAILY_LIMIT=50
GAMMA_RATE_LIMIT_PER_MINUTE=5
OFDATA_QUEUE_MAX_WORKERS=5
OFDATA_RATE_LIMIT_PER_MINUTE=30
OFDATA_RATE_LIMIT_PER_HOUR=1000

# Bot Settings
BOT_TOKEN=your_bot_token
OFDATA_KEY=your_ofdata_key
GAMMA_API_KEY=your_gamma_key
```

## Deployment Options

### 1. Docker Compose (Recommended)

```bash
# Clone repository
git clone <repository_url>
cd bizscan

# Copy environment file
cp .env.example .env
# Edit .env with your values

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f bot
```

### 2. Manual Deployment

#### Prerequisites
- Python 3.11+
- PostgreSQL 13+
- Redis (optional, for caching)

#### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set up PostgreSQL
createdb bizscan
psql bizscan -c "CREATE USER bizscan WITH PASSWORD 'your_password';"
psql bizscan -c "GRANT ALL PRIVILEGES ON DATABASE bizscan TO bizscan;"

# Configure environment
export DATABASE_TYPE=postgresql
export POSTGRES_HOST=localhost
export POSTGRES_DB=bizscan
export POSTGRES_USER=bizscan
export POSTGRES_PASSWORD=your_password

# Run application
python app.py
```

### 3. Cloud Deployment

#### Heroku
```bash
# Add PostgreSQL addon
heroku addons:create heroku-postgresql:mini

# Set environment variables
heroku config:set DATABASE_TYPE=postgresql
heroku config:set BOT_TOKEN=your_token
heroku config:set OFDATA_KEY=your_key
heroku config:set GAMMA_API_KEY=your_key

# Deploy
git push heroku main
```

#### Railway
```yaml
# railway.toml
[build]
builder = "dockerfile"

[deploy]
startCommand = "python app.py"
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "on_failure"
```

#### DigitalOcean App Platform
```yaml
# .do/app.yaml
name: bizscan-bot
services:
- name: bot
  source_dir: /
  github:
    repo: your-username/bizscan
    branch: main
  run_command: python app.py
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  envs:
  - key: DATABASE_TYPE
    value: postgresql
  - key: BOT_TOKEN
    value: ${BOT_TOKEN}
databases:
- name: postgres
  engine: PG
  version: "15"
```

## Monitoring

### Health Checks
- Application: `GET /health`
- Database: Automatic connection checks
- Queue: Worker status monitoring

### Logs
- Structured JSON logging
- Log levels: DEBUG, INFO, WARNING, ERROR
- Automatic log rotation

### Metrics
- Queue processing rates
- API request counts
- Error rates
- Daily quotas usage

## Performance Tuning

### Queue Workers
```bash
# For high load
GAMMA_QUEUE_MAX_WORKERS=5
OFDATA_QUEUE_MAX_WORKERS=10

# For low load
GAMMA_QUEUE_MAX_WORKERS=1
OFDATA_QUEUE_MAX_WORKERS=3
```

### Rate Limits
```bash
# Conservative (default)
GAMMA_RATE_LIMIT_PER_MINUTE=5
OFDATA_RATE_LIMIT_PER_MINUTE=30

# Aggressive (if you have higher quotas)
GAMMA_RATE_LIMIT_PER_MINUTE=10
OFDATA_RATE_LIMIT_PER_MINUTE=60
```

### Database
```bash
# PostgreSQL tuning
POSTGRES_SHARED_BUFFERS=256MB
POSTGRES_EFFECTIVE_CACHE_SIZE=1GB
POSTGRES_MAINTENANCE_WORK_MEM=64MB
```

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check PostgreSQL is running
   - Verify connection parameters
   - Check firewall settings

2. **Queue Workers Not Starting**
   - Check worker limits in settings
   - Verify API keys are configured
   - Check logs for errors

3. **Rate Limit Errors**
   - Reduce `RATE_LIMIT_PER_MINUTE` values
   - Increase `QUEUE_PROCESS_INTERVAL`
   - Check API quotas

### Logs
```bash
# Docker
docker-compose logs -f bot

# Manual
tail -f logs/bot.log
```

### Database
```bash
# Check connections
psql bizscan -c "SELECT * FROM pg_stat_activity;"

# Check queue status
psql bizscan -c "SELECT task_type, status, COUNT(*) FROM bot_stats GROUP BY task_type, status;"
```

## Migration from SQLite

The system automatically handles migration from SQLite to PostgreSQL:

1. Set `DATABASE_TYPE=postgresql`
2. Configure PostgreSQL connection
3. Restart application
4. Data will be migrated automatically

## Security

- Use strong PostgreSQL passwords
- Enable SSL for database connections
- Set up firewall rules
- Use environment variables for secrets
- Regular security updates

## Backup

```bash
# Database backup
pg_dump bizscan > backup_$(date +%Y%m%d).sql

# Restore
psql bizscan < backup_20240101.sql
```

## Scaling

### Horizontal Scaling
- Multiple bot instances behind load balancer
- Shared PostgreSQL database
- Redis for session storage

### Vertical Scaling
- Increase worker counts
- Larger database instance
- More memory for caching

## Support

For issues and questions:
- Check logs first
- Review configuration
- Test with minimal setup
- Contact support team


