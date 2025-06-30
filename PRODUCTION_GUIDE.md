# DHI Transaction Analytics - Production Deployment Guide

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- 4GB+ RAM recommended
- Plaid API credentials (sandbox or production)

### 1. Clone & Deploy
```bash
git clone <your-repo-url>
cd dhi.core
chmod +x deploy.sh
./deploy.sh
```

### 2. Access Your Dashboard
- **Dashboard:** http://localhost:8081
- **API:** http://localhost:8080
- **Neo4j Browser:** http://localhost:7474

## 🏦 Plaid Production Setup

### Moving from Sandbox to Production

1. **Get Production Credentials**
   ```bash
   # Set production environment variables
   export PLAID_CLIENT_ID="your_production_client_id"
   export PLAID_SECRET="your_production_secret"
   export PLAID_ENV="production"
   ```

2. **Update Configuration**
   ```bash
   # Update .env file
   echo "PLAID_ENV=production" >> .env
   echo "PLAID_CLIENT_ID=$PLAID_CLIENT_ID" >> .env
   echo "PLAID_SECRET=$PLAID_SECRET" >> .env
   ```

3. **Restart Services**
   ```bash
   docker-compose -f docker-compose.production.yml down
   docker-compose -f docker-compose.production.yml up -d
   ```

### Plaid Production Considerations

**Data Access:**
- Production environment provides access to real financial data
- Transactions from the last 24 months
- Real-time account balances
- Live transaction updates

**Rate Limits:**
- Standard: 10 requests/second
- Higher limits available with paid plans
- Monitor usage in Plaid Dashboard

**Compliance:**
- SOC 2 Type II certified
- Bank-level security
- GDPR/CCPA compliant
- Regular security audits

## 🤖 LLM Integration Setup

### Supported LLM Providers

1. **OpenAI (Recommended)**
   ```bash
   export OPENAI_API_KEY="sk-your-openai-key"
   ```

2. **Anthropic Claude**
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-your-key"
   ```

3. **Local Ollama** (Free, runs locally)
   ```bash
   # Install Ollama
   curl -fsSL https://ollama.ai/install.sh | sh
   ollama serve
   ollama pull llama2
   ```

4. **Groq (Fast inference)**
   ```bash
   export GROQ_API_KEY="gsk-your-groq-key"
   ```

### Testing LLM Queries

The system automatically tries providers in this order:
1. OpenAI (if API key available)
2. Anthropic (if API key available)
3. Ollama (if running locally)
4. Fallback mode (basic query templates)

**Example Queries:**
- "Show me my spending by category this month"
- "Find transactions over $500"
- "What are my largest expenses?"
- "Compare spending vs last month"

## 🗄️ Database Configuration

### Default Databases
- **SQLite:** Local file-based database (development)
- **PostgreSQL:** Production relational database
- **Neo4j:** Graph database for relationship analysis
- **Redis:** Caching and session storage

### Adding Custom Databases

Use the Database Management UI:
1. Navigate to "Databases" section
2. Click "Add Connection"
3. Configure connection details
4. Test connection
5. Save and activate

**Supported Types:**
- PostgreSQL
- MySQL
- SQLite
- Neo4j
- Redis
- MongoDB

## 📊 Analytics Features

### Dashboard Components
- **Real-time Analytics:** Live transaction monitoring
- **AI Insights:** Natural language query interface
- **Graph Analysis:** Relationship and pattern detection
- **Anomaly Detection:** Unusual transaction identification
- **Spending Patterns:** Category and trend analysis

### Mobile Support
- **Progressive Web App (PWA)**
- **Offline Functionality**
- **Camera Integration** (receipt capture)
- **Audio Recording** (voice notes)
- **Touch-optimized Interface**

## 🔐 Security & Compliance

### Data Security
- **Encryption at Rest:** All sensitive data encrypted
- **TLS/SSL:** Secure communication channels
- **API Authentication:** JWT tokens and API keys
- **Database Security:** Encrypted connections
- **File Upload Validation:** Secure file handling

### Privacy Controls
- **Data Retention:** Configurable retention policies
- **Access Logs:** Comprehensive audit trails
- **User Permissions:** Role-based access control
- **Data Export:** GDPR-compliant data export

## 🚀 Production Deployment Options

### 1. Docker Compose (Recommended)
```bash
# Standard deployment
docker-compose -f docker-compose.production.yml up -d

