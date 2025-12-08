# Phase 2: LLM CLI Wrappers

## Overview
This phase implements async wrappers for all LLM CLIs (Claude, Gemini, DeepSeek/Ollama, Codex) and intelligent routing logic.

## Dependencies
Ensure Phase 1 is complete before starting this phase.

## Directory Structure
```
src/blueprint/models/
├── __init__.py
├── base.py
├── claude.py
├── gemini.py
├── deepseek.py
├── codex.py
└── router.py
```

## File: `src/blueprint/models/base.py`
**Purpose**: Base interface for all LLM wrappers

**Requirements**:
1. Abstract base class for LLM clients
2. Async subprocess execution
3. Streaming output support
4. Error handling and retry logic
5. Process lifecycle management (start, stop, cleanup)

**Implementation outline**:
```python
import asyncio
import signal
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional
from pathlib import Path

class LLMException(Exception):
    """Base exception for LLM errors"""
    pass

class LLMUnavailableException(LLMException):
    """Raised when LLM CLI is not available"""
    pass

class LLMExecutionException(LLMException):
    """Raised when LLM execution fails"""
    pass

class BaseLLM(ABC):
    """Base class for all LLM CLI wrappers"""

    def __init__(self, cli_command: str):
        self.cli_command = cli_command
        self.process: Optional[asyncio.subprocess.Process] = None

    @abstractmethod
    async def check_availability(self) -> bool:
        """Check if LLM CLI is available"""
        pass

    async def execute(self, prompt: str, stream: bool = True) -> AsyncGenerator[str, None]:
        """
        Execute LLM command with prompt

        Args:
            prompt: The prompt to send to the LLM
            stream: Whether to stream output line by line

        Yields:
            Lines of output from the LLM
        """
        if not await self.check_availability():
            raise LLMUnavailableException(f"{self.cli_command} is not available")

        try:
            # Create subprocess
            self.process = await asyncio.create_subprocess_exec(
                self.cli_command,
                prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Stream output
            if stream:
                async for line in self._stream_output():
                    yield line
            else:
                stdout, stderr = await self.process.communicate()
                if self.process.returncode != 0:
                    raise LLMExecutionException(f"Command failed: {stderr.decode()}")
                yield stdout.decode()

        except Exception as e:
            await self.stop()
            raise LLMExecutionException(f"Execution failed: {str(e)}")

    async def _stream_output(self) -> AsyncGenerator[str, None]:
        """Stream stdout line by line"""
        if not self.process or not self.process.stdout:
            return

        while True:
            line = await self.process.stdout.readline()
            if not line:
                break
            yield line.decode().rstrip()

    async def stop(self):
        """Stop the running process gracefully"""
        if not self.process:
            return

        try:
            # Try SIGTERM first
            self.process.terminate()
            await asyncio.wait_for(self.process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            # Force kill if doesn't terminate
            self.process.kill()
            await self.process.wait()
        finally:
            self.process = None

    def is_running(self) -> bool:
        """Check if process is currently running"""
        return self.process is not None and self.process.returncode is None
```

## File: `src/blueprint/models/claude.py`
**Purpose**: Claude CLI wrapper

**Requirements**:
1. Extends BaseLLM
2. Command: `claude "prompt"`
3. Role: System Architect (spec generation)

**Implementation outline**:
```python
import asyncio
from .base import BaseLLM

class ClaudeCLI(BaseLLM):
    """Wrapper for Claude CLI"""

    def __init__(self, cli_command: str = "claude"):
        super().__init__(cli_command)

    async def check_availability(self) -> bool:
        """Check if claude CLI is available"""
        try:
            process = await asyncio.create_subprocess_exec(
                "which", self.cli_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.wait()
            return process.returncode == 0
        except Exception:
            return False

    async def generate_spec(self, brief: str) -> str:
        """
        Generate technical specification from brief

        Args:
            brief: User's feature brief

        Returns:
            Full technical specification as markdown
        """
        prompt = f"""You are a system architect. Convert this brief into a detailed technical specification.

Brief:
{brief}

Generate a comprehensive specification including:
- Overview
- Architecture
- API definitions
- Data models
- Test plan
- Implementation steps

Format as markdown."""

        result = []
        async for line in self.execute(prompt, stream=False):
            result.append(line)

        return "\n".join(result)
```

## File: `src/blueprint/models/gemini.py`
**Purpose**: Gemini CLI wrapper

**Requirements**:
1. Extends BaseLLM
2. Command: `gemini "prompt"`
3. Roles: Large doc parser, boilerplate generator, test summarizer

