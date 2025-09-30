#!/usr/bin/env python3
"""
Secure secrets generator for Copilotos Bridge.

Generates cryptographically secure passwords and keys for production deployment.
"""

import secrets
import string
import hashlib
import base64
from pathlib import Path

def generate_password(length: int = 32) -> str:
    """Generate a cryptographically secure password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_secret_key(length: int = 32) -> str:
    """Generate a cryptographically secure secret key (hex)."""
    return secrets.token_hex(length)

def generate_base64_key(length: int = 32) -> str:
    """Generate a base64 encoded secret key."""
    return base64.urlsafe_b64encode(secrets.token_bytes(length)).decode('utf-8')

def main():
    print("🔐 Copilotos Bridge - Secure Secrets Generator")
    print("=" * 60)
    print()

    print("⚠️  SECURITY WARNING:")
    print("   - Store these secrets securely")
    print("   - Never commit to version control")
    print("   - Use different secrets per environment")
    print("   - Rotate regularly")
    print()

    secrets_config = {
        "# MongoDB Credentials": None,
        "MONGODB_PASSWORD": generate_password(24),
        "REDIS_PASSWORD": generate_password(24),

        "# JWT & Session Secrets": None,
        "JWT_SECRET_KEY": generate_secret_key(32),
        "SECRET_KEY": generate_secret_key(32),

        "# Database Root Passwords": None,
        "MONGO_ROOT_PASSWORD": generate_password(32),
        "GRAFANA_ADMIN_PASSWORD": generate_password(16),

        "# Encryption Keys": None,
        "ENCRYPTION_KEY": generate_base64_key(32),
    }

    print("🔑 Generated Secrets:")
    print("-" * 60)

    for key, value in secrets_config.items():
        if value is None:
            print(f"\n{key}")
            continue
        print(f"{key}={value}")

    print()
    print("-" * 60)
    print("📋 Next Steps:")
    print()
    print("1. Copy these values to your secure secrets store")
    print("2. Set them as environment variables in production")
    print("3. For local development, add to envs/.env.local")
    print("4. NEVER commit these values to git")
    print()
    print("🛡️  Docker Secrets Example:")
    print("   echo 'your-secret' | docker secret create mongodb_password -")
    print()
    print("☁️  AWS Secrets Manager Example:")
    print("   aws secretsmanager create-secret --name 'copilotos/mongodb-password' --secret-string 'your-secret'")
    print()
    print("🔒 Kubernetes Secrets Example:")
    print("   kubectl create secret generic copilotos-secrets \\")
    for key, value in secrets_config.items():
        if value is not None:
            print(f"     --from-literal={key.lower()}='{value}' \\")
    print()

if __name__ == "__main__":
    main()