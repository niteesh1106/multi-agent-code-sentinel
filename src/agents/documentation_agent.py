"""
Documentation Agent - Evaluates code documentation quality and completeness.
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


class DocumentationAgent(BaseAgent):
    """Agent specialized in documentation quality and completeness."""
    
    # Documentation patterns to check
    DOC_PATTERNS = {
        "missing_docstring": [
            (r'def\s+\w+\([^)]*\):\s*\n\s*[^"\']', "HIGH", "Function missing docstring"),
            (r'class\s+\w+.*:\s*\n\s*[^"\']', "HIGH", "Class missing docstring"),
        ],
        "incomplete_docs": [
            (r'"""[^"]{0,20}"""', "MEDIUM", "Docstring too short - add more detail"),
            (r'#\s*TODO(?!.*\d{4})', "LOW", "TODO without deadline or assignee"),
        ],
        "missing_type_hints": [
            (r'def\s+\w+\([^:)]+\)(?!.*->)', "MEDIUM", "Function missing return type hint"),
        ],
    }
    
    def __init__(self):
        super().__init__(AGENT_CONFIGS["documentation"])
        
    def _filter_issues(self, issues: List[CodeReviewIssue]) -> List[CodeReviewIssue]:
        """Filter and prioritize documentation issues."""
        # Group similar issues
        unique_issues = []
        seen_types = {}
        
        for issue in issues:
            issue_type = issue.category
            if issue_type in seen_types:
                # If we already have 3 of this type, skip
                if seen_types[issue_type] >= 3:
                    continue
                seen_types[issue_type] += 1
            else:
                seen_types[issue_type] = 1
            
            unique_issues.append(issue)
        
        # Sort by severity and line number
        unique_issues.sort(key=lambda x: (
            {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}.get(x.severity, 5),
            x.line_number
        ))
        
        return unique_issues[:15]  # Limit to top 15 documentation issues
    
    def _prepare_prompt(
        self,
        code_diff: str,
        file_path: str,
        full_content: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Prepare documentation-focused prompt."""
        prompt_parts = [
            f"As a documentation expert, review the documentation in {file_path}:",
            "",
            "Check for these documentation aspects:",
            "1. Function and class docstrings (presence and quality)",
            "2. Parameter descriptions and type hints",
            "3. Return value documentation",
            "4. Complex logic explanations via comments",
            "5. API documentation for public methods",
            "6. Example usage in docstrings",
            "7. Module-level documentation",
            "8. TODO/FIXME comments with context",
            "",
            "=== CODE DIFF ===",
            code_diff,
            ""
        ]
        
        if full_content:
            prompt_parts.extend([
                "=== CONTEXT ===",
                "Note: Check if new functions match the documentation style of existing code.",
                ""
            ])
        
        prompt_parts.extend([
            "Provide your documentation review in the following JSON format:",
            json.dumps({
                "issues": [
                    {
                        "line_number": "line where documentation is missing or inadequate",
                        "severity": "HIGH for missing docs on public APIs, MEDIUM for missing internal docs, LOW for enhancement suggestions",
                        "category": "missing_docstring|incomplete_docs|missing_params|missing_return|missing_types|unclear_comment",
                        "message": "what documentation is missing or needs improvement",
                        "suggestion": "specific documentation to add"
                    }
                ]
            }, indent=2),
            "",
            "Focus on documentation that helps future developers understand the code.",
            "Return only valid JSON without any additional text."
        ])
        
        return "\n".join(prompt_parts)


# Test the agent
if __name__ == "__main__":
    import asyncio
    
    async def test_documentation_agent():
        agent = DocumentationAgent()
        
        # Example code with documentation issues
        test_diff = """
+def calculate_discount(price, customer_type, season):
+    # Apply discount
+    if customer_type == 'premium':
+        discount = 0.2
+    elif season == 'holiday':
+        discount = 0.15
+    else:
+        discount = 0.05
+    
+    final_price = price * (1 - discount)
+    return final_price
+
+class OrderProcessor:
+    def __init__(self):
+        self.orders = []
+    
+    def process(self, order):
+        # TODO: implement this
+        pass
        """
        
        issues = await agent.review_code(
            code_diff=test_diff,
            file_path="order_service.py"
        )
        
        print(f"\nFound {len(issues)} documentation issues:")
        for issue in issues:
            print(f"  Line {issue.line_number} ({issue.severity}): {issue.message}")
            if issue.suggestion:
                print(f"    → Suggestion: {issue.suggestion}")
    
    asyncio.run(test_documentation_agent())