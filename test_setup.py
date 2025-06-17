import os
from dotenv import load_dotenv
import requests

load_dotenv()

# Test Ollama
print("Testing Ollama connection...")
try:
    response = requests.get("http://localhost:11434/api/tags")
    if response.status_code == 200:
        models = response.json()
        print("✅ Ollama is running!")
        print("Available models:", [m['name'] for m in models['models']])
    else:
        print("❌ Ollama is not responding")
except Exception as e:
    print(f"❌ Error connecting to Ollama: {e}")

# Test GitHub token
print("\nTesting GitHub token...")
token = os.getenv("GITHUB_TOKEN")
if token:
    headers = {"Authorization": f"token {token}"}
    response = requests.get("https://api.github.com/user", headers=headers)
    if response.status_code == 200:
        user = response.json()
        print(f"✅ GitHub token valid! Logged in as: {user['login']}")
    else:
        print("❌ GitHub token invalid")
else:
    print("❌ No GitHub token found in .env")