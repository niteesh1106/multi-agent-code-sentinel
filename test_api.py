"""
Test script for the Code Review API
"""
import requests
import json
import time
from datetime import datetime

# API base URL
BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("1. Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Health check passed!")
        print(f"  - Status: {data['status']}")
        print(f"  - Agents: {', '.join(data['agents'])}")
        print(f"  - Version: {data['version']}")
    else:
        print(f"✗ Health check failed: {response.status_code}")
    print()

def test_manual_review():
    """Test manual review endpoint"""
    print("2. Testing manual review...")
    
    # You can change this to a real PR in your repo
    # For testing, we'll use a popular open source repo
    review_request = {
        "repo": "microsoft/vscode",  # Popular repo with many PRs
        "pr_number": 150000,  # A real PR number
        "post_comment": False,  # Don't post to real PR
        "include_details": True
    }
    
    print(f"   Requesting review for {review_request['repo']} PR #{review_request['pr_number']}")
    
    # Submit review request
    response = requests.post(
        f"{BASE_URL}/api/review",
        json=review_request
    )
    
    if response.status_code == 200:
        data = response.json()
        review_id = data['review_id']
        print(f"✓ Review started!")
        print(f"  - Review ID: {review_id}")
        print(f"  - Status: {data['status']}")
        print()
        
        # Poll for results
        print("3. Checking review status...")
        for i in range(30):  # Check for up to 5 minutes
            response = requests.get(f"{BASE_URL}/api/review/{review_id}")
            if response.status_code == 200:
                status_data = response.json()
                status = status_data['status']
                
                if status == "completed":
                    print(f"✓ Review completed!")
                    print(f"  - Total issues: {status_data.get('total_issues', 0)}")
                    print(f"  - Critical issues: {status_data.get('critical_issues', 0)}")
                    if 'summary' in status_data:
                        print(f"  - Files reviewed: {status_data['summary'].get('total_files', 0)}")
                        print(f"  - Duration: {status_data['summary'].get('duration_seconds', 0):.1f}s")
                    break
                elif status == "failed":
                    print(f"✗ Review failed: {status_data.get('error', 'Unknown error')}")
                    break
                else:
                    print(f"  Status: {status} (checking again in 10s...)")
                    time.sleep(10)
            else:
                print(f"✗ Failed to get status: {response.status_code}")
                break
    else:
        print(f"✗ Failed to start review: {response.status_code}")
        print(f"   Response: {response.text}")

def test_your_own_pr():
    """Test with your own repository"""
    print("\n4. Test with your own repository")
    print("   To test with your own PR, update the review_request below:")
    
    # Replace with your own repo and PR
    review_request = {
        "repo": "niteesh1106/multi-agent-code-sentinel",  # Your repo
        "pr_number": 1,  # Your PR number
        "post_comment": True,  # Post comment to your PR
        "include_details": True
    }
    
    print(f"   You can modify test_api.py to use:")
    print(f'   "repo": "{review_request["repo"]}"')
    print(f'   "pr_number": {review_request["pr_number"]}')
    print("\n   First, create a test PR in your repository with some code changes.")

if __name__ == "__main__":
    print("=== Multi-Agent Code Review API Test ===\n")
    
    # Test health
    test_health()
    
    # Test manual review
    print("Note: This will test with a public repository (microsoft/vscode)")
    print("The review might take 1-2 minutes to complete.\n")
    
    confirm = input("Continue with test? (y/n): ")
    if confirm.lower() == 'y':
        test_manual_review()
    
    # Instructions for own PR
    test_your_own_pr()