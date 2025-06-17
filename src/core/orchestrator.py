"""
Orchestrator - Coordinates multiple agents to perform comprehensive code review.
"""
import asyncio
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timezone
import json
from pathlib import Path
from loguru import logger

from src.agents.base_agent import BaseAgent, CodeReviewIssue
from src.agents.security_agent import SecurityAgent
from src.agents.performance_agent import PerformanceAgent
from src.agents.style_agent import StyleAgent
from src.agents.documentation_agent import DocumentationAgent
from src.core.config import settings


class ReviewResult:
    """Complete review result from all agents."""
    
    def __init__(self, pr_number: int, repo_name: str):
        self.pr_number = pr_number
        self.repo_name = repo_name
        self.start_time = datetime.now(timezone.utc)
        self.end_time: Optional[datetime] = None
        self.file_results: Dict[str, Dict[str, List[CodeReviewIssue]]] = {}
        self.summary: Dict[str, Any] = {}
        self.total_issues = 0
        self.critical_issues = 0
        
    def add_file_result(self, file_path: str, agent_name: str, issues: List[CodeReviewIssue]):
        """Add results from an agent for a specific file."""
        if file_path not in self.file_results:
            self.file_results[file_path] = {}
        
        self.file_results[file_path][agent_name] = issues
        self.total_issues += len(issues)
        self.critical_issues += sum(1 for issue in issues if issue.severity == "CRITICAL")
    
    def finalize(self):
        """Calculate final summary statistics."""
        self.end_time = datetime.now(timezone.utc)
        self.duration = (self.end_time - self.start_time).total_seconds()
        
        # Calculate summary by severity
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        category_counts = {}
        
        for file_path, agents_results in self.file_results.items():
            for agent_name, issues in agents_results.items():
                for issue in issues:
                    severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1
                    category_counts[issue.category] = category_counts.get(issue.category, 0) + 1
        
        self.summary = {
            "total_files": len(self.file_results),
            "total_issues": self.total_issues,
            "critical_issues": self.critical_issues,
            "severity_breakdown": severity_counts,
            "category_breakdown": category_counts,
            "duration_seconds": self.duration,
            "agents_used": list(set(
                agent for agents in self.file_results.values() for agent in agents.keys()
            ))
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "pr_number": self.pr_number,
            "repo_name": self.repo_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "summary": self.summary,
            "file_results": {
                file_path: {
                    agent_name: [issue.to_dict() for issue in issues]
                    for agent_name, issues in agents_results.items()
                }
                for file_path, agents_results in self.file_results.items()
            }
        }
    
    def to_markdown(self) -> str:
        """Generate markdown report for GitHub comment."""
        lines = [
            "## 🤖 Code Review Report",
            "",
            f"**Repository:** {self.repo_name}",
            f"**Pull Request:** #{self.pr_number}",
            f"**Review Duration:** {self.duration:.1f}s",
            "",
            "### 📊 Summary",
            f"- **Total Issues:** {self.total_issues}",
            f"- **Critical Issues:** {self.critical_issues} 🚨" if self.critical_issues > 0 else "- **Critical Issues:** 0 ✅",
            f"- **Files Reviewed:** {len(self.file_results)}",
            ""
        ]
        
        # Severity breakdown
        if self.total_issues > 0:
            lines.extend([
                "### 🎯 Issues by Severity",
                "| Severity | Count | Percentage |",
                "|----------|-------|------------|"
            ])
            
            for severity, count in self.summary["severity_breakdown"].items():
                if count > 0:
                    percentage = (count / self.total_issues) * 100
                    emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🔵", "INFO": "ℹ️"}.get(severity, "")
                    lines.append(f"| {emoji} {severity} | {count} | {percentage:.1f}% |")
            
            lines.append("")
        
        # File-by-file results
        lines.extend(["### 📁 Detailed Results", ""])
        
        for file_path, agents_results in sorted(self.file_results.items()):
            all_issues = []
            for agent_name, issues in agents_results.items():
                all_issues.extend([(agent_name, issue) for issue in issues])
            
            if all_issues:
                lines.append(f"#### `{file_path}`")
                lines.append("")
                
                # Group by severity for better readability
                critical_issues = [(a, i) for a, i in all_issues if i.severity == "CRITICAL"]
                high_issues = [(a, i) for a, i in all_issues if i.severity == "HIGH"]
                other_issues = [(a, i) for a, i in all_issues if i.severity not in ["CRITICAL", "HIGH"]]
                
                # Show critical issues first
                for agent_name, issue in critical_issues:
                    lines.append(f"- **Line {issue.line_number}** 🔴 `CRITICAL` ({agent_name}): {issue.message}")
                    if issue.suggestion:
                        lines.append(f"  - 💡 {issue.suggestion}")
                
                # Then high severity
                for agent_name, issue in high_issues:
                    lines.append(f"- **Line {issue.line_number}** 🟠 `HIGH` ({agent_name}): {issue.message}")
                    if issue.suggestion:
                        lines.append(f"  - 💡 {issue.suggestion}")
                
                # Show a few other issues (collapsed if many)
                if len(other_issues) > 3:
                    lines.extend([
                        "",
                        "<details>",
                        f"<summary>Show {len(other_issues)} more issues</summary>",
                        ""
                    ])
                
                for agent_name, issue in other_issues[:10]:  # Limit to 10
                    severity_emoji = {"MEDIUM": "🟡", "LOW": "🔵", "INFO": "ℹ️"}.get(issue.severity, "")
                    lines.append(f"- **Line {issue.line_number}** {severity_emoji} `{issue.severity}` ({agent_name}): {issue.message}")
                
                if len(other_issues) > 3:
                    lines.extend(["", "</details>"])
                
                lines.append("")
        
        # Footer
        lines.extend([
            "---",
            "*Generated by Multi-Agent Code Review System*",
            f"*Agents used: {', '.join(self.summary['agents_used'])}*"
        ])
        
        return "\n".join(lines)


