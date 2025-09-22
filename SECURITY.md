# Security Policy

## 🔒 Security Overview

Synrax AI Agent takes security seriously. This document outlines our security practices, how to report security vulnerabilities, and guidelines for secure deployment.

## 🛡️ Supported Versions

We provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | ✅ Yes             |
| < 1.0   | ❌ No              |

## 🚨 Reporting Security Vulnerabilities

### How to Report

**Please DO NOT report security vulnerabilities through public GitHub issues.**

Instead, please report security vulnerabilities by emailing:

📧 **martin.sebastian@synrax.com**

### What to Include

When reporting a security vulnerability, please include:

1. **Description**: Clear description of the vulnerability
2. **Impact**: Potential impact and severity assessment
3. **Reproduction**: Step-by-step instructions to reproduce
4. **Environment**: Version, OS, configuration details
5. **Proof of Concept**: Minimal code example (if applicable)
6. **Suggested Fix**: If you have ideas for remediation

### Response Timeline

- **Initial Response**: Within 24 hours
- **Status Update**: Within 72 hours
- **Fix Development**: 1-14 days (depending on severity)
- **Public Disclosure**: After fix is released and users have time to update

## 🔐 Security Features

### Authentication & Authorization

- **JWT Tokens**: Secure, stateless authentication
- **Password Hashing**: bcrypt with salt
- **Session Management**: Secure HTTP-only cookies
- **Multi-User Support**: User isolation and access controls

### Input Validation & Sanitization

- **XSS Prevention**: Input sanitization and output encoding
- **SQL Injection Protection**: Parameterized queries with SQLAlchemy
- **File Upload Security**: Type validation and size limits
- **Request Validation**: Pydantic models for strict input validation

### Infrastructure Security

- **Rate Limiting**: Configurable request throttling
- **CORS Protection**: Restrictive cross-origin policies
- **Security Headers**: CSP, HSTS, X-Frame-Options
- **TLS/HTTPS**: Full SSL/TLS support
- **Environment Isolation**: Secure configuration management

### Data Protection

- **User Data Isolation**: Database-level separation
- **Secure Storage**: Encrypted sensitive data
- **Audit Logging**: Comprehensive security event tracking
- **Data Retention**: Configurable data cleanup policies

## ⚙️ Security Configuration

### Environment Variables

```env
# Required - Use a strong, unique secret key
SECRET_KEY=your-secure-random-32-byte-key

# Security settings
RATE_LIMIT_ENABLED=true
RATE_LIMIT=60
MAX_REQUEST_SIZE=1048576
SESSION_LIFETIME=3600

# CORS - Be restrictive in production
CORS_ORIGINS=https://yourdomain.com

# TLS/HTTPS
FORCE_HTTPS=true
SECURE_COOKIES=true
```

### Production Security Checklist

#### 🔑 **Authentication**
- [ ] Generate unique SECRET_KEY using `secrets.token_urlsafe(32)`
- [ ] Set strong admin password if using single-user mode
- [ ] Configure appropriate session timeout
- [ ] Enable rate limiting

#### 🌐 **Network Security**
- [ ] Configure CORS_ORIGINS with specific domains (not `*`)
- [ ] Use HTTPS in production (TLS 1.2+)
- [ ] Configure proper firewall rules
- [ ] Use reverse proxy (nginx/Apache) with security headers

#### 📊 **Database Security**
- [ ] Use PostgreSQL in production (not SQLite)
- [ ] Configure database connection encryption
- [ ] Set up database backups with encryption
- [ ] Limit database user permissions

#### 🐳 **Container Security**
- [ ] Run containers as non-root user
- [ ] Use specific image tags (not `latest`)
- [ ] Scan images for vulnerabilities
- [ ] Limit container resources

#### 📝 **Logging & Monitoring**
- [ ] Enable audit logging
- [ ] Configure log rotation
- [ ] Set up monitoring and alerting
- [ ] Review logs regularly for suspicious activity

## 🚀 Secure Deployment Guide

### Docker Security

```dockerfile
# Use specific version tags
FROM python:3.11-slim

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

# Set security headers
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
```

### Nginx Configuration

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    # SSL Configuration
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Security
        proxy_hide_header X-Powered-By;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
    }
}
```

### Database Security

```python
# Use connection pooling with SSL
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require

# Configure connection limits
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    connect_args={"sslmode": "require"}
)
```

## 🔍 Security Monitoring

### Key Metrics to Monitor

- Failed authentication attempts
- Rate limit violations
- Unusual request patterns
- File upload attempts
- Database connection errors
- Application errors and exceptions

### Alerting Rules

```yaml
# Example Prometheus alerting rules
groups:
  - name: security_alerts
    rules:
      - alert: HighFailedAuthRate
        expr: rate(auth_attempts_total{result="failed"}[5m]) > 0.1
        for: 1m
        annotations:
          summary: "High rate of failed authentication attempts"
          
      - alert: RateLimitExceeded
        expr: rate(rate_limit_exceeded_total[5m]) > 0.05
        for: 1m
        annotations:
          summary: "Rate limit frequently exceeded"
```

## 🧪 Security Testing

### Automated Security Testing

```bash
# Install security testing tools
pip install bandit safety

# Run security linting
bandit -r src/

# Check for known vulnerabilities
safety check

# Run tests with security focus
pytest tests/test_security.py -v
```

### Manual Security Testing

1. **Authentication Testing**
   - Test with invalid credentials
   - Test session timeout
   - Test token manipulation

2. **Input Validation Testing**
   - Test with malicious inputs
   - Test file upload edge cases
   - Test SQL injection attempts

3. **Authorization Testing**
   - Test access to unauthorized resources
   - Test privilege escalation attempts
   - Test cross-user data access

## 📋 Incident Response

### In Case of Security Incident

1. **Immediate Response**
   - Isolate affected systems
   - Preserve evidence
   - Assess scope of breach

2. **Investigation**
   - Review audit logs
   - Identify attack vector
   - Determine data impact

3. **Remediation**
   - Apply security patches
   - Update credentials
   - Notify affected users

4. **Post-Incident**
   - Document lessons learned
   - Update security measures
   - Improve monitoring

## 🔄 Security Updates

### Staying Updated

- Subscribe to security advisories
- Regularly update dependencies
- Monitor CVE databases
- Follow security best practices

### Updating Dependencies

```bash
# Check for security updates
pip list --outdated

# Update specific packages
pip install --upgrade package-name

# Audit dependencies
pip-audit
```

## 📞 Contact Information

For security-related questions or concerns:

📧 **Security Team**: martin.sebastian@synrax.com  
🌐 **Website**: [martinsebastian.dev](https://martinsebastian.dev)  
💼 **LinkedIn**: [linkedin.com/in/martinsebastian](https://linkedin.com/in/martinsebastian)

## 📚 Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [Python Security Best Practices](https://python.org/dev/security/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)

---

*This security policy is reviewed and updated regularly. Last updated: September 2025*

**Remember: Security is everyone's responsibility. When in doubt, ask questions and err on the side of caution.**