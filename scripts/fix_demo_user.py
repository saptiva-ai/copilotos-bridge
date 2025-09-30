#!/usr/bin/env python3
"""Fix demo user password"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from passlib.context import CryptContext
import sys
import os

# Add src to path
sys.path.insert(0, '/app')

from src.models.user import User, UserPreferences
from src.core.config import get_settings

async def recreate_user():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.mongodb_url)
    db_name = settings.mongodb_url.split('/')[-1].split('?')[0]
    database = client[db_name]
    await init_beanie(database=database, document_models=[User])

    # Delete existing user
    user = await User.find_one(User.username == 'demo')
    if user:
        await user.delete()
        print('✓ Deleted existing demo user')

    # Create new user with correct password
    pwd_context = CryptContext(
        schemes=['argon2', 'bcrypt', 'pbkdf2_sha256'],
        default='argon2',
        deprecated=['bcrypt', 'pbkdf2_sha256'],
    )

    # Important: No shell escaping here
    correct_password = 'Demo123!'
    password_hash = pwd_context.hash(correct_password)

    user = User(
        username='demo',
        email='demo@example.com',
        password_hash=password_hash,
        preferences=UserPreferences(),
    )

    await user.create()
    print(f'✓ Demo user created successfully')
    print(f'  Username: {user.username}')
    print(f'  Email: {user.email}')
    print(f'  ID: {user.id}')

    # Verify password works
    is_valid = pwd_context.verify(correct_password, user.password_hash)
    print(f'  Password verification: {"✓ Valid" if is_valid else "✗ Invalid"}')
    print(f'  Password bytes: {correct_password.encode("utf-8").hex()}')

if __name__ == '__main__':
    asyncio.run(recreate_user())