class Orchestrator:
    """Coordinates multiple agents to review code changes."""
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self._initialize_agents()
        
    def _initialize_agents(self):
        """Initialize all enabled agents."""
        if settings.enable_security_agent:
            self.agents["Security"] = SecurityAgent()
            
        if settings.enable_performance_agent:
            self.agents["Performance"] = PerformanceAgent()
            
        if settings.enable_style_agent:
            self.agents["Style"] = StyleAgent()
            
        if settings.enable_docs_agent:
            self.agents["Documentation"] = DocumentationAgent()
            
        logger.info(f"Initialized {len(self.agents)} agents: {list(self.agents.keys())}")
    
    async def review_file(
        self,
        file_path: str,
        code_diff: str,
        full_content: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, List[CodeReviewIssue]]:
        """Run all agents on a single file."""
        results = {}
        
        # Run agents concurrently
        tasks = []
        for agent_name, agent in self.agents.items():
            task = agent.review_code(code_diff, file_path, full_content, context)
            tasks.append((agent_name, task))
        
        # Gather results
        for agent_name, task in tasks:
            try:
                issues = await task
                results[agent_name] = issues
                logger.info(f"{agent_name} found {len(issues)} issues in {file_path}")
            except Exception as e:
                logger.error(f"{agent_name} failed for {file_path}: {e}")
                results[agent_name] = []
        
        return results
    
    async def review_pull_request(
        self,
        pr_number: int,
        repo_name: str,
        files_data: List[Dict[str, Any]]
    ) -> ReviewResult:
        """
        Review an entire pull request.
        
        Args:
            pr_number: PR number
            repo_name: Repository name (owner/repo)
            files_data: List of file data, each containing:
                - file_path: Path to the file
                - diff: Git diff of changes
                - content: Full file content (optional)
        """
        logger.info(f"Starting review of PR #{pr_number} in {repo_name} with {len(files_data)} files")
        
        result = ReviewResult(pr_number, repo_name)
        
        # Process files with rate limiting
        for file_data in files_data:
            file_path = file_data["file_path"]
            
            # Skip non-code files
            if not self._should_review_file(file_path):
                logger.debug(f"Skipping non-code file: {file_path}")
                continue
            
            logger.info(f"Reviewing file: {file_path}")
            
            # Review the file with all agents
            file_results = await self.review_file(
                file_path=file_path,
                code_diff=file_data.get("diff", ""),
                full_content=file_data.get("content"),
                context={"pr_number": pr_number, "repo": repo_name}
            )
            
            # Add results
            for agent_name, issues in file_results.items():
                if issues:
                    result.add_file_result(file_path, agent_name, issues)
            
            # Small delay to avoid overwhelming the LLM
            await asyncio.sleep(0.5)
        
        result.finalize()
        logger.info(f"Review complete. Total issues: {result.total_issues} (Critical: {result.critical_issues})")
        
        return result
    
    def _should_review_file(self, file_path: str) -> bool:
        """Check if file should be reviewed based on extension."""
        supported_extensions = {
            ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".cpp", ".c", 
            ".cs", ".go", ".rb", ".php", ".swift", ".kt", ".rs", ".scala"
        }
        
        path = Path(file_path)
        return path.suffix.lower() in supported_extensions
    
    async def shutdown(self):
        """Clean up resources."""
        # Close aiohttp session if needed
        try:
            from src.agents.base_agent import close_aiohttp_session
            await close_aiohttp_session()
        except:
            pass


# Example usage
if __name__ == "__main__":
    async def test_orchestrator():
        orchestrator = Orchestrator()
        
        # Test data
        test_files = [
            {
                "file_path": "api/user_service.py",
                "diff": """
+def authenticate_user(username, password):
+    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
+    user = db.execute(query)
+    
+    if user:
+        token = "hardcoded_token_123"
+        return {"user": user, "token": token}
+    return None

+def process_payment(amount, card_number):
+    # Process payment
+    for transaction in get_all_transactions():
+        if transaction.amount > amount:
+            validate_transaction(transaction)
+    
+    result = ""
+    for i in range(100):
+        result += str(i)
+    
+    return result
                """
            }
        ]
        
        # Run review
        result = await orchestrator.review_pull_request(
            pr_number=123,
            repo_name="test/repo",
            files_data=test_files
        )
        
        # Print markdown report
        print(result.to_markdown())
        
        # Save JSON report
        with open("test_review_report.json", "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        
        await orchestrator.shutdown()
    
    asyncio.run(test_orchestrator())