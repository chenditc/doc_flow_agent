# Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability in Doc Flow Agent, please report it responsibly:

1. **DO NOT** open a public issue for security vulnerabilities
2. Email the maintainer directly at [chenditc@gmail.com] with details
3. Include steps to reproduce and potential impact
4. We will respond within 48 hours to acknowledge the report

## Security Considerations

### API Key Management
- Never commit API keys or secrets to the repository
- Use environment variables for all credentials
- Use `.env` files locally (excluded from git)
- Rotate API keys regularly

### Code Execution Security
- The JsonPathGenerator executes dynamically generated Python code
- This poses potential security risks in production environments
- Consider implementing sandboxing or AST validation
- Review generated code before execution in production

### Data Privacy
- Context files may contain sensitive information
- Consider implementing encryption for context.json
- Be aware of data retention in trace files
- Sanitize sensitive data in logs and traces

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | ✅ |

## Security Updates

Security updates will be released as patch versions. Please keep your installation up to date.
