"""
Security Agent - Detects security vulnerabilities in code.
"""
import json
from typing import List, Dict, Any, Optional
import re
from loguru import logger
from src.agents.base_agent import BaseAgent, CodeReviewIssue
from src.core.config import AGENT_CONFIGS

class SecurityAgent(BaseAgent):
    """Agent specialized in detecting security vulnerabilities."""
    
    # Common security patterns to look for
    SECURITY_PATTERNS = {
        # SQL Injection patterns
        "sql_injection": [
            (r'f["\'].*SELECT.*WHERE.*{.*}', "CRITICAL", "Potential SQL injection via f-string"),
            (r'\".*SELECT.*WHERE.*\"\s*\+\s*', "CRITICAL", "Potential SQL injection via string concatenation"),
            (r'\.format\(.*\).*WHERE', "HIGH", "Potential SQL injection via .format()"),
            (r'%\s*\(.*\).*WHERE', "HIGH", "Potential SQL injection via % formatting"),
        ],
        
        # XSS patterns
        "xss": [
            (r'innerHTML\s*=\s*[^\'\"]*\+', "HIGH", "Potential XSS via innerHTML manipulation"),
            (r'document\.write\s*\([^\'\"]*\+', "HIGH", "Potential XSS via document.write"),
            (r'\.html\(\s*[^\'\"]*\+', "MEDIUM", "Potential XSS via jQuery .html()"),
        ],
        
        # Hardcoded secrets
        "secrets": [
            (r'(password|passwd|pwd)\s*=\s*["\'][^"\']+["\']', "CRITICAL", "Hardcoded password detected"),
            (r'(api_key|apikey|api_token)\s*=\s*["\'][^"\']+["\']', "CRITICAL", "Hardcoded API key detected"),
            (r'(secret|private_key)\s*=\s*["\'][^"\']+["\']', "CRITICAL", "Hardcoded secret detected"),
            (r'(aws_access_key|aws_secret)\s*=\s*["\'][^"\']+["\']', "CRITICAL", "AWS credentials detected"),
        ],
        
        # Insecure functions
        "insecure_functions": [
            (r'eval\s*\(', "HIGH", "Use of eval() is dangerous"),
            (r'exec\s*\(', "HIGH", "Use of exec() is dangerous"),
            (r'pickle\.loads\s*\(', "HIGH", "Unpickling untrusted data is dangerous"),
            (r'yaml\.load\s*\([^,)]*\)', "MEDIUM", "Use yaml.safe_load() instead of yaml.load()"),
        ],
        
        # Path traversal
        "path_traversal": [
            (r'open\s*\([^,)]*\+[^,)]*\)', "HIGH", "Potential path traversal vulnerability"),
            (r'os\.path\.join\s*\([^,)]*request', "HIGH", "Potential path traversal via user input"),
        ],
        
        # Weak cryptography
        "weak_crypto": [
            (r'md5\s*\(', "MEDIUM", "MD5 is cryptographically weak"),
            (r'sha1\s*\(', "MEDIUM", "SHA1 is cryptographically weak"),
            (r'Random\s*\(\)', "LOW", "Use secrets module for cryptographic randomness"),
        ],
    }
    
    def __init__(self):
        super().__init__(AGENT_CONFIGS["security"])
        self.severity_priority = {
            "CRITICAL": 0,
            "HIGH": 1,
            "MEDIUM": 2,
            "LOW": 3,
            "INFO": 4
        }
    
    def _filter_issues(self, issues: List[CodeReviewIssue]) -> List[CodeReviewIssue]:
        """Filter and prioritize security issues."""
        # Remove duplicates
        unique_issues = []
        seen = set()
        
        for issue in issues:
            key = (issue.line_number, issue.message)
            if key not in seen:
                seen.add(key)
                unique_issues.append(issue)
        
        # Sort by severity
        unique_issues.sort(key=lambda x: self.severity_priority.get(x.severity, 5))
        
        # Apply additional pattern-based detection
        pattern_issues = self._detect_pattern_issues(issues[0].file_path if issues else "")
        unique_issues.extend(pattern_issues)
        
        return unique_issues[:20]  # Limit to top 20 issues
    
    def _detect_pattern_issues(self, file_path: str) -> List[CodeReviewIssue]:
        """Detect issues using predefined patterns."""
        pattern_issues = []
        
        # This would normally scan the actual code content
        # For now, we'll return empty list as we need the code content
        return pattern_issues
    
    def _prepare_prompt(
        self,
        code_diff: str,
        file_path: str,
        full_content: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Prepare security-focused prompt."""
        prompt_parts = [
            f"As a security expert, review the following code changes in {file_path}:",
            "",
            "Focus on these security concerns:",
            "1. SQL Injection vulnerabilities",
            "2. Cross-Site Scripting (XSS)",
            "3. Authentication and authorization issues",
            "4. Hardcoded secrets or credentials",
            "5. Insecure cryptography",
            "6. Path traversal vulnerabilities",
            "7. Code injection risks",
            "8. OWASP Top 10 vulnerabilities",
            "",
            "=== CODE DIFF ===",
            code_diff,
            ""
        ]
        
        if full_content:
            prompt_parts.extend([
                "=== FULL FILE CONTENT (truncated) ===",
                full_content[:2000],
                ""
            ])
        
        prompt_parts.extend([
            "Provide your security review in the following JSON format:",
            json.dumps({
                "issues": [
                    {
                        "line_number": "line number where issue occurs",
                        "severity": "CRITICAL for immediate threats, HIGH for serious issues, MEDIUM for concerning patterns, LOW for best practice violations",
                        "category": "sql_injection|xss|auth|secrets|crypto|path_traversal|injection|other",
                        "message": "clear description of the security issue",
                        "suggestion": "specific fix or mitigation"
                    }
                ]
            }, indent=2),
            "",
            "Only report actual security issues, not style or performance concerns.",
            "Return only valid JSON without any additional text."
        ])
        
        return "\n".join(prompt_parts)
    
    async def analyze_file_for_secrets(self, content: str) -> List[CodeReviewIssue]:
        """Special method to scan entire file for secrets."""
        issues = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            for category, patterns in self.SECURITY_PATTERNS.items():
                if category == "secrets":
                    for pattern, severity, message in patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            # Verify it's not a placeholder
                            if not any(placeholder in line.lower() for placeholder in 
                                     ['example', 'placeholder', 'your_', 'xxx', '...']):
                                issues.append(CodeReviewIssue(
                                    line_number=line_num,
                                    severity=severity,
                                    category="secrets",
                                    message=message,
                                    suggestion="Remove hardcoded secrets and use environment variables",
                                    file_path="scan"
                                ))
        
        return issues


# Example usage for testing
if __name__ == "__main__":
    import asyncio
    
    async def test_security_agent():
        agent = SecurityAgent()
        
        # Example vulnerable code diff
        test_diff = """
+def get_user(user_id):
+    query = f"SELECT * FROM users WHERE id = {user_id}"
+    password = "admin123"
+    api_key = "sk-1234567890abcdef"
+    return execute_query(query)
        """
        
        issues = await agent.review_code(
            code_diff=test_diff,
            file_path="test.py"
        )
        
        print(f"Found {len(issues)} security issues:")
        for issue in issues:
            print(f"  Line {issue.line_number} ({issue.severity}): {issue.message}")
    
    # Run the test
    asyncio.run(test_security_agent())