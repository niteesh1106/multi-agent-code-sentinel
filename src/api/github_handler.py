"""
GitHub API handler for fetching PR data and posting comments.
"""
from typing import List, Dict, Any, Optional
import base64
from github import Github, GithubException
from loguru import logger
import asyncio
from concurrent.futures import ThreadPoolExecutor


class GitHubHandler:
    """Handles GitHub API interactions."""
    
    def __init__(self, token: str):
        self.github = Github(token)
        self.executor = ThreadPoolExecutor(max_workers=5)
    
    async def get_pr_files(self, repo_name: str, pr_number: int) -> List[Dict[str, Any]]:
        """
        Fetch files changed in a pull request.
        
        Returns:
            List of dicts with keys: file_path, diff, content
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._get_pr_files_sync,
            repo_name,
            pr_number
        )
    
    def _get_pr_files_sync(self, repo_name: str, pr_number: int) -> List[Dict[str, Any]]:
        """Synchronous version of get_pr_files."""
        try:
            repo = self.github.get_repo(repo_name)
            pr = repo.get_pull(pr_number)
            
            files_data = []
            
            for file in pr.get_files():
                file_data = {
                    "file_path": file.filename,
                    "diff": file.patch or "",
                    "status": file.status,
                    "additions": file.additions,
                    "deletions": file.deletions
                }
                
                # Try to get file content for context (if not too large)
                if file.additions > 0 and file.additions < 500:
                    try:
                        # Get the file content from the PR head
                        content_file = repo.get_contents(
                            file.filename, 
                            ref=pr.head.sha
                        )
                        if content_file.size < 100000:  # Limit to 100KB
                            content = base64.b64decode(content_file.content).decode('utf-8')
                            file_data["content"] = content
                    except Exception as e:
                        logger.debug(f"Could not fetch content for {file.filename}: {e}")
                
                files_data.append(file_data)
            
            logger.info(f"Fetched {len(files_data)} files for PR #{pr_number}")
            return files_data
            
        except GithubException as e:
            logger.error(f"GitHub API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching PR files: {e}")
            raise
    
    async def post_pr_comment(self, repo_name: str, pr_number: int, comment_body: str):
        """Post a comment on a pull request."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._post_pr_comment_sync,
            repo_name,
            pr_number,
            comment_body
        )
    
    def _post_pr_comment_sync(self, repo_name: str, pr_number: int, comment_body: str):
        """Synchronous version of post_pr_comment."""
        try:
            repo = self.github.get_repo(repo_name)
            pr = repo.get_pull(pr_number)
            
            # Check if we already commented (to avoid spam)
            bot_login = self.github.get_user().login
            for comment in pr.get_issue_comments():
                if comment.user.login == bot_login and "🤖 Code Review Report" in comment.body:
                    # Update existing comment
                    comment.edit(comment_body)
                    logger.info(f"Updated existing comment on PR #{pr_number}")
                    return
            
            # Create new comment
            pr.create_issue_comment(comment_body)
            logger.info(f"Posted new comment on PR #{pr_number}")
            
        except GithubException as e:
            logger.error(f"GitHub API error posting comment: {e}")
            raise
        except Exception as e:
            logger.error(f"Error posting PR comment: {e}")
            raise
    
    async def get_pr_info(self, repo_name: str, pr_number: int) -> Dict[str, Any]:
        """Get basic PR information."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._get_pr_info_sync,
            repo_name,
            pr_number
        )
    
    def _get_pr_info_sync(self, repo_name: str, pr_number: int) -> Dict[str, Any]:
        """Synchronous version of get_pr_info."""
        try:
            repo = self.github.get_repo(repo_name)
            pr = repo.get_pull(pr_number)
            
            return {
                "number": pr.number,
                "title": pr.title,
                "description": pr.body,
                "author": pr.user.login,
                "base_branch": pr.base.ref,
                "head_branch": pr.head.ref,
                "state": pr.state,
                "created_at": pr.created_at.isoformat(),
                "updated_at": pr.updated_at.isoformat()
            }
            
        except GithubException as e:
            logger.error(f"GitHub API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching PR info: {e}")
            raise