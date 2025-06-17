"""
Test Ollama connection and models
"""
import asyncio
import requests
from litellm import completion, acompletion
import litellm

# Enable debug mode
# litellm.set_verbose = True

async def test_ollama_direct():
    """Test direct Ollama API"""
    print("Testing direct Ollama API...")
    
    # List models
    response = requests.get("http://localhost:11434/api/tags")
    models = response.json()
    print(f"Available models: {[m['name'] for m in models['models']]}")
    
    # Test generation
    data = {
        "model": "mistral",
        "prompt": "What is 2+2?",
        "stream": False
    }
    
    response = requests.post("http://localhost:11434/api/generate", json=data)
    if response.status_code == 200:
        print("✓ Direct Ollama API works!")
        print(f"Response: {response.json()['response'][:100]}...")
    else:
        print(f"✗ Error: {response.status_code} - {response.text}")

async def test_litellm_ollama():
    """Test LiteLLM with Ollama"""
    print("\nTesting LiteLLM with Ollama...")
    
    # Test different model name formats
    model_formats = [
        "ollama/mistral",
        "ollama/mistral:latest",
        "mistral"
    ]
    
    for model_name in model_formats:
        print(f"\nTrying model format: {model_name}")
        try:
            response = await acompletion(
                model=model_name,
                messages=[{"role": "user", "content": "What is 2+2?"}],
                api_base="http://localhost:11434",
                temperature=0.1,
                max_tokens=50
            )
            print(f"✓ Success with format: {model_name}")
            print(f"Response: {response.choices[0].message.content[:100]}")
            return model_name  # Return working format
            
        except Exception as e:
            print(f"✗ Failed with {model_name}: {str(e)}")
    
    return None

async def test_security_prompt():
    """Test with actual security prompt"""
    print("\nTesting security analysis prompt...")
    
    working_format = await test_litellm_ollama()
    if not working_format:
        print("No working format found!")
        return
    
    messages = [
        {
            "role": "system", 
            "content": "You are a security expert. Analyze code for vulnerabilities."
        },
        {
            "role": "user",
            "content": """Review this code:
            
            def get_user(user_id):
                query = f"SELECT * FROM users WHERE id = {user_id}"
                return execute_query(query)
            
            Identify security issues in JSON format."""
        }
    ]
    
    try:
        response = await acompletion(
            model=working_format,
            messages=messages,
            api_base="http://localhost:11434",
            temperature=0.1,
            max_tokens=500
        )
        print("✓ Security prompt works!")
        print(f"Response: {response.choices[0].message.content}")
        
    except Exception as e:
        print(f"✗ Security prompt failed: {str(e)}")

async def main():
    await test_ollama_direct()
    working_format = await test_litellm_ollama()
    if working_format:
        await test_security_prompt()

if __name__ == "__main__":
    asyncio.run(main())