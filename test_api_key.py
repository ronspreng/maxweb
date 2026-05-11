#!/usr/bin/env python3
"""Test if the API key is valid."""
import os
from dotenv import load_dotenv
import anthropic

load_dotenv()

api_key = os.environ.get("ANTHROPIC_API_KEY")

if not api_key:
    print("[ERROR] ANTHROPIC_API_KEY not found in .env")
    exit(1)

print(f"[INFO] Key starts with: {api_key[:20]}...")
print(f"[INFO] Key length: {len(api_key)}")

try:
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=100,
        messages=[
            {"role": "user", "content": "Say 'API key is valid' in one word"}
        ]
    )
    print(f"[OK] API key is VALID!")
    print(f"[OK] Response: {message.content[0].text}")
except Exception as e:
    print(f"[ERROR] API key test failed:")
    print(f"[ERROR] {type(e).__name__}: {str(e)}")
    exit(1)
