# Changelog - BizScan Bot

## [2.0.0] - 2024-01-XX

### Added
- **PPTX Generation**: Added PowerPoint presentation generation support in Gamma exporter
- **PostgreSQL Support**: Full migration from SQLite to PostgreSQL with SQLAlchemy ORM
- **Queue System**: Advanced queuing system for Gamma and OFData API requests with rate limiting
- **Docker Support**: Complete Docker and docker-compose setup for cloud deployment
- **Rate Limiting**: Configurable rate limits for external API calls
- **Daily Quotas**: Automatic daily quota management for Gamma API (50 reports/day)
- **Background Workers**: Asynchronous task processing with configurable worker counts
- **Health Checks**: Application health monitoring endpoints
- **Structured Logging**: Enhanced logging with JSON format and better error tracking

### Changed
- **Database Layer**: Migrated from aiosqlite to SQLAlchemy with async support
- **API Management**: Centralized API request management through queue system
- **Configuration**: Enhanced settings with queue and database configuration
- **Error Handling**: Improved error handling and retry mechanisms
- **Performance**: Optimized for concurrent users and high load

### Technical Details

#### Database Migration
- New `DatabaseService` with SQLAlchemy ORM
- Support for both SQLite (legacy) and PostgreSQL
- Automatic table creation and schema management
- Backward compatibility maintained

#### Queue System
- **Gamma API**: 2 workers, 5 requests/minute, 50/day limit
- **OFData API**: 5 workers, 30 requests/minute, 1000/hour limit
- Automatic task cleanup and retry logic
- Real-time queue monitoring

#### Deployment
- Docker containerization with multi-stage builds
- Docker Compose for local development
- Cloud deployment guides (Heroku, Railway, DigitalOcean)
- Environment-based configuration

### Configuration

#### New Environment Variables
```bash
# Database
DATABASE_TYPE=postgresql
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=bizscan
POSTGRES_USER=bizscan
POSTGRES_PASSWORD=password

# Queue System
GAMMA_QUEUE_MAX_WORKERS=2
GAMMA_DAILY_LIMIT=50
GAMMA_RATE_LIMIT_PER_MINUTE=5
OFDATA_QUEUE_MAX_WORKERS=5
OFDATA_RATE_LIMIT_PER_MINUTE=30
OFDATA_RATE_LIMIT_PER_HOUR=1000
```

#### New Dependencies
- `sqlalchemy>=2.0.0` - Database ORM
- `asyncpg>=0.29.0` - PostgreSQL async driver

### Files Added
- `services/database.py` - Database service with SQLAlchemy
- `services/queue.py` - Queue management system
- `Dockerfile` - Container configuration
- `docker-compose.yml` - Local development setup
- `DEPLOYMENT.md` - Comprehensive deployment guide
- `.env.example` - Environment variables template

### Files Modified
- `settings.py` - Added database and queue configuration
- `services/stats.py` - Updated to use new DatabaseService
- `app.py` - Added database and queue initialization
- `requirements.txt` - Added PostgreSQL dependencies
- `services/export/gamma_exporter.py` - Added PPTX generation

### Breaking Changes
- **Database**: Requires PostgreSQL for production (SQLite still supported for development)
- **Configuration**: New environment variables required
- **Dependencies**: Additional packages required (SQLAlchemy, asyncpg)

### Migration Guide
1. Install new dependencies: `pip install -r requirements.txt`
2. Set up PostgreSQL database
3. Configure environment variables
4. Restart application
5. Database schema will be created automatically

### Performance Improvements
- **Concurrent Processing**: Multiple workers for API requests
- **Rate Limiting**: Prevents API quota exhaustion
- **Connection Pooling**: Efficient database connections
- **Background Tasks**: Non-blocking API calls
- **Caching**: Improved data caching strategies

### Monitoring
- Health check endpoints
- Queue status monitoring
- Database connection monitoring
- Structured logging with metrics

### Security
- Secure database connections
- Environment-based secrets
- Rate limiting protection
- Input validation and sanitization

### Deployment Options
- **Local**: Docker Compose
- **Cloud**: Heroku, Railway, DigitalOcean
- **VPS**: Manual installation with systemd
- **Kubernetes**: Ready for container orchestration

### Future Roadmap
- Redis caching layer
- Horizontal scaling support
- Advanced monitoring dashboard
- API rate limit analytics
- Automated backup system


