#!/usr/bin/env python3
"""
Reproduce Golden Case for OctaviOS Chat
Usage: python3 scripts/reproduce_golden_case.py [--api-url URL]
"""

import argparse
import sys
import requests
import json
from typing import Optional

class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'

def print_colored(color: str, message: str):
    print(f"{color}{message}{Colors.NC}")

def get_token(api_url: str) -> str:
    # Try demo user
    creds = {"identifier": "demo", "password": "Demo1234"}
    try:
        resp = requests.post(f"{api_url}/api/auth/login", json=creds, timeout=5)
        if resp.status_code == 200:
            return resp.json()["access_token"]
    except Exception:
        pass
    
    # Fallback to test user registration
    reg_data = {
        "username": "tester_golden",
        "email": "tester@example.com",
        "password": "TestPass123!",
        "name": "Tester Golden"
    }
    try:
        requests.post(f"{api_url}/api/auth/register", json=reg_data, timeout=5)
        resp = requests.post(f"{api_url}/api/auth/login", json={"identifier": "tester_golden", "password": "TestPass123!"}, timeout=5)
        if resp.status_code == 200:
            return resp.json()["access_token"]
    except Exception as e:
        print_colored(Colors.RED, f"Auth failed: {e}")
        sys.exit(1)
    
    print_colored(Colors.RED, "Could not authenticate.")
    sys.exit(1)

def run_chat(api_url: str, token: str, message: str, chat_id: Optional[str] = None):
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "message": message,
        "model": "Saptiva Turbo",
        "stream": False,
        "chat_id": chat_id
    }
    
    print_colored(Colors.YELLOW, f"\n📤 Sending: {message}")
    if chat_id:
        print_colored(Colors.CYAN, f"   Chat ID: {chat_id}")

    try:
        resp = requests.post(f"{api_url}/api/chat", headers=headers, json=payload, timeout=120)
        if resp.status_code == 200:
            data = resp.json()
            print_colored(Colors.GREEN, f"✅ Response: {data.get('content', '')[:200]}...")
            return data
        else:
            print_colored(Colors.RED, f"❌ Error {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        print_colored(Colors.RED, f"❌ Exception: {e}")
        return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="http://localhost:8000")
    args = parser.parse_args()
    
    print_colored(Colors.BLUE, "=== Reproducing Golden Case ===")
    
    token = get_token(args.api_url)
    print_colored(Colors.GREEN, "Auth OK.")

    # 1. First Question
    q1 = "Cómo se comportó la cartera empresarial de investigación en Q2 2025 vs el mercado?"
    resp1 = run_chat(args.api_url, token, q1)
    
    if not resp1:
        sys.exit(1)
        
    chat_id = resp1.get("chat_id")
    
    # 2. Follow-up
    q2 = "revisa Q2"
    run_chat(args.api_url, token, q2, chat_id=chat_id)

if __name__ == "__main__":
    main()
