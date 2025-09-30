#!/usr/bin/env python3
"""
Test all available Saptiva models to verify they work and produce different outputs
Usage: python3 scripts/test-all-models.py [--api-url URL]
"""

import argparse
import sys
import requests
import time
from typing import Dict, List, Optional


class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    MAGENTA = '\033[0;35m'
    NC = '\033[0m'


def print_colored(color: str, message: str):
    print(f"{color}{message}{Colors.NC}")


def get_available_models(api_url: str) -> List[str]:
    """Get list of available models from API"""
    try:
        response = requests.get(f"{api_url}/api/models", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("allowed_models", [])
        return []
    except Exception as e:
        print_colored(Colors.RED, f"✗ Failed to get models: {str(e)}")
        return []


def authenticate(api_url: str, username: str, password: str) -> Optional[str]:
    """Authenticate and return token"""
    # Try registration
    try:
        response = requests.post(
            f"{api_url}/api/auth/register",
            json={
                "username": username,
                "email": f"{username}@example.com",
                "password": password,
                "name": f"{username.title()} User"
            },
            timeout=10
        )
        if response.status_code in [200, 201]:
            return response.json().get("access_token")
    except:
        pass

    # Try login
    try:
        response = requests.post(
            f"{api_url}/api/auth/login",
            json={"identifier": username, "password": password},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("access_token")
    except Exception as e:
        print_colored(Colors.RED, f"✗ Authentication failed: {str(e)}")

    return None


def test_model(api_url: str, token: str, model: str, prompt: str, test_num: int) -> Dict:
    """Test a specific model and return response details"""
    print_colored(Colors.CYAN, f"\n  📤 Test {test_num}: {prompt[:50]}...")

    try:
        start_time = time.time()
        response = requests.post(
            f"{api_url}/api/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "message": prompt,
                "model": model,
                "stream": False
            },
            timeout=60
        )
        elapsed = time.time() - start_time

        if response.status_code == 200:
            data = response.json()
            content = data.get("content", "")
            used_model = data.get("model", "N/A")

            print_colored(Colors.GREEN, f"     ✓ Response received ({elapsed:.2f}s)")
            print_colored(Colors.CYAN, f"     💬 \"{content[:100]}{'...' if len(content) > 100 else ''}\"")

            return {
                "success": True,
                "content": content,
                "model": used_model,
                "elapsed": elapsed,
                "length": len(content),
                "error": None
            }
        else:
            error = response.text[:200]
            print_colored(Colors.RED, f"     ✗ Failed: {response.status_code}")
            print_colored(Colors.RED, f"     {error}")
            return {
                "success": False,
                "content": None,
                "model": model,
                "elapsed": elapsed,
                "length": 0,
                "error": error
            }

    except Exception as e:
        print_colored(Colors.RED, f"     ✗ Exception: {str(e)[:100]}")
        return {
            "success": False,
            "content": None,
            "model": model,
            "elapsed": 0,
            "length": 0,
            "error": str(e)
        }


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate basic similarity between two texts (0-1)"""
    if not text1 or not text2:
        return 0.0

    # Simple word-based similarity
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())

    if not words1 or not words2:
        return 0.0

    intersection = words1.intersection(words2)
    union = words1.union(words2)

    return len(intersection) / len(union) if union else 0.0


def main():
    parser = argparse.ArgumentParser(
        description="Test all available Saptiva models"
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8001",
        help="API base URL"
    )
    parser.add_argument(
        "--username",
        default="modeltester",
        help="Username for authentication"
    )
    parser.add_argument(
        "--password",
        default="ModelTest123!",
        help="Password for authentication"
    )

    args = parser.parse_args()

    print_colored(Colors.BLUE, "\n" + "=" * 80)
    print_colored(Colors.BLUE, "  🧪 Saptiva Models Comparison Test")
    print_colored(Colors.BLUE, "=" * 80)

    # Get available models
    print_colored(Colors.YELLOW, "\n🎯 Fetching available models...")
    models = get_available_models(args.api_url)

    if not models:
        print_colored(Colors.RED, "✗ No models found")
        sys.exit(1)

    print_colored(Colors.GREEN, f"✓ Found {len(models)} models:")
    for model in models:
        print_colored(Colors.CYAN, f"   • {model}")

    # Authenticate
    print_colored(Colors.YELLOW, f"\n🔐 Authenticating as {args.username}...")
    token = authenticate(args.api_url, args.username, args.password)

    if not token:
        print_colored(Colors.RED, "✗ Authentication failed")
        sys.exit(1)

    print_colored(Colors.GREEN, "✓ Authenticated successfully")

    # Test prompts - designed to elicit different responses
    test_prompts = [
        "Explica en una oración qué eres y qué haces.",
        "Dame un consejo breve sobre programación.",
        "Describe el color azul en pocas palabras."
    ]

    # Test all models
    results = {}

    for model in models:
        print_colored(Colors.MAGENTA, f"\n{'=' * 80}")
        print_colored(Colors.MAGENTA, f"🤖 Testing model: {model}")
        print_colored(Colors.MAGENTA, "=" * 80)

        model_results = []

        for i, prompt in enumerate(test_prompts, 1):
            result = test_model(args.api_url, token, model, prompt, i)
            model_results.append(result)
            time.sleep(0.5)  # Small delay between requests

        results[model] = model_results

        # Summary for this model
        successes = sum(1 for r in model_results if r["success"])
        avg_length = sum(r["length"] for r in model_results) / len(model_results) if model_results else 0
        avg_time = sum(r["elapsed"] for r in model_results) / len(model_results) if model_results else 0

        print_colored(Colors.CYAN, f"\n  📊 Model Summary:")
        print_colored(Colors.CYAN, f"     Success rate: {successes}/{len(test_prompts)}")
        print_colored(Colors.CYAN, f"     Avg response length: {avg_length:.0f} chars")
        print_colored(Colors.CYAN, f"     Avg response time: {avg_time:.2f}s")

    # Analysis: Compare responses between models
    print_colored(Colors.BLUE, f"\n{'=' * 80}")
    print_colored(Colors.BLUE, "📊 Cross-Model Analysis")
    print_colored(Colors.BLUE, "=" * 80)

    working_models = [m for m in models if any(r["success"] for r in results[m])]

    if len(working_models) < 2:
        print_colored(Colors.YELLOW, "\n⚠️  Not enough working models to compare")
    else:
        print_colored(Colors.CYAN, f"\n🔍 Comparing responses from {len(working_models)} working models...\n")

        # Compare each prompt across models
        for prompt_idx, prompt in enumerate(test_prompts):
            print_colored(Colors.YELLOW, f"\n  Prompt {prompt_idx + 1}: \"{prompt[:60]}...\"")

            # Get responses from all models for this prompt
            prompt_responses = {}
            for model in working_models:
                if results[model][prompt_idx]["success"]:
                    prompt_responses[model] = results[model][prompt_idx]["content"]

            if len(prompt_responses) < 2:
                print_colored(Colors.YELLOW, "     ⚠️  Not enough responses to compare")
                continue

            # Calculate similarities between all pairs
            model_list = list(prompt_responses.keys())
            similarities = []

            for i in range(len(model_list)):
                for j in range(i + 1, len(model_list)):
                    model1 = model_list[i]
                    model2 = model_list[j]
                    similarity = calculate_similarity(
                        prompt_responses[model1],
                        prompt_responses[model2]
                    )
                    similarities.append((model1, model2, similarity))

                    color = Colors.GREEN if similarity < 0.5 else Colors.YELLOW if similarity < 0.8 else Colors.RED
                    print_colored(color, f"     {model1} ↔️  {model2}: {similarity:.1%} similar")

            # Average similarity
            if similarities:
                avg_similarity = sum(s[2] for s in similarities) / len(similarities)
                color = Colors.GREEN if avg_similarity < 0.5 else Colors.YELLOW if avg_similarity < 0.8 else Colors.RED
                print_colored(color, f"     📊 Average similarity: {avg_similarity:.1%}")

                if avg_similarity > 0.8:
                    print_colored(Colors.YELLOW, "     ⚠️  Models seem very similar for this prompt")
                elif avg_similarity < 0.3:
                    print_colored(Colors.GREEN, "     ✓ Models show good differentiation")

    # Final summary
    print_colored(Colors.BLUE, f"\n{'=' * 80}")
    print_colored(Colors.BLUE, "📋 Final Summary")
    print_colored(Colors.BLUE, "=" * 80 + "\n")

    total_tests = len(models) * len(test_prompts)
    total_successes = sum(
        sum(1 for r in model_results if r["success"])
        for model_results in results.values()
    )

    print_colored(Colors.CYAN, f"  Total tests run: {total_tests}")
    print_colored(Colors.CYAN, f"  Successful: {total_successes}")
    print_colored(Colors.CYAN, f"  Failed: {total_tests - total_successes}")
    print_colored(Colors.CYAN, f"  Success rate: {total_successes / total_tests * 100:.1f}%\n")

    # Model-by-model summary
    print_colored(Colors.CYAN, "  Model Performance:")
    for model in models:
        successes = sum(1 for r in results[model] if r["success"])
        status = "✅" if successes == len(test_prompts) else "⚠️" if successes > 0 else "❌"
        print_colored(Colors.CYAN, f"     {status} {model}: {successes}/{len(test_prompts)} tests passed")

    print_colored(Colors.BLUE, "\n" + "=" * 80)

    if total_successes == total_tests:
        print_colored(Colors.GREEN, "✅ ALL MODELS WORKING CORRECTLY!")
        print_colored(Colors.BLUE, "=" * 80 + "\n")
        sys.exit(0)
    elif total_successes > 0:
        print_colored(Colors.YELLOW, "⚠️  SOME MODELS FAILED")
        print_colored(Colors.BLUE, "=" * 80 + "\n")
        sys.exit(1)
    else:
        print_colored(Colors.RED, "❌ ALL MODELS FAILED")
        print_colored(Colors.BLUE, "=" * 80 + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()