# With monitoring
docker-compose -f docker-compose.production.yml --profile monitoring up -d
```

### 2. Kubernetes
```bash
# Generate Kubernetes manifests
docker-compose -f docker-compose.production.yml config > k8s-manifests.yml
kubectl apply -f k8s-manifests.yml
```

### 3. Cloud Deployment
- **AWS:** Use ECS, RDS, and ElastiCache
- **Google Cloud:** Use Cloud Run, Cloud SQL, and Memorystore
- **Azure:** Use Container Instances, Azure Database, and Redis Cache

## 📈 Monitoring & Observability

### Built-in Monitoring
- **Health Checks:** Service availability monitoring
- **System Logs:** Centralized logging with real-time streaming
- **Performance Metrics:** Response times and throughput
- **Error Tracking:** Automatic error detection and alerting

### Optional Monitoring Stack
```bash
# Enable Prometheus + Grafana
docker-compose -f docker-compose.production.yml --profile monitoring up -d
```

**Access Points:**
- **Prometheus:** http://localhost:9090
- **Grafana:** http://localhost:3000 (admin/admin)

## 🔧 Configuration

### Environment Variables
```bash
# Core Application
NODE_ENV=production
PYTHONPATH=/app

# Plaid API
PLAID_CLIENT_ID=your_client_id
PLAID_SECRET=your_secret
PLAID_ENV=production

# Database
POSTGRES_HOST=postgres
POSTGRES_DB=dhi_analytics
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure_password

# Neo4j
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=secure_password

# LLM APIs
OPENAI_API_KEY=sk-your-key
ANTHROPIC_API_KEY=sk-ant-your-key

# Security
JWT_SECRET_KEY=your-jwt-secret
ENCRYPTION_KEY=your-encryption-key
```

### Volume Mounts
```yaml
volumes:
  - ./data:/app/data                    # Application data
  - ./logs:/app/logs                    # Log files
  - ./frontend/uploads:/app/frontend/uploads  # File uploads
  - ./ssl:/etc/nginx/ssl               # SSL certificates
```

## 🐛 Troubleshooting

### Common Issues

**1. Services won't start**
```bash
# Check logs
docker-compose -f docker-compose.production.yml logs

# Check service health
curl http://localhost:8081/api/health
```

**2. Database connection errors**
```bash
# Check database status
docker-compose -f docker-compose.production.yml ps
docker-compose -f docker-compose.production.yml logs postgres
```

**3. Plaid API errors**
```bash
# Verify credentials
curl -X POST http://localhost:8080/health
```

**4. LLM queries not working**
- Check API keys in environment variables
- Verify Ollama is running (for local LLM)
- Check service logs for detailed errors

### Performance Optimization

**1. Database Tuning**
```sql
-- PostgreSQL optimization
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
```

**2. Neo4j Memory Settings**
```bash
# Increase heap size
NEO4J_dbms_memory_heap_initial_size=1G
NEO4J_dbms_memory_heap_max_size=2G
```

**3. Application Scaling**
```bash
# Scale specific services
docker-compose -f docker-compose.production.yml up -d --scale dhi-app=3
```

## 📞 Support & Maintenance

### Regular Maintenance
```bash
# Update system
docker-compose -f docker-compose.production.yml pull
docker-compose -f docker-compose.production.yml up -d

# Backup databases
docker exec dhi-postgres pg_dump -U postgres dhi_analytics > backup.sql
docker exec dhi-neo4j neo4j-admin backup --to=/backups/neo4j

# Clean up unused resources
docker system prune -af
```

### Backup Strategy
1. **Database Backups:** Automated daily backups
2. **File Backups:** User uploads and media files
3. **Configuration Backups:** Environment and settings
4. **Off-site Storage:** Cloud backup integration

## 🎯 Next Steps

1. **Complete Plaid Integration:** Set up production credentials
2. **Configure LLM Provider:** Choose and set up your preferred AI service
3. **Customize Analytics:** Add custom queries and visualizations
4. **Set up Monitoring:** Enable comprehensive system monitoring
5. **Security Review:** Implement additional security measures
6. **Scale Infrastructure:** Optimize for your expected load

---

**Need Help?** 
- Check the troubleshooting section
- Review application logs
- Test with sandbox data first
- Verify all environment variables
