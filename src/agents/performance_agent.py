"""
Performance Agent - Analyzes code for performance issues and optimization opportunities.
"""
from typing import List, Dict, Any, Optional
import re
import json
from loguru import logger

# Handle imports for both module and direct execution
try:
    from src.agents.base_agent import BaseAgent, CodeReviewIssue
    from src.core.config import AGENT_CONFIGS
except ImportError:
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent))
    from src.agents.base_agent import BaseAgent, CodeReviewIssue
    from src.core.config import AGENT_CONFIGS


class PerformanceAgent(BaseAgent):
    """Agent specialized in detecting performance issues and optimization opportunities."""
    
    # Common performance anti-patterns
    PERFORMANCE_PATTERNS = {
        "n_plus_one": [
            (r'for.*in.*:\s*\n.*\.(get|select|find|query)', "HIGH", "Potential N+1 query pattern"),
        ],
        "inefficient_loops": [
            (r'for.*in.*:\s*\n\s*for.*in', "MEDIUM", "Nested loops detected - check time complexity"),
        ],
        "memory_issues": [
            (r'(\+=|\+\s*=).*loop', "MEDIUM", "String concatenation in loop - use list.append() and join()"),
            (r'list\s*\(.*\).*list\s*\(', "LOW", "Multiple list conversions may impact memory"),
        ],
        "database": [
            (r'SELECT\s+\*', "MEDIUM", "Avoid SELECT * - specify needed columns"),
            (r'(get|filter|query).*loop', "HIGH", "Database query inside loop detected"),
        ],
    }
    
    def __init__(self):
        super().__init__(AGENT_CONFIGS["performance"])
        self.complexity_thresholds = {
            "acceptable": ["O(1)", "O(log n)", "O(n)"],
            "warning": ["O(n log n)"],
            "critical": ["O(n²)", "O(n³)", "O(2ⁿ)"]
        }
    
    def _filter_issues(self, issues: List[CodeReviewIssue]) -> List[CodeReviewIssue]:
        """Filter and prioritize performance issues."""
        # Remove duplicates
        unique_issues = []
        seen = set()
        
        for issue in issues:
            key = (issue.line_number, issue.category, issue.message[:30])
            if key not in seen:
                seen.add(key)
                unique_issues.append(issue)
        
        # Sort by severity
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
        unique_issues.sort(key=lambda x: severity_order.get(x.severity, 5))
        
        return unique_issues[:15]  # Limit to top 15 performance issues
    
    def _prepare_prompt(
        self,
        code_diff: str,
        file_path: str,
        full_content: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Prepare performance-focused prompt."""
        prompt_parts = [
            f"As a performance optimization expert, analyze the following code changes in {file_path}:",
            "",
            "Focus on these performance aspects:",
            "1. Time complexity (identify O(n²) or worse algorithms)",
            "2. Space complexity and memory usage",
            "3. Database query efficiency (N+1 queries, missing indexes)",
            "4. Caching opportunities",
            "5. Unnecessary computations or redundant operations",
            "6. Resource leaks (unclosed connections, file handles)",
            "7. Inefficient data structures",
            "8. Blocking I/O operations that could be async",
            "",
            "=== CODE DIFF ===",
            code_diff,
            ""
        ]
        
        if full_content:
            prompt_parts.extend([
                "=== CONTEXT (partial file) ===",
                full_content[:1500],
                ""
            ])
        
        prompt_parts.extend([
            "Provide your performance review in the following JSON format:",
            json.dumps({
                "issues": [
                    {
                        "line_number": "line where issue occurs",
                        "severity": "CRITICAL for O(n²)+ complexity, HIGH for performance bugs, MEDIUM for optimization opportunities, LOW for minor improvements",
                        "category": "complexity|memory|database|caching|io|algorithm|resource_leak",
                        "message": "clear description of the performance issue",
                        "suggestion": "specific optimization technique or fix"
                    }
                ]
            }, indent=2),
            "",
            "Focus only on performance-related issues. Include estimated complexity where relevant.",
            "Return only valid JSON without any additional text."
        ])
        
        return "\n".join(prompt_parts)


# Test the agent
if __name__ == "__main__":
    import asyncio
    
    async def test_performance_agent():
        agent = PerformanceAgent()
        
        # Example code with performance issues
        test_diff = """
+def process_users(user_ids):
+    results = []
+    for user_id in user_ids:
+        # N+1 query problem
+        user = db.query(f"SELECT * FROM users WHERE id = {user_id}")
+        
+        # Nested loop - O(n²)
+        for order in user.orders:
+            for item in order.items:
+                results.append(item.price)
+    
+    # Inefficient string concatenation
+    output = ""
+    for result in results:
+        output += str(result) + ","
+    
+    return output
        """
        
        issues = await agent.review_code(
            code_diff=test_diff,
            file_path="process.py"
        )
        
        print(f"\nFound {len(issues)} performance issues:")
        for issue in issues:
            print(f"  Line {issue.line_number} ({issue.severity}): {issue.message}")
            if issue.suggestion:
                print(f"    → Suggestion: {issue.suggestion}")
    
    asyncio.run(test_performance_agent())