**Implementation outline**:
```python
import asyncio
from typing import List, Dict
from .base import BaseLLM

class GeminiCLI(BaseLLM):
    """Wrapper for Gemini CLI"""

    def __init__(self, cli_command: str = "gemini"):
        super().__init__(cli_command)

    async def check_availability(self) -> bool:
        """Check if gemini CLI is available"""
        try:
            process = await asyncio.create_subprocess_exec(
                "which", self.cli_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.wait()
            return process.returncode == 0
        except Exception:
            return False

    async def parse_spec_to_tasks(self, spec: str) -> List[Dict]:
        """
        Parse specification into structured tasks

        Args:
            spec: Technical specification markdown

        Returns:
            List of task dictionaries
        """
        prompt = f"""Convert this specification into structured tasks JSON.

Specification:
{spec}

Return ONLY valid JSON array with tasks in this format:
[
  {{
    "id": "task-1",
    "title": "Task title",
    "description": "Detailed description",
    "type": "code|boilerplate|review|architecture"
  }}
]"""

        result = []
        async for line in self.execute(prompt, stream=False):
            result.append(line)

        return "\n".join(result)

    async def generate_boilerplate(self, task_description: str) -> str:
        """Generate boilerplate code for a task"""
        prompt = f"""Generate boilerplate code for this task:

{task_description}

Provide complete, production-ready code."""

        result = []
        async for line in self.execute(prompt, stream=True):
            result.append(line)

        return "\n".join(result)
```

## File: `src/blueprint/models/deepseek.py`
**Purpose**: DeepSeek/Ollama wrapper

**Requirements**:
1. Extends BaseLLM
2. Command: `ollama run <model> "prompt"`
3. Roles: Main code generator, refactorer, summarizer
4. Configurable model name
5. Graceful handling when Ollama unavailable

**Implementation outline**:
```python
import asyncio
from typing import Optional
from .base import BaseLLM, LLMUnavailableException

class DeepSeekCLI(BaseLLM):
    """Wrapper for DeepSeek via Ollama"""

    def __init__(self, model: str = "deepseek-coder:14b", cli_command: str = "ollama"):
        super().__init__(cli_command)
        self.model = model

    async def check_availability(self) -> bool:
        """Check if ollama CLI is available"""
        try:
            process = await asyncio.create_subprocess_exec(
                "which", self.cli_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.wait()
            if process.returncode != 0:
                return False

            # Check if model is available
            process = await asyncio.create_subprocess_exec(
                self.cli_command, "list",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            return self.model in stdout.decode()
        except Exception:
            return False

    async def execute(self, prompt: str, stream: bool = True):
        """Execute with ollama run command"""
        if not await self.check_availability():
            raise LLMUnavailableException(f"Ollama or model {self.model} is not available")

        try:
            self.process = await asyncio.create_subprocess_exec(
                self.cli_command,
                "run",
                self.model,
                prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            if stream:
                async for line in self._stream_output():
                    yield line
            else:
                stdout, stderr = await self.process.communicate()
                if self.process.returncode != 0:
                    raise Exception(f"Command failed: {stderr.decode()}")
                yield stdout.decode()

        except Exception as e:
            await self.stop()
            raise Exception(f"Execution failed: {str(e)}")

    async def generate_code(self, task_description: str, context: str = "") -> str:
        """Generate code for a task"""
        prompt = f"""Generate production-ready code for this task:

Task: {task_description}

Context:
{context}

Provide clean, well-documented code."""

        result = []
        async for line in self.execute(prompt, stream=True):
            result.append(line)

        return "\n".join(result)

    async def refactor_code(self, code: str, instructions: str) -> str:
        """Refactor existing code"""
        prompt = f"""Refactor this code according to the instructions:

Code:
{code}

Instructions: {instructions}

Provide the refactored code."""

        result = []
        async for line in self.execute(prompt, stream=False):
            result.append(line)

        return "\n".join(result)
```

## File: `src/blueprint/models/codex.py`
**Purpose**: GPT Codex CLI wrapper

**Requirements**:
1. Extends BaseLLM
2. Command: `codex "prompt"`
3. Roles: Supervisor, task reviewer, correction generator

**Implementation outline**:
```python
import asyncio
from typing import List, Dict
from .base import BaseLLM

class CodexCLI(BaseLLM):
    """Wrapper for GPT Codex CLI"""

    def __init__(self, cli_command: str = "codex"):
        super().__init__(cli_command)

    async def check_availability(self) -> bool:
        """Check if codex CLI is available"""
        try:
            process = await asyncio.create_subprocess_exec(
                "which", self.cli_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.wait()
            return process.returncode == 0
        except Exception:
            return False

    async def review_tasks(self, tasks_json: str) -> str:
        """Review and refine tasks generated from spec"""
        prompt = f"""Review these tasks and suggest improvements:

Tasks:
{tasks_json}

Provide refined tasks JSON with better organization, clearer descriptions, and proper dependencies."""

        result = []
        async for line in self.execute(prompt, stream=False):
            result.append(line)

        return "\n".join(result)

    async def review_code(self, code: str, requirements: str) -> Dict:
        """
        Review generated code

        Returns:
            Dictionary with 'approved' bool and 'feedback' string
        """
        prompt = f"""Review this code against requirements:

Requirements:
{requirements}

Code:
{code}

Respond in JSON format:
{{
  "approved": true/false,
  "feedback": "Detailed feedback",
  "corrections": ["List of required corrections"]
}}"""

        result = []
        async for line in self.execute(prompt, stream=False):
            result.append(line)

        # Parse JSON response
        import json
        return json.loads("\n".join(result))

    async def generate_correction(self, code: str, issue: str) -> str:
        """Generate corrected code"""
        prompt = f"""Fix this issue in the code:

Issue: {issue}

Code:
{code}

Provide the corrected code."""

        result = []
        async for line in self.execute(prompt, stream=False):
            result.append(line)

        return "\n".join(result)
```

