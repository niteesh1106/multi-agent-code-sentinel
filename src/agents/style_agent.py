"""
Style Agent - Ensures code follows style guidelines and best practices.
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


class StyleAgent(BaseAgent):
    """Agent specialized in code style and readability."""
    
    # Language-specific style guidelines
    STYLE_RULES = {
        "python": {
            "naming": [
                (r'class\s+[a-z]', "MEDIUM", "Class names should use PascalCase"),
                (r'def\s+[A-Z]', "MEDIUM", "Function names should use snake_case"),
                (r'[A-Z]{3,}', "LOW", "Avoid ALL_CAPS except for constants"),
            ],
            "structure": [
                (r'^\s{5,}', "LOW", "Deep nesting detected - consider refactoring"),
                (r'def\s+\w+\(([^)]{50,})\)', "MEDIUM", "Too many parameters - consider using configuration object"),
            ],
        },
        "javascript": {
            "naming": [
                (r'function\s+[A-Z]', "MEDIUM", "Function names should use camelCase"),
                (r'const\s+[A-Z][a-z]', "LOW", "Constants are often ALL_CAPS"),
            ],
        },
    }
    
    def __init__(self):
        super().__init__(AGENT_CONFIGS["style"])
        
    def _filter_issues(self, issues: List[CodeReviewIssue]) -> List[CodeReviewIssue]:
        """Filter and prioritize style issues."""
        # Remove duplicates and minor issues
        unique_issues = []
        seen = set()
        
        for issue in issues:
            # Skip very minor issues if we have many
            if len(unique_issues) > 10 and issue.severity == "LOW":
                continue
                
            key = (issue.line_number, issue.category)
            if key not in seen:
                seen.add(key)
                unique_issues.append(issue)
        
        # Sort by severity and line number
        unique_issues.sort(key=lambda x: (
            {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "INFO": 3}.get(x.severity, 4),
            x.line_number
        ))
        
        return unique_issues[:20]  # Limit to top 20 style issues
    
    def _prepare_prompt(
        self,
        code_diff: str,
        file_path: str,
        full_content: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Prepare style-focused prompt."""
        # Detect language from file extension
        language = "python" if file_path.endswith(".py") else "javascript" if file_path.endswith(".js") else "general"
        
        prompt_parts = [
            f"As a code style expert, review the following {language} code changes in {file_path}:",
            "",
            "Focus on these style aspects:",
            "1. Naming conventions (variables, functions, classes)",
            "2. Code organization and structure",
            "3. Line length and formatting",
            "4. Comment quality and placement",
            "5. Consistency with language idioms",
            "6. DRY (Don't Repeat Yourself) principles",
            "7. Function and class size",
            "8. Clear variable and function names",
            "",
            f"Apply {language.upper()} style guidelines (PEP 8 for Python, ESLint for JavaScript).",
            "",
            "=== CODE DIFF ===",
            code_diff,
            ""
        ]
        
        prompt_parts.extend([
            "Provide your style review in the following JSON format:",
            json.dumps({
                "issues": [
                    {
                        "line_number": "line where style issue occurs",
                        "severity": "HIGH for major violations, MEDIUM for standard issues, LOW for suggestions",
                        "category": "naming|formatting|structure|documentation|consistency|complexity",
                        "message": "description of the style issue",
                        "suggestion": "how to improve the style"
                    }
                ]
            }, indent=2),
            "",
            "Focus on readability and maintainability. Be constructive in suggestions.",
            "Return only valid JSON without any additional text."
        ])
        
        return "\n".join(prompt_parts)


# Test the agent
if __name__ == "__main__":
    import asyncio
    
    async def test_style_agent():
        agent = StyleAgent()
        
        # Example code with style issues
        test_diff = """
+def ProcessUserData(user_id,user_name,user_email,user_phone,user_address):
+    # TODO: fix this later
+    x = getUserFromDatabase(user_id)
+    if x:
+        x['name'] = user_name
+        x['email'] = user_email
+        x['phone'] = user_phone
+        x['address'] = user_address
+        # do something
+        for i in range(len(x['orders'])):
+            if x['orders'][i]['status'] == 'pending':
+                x['orders'][i]['status'] = 'processed'
+    return x
        """
        
        issues = await agent.review_code(
            code_diff=test_diff,
            file_path="user_service.py"
        )
        
        print(f"\nFound {len(issues)} style issues:")
        for issue in issues:
            print(f"  Line {issue.line_number} ({issue.severity}): {issue.message}")
            if issue.suggestion:
                print(f"    → Suggestion: {issue.suggestion}")
    
    asyncio.run(test_style_agent())