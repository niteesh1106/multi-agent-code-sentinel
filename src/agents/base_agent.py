"""
Base Agent class for all code review agents.
"""
import asyncio
import aiohttp
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from loguru import logger

from langchain.prompts import ChatPromptTemplate
from langchain.schema import BaseMessage, HumanMessage, SystemMessage
from litellm import acompletion, completion
import litellm

from src.core.config import AgentConfig, settings

# Configure litellm to use Ollama
litellm.drop_params = True  # Important for Ollama compatibility

# Global aiohttp session
_aiohttp_session = None

async def get_aiohttp_session():
    global _aiohttp_session
    if _aiohttp_session is None or _aiohttp_session.closed:
        _aiohttp_session = aiohttp.ClientSession()
    return _aiohttp_session

async def close_aiohttp_session():
    global _aiohttp_session
    if _aiohttp_session and not _aiohttp_session.closed:
        await _aiohttp_session.close()

class CodeReviewIssue:
    """Represents a single issue found during code review."""
    
    def __init__(
        self,
        line_number: int,
        severity: str,  # CRITICAL, HIGH, MEDIUM, LOW, INFO
        category: str,
        message: str,
        suggestion: Optional[str] = None,
        file_path: Optional[str] = None
    ):
        self.line_number = line_number
        self.severity = severity
        self.category = category
        self.message = message
        self.suggestion = suggestion
        self.file_path = file_path
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert issue to dictionary format."""
        return {
            "line_number": self.line_number,
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "suggestion": self.suggestion,
            "file_path": self.file_path,
            "timestamp": self.timestamp.isoformat()
        }
    
    def __repr__(self):
        return f"Issue(L{self.line_number}, {self.severity}): {self.message[:50]}..."

class BaseAgent(ABC):
    """Base class for all code review agents."""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.name = config.name
        self.model = f"ollama/{config.model}"
        self.issues: List[CodeReviewIssue] = []
        self.execution_time: Optional[float] = None
        logger.info(f"Initialized {self.name} with model {self.model}")
    
    async def review_code(
        self,
        code_diff: str,
        file_path: str,
        full_content: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[CodeReviewIssue]:
        """
        Main method to review code.
        
        Args:
            code_diff: The git diff of changes
            file_path: Path to the file being reviewed
            full_content: Full file content (optional)
            context: Additional context (PR info, related files, etc.)
        
        Returns:
            List of CodeReviewIssue objects
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Prepare the review prompt
            prompt = self._prepare_prompt(code_diff, file_path, full_content, context)
            
            # Get review from LLM
            response = await self._get_llm_response(prompt)
            
            # Parse the response into issues
            self.issues = self._parse_response(response, file_path)
            
            # Filter and validate issues
            self.issues = self._filter_issues(self.issues)
            
        except Exception as e:
            logger.error(f"{self.name} error reviewing {file_path}: {str(e)}")
            self.issues = []
        
        finally:
            self.execution_time = asyncio.get_event_loop().time() - start_time
            logger.info(f"{self.name} completed review of {file_path} in {self.execution_time:.2f}s. Found {len(self.issues)} issues.")
        
        return self.issues
    
    async def _get_llm_response(self, prompt: str) -> str:
        """Get response from the LLM."""
        messages = [
            {"role": "system", "content": self.config.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        try:
            # For Ollama, we need to use the correct format
            # Use ollama/ prefix with the model name
            response = await acompletion(
                model=self.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                timeout=settings.model_timeout,
                api_base=settings.ollama_base_url  # Explicitly set for Ollama
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"{self.name} LLM error: {str(e)}")
            # Try with synchronous call as fallback
            try:
                response = completion(
                    model=self.model,
                    messages=messages,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    timeout=settings.model_timeout,
                    api_base=settings.ollama_base_url
                )
                return response.choices[0].message.content
            except Exception as e2:
                logger.error(f"{self.name} Sync LLM error: {str(e2)}")
                raise
    
    def _prepare_prompt(
        self,
        code_diff: str,
        file_path: str,
        full_content: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Prepare the prompt for the LLM."""
        prompt_parts = [
            f"Review the following code changes in {file_path}:",
            "",
            "=== CODE DIFF ===",
            code_diff,
            ""
        ]
        
        if full_content:
            prompt_parts.extend([
                "=== FULL FILE CONTENT ===",
                full_content[:3000],  # Limit to prevent token overflow
                ""
            ])
        
        prompt_parts.extend([
            "Provide your review in the following JSON format:",
            json.dumps({
                "issues": [
                    {
                        "line_number": "integer",
                        "severity": "CRITICAL|HIGH|MEDIUM|LOW|INFO",
                        "category": "category_name",
                        "message": "description of the issue",
                        "suggestion": "how to fix it (optional)"
                    }
                ]
            }, indent=2),
            "",
            "Focus on issues relevant to your expertise. Return only valid JSON."
        ])
        
        return "\n".join(prompt_parts)
    
    def _parse_response(self, response: str, file_path: str) -> List[CodeReviewIssue]:
        """Parse LLM response into CodeReviewIssue objects."""
        issues = []
        
        try:
            # Extract JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
                
                for issue_data in data.get("issues", []):
                    # Handle different line number formats
                    line_num_str = str(issue_data.get("line_number", 0))
                    
                    # Extract first number if it's a range or list
                    import re
                    line_match = re.search(r'(\d+)', line_num_str)
                    line_number = int(line_match.group(1)) if line_match else 0
                    
                    issue = CodeReviewIssue(
                        line_number=line_number,
                        severity=issue_data.get("severity", "MEDIUM"),
                        category=issue_data.get("category", "general"),
                        message=issue_data.get("message", ""),
                        suggestion=issue_data.get("suggestion"),
                        file_path=file_path
                    )
                    issues.append(issue)
        
        except json.JSONDecodeError as e:
            logger.warning(f"{self.name} failed to parse JSON response: {e}")
            # Fallback: try to extract issues from text
            issues = self._parse_text_response(response, file_path)
        
        except Exception as e:
            logger.error(f"{self.name} error parsing response: {e}")
        
        return issues
    
    def _parse_text_response(self, response: str, file_path: str) -> List[CodeReviewIssue]:
        """Fallback parser for non-JSON responses."""
        # This is a simple implementation - can be enhanced
        issues = []
        lines = response.split("\n")
        
        for line in lines:
            if "line" in line.lower() and ("issue" in line.lower() or "problem" in line.lower()):
                # Try to extract line number
                import re
                line_match = re.search(r'line\s*(\d+)', line, re.IGNORECASE)
                line_num = int(line_match.group(1)) if line_match else 0
                
                issues.append(CodeReviewIssue(
                    line_number=line_num,
                    severity="MEDIUM",
                    category="general",
                    message=line.strip(),
                    file_path=file_path
                ))
        
        return issues
    
    @abstractmethod
    def _filter_issues(self, issues: List[CodeReviewIssue]) -> List[CodeReviewIssue]:
        """Filter issues based on agent-specific criteria. Must be implemented by subclasses."""
        pass
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of the review."""
        severity_counts = {}
        for issue in self.issues:
            severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1
        
        return {
            "agent": self.name,
            "total_issues": len(self.issues),
            "severity_breakdown": severity_counts,
            "execution_time": self.execution_time,
            "categories": list(set(issue.category for issue in self.issues))
        }