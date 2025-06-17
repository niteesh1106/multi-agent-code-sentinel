"""
Test the orchestrator locally without GitHub
"""
import asyncio
from src.core.orchestrator import Orchestrator

async def test_local_review():
    """Test the review system with local code"""
    orchestrator = Orchestrator()
    
    # Test data - simulating a PR with problematic code
    test_files = [
        {
            "file_path": "backend/auth_service.py",
            "diff": """
+from flask import request
+import mysql.connector
+
+def login_user():
+    username = request.args.get('username')
+    password = request.args.get('password')
+    
+    # SQL Injection vulnerability
+    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
+    
+    # Hardcoded database credentials
+    db = mysql.connector.connect(
+        host="localhost",
+        user="root",
+        password="admin123",
+        database="production_db"
+    )
+    
+    cursor = db.cursor()
+    cursor.execute(query)
+    user = cursor.fetchone()
+    
+    if user:
+        # Hardcoded secret key
+        token = jwt.encode({'user_id': user[0]}, 'secret123', algorithm='HS256')
+        return {'token': token}
+    
+    return {'error': 'Invalid credentials'}
+
+def process_orders():
+    orders = get_all_orders()  # This could be thousands
+    
+    # Nested loops - O(n²) complexity
+    for order in orders:
+        for item in order.items:
+            for discount in all_discounts:
+                if discount.applies_to(item):
+                    item.price *= (1 - discount.rate)
+    
+    # Inefficient string concatenation
+    report = ""
+    for order in orders:
+        report += f"Order {order.id}: ${order.total}\\n"
+    
+    return report
"""
        },
        {
            "file_path": "frontend/user_component.js",
            "diff": """
+class UserProfile {
+    constructor() {
+        this.data = null;
+    }
+    
+    // Missing JSDoc
+    loadUserData(userId) {
+        // XSS vulnerability
+        document.getElementById('welcome').innerHTML = 'Welcome ' + userName;
+        
+        // Hardcoded API endpoint
+        fetch('http://localhost:3000/api/users/' + userId)
+            .then(r => r.json())
+            .then(d => this.data = d);
+    }
+    
+    updateProfile(newData) {
+        // No input validation
+        Object.assign(this.data, newData);
+        
+        // Exposed API key
+        const API_KEY = 'sk-1234567890abcdef';
+        
+        fetch('/api/profile', {
+            method: 'POST',
+            headers: {
+                'Authorization': API_KEY,
+                'Content-Type': 'application/json'
+            },
+            body: JSON.stringify(this.data)
+        });
+    }
+}
"""
        }
    ]
    
    print("🔍 Starting local code review...\n")
    
    # Run review
    result = await orchestrator.review_pull_request(
        pr_number=1,
        repo_name="local/test",
        files_data=test_files
    )
    
    # Print results
    print("\n" + "="*60)
    print(result.to_markdown())
    print("="*60)
    
    # Summary
    print(f"\n📊 Review Summary:")
    print(f"   Total Issues: {result.total_issues}")
    print(f"   Critical Issues: {result.critical_issues}")
    print(f"   Review Time: {result.summary['duration_seconds']:.1f}s")
    
    await orchestrator.shutdown()

if __name__ == "__main__":
    print("=== Local Code Review Test ===")
    print("This tests the review system without GitHub integration\n")
    
    asyncio.run(test_local_review())