## File: `src/blueprint/models/router.py`
**Purpose**: Intelligent model selection and routing

**Requirements**:
1. Route tasks to appropriate models based on type and size
2. Handle fallbacks when models unavailable
3. Respect user-configured limits
4. Provide routing suggestions

**Implementation outline**:
```python
from typing import Optional
from enum import Enum
from .claude import ClaudeCLI
from .gemini import GeminiCLI
from .deepseek import DeepSeekCLI
from .codex import CodexCLI
from .base import BaseLLM
from ..config import Config

class ModelRole(Enum):
    ARCHITECT = "architecture"
    CODER = "code"
    BOILERPLATE = "boilerplate"
    REVIEWER = "review"
    PARSER = "parser"

class ModelRouter:
    """Routes tasks to appropriate LLM models"""

    def __init__(self, config: Config):
        self.config = config
        self.claude = ClaudeCLI(config.get("cli_commands").get("claude", "claude"))
        self.gemini = GeminiCLI(config.get("cli_commands").get("gemini", "gemini"))
        self.deepseek = DeepSeekCLI(
            model=config.get("local_model", "deepseek-coder:14b"),
            cli_command=config.get("cli_commands").get("ollama", "ollama")
        )
        self.codex = CodexCLI(config.get("cli_commands").get("codex", "codex"))

        self.ollama_available = None
        self.max_chars_local = config.get("max_chars_local_model", 20000)

    async def check_availability(self):
        """Check which models are available"""
        self.ollama_available = await self.deepseek.check_availability()

        if not self.ollama_available and self.config.get("ollama_unavailable_warning"):
            print("WARNING: Ollama is not available. Local coding disabled.")
            print("Blueprint will use Gemini for code generation.")

    async def route(self, role: ModelRole, content_size: int = 0) -> BaseLLM:
        """
        Route to appropriate model based on role and content size

        Args:
            role: The model role needed
            content_size: Size of content in characters

        Returns:
            Appropriate LLM client
        """
        if self.ollama_available is None:
            await self.check_availability()

        if role == ModelRole.ARCHITECT:
            return self.claude

        elif role == ModelRole.REVIEWER:
            return self.codex

        elif role == ModelRole.BOILERPLATE or content_size > self.max_chars_local:
            return self.gemini

        elif role == ModelRole.CODER:
            if self.ollama_available and content_size <= self.max_chars_local:
                return self.deepseek
            else:
                return self.gemini

        elif role == ModelRole.PARSER:
            if content_size > self.max_chars_local:
                return self.gemini
            elif self.ollama_available:
                return self.deepseek
            else:
                return self.gemini

        # Default fallback
        return self.gemini

    def get_routing_stats(self) -> dict:
        """Get statistics for routing suggestions"""
        return {
            "ollama_available": self.ollama_available,
            "max_chars_local": self.max_chars_local,
            "models": {
                "claude": "available",
                "gemini": "available",
                "deepseek": "available" if self.ollama_available else "unavailable",
                "codex": "available"
            }
        }
```

## File: `src/blueprint/models/__init__.py`
```python
"""LLM CLI wrappers and routing"""

from .base import BaseLLM, LLMException, LLMUnavailableException, LLMExecutionException
from .claude import ClaudeCLI
from .gemini import GeminiCLI
from .deepseek import DeepSeekCLI
from .codex import CodexCLI
from .router import ModelRouter, ModelRole

__all__ = [
    "BaseLLM",
    "LLMException",
    "LLMUnavailableException",
    "LLMExecutionException",
    "ClaudeCLI",
    "GeminiCLI",
    "DeepSeekCLI",
    "CodexCLI",
    "ModelRouter",
    "ModelRole"
]
```

## Testing Checklist
- [ ] Each CLI wrapper can check availability
- [ ] Subprocess execution works with streaming
- [ ] Process can be stopped mid-execution
- [ ] Fallback works when Ollama unavailable
- [ ] Router selects correct model for each role
- [ ] Router respects max_chars_local_model setting
- [ ] Error handling works for unavailable CLIs
- [ ] Async execution doesn't block

## Dependencies
Add to requirements/pyproject.toml:
- asyncio (built-in)

## Success Criteria
- All LLM CLI wrappers can execute commands
- Streaming output works for all models
- Router correctly selects models based on role and size
- Graceful degradation when Ollama unavailable
- Processes can be stopped cleanly
- Error messages are clear and actionable
