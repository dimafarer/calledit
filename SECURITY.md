# Security Policy

## Overview

CalledIt is a serverless prediction verification platform built with security-first principles. This document outlines our security practices, vulnerability reporting process, and deployment security considerations.

## 🔒 Security Architecture

### Authentication & Authorization
- **AWS Cognito** for user authentication and session management
- **JWT tokens** for API authorization with automatic expiration
- **IAM roles** with least-privilege access principles
- **API Gateway authorizers** for endpoint protection

### Data Protection
- **Encryption at rest** via DynamoDB default encryption
- **Encryption in transit** via HTTPS/WSS for all communications
- **No sensitive data** stored in client-side code
- **Environment variable isolation** for configuration secrets

### Infrastructure Security
- **Serverless architecture** reduces attack surface
- **AWS Lambda** with isolated execution environments
- **VPC isolation** available for enhanced network security
- **CloudFormation** for infrastructure as code with security controls

## 🛡️ Security Best Practices Implemented

### Code Security
- ✅ **No hardcoded credentials** in source code
- ✅ **Environment variables** for all sensitive configuration
- ✅ **Input validation** on all API endpoints
- ✅ **CORS policies** properly configured
- ✅ **Content Security Policy** headers implemented

### Dependency Management
- ✅ **Regular dependency updates** via automated scanning
- ✅ **Vulnerability scanning** of npm and pip packages
- ✅ **Minimal dependency footprint** to reduce attack surface
- ✅ **Pinned versions** for reproducible builds

### Deployment Security
- ✅ **Separate environments** (dev/staging/prod) with isolated credentials
- ✅ **Infrastructure as Code** with version control
- ✅ **Automated security testing** in CI/CD pipeline
- ✅ **Zero-downtime deployments** with rollback capabilities

## 🔐 Secrets Management

### Environment Variables
All sensitive configuration is managed through environment variables:

```bash
# Frontend (.env - never committed)
VITE_COGNITO_USER_POOL_ID=your-pool-id
VITE_COGNITO_CLIENT_ID=your-client-id
VITE_API_URL=https://your-api.execute-api.region.amazonaws.com

# Backend (AWS Lambda environment variables)
COGNITO_USER_POOL_ID=${CognitoUserPool}
DYNAMODB_TABLE_NAME=${DynamoDBTable}
```

### AWS Credentials
- **IAM roles** used for Lambda execution (no access keys in code)
- **Temporary credentials** via AWS STS for cross-service access
- **Least privilege** permissions for all AWS resources
- **Regular credential rotation** following AWS best practices

## 🚨 Vulnerability Reporting

### Reporting Security Issues

If you discover a security vulnerability, please report it responsibly:

1. **DO NOT** create a public GitHub issue
2. **Email**: [Your security contact email]
3. **Include**: Detailed description, steps to reproduce, potential impact
4. **Response**: We will acknowledge within 48 hours and provide updates

### Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.5.x   | ✅ Yes             |
| 1.4.x   | ✅ Yes             |
| 1.3.x   | ⚠️ Security fixes only |
| < 1.3   | ❌ No              |

### Security Updates

- **Critical vulnerabilities**: Patched within 24-48 hours
- **High severity**: Patched within 1 week
- **Medium/Low severity**: Included in next regular release

## 🔍 Security Testing

### Automated Testing
- **SAST** (Static Application Security Testing) via GitHub CodeQL
- **Dependency scanning** via GitHub Dependabot
- **Container scanning** for Docker images (if applicable)
- **Infrastructure scanning** via AWS Config and Security Hub

### Manual Testing
- **Penetration testing** performed quarterly
- **Code reviews** with security focus for all changes
- **Security architecture reviews** for major features

## 📋 Security Checklist for Contributors

Before submitting code:

- [ ] No hardcoded secrets or credentials
- [ ] Input validation implemented for user data
- [ ] Error messages don't leak sensitive information
- [ ] Authentication/authorization properly implemented
- [ ] Dependencies are up-to-date and vulnerability-free
- [ ] Environment variables used for configuration
- [ ] HTTPS/WSS used for all communications

## 🛠️ Development Security

### Local Development
```bash
# Use example files for configuration
cp .env.example .env
cp testing/config.example.py testing/config.py

# Never commit actual credentials
git status --ignored  # Verify sensitive files are ignored
```

### Git Security
- **Sensitive files** protected via `.gitignore`
- **Pre-commit hooks** scan for secrets
- **Branch protection** rules enforce reviews
- **Signed commits** recommended for maintainers

## 🌐 Deployment Security

### Production Environment
- **AWS WAF** for application firewall protection
- **CloudTrail** for audit logging
- **GuardDuty** for threat detection
- **Config** for compliance monitoring

### Monitoring & Alerting
- **CloudWatch** for application monitoring
- **AWS Security Hub** for security findings
- **SNS notifications** for security alerts
- **Log aggregation** with retention policies

## 📚 Security Resources

### AWS Security Best Practices
- [AWS Well-Architected Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/)
- [AWS Security Best Practices](https://aws.amazon.com/architecture/security-identity-compliance/)
- [Serverless Security Best Practices](https://aws.amazon.com/lambda/security/)

### OWASP Guidelines
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP Serverless Top 10](https://owasp.org/www-project-serverless-top-10/)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)

## 🔄 Security Maintenance

### Regular Tasks
- **Monthly**: Dependency updates and vulnerability scans
- **Quarterly**: Security architecture review
- **Annually**: Penetration testing and security audit
- **As needed**: Incident response and security patches

### Compliance
- **SOC 2 Type II** compliance considerations
- **GDPR** data protection compliance
- **AWS Shared Responsibility Model** adherence
- **Industry security standards** alignment

## 📞 Contact Information

For security-related questions or concerns:
- **Security Team**: [Your security contact]
- **General Issues**: Create a GitHub issue (non-security only)
- **Documentation**: See [docs/](./docs/) directory

---

**Last Updated**: January 2025  
**Version**: 1.5.0  
**Review Cycle**: Quarterly
