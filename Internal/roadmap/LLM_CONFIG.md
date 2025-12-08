# LLM Configuration Interface — Interactive Terminal UI Design

**Purpose**: Provide a simple, intuitive terminal-based interface for configuring the multi-LLM orchestration tools and backends (OpenAI, Gemini, Claude, Ollama). This interface should enable users to manage API keys, endpoints, model selection, and backend modes through keyboard-driven navigation.

**Target Environment**: Unix-like systems (Linux, macOS), Python 3.10+, standard terminal emulators.

---

## 1. Interface Overview & User Flow

### 1.1 High-Level Architecture

The configuration interface operates as a **modal TUI** (text user interface) with:
- **Main Menu**: Backend selection screen showing all 4 backends with their status
- **Configuration Views**: Per-backend screens for detailed settings
- **Model Picker**: Dynamic model selection from live backend queries
- **Input Dialogs**: Secure text entry for API keys, URLs, etc.
- **Confirmation Dialogs**: Save/discard/reset confirmations

### 1.2 User Journey

```
┌─────────────────────────────────────────────────┐
│ 1. Launch config tool                          │
│ 2. See main menu with backend statuses         │
│ 3. Select backend to configure (↑/↓ + Enter)   │
│ 4. Edit settings in backend config view        │
│ 5. Select model from live query                │
│ 6. Return to main menu (Esc)                   │
│ 7. Save all & exit OR discard changes          │
└─────────────────────────────────────────────────┘
```

### 1.3 Navigation Keybindings

| Key           | Action                                    |
|---------------|-------------------------------------------|
| `↑` / `↓`     | Navigate menu items                       |
| `←` / `→`     | Navigate tabs or radio options            |
| `Enter`       | Activate/confirm selection                |
| `Esc`         | Go back / cancel                          |
| `Tab`         | Move to next field                        |
| `Shift+Tab`   | Move to previous field                    |
| `Space`       | Toggle checkbox                           |
| `Ctrl+S`      | Quick save (from main menu)               |
| `Ctrl+C`      | Exit without saving                       |
| `Ctrl+R`      | Reset current backend to defaults         |

---

## 2. Screen Layouts (ASCII Mockups)

### 2.1 Main Menu Screen

```
╔═══════════════════════════════════════════════════════════════════════╗
║  LLM Backend Configuration                                            ║
║  Select a backend to configure (↑/↓), press Enter to edit            ║
╠═══════════════════════════════════════════════════════════════════════╣
║                                                                       ║
║  > [✓] OpenAI API                                                     ║
║         Model: gpt-4o-2024-11-20                                      ║
║         API Key: ********k3J2  (set)                                  ║
║         Endpoint: https://api.openai.com/v1  (default)                ║
║                                                                       ║
║    [✓] Gemini API                                                     ║
║         Model: gemini-2.5-flash                                       ║
║         API Key: (not set)                                            ║
║         Endpoint: (default)                                           ║
║                                                                       ║
║    [ ] Ollama                                                         ║
║         Mode: Local                                                   ║
║         Model: deepseek-coder:latest                                  ║
║         Endpoint: http://localhost:11434                              ║
║                                                                       ║
║    [✓] Claude API                                                     ║
║         Model: claude-sonnet-4.5-20250514                             ║
║         API Key: ********x9Lm  (set)                                  ║
║         Endpoint: https://api.anthropic.com  (default)                ║
║                                                                       ║
╠═══════════════════════════════════════════════════════════════════════╣
║  [S] Save All & Exit  │  [D] Discard Changes  │  [Q] Quit            ║
╚═══════════════════════════════════════════════════════════════════════╝
```

**Layout Notes**:
- Each backend shows: checkbox (enabled/disabled), name, model, key status, endpoint
- Current selection highlighted with `>` prefix and inverted colors
- Masked API keys show last 4 chars for verification
- `(not set)` appears when credentials/models are missing
- Bottom action bar for global commands

### 2.2 Backend Configuration Screen (Example: OpenAI)

```
╔═══════════════════════════════════════════════════════════════════════╗
║  Configure OpenAI API                                                 ║
║  Tab/Shift+Tab to navigate fields, Enter to edit                     ║
╠═══════════════════════════════════════════════════════════════════════╣
║                                                                       ║
║  [✓] Enable this backend                                              ║
║                                                                       ║
║  API Key: [************************************************k3J2     ] ║
║           Press Enter to edit (current: set)                          ║
║                                                                       ║
║  API Endpoint:                                                        ║
║    ( ) Use default: https://api.openai.com/v1                         ║
║    (•) Custom URL: [https://custom-proxy.example.com/v1           ]  ║
║                                                                       ║
║  Model: [gpt-4o-2024-11-20                                ▼]          ║
║         Press Enter to query and select from available models         ║
║                                                                       ║
║  ┌─────────────────────────────────────────────────────────────────┐ ║
║  │ Connection Test                                                 │ ║
║  │ Status: ✓ Connected successfully                                │ ║
║  │ Models found: 12                                                │ ║
║  │ [Test Connection]                                               │ ║
║  └─────────────────────────────────────────────────────────────────┘ ║
║                                                                       ║
╠═══════════════════════════════════════════════════════════════════════╣
║  [R] Reset to Defaults  │  [Esc] Back to Main Menu                   ║
╚═══════════════════════════════════════════════════════════════════════╝
```

**Layout Notes**:
- Enable/disable toggle at top
- API key field with masking (shows last 4 chars)
- Radio buttons for default vs. custom endpoint
- Model dropdown triggers model picker (see 2.3)
- Connection test panel shows live validation results
- Escape returns to main menu (changes staged, not saved until main menu save)

### 2.3 Model Selection Dialog

```
╔═══════════════════════════════════════════════════════════════════════╗
║  Select Model for OpenAI API                                          ║
║  Querying available models...                                         ║
╠═══════════════════════════════════════════════════════════════════════╣
║                                                                       ║
║  Filter: [gpt-4                                ] (type to filter)     ║
║                                                                       ║
║  ┌─────────────────────────────────────────────────────────────────┐ ║
║  │ > gpt-4o-2024-11-20                         (currently selected)│ ║
║  │   gpt-4o-2024-08-06                                             │ ║
║  │   gpt-4-turbo-2024-04-09                                        │ ║
║  │   gpt-4-turbo-preview                                           │ ║
║  │   gpt-4                                                         │ ║
║  │   gpt-3.5-turbo                                                 │ ║
║  │   gpt-3.5-turbo-16k                                             │ ║
║  │   ...                                                           │ ║
║  │                                                                 │ ║
║  │   [Showing 7 of 12 models]                 [↑/↓ to scroll]     │ ║
║  └─────────────────────────────────────────────────────────────────┘ ║
║                                                                       ║
╠═══════════════════════════════════════════════════════════════════════╣
║  [Enter] Select Model  │  [Esc] Cancel                                ║
╚═══════════════════════════════════════════════════════════════════════╝
```

**Layout Notes**:
- Shows "Querying..." message while fetching from API
- Type-to-filter for quick search
- Scrollable list with current selection highlighted
- Currently configured model marked
- Cancel returns without changing selection

### 2.4 Ollama-Specific Configuration

```
╔═══════════════════════════════════════════════════════════════════════╗
║  Configure Ollama                                                     ║
║  Tab/Shift+Tab to navigate fields, Enter to edit                     ║
╠═══════════════════════════════════════════════════════════════════════╣
║                                                                       ║
║  [✓] Enable this backend                                              ║
║                                                                       ║
║  Connection Mode:                                                     ║
║    (•) Local instance (http://localhost:11434)                        ║
║    ( ) Remote API server                                              ║
║                                                                       ║
║  ┌─── Remote API Settings (disabled in Local mode) ─────────────────┐ ║
║  │                                                                   │ ║
║  │  Custom API URL: [                                              ] │ ║
║  │                                                                   │ ║
║  │  API Key: [                                                     ] │ ║
║  │           (optional, if remote server requires auth)             │ ║
║  │                                                                   │ ║
║  └───────────────────────────────────────────────────────────────────┘ ║
║                                                                       ║
║  Model: [deepseek-coder:latest                            ▼]          ║
║         Press Enter to query and select from available models         ║
║                                                                       ║
║  ┌─────────────────────────────────────────────────────────────────┐ ║
║  │ Connection Test                                                 │ ║
║  │ Status: ✓ Local Ollama running (v0.5.2)                         │ ║
║  │ Models found: 8                                                 │ ║
║  │ [Test Connection]  [Pull New Model]                             │ ║
║  └─────────────────────────────────────────────────────────────────┘ ║
║                                                                       ║
╠═══════════════════════════════════════════════════════════════════════╣
║  [R] Reset to Defaults  │  [Esc] Back to Main Menu                   ║
╚═══════════════════════════════════════════════════════════════════════╝
```

**Layout Notes**:
- Radio selection between Local and Remote modes
- Remote settings section grayed/disabled when Local mode selected
- Additional "Pull New Model" button for Ollama-specific functionality
- Test connection verifies local daemon or remote endpoint

### 2.5 Text Input Dialog (API Key Entry)

```
╔═══════════════════════════════════════════════════════════════════════╗
║  Enter API Key for OpenAI API                                         ║
╠═══════════════════════════════════════════════════════════════════════╣
║                                                                       ║
║  API Key: [sk-proj-***********************************************]   ║
║                                                                       ║
║  The key will be stored securely in ~/.blueprint/config.json          ║
║  and will only be displayed masked (last 4 chars visible).            ║
║                                                                       ║
║  Tips:                                                                ║
║  • Keys typically start with 'sk-' for OpenAI                         ║
║  • Paste from clipboard: Ctrl+V (or Cmd+V on macOS)                   ║
║  • Clear field: Ctrl+U                                                ║
║                                                                       ║
╠═══════════════════════════════════════════════════════════════════════╣
║  [Enter] Save  │  [Esc] Cancel  │  [Ctrl+X] Clear                     ║
╚═══════════════════════════════════════════════════════════════════════╝
```

**Layout Notes**:
- Live masking of input (shows `*` after first 7 chars, last 4 visible)
- Helpful context about storage location and format
- Provider-specific hints about key format
- Clear action to remove existing key

### 2.6 Confirmation Dialog (Save/Discard)

```
╔═══════════════════════════════════════════════════════════════════════╗
║  Unsaved Changes                                                      ║
╠═══════════════════════════════════════════════════════════════════════╣
║                                                                       ║
║  You have unsaved configuration changes:                              ║
║                                                                       ║
║    • OpenAI: API key updated                                          ║
║    • Gemini: Enabled, model changed to gemini-2.5-flash               ║
║    • Ollama: Switched to Remote mode                                  ║
║                                                                       ║
║  What would you like to do?                                           ║
║                                                                       ║
║    > [Save All Changes]                                               ║
║      [Discard Changes]                                                ║
║      [Cancel (return to menu)]                                        ║
║                                                                       ║
╠═══════════════════════════════════════════════════════════════════════╣
║  ↑/↓ to select, Enter to confirm                                      ║
╚═══════════════════════════════════════════════════════════════════════╝
```

**Layout Notes**:
- Summary of pending changes by backend
- Three clear options: save, discard, cancel
- Default selection on "Save All"

---

## 3. Detailed Behavior & Interaction Flows

### 3.1 Startup Sequence

1. **Load Configuration**: Read `~/.blueprint/config.json` (global config)
2. **Parse Backend States**: Extract enabled/disabled status, API keys, endpoints, models for all 4 backends
3. **Render Main Menu**: Display current configuration state
4. **Highlight First Backend**: Set initial cursor position

### 3.2 Backend Configuration Flow

**Entering Configuration View**:
1. User presses Enter on a backend in main menu
2. System loads current settings for that backend into a staging area
3. Renders backend-specific configuration screen
4. Sets focus on first editable field

**Editing Fields**:
- **Toggle Enable/Disable**: Space bar toggles checkbox
- **Text Inputs** (API key, URL): 
  - Enter opens text input dialog with current value pre-filled
  - User types or pastes new value
  - Enter saves to staging, Esc cancels
- **Radio Buttons** (Ollama mode, endpoint type):
  - Left/Right arrows change selection
  - Changes apply immediately to staging
- **Model Selection**:
  - Enter triggers model query (see 3.3)
  - Shows loading spinner while querying
  - Displays model picker dialog on success

**Exiting Configuration View**:
- Esc returns to main menu
- Changes remain in staging (not persisted until "Save All")
- Main menu updates to reflect staged changes

### 3.3 Model Selection Flow

**Trigger**: User presses Enter on Model field

**Process**:
1. **Validate Prerequisites**: Check if API key (for API backends) or endpoint (for Ollama) is configured
   - If missing: Show error dialog "Please configure API key/endpoint first", return to config view
2. **Query Backend**:
   ```python
   try:
       models = await query_models(backend, api_key, endpoint)
   except NetworkError:
       show_error("Could not connect to backend. Check your API key and endpoint.")
       return
   except AuthError:
       show_error("Authentication failed. Please check your API key.")
       return
   ```
3. **Display Model Picker**: Show scrollable list of models
4. **Filter Support**: User can type to filter list in real-time
5. **Selection**: Enter confirms, Esc cancels
6. **Update Staging**: Selected model stored in staging area

### 3.4 Connection Testing

**Available in**: Backend configuration views

**Trigger**: User activates "Test Connection" button

**Process**:
1. Show "Testing..." status in connection panel
2. Attempt to:
   - Connect to API endpoint with current credentials
   - Query models list
   - Parse response
3. **Success**: Display ✓ with model count, backend version (if available)
4. **Failure**: Display ✗ with error message:
   - "Connection refused" → Check if service is running (Ollama) or endpoint is correct
   - "401 Unauthorized" → Invalid API key
   - "404 Not Found" → Wrong endpoint URL
   - "Network timeout" → Firewall/network issue

### 3.5 Save & Persistence Flow

**Trigger**: User selects "Save All & Exit" from main menu or presses Ctrl+S

**Process**:
1. **Validate All Backends**: Ensure enabled backends have required fields:
   - API backends: API key required
   - Ollama Remote mode: URL required
   - All: Model selected
2. **Show Validation Errors**: If validation fails:
   ```
   Cannot save: The following backends have configuration errors:
   
   • Gemini API: Enabled but no API key set
   • Ollama: Remote mode selected but no URL provided
   
   Please fix these issues before saving.
   ```
3. **Write Configuration**:
   ```python
   config = {
       "backends": {
           "openai": {
               "enabled": True,
               "api_key": encrypt(staged_openai_key),
               "endpoint": "https://api.openai.com/v1",
               "model": "gpt-4o-2024-11-20"
           },
           # ... other backends
       },
       "metadata": {
           "last_updated": datetime.now().isoformat(),
           "version": "1.0"
       }
   }
   write_json("~/.blueprint/config.json", config)
   ```
4. **Confirm & Exit**: Show success message "Configuration saved successfully" and exit

### 3.6 Reset to Defaults

**Trigger**: User presses Ctrl+R in backend configuration view, or selects "Reset to Defaults"

**Behavior**:
1. Show confirmation dialog:
   ```
   Reset OpenAI API to defaults?
   
   This will:
   • Clear API key
   • Reset endpoint to default
   • Clear model selection
   • Disable this backend
   
   [Reset]  [Cancel]
   ```
2. If confirmed, reset staging area for this backend to:
   ```python
   default_config = {
       "enabled": False,
       "api_key": None,
       "endpoint": DEFAULT_ENDPOINTS[backend],
       "model": None
   }
   ```
3. Re-render configuration view with defaults

---

## 4. Implementation Pseudocode

### 4.1 Technology Choice: `prompt_toolkit`

**Rationale**: 
- Cross-platform (Windows, macOS, Linux)
- Rich input handling (arrow keys, text fields, key bindings)
- Built-in widgets (menus, radio buttons, checkboxes, text inputs)
- Async support for API queries
- Active maintenance and good documentation

**Alternative**: `curses` (lower-level, more control but more complexity), `textual` (newer, rich widgets)

### 4.2 Core Data Structures

```python
from dataclasses import dataclass, field
from typing import Optional, Literal
from enum import Enum

class BackendType(Enum):
    OPENAI = "openai"
    GEMINI = "gemini"
    OLLAMA = "ollama"
    CLAUDE = "claude"

class OllamaMode(Enum):
    LOCAL = "local"
    REMOTE = "remote"

@dataclass
class BackendConfig:
    """Configuration for a single backend."""
    type: BackendType
    enabled: bool = False
    api_key: Optional[str] = None
    endpoint: Optional[str] = None
    model: Optional[str] = None
    
    # Ollama-specific
    ollama_mode: OllamaMode = OllamaMode.LOCAL
    
    def is_valid(self) -> tuple[bool, Optional[str]]:
        """Validate configuration. Returns (is_valid, error_message)."""
        if not self.enabled:
            return (True, None)
        
        if self.type == BackendType.OLLAMA:
            if self.ollama_mode == OllamaMode.REMOTE:
                if not self.endpoint:
                    return (False, "Remote mode requires endpoint URL")
        else:  # API backends
            if not self.api_key:
                return (False, "API key required for enabled backend")
        
        if not self.model:
            return (False, "Model must be selected")
        
        return (True, None)

@dataclass
class AppState:
    """Global application state."""
    # Current configuration (staging area)
    backends: dict[BackendType, BackendConfig] = field(default_factory=dict)
    
    # Original configuration (for detecting changes)
    original_backends: dict[BackendType, BackendConfig] = field(default_factory=dict)
    
    # UI state
    current_view: Literal["main_menu", "backend_config", "model_picker"] = "main_menu"
    selected_backend: Optional[BackendType] = None
    has_unsaved_changes: bool = False
    
    def detect_changes(self) -> list[str]:
        """Return list of change descriptions."""
        changes = []
        for backend_type, config in self.backends.items():
            original = self.original_backends[backend_type]
            if config != original:
                change_parts = []
                if config.enabled != original.enabled:
                    change_parts.append("Enabled" if config.enabled else "Disabled")
                if config.model != original.model:
                    change_parts.append(f"Model changed to {config.model}")
                if config.api_key != original.api_key:
                    change_parts.append("API key updated")
                
                if change_parts:
                    changes.append(f"{backend_type.value}: {', '.join(change_parts)}")
        return changes
```

### 4.3 Backend API Querying

```python
import httpx
from typing import Protocol

class BackendClient(Protocol):
    """Protocol for backend API clients."""
    async def list_models(self) -> list[str]:
        """Query available models from the backend."""
        ...
    
    async def test_connection(self) -> tuple[bool, str]:
        """Test connection. Returns (success, message)."""
        ...

class OpenAIClient:
    def __init__(self, api_key: str, endpoint: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.endpoint = endpoint
    
    async def list_models(self) -> list[str]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.endpoint}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            # Filter to chat-compatible models
            return [m["id"] for m in data["data"] if "gpt" in m["id"]]
    
    async def test_connection(self) -> tuple[bool, str]:
        try:
            models = await self.list_models()
            return (True, f"Connected successfully, {len(models)} models found")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return (False, "Authentication failed: Invalid API key")
            elif e.response.status_code == 404:
                return (False, "Endpoint not found: Check your API URL")
            else:
                return (False, f"HTTP {e.response.status_code}: {e.response.text[:100]}")
        except httpx.ConnectError:
            return (False, "Connection refused: Check endpoint URL and network")
        except httpx.TimeoutException:
            return (False, "Request timed out: Network or server issue")
        except Exception as e:
            return (False, f"Unexpected error: {str(e)}")

class GeminiClient:
    def __init__(self, api_key: str, endpoint: str = "https://generativelanguage.googleapis.com/v1beta"):
        self.api_key = api_key
        self.endpoint = endpoint
    
    async def list_models(self) -> list[str]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.endpoint}/models",
                params={"key": self.api_key},
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            return [m["name"].replace("models/", "") for m in data.get("models", [])]
    
    async def test_connection(self) -> tuple[bool, str]:
        try:
            models = await self.list_models()
            return (True, f"Connected successfully, {len(models)} models found")
        except Exception as e:
            return (False, f"Connection failed: {str(e)}")

class OllamaClient:
    def __init__(self, endpoint: str = "http://localhost:11434", api_key: Optional[str] = None):
        self.endpoint = endpoint
        self.api_key = api_key
    
    async def list_models(self) -> list[str]:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            response = await client.get(
                f"{self.endpoint}/api/tags",
                headers=headers,
                timeout=5.0
            )
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
    
    async def test_connection(self) -> tuple[bool, str]:
        try:
            async with httpx.AsyncClient() as client:
                # Try version endpoint first
                response = await client.get(f"{self.endpoint}/api/version", timeout=5.0)
                version = response.json().get("version", "unknown")
                
                models = await self.list_models()
                return (True, f"Ollama v{version} running, {len(models)} models available")
        except httpx.ConnectError:
            return (False, "Cannot connect: Is Ollama running?")
        except Exception as e:
            return (False, f"Connection failed: {str(e)}")

class ClaudeClient:
    def __init__(self, api_key: str, endpoint: str = "https://api.anthropic.com"):
        self.api_key = api_key
        self.endpoint = endpoint
    
    async def list_models(self) -> list[str]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.endpoint}/v1/models",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01"
                },
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            return [m["id"] for m in data.get("data", [])]
    
    async def test_connection(self) -> tuple[bool, str]:
        try:
            models = await self.list_models()
            return (True, f"Connected successfully, {len(models)} models found")
        except Exception as e:
            return (False, f"Connection failed: {str(e)}")

def get_client(config: BackendConfig) -> BackendClient:
    """Factory function to create appropriate client."""
    if config.type == BackendType.OPENAI:
        return OpenAIClient(config.api_key, config.endpoint or "https://api.openai.com/v1")
    elif config.type == BackendType.GEMINI:
        return GeminiClient(config.api_key, config.endpoint or "https://generativelanguage.googleapis.com/v1beta")
    elif config.type == BackendType.OLLAMA:
        endpoint = config.endpoint if config.ollama_mode == OllamaMode.REMOTE else "http://localhost:11434"
        return OllamaClient(endpoint, config.api_key if config.ollama_mode == OllamaMode.REMOTE else None)
    elif config.type == BackendType.CLAUDE:
        return ClaudeClient(config.api_key, config.endpoint or "https://api.anthropic.com")
    else:
        raise ValueError(f"Unknown backend type: {config.type}")
```

### 4.4 Configuration Persistence

```python
import json
from pathlib import Path
from cryptography.fernet import Fernet
from typing import Optional
from datetime import datetime

class ConfigManager:
    """Handles reading/writing configuration with encryption."""
    
    def __init__(self, config_path: Path = Path.home() / ".blueprint" / "config.json"):
        self.config_path = config_path
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Encryption key stored separately (or derive from machine ID)
        self.key_path = config_path.parent / ".key"
        self.cipher = self._init_cipher()
    
    def _init_cipher(self) -> Fernet:
        """Initialize encryption cipher."""
        if self.key_path.exists():
            key = self.key_path.read_bytes()
        else:
            key = Fernet.generate_key()
            self.key_path.write_bytes(key)
            self.key_path.chmod(0o600)  # Read/write for owner only
        return Fernet(key)
    
    def _encrypt(self, value: str) -> str:
        """Encrypt sensitive value."""
        return self.cipher.encrypt(value.encode()).decode()
    
    def _decrypt(self, value: str) -> str:
        """Decrypt sensitive value."""
        return self.cipher.decrypt(value.encode()).decode()
    
    def load(self) -> dict[BackendType, BackendConfig]:
        """Load configuration from disk."""
        if not self.config_path.exists():
            return self._get_defaults()
        
        try:
            data = json.loads(self.config_path.read_text())
            backends = {}
            
            for backend_name, backend_data in data.get("backends", {}).items():
                backend_type = BackendType(backend_name)
                
                # Decrypt API key if present
                api_key = backend_data.get("api_key")
                if api_key:
                    try:
                        api_key = self._decrypt(api_key)
                    except Exception:
                        api_key = None  # Corrupted or invalid encryption
                
                backends[backend_type] = BackendConfig(
                    type=backend_type,
                    enabled=backend_data.get("enabled", False),
                    api_key=api_key,
                    endpoint=backend_data.get("endpoint"),
                    model=backend_data.get("model"),
                    ollama_mode=OllamaMode(backend_data.get("ollama_mode", "local")) if backend_type == BackendType.OLLAMA else OllamaMode.LOCAL
                )
            
            # Ensure all backends are present
            for backend_type in BackendType:
                if backend_type not in backends:
                    backends[backend_type] = self._get_default_backend(backend_type)
            
            return backends
        except Exception as e:
            print(f"Warning: Could not load config: {e}")
            return self._get_defaults()
    
    def save(self, backends: dict[BackendType, BackendConfig]) -> None:
        """Save configuration to disk."""
        data = {
            "backends": {},
            "metadata": {
                "last_updated": datetime.now().isoformat(),
                "version": "1.0"
            }
        }
        
        for backend_type, config in backends.items():
            # Encrypt API key
            api_key = self._encrypt(config.api_key) if config.api_key else None
            
            data["backends"][backend_type.value] = {
                "enabled": config.enabled,
                "api_key": api_key,
                "endpoint": config.endpoint,
                "model": config.model,
            }
            
            if backend_type == BackendType.OLLAMA:
                data["backends"][backend_type.value]["ollama_mode"] = config.ollama_mode.value
        
        # Atomic write: write to temp file, then rename
        temp_path = self.config_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(data, indent=2))
        temp_path.replace(self.config_path)
        self.config_path.chmod(0o600)  # Read/write for owner only
    
    def _get_defaults(self) -> dict[BackendType, BackendConfig]:
        """Get default configuration for all backends."""
        return {backend_type: self._get_default_backend(backend_type) for backend_type in BackendType}
    
    def _get_default_backend(self, backend_type: BackendType) -> BackendConfig:
        """Get default configuration for a specific backend."""
        defaults = {
            BackendType.OPENAI: BackendConfig(
                type=BackendType.OPENAI,
                endpoint="https://api.openai.com/v1"
            ),
            BackendType.GEMINI: BackendConfig(
                type=BackendType.GEMINI,
                endpoint="https://generativelanguage.googleapis.com/v1beta"
            ),
            BackendType.OLLAMA: BackendConfig(
                type=BackendType.OLLAMA,
                ollama_mode=OllamaMode.LOCAL,
                endpoint="http://localhost:11434"
            ),
            BackendType.CLAUDE: BackendConfig(
                type=BackendType.CLAUDE,
                endpoint="https://api.anthropic.com"
            ),
        }
        return defaults[backend_type]
```

### 4.5 Main Application (prompt_toolkit)

```python
from prompt_toolkit import Application
from prompt_toolkit.layout import Layout, HSplit, VSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.widgets import RadioList, Button, TextArea, Frame, Label, Dialog
from prompt_toolkit.formatted_text import HTML
import asyncio

class LLMConfigApp:
    """Main application controller."""
    
    def __init__(self):
        self.state = AppState()
        self.config_manager = ConfigManager()
        self.kb = KeyBindings()
        self._setup_keybindings()
        
        # Load configuration
        self.state.backends = self.config_manager.load()
        self.state.original_backends = {k: v.__class__(**v.__dict__) for k, v in self.state.backends.items()}  # Deep copy
    
    def _setup_keybindings(self):
        """Setup global keybindings."""
        
        @self.kb.add('escape')
        def _(event):
            """Go back or show exit confirmation."""
            if self.state.current_view == "main_menu":
                if self.state.has_unsaved_changes:
                    self._show_save_dialog()
                else:
                    event.app.exit()
            else:
                self.state.current_view = "main_menu"
                self._refresh_layout()
        
        @self.kb.add('c-s')
        def _(event):
            """Quick save from main menu."""
            if self.state.current_view == "main_menu":
                self._save_and_exit()
        
        @self.kb.add('c-c')
        def _(event):
            """Force exit without saving."""
            event.app.exit()
        
        @self.kb.add('c-r')
        def _(event):
            """Reset current backend to defaults."""
            if self.state.current_view == "backend_config" and self.state.selected_backend:
                self._reset_backend(self.state.selected_backend)
    
    def _render_main_menu(self) -> Layout:
        """Render the main backend selection menu."""
        backend_items = []
        
        for backend_type in BackendType:
            config = self.state.backends[backend_type]
            
            # Format status line
            enabled_icon = "✓" if config.enabled else " "
            model_text = config.model or "(not set)"
            
            if backend_type == BackendType.OLLAMA:
                mode_text = f"Mode: {config.ollama_mode.value.capitalize()}"
                endpoint_text = config.endpoint or "http://localhost:11434"
                key_text = mode_text
            else:
                key_status = self._format_key(config.api_key) if config.api_key else "(not set)"
                endpoint_text = config.endpoint or "(default)"
                key_text = f"API Key: {key_status}"
            
            item_html = f"""
            <b>[{enabled_icon}] {backend_type.value.upper()}</b>
                Model: {model_text}
                {key_text}
                Endpoint: {endpoint_text}
            """
            
            backend_items.append((backend_type, HTML(item_html)))
        
        radio_list = RadioList(values=backend_items)
        
        def on_select():
            self.state.selected_backend = radio_list.current_value
            self.state.current_view = "backend_config"
            self._refresh_layout()
        
        radio_list.control.key_bindings.add('enter')(lambda e: on_select())
        
        # Action buttons
        save_btn = Button("Save All & Exit", handler=self._save_and_exit)
        discard_btn = Button("Discard Changes", handler=self._discard_changes)
        
        return Layout(
            HSplit([
                Frame(
                    body=HSplit([
                        Label(HTML("<b>LLM Backend Configuration</b>")),
                        Label("Select a backend to configure (↑/↓), press Enter to edit"),
                        Window(height=1),  # Spacer
                        radio_list,
                    ]),
                    title="Configuration Menu"
                ),
                VSplit([save_btn, discard_btn]),
            ])
        )
    
    def _render_backend_config(self, backend_type: BackendType) -> Layout:
        """Render configuration view for a specific backend."""
        config = self.state.backends[backend_type]
        
        # Enable/disable checkbox
        enable_checkbox = CheckBox(text="Enable this backend", checked=config.enabled)
        
        # API key field (for API backends)
        if backend_type != BackendType.OLLAMA:
            key_display = self._format_key(config.api_key) if config.api_key else "(not set)"
            api_key_field = Button(
                f"API Key: {key_display}",
                handler=lambda: self._edit_api_key(backend_type)
            )
        
        # Endpoint selection
        if backend_type == BackendType.OLLAMA:
            mode_radio = RadioList(
                values=[
                    (OllamaMode.LOCAL, "Local instance (http://localhost:11434)"),
                    (OllamaMode.REMOTE, "Remote API server"),
                ],
                default=config.ollama_mode
            )
            
            endpoint_field = TextArea(
                text=config.endpoint or "",
                multiline=False,
                read_only=(config.ollama_mode == OllamaMode.LOCAL)
            )
        else:
            endpoint_field = TextArea(
                text=config.endpoint or "",
                multiline=False
            )
        
        # Model selection
        model_btn = Button(
            f"Model: {config.model or '(not set)'}",
            handler=lambda: asyncio.create_task(self._select_model(backend_type))
        )
        
        # Test connection
        test_btn = Button(
            "Test Connection",
            handler=lambda: asyncio.create_task(self._test_connection(backend_type))
        )
        
        # Assembly depends on backend type...
        # (This is simplified; full implementation would have conditional layouts)
        
        body = HSplit([
            Label(HTML(f"<b>Configure {backend_type.value.upper()}</b>")),
            enable_checkbox,
            api_key_field if backend_type != BackendType.OLLAMA else mode_radio,
            endpoint_field,
            model_btn,
            test_btn,
        ])
        
        return Layout(Frame(body=body, title=f"{backend_type.value.upper()} Configuration"))
    
    async def _select_model(self, backend_type: BackendType):
        """Show model picker dialog."""
        config = self.state.backends[backend_type]
        
        # Validate prerequisites
        if backend_type != BackendType.OLLAMA and not config.api_key:
            self._show_error("Please configure API key first")
            return
        
        # Query models
        try:
            client = get_client(config)
            models = await client.list_models()
            
            if not models:
                self._show_error("No models available from this backend")
                return
            
            # Show picker (simplified; would use RadioList + filter)
            selected_model = await self._show_model_picker(models, config.model)
            
            if selected_model:
                config.model = selected_model
                self.state.has_unsaved_changes = True
                self._refresh_layout()
                
        except Exception as e:
            self._show_error(f"Could not query models: {str(e)}")
    
    async def _test_connection(self, backend_type: BackendType):
        """Test connection to backend."""
        config = self.state.backends[backend_type]
        
        try:
            client = get_client(config)
            success, message = await client.test_connection()
            
            if success:
                self._show_info(f"✓ {message}")
            else:
                self._show_error(f"✗ {message}")
        except Exception as e:
            self._show_error(f"Test failed: {str(e)}")
    
    def _save_and_exit(self):
        """Validate, save, and exit."""
        # Validate all enabled backends
        errors = []
        for backend_type, config in self.state.backends.items():
            is_valid, error = config.is_valid()
            if not is_valid:
                errors.append(f"{backend_type.value}: {error}")
        
        if errors:
            self._show_error("Cannot save:\n\n" + "\n".join(errors))
            return
        
        # Save
        try:
            self.config_manager.save(self.state.backends)
            # Exit application
            # (In prompt_toolkit: get_app().exit())
        except Exception as e:
            self._show_error(f"Could not save configuration: {str(e)}")
    
    def _discard_changes(self):
        """Discard changes and exit."""
        if self.state.has_unsaved_changes:
            # Show confirmation dialog
            # If confirmed, exit without saving
            pass
    
    def _format_key(self, api_key: Optional[str]) -> str:
        """Format API key for display (masked with last 4 chars)."""
        if not api_key or len(api_key) < 8:
            return "****"
        return f"{'*' * (len(api_key) - 4)}{api_key[-4:]}"
    
    def run(self):
        """Run the application."""
        app = Application(
            layout=self._render_main_menu(),
            key_bindings=self.kb,
            full_screen=True,
            mouse_support=True
        )
        app.run()

def main():
    """Entry point."""
    app = LLMConfigApp()
    app.run()

if __name__ == "__main__":
    main()
```

---

## 5. Edge Cases & Failure Modes

### 5.1 Network & API Failures

| Scenario | Behavior |
|----------|----------|
| **Backend unreachable** | Show error dialog: "Cannot connect to {backend}. Check endpoint and network." Allow user to retry or continue editing. |
| **Invalid API key** | Show error: "Authentication failed. Please check your API key." Highlight the API key field for correction. |
| **Model list empty** | Show warning: "No models available. The backend may not support model listing or requires special permissions." Allow manual model entry. |
| **Timeout during query** | Show error after 10s: "Request timed out. Try again or check network." |
| **Rate limiting (429)** | Show error: "Rate limit exceeded. Please wait and try again." |

### 5.2 User Input Errors

| Scenario | Behavior |
|----------|----------|
| **Invalid URL format** | Validate on blur/save: "Invalid URL format. Please enter a valid HTTP(S) URL." |
| **Empty required fields** | Prevent saving with validation message (see 3.5). Don't allow silent failures. |
| **Paste malformed key** | Accept any input, validate on test/save. Show masked preview. |
| **Model not in list** | If user manually types model name, accept it but warn: "Model not found in list. It may not exist." |

### 5.3 Configuration File Issues

| Scenario | Behavior |
|----------|----------|
| **Corrupted config.json** | On load error: show warning, load defaults, preserve corrupted file as `config.json.bak` |
| **Permission denied writing** | On save error: "Cannot write to ~/.blueprint/config.json. Check file permissions." |
| **Encryption key lost** | If decryption fails: warn user, treat keys as unset, prompt to re-enter |
| **Concurrent modification** | Not handled in v1. Future: file locking or timestamp checking. |

### 5.4 Terminal & Display Issues

| Scenario | Behavior |
|----------|----------|
| **Terminal too small** | Detect minimum size (80x24). If smaller: show message "Terminal too small. Resize to at least 80x24." |
| **Screen resize during use** | `prompt_toolkit` handles gracefully with re-layout. Ensure no crashes. |
| **No color support** | Fallback to plain text with symbols (✓/✗) instead of colors |
| **SSH/remote terminal** | Should work normally. Test with TERM=xterm-256color |

### 5.5 Backend-Specific Issues

**Ollama**:
- **Daemon not running**: Test connection shows clear error; suggest `ollama serve` command
- **No models pulled**: On empty list, provide button "Pull New Model" that guides user to `ollama pull <model>`

**OpenAI/Gemini/Claude**:
- **Account suspended**: API returns 403 → show message with link to provider support
- **Billing issue**: API returns 402 → "Payment required. Check your billing status at {provider URL}"

---

## 6. Configuration Persistence Details

### 6.1 File Location & Structure

**Path**: `~/.blueprint/config.json` (global, not per-project)

**Structure**:
```json
{
  "backends": {
    "openai": {
      "enabled": true,
      "api_key": "gAAAAABh...[encrypted]",
      "endpoint": "https://api.openai.com/v1",
      "model": "gpt-4o-2024-11-20"
    },
    "gemini": {
      "enabled": false,
      "api_key": null,
      "endpoint": null,
      "model": null
    },
    "ollama": {
      "enabled": true,
      "api_key": null,
      "endpoint": "http://localhost:11434",
      "model": "deepseek-coder:latest",
      "ollama_mode": "local"
    },
    "claude": {
      "enabled": true,
      "api_key": "gAAAAABh...[encrypted]",
      "endpoint": "https://api.anthropic.com",
      "model": "claude-sonnet-4.5-20250514"
    }
  },
  "metadata": {
    "last_updated": "2025-12-08T21:15:00Z",
    "version": "1.0"
  }
}
```

**Encryption**:
- API keys encrypted using `cryptography.fernet`
- Encryption key stored in `~/.blueprint/.key` (600 permissions)
- Key derived from Fernet.generate_key() on first run
- Alternative: platform keyring (macOS Keychain, Windows Credential Manager, Linux Secret Service)

### 6.2 Write Strategy

1. **Atomic writes**: Write to `config.json.tmp`, then rename to `config.json`
2. **Backup on corruption**: If load fails, copy to `config.json.bak` before overwriting
3. **Validation before write**: Ensure JSON is well-formed and all required fields are present
4. **Permissions**: Set file to 600 (owner read/write only) after creation

### 6.3 Reload Behavior

- **On startup**: Load from disk, populate UI
- **Manual reload**: Not implemented in v1 (single-user assumed)
- **External edits**: Not detected automatically (future: file watcher or timestamp check)

### 6.4 Migration & Versioning

- **Version field**: `metadata.version` tracks config schema version
- **Migration on load**: If version mismatch, run migrations to upgrade schema
- **Example migration**: v1.0 → v1.1 adds new backend, preserves existing config

---

## 7. User Experience Considerations

### 7.1 Visual Feedback

- **Loading states**: Show spinners for async operations (querying models, testing connection)
- **Success/error messages**: Use color coding (green ✓ for success, red ✗ for errors)
- **Change indicators**: Mark fields with `*` if modified since last save
- **Progress bars**: For long operations (e.g., pulling Ollama models)

### 7.2 Help & Documentation

- **Inline help**: Show tooltips/hints for each field (e.g., "Keys start with 'sk-' for OpenAI")
- **Help key (F1)**: Show context-sensitive help dialog
- **Examples**: Provide sample endpoints, model names in help text

### 7.3 Accessibility

- **Keyboard-only navigation**: No mouse required (though mouse support nice-to-have)
- **Clear visual hierarchy**: Use frames, spacing, and headers to group related fields
- **Color-blind friendly**: Don't rely solely on color; use symbols (✓/✗) and text

### 7.4 Performance

- **Lazy loading**: Don't query all backends on startup; only when user enters config view
- **Caching**: Cache model lists for 5 minutes to avoid repeated queries
- **Async operations**: Use async/await for all network calls; don't block UI
- **Cancellation**: Allow user to cancel long-running operations (Esc during query)

### 7.5 Security

- **Masked input**: Show `*` for API keys during entry
- **No logging**: Never log API keys, even in debug mode
- **Secure storage**: Encrypt keys at rest, use platform keyring if available
- **Clear clipboard**: If pasting keys, don't leave them in clipboard history

---

## 8. Implementation Recommendations

### 8.1 Libraries

**Primary**: `prompt_toolkit` (v3.0+)
- Rich widget library
- Async support
- Cross-platform
- Active development

**Alternative**: `textual` (by Textualize)
- Modern, declarative approach
- Built-in widgets (DataTable, Tree, etc.)
- CSS-like styling
- Good for complex layouts

**For encryption**: `cryptography` (Fernet symmetric encryption)

**For API calls**: `httpx` (async HTTP client)

### 8.2 Testing Strategy

**Unit tests**:
- Config loading/saving with various malformed inputs
- Encryption/decryption round-trips
- Validation logic for backend configs

**Integration tests**:
- Mock API endpoints to test client behavior
- Test error handling (404, 401, timeouts)

**Manual testing**:
- Test on different terminal sizes
- Test with different TERM values
- Test SSH/remote scenarios
- Test with each backend (use test API keys)

### 8.3 Development Phases

**Phase 1: Core infrastructure**
- Config data structures
- Config manager (load/save/encrypt)
- Default backend configs

**Phase 2: API clients**
- Implement backend clients for OpenAI, Gemini, Ollama, Claude
- Test connection methods
- Model listing

**Phase 3: Basic UI**
- Main menu with backend list
- Backend config view (text fields only)
- Save/discard flow

**Phase 4: Enhanced UI**
- Model picker dialog
- Connection testing
- Validation and error handling

**Phase 5: Polish**
- Help system
- Inline documentation
- Visual refinements
- Performance optimization

---

## 9. CLI Integration

The config interface should be invokable via:

```bash
# Launch interactive config
blueprint config

# Non-interactive: set API key
blueprint config set openai.api_key sk-proj-...

# Non-interactive: enable backend
blueprint config set gemini.enabled true

# Non-interactive: set model
blueprint config set claude.model claude-sonnet-4.5-20250514

# Show current config (masked keys)
blueprint config show

# Reset backend to defaults
blueprint config reset ollama

# Validate config without saving
blueprint config validate
```

**Implementation**: Add subcommands to main CLI that either launch the TUI or manipulate config directly using ConfigManager.

---

## 10. Future Enhancements

### 10.1 Multi-Profile Support

Allow users to define named profiles (e.g., "work", "personal") with different backend configurations:

```bash
blueprint config --profile work
blueprint run --profile personal
```

### 10.2 Project-Level Overrides

Allow per-project config (`.blueprint/config.json`) that overrides global settings:

```json
{
  "backends": {
    "openai": {
      "model": "gpt-4o-mini"  // Override for this project only
    }
  }
}
```

### 10.3 Cost/Usage Display

Show estimated costs and usage stats in the config UI:

```
OpenAI API
  This month: 150K tokens, ~$0.45
  Model pricing: $0.003/1K tokens (input), $0.006/1K tokens (output)
```

### 10.4 Model Capabilities Matrix

Show which models support which features:

```
gpt-4o-2024-11-20
  ✓ Function calling
  ✓ JSON mode
  ✓ Vision
  Context: 128K tokens
  Output: 16K tokens max
```

### 10.5 Auto-Discovery

For Ollama: auto-detect running instances on localhost and common ports.

For cloud providers: integrate with provider CLIs to auto-import credentials (e.g., `gcloud auth print-access-token`).

### 10.6 Configuration Import/Export

Export config (with or without keys) to share with team:

```bash
blueprint config export --no-keys > team-config.json
blueprint config import team-config.json
```

---

## 11. Sample Session Walkthrough

```
User launches: $ blueprint config

┌─────────────────────────────────────────────────┐
│ LLM Backend Configuration                       │
│ Select a backend (↑/↓), Enter to edit          │
├─────────────────────────────────────────────────┤
│ > [✓] OpenAI API                                │
│      Model: gpt-4o-2024-11-20                   │
│      API Key: ********k3J2                      │
│ ...                                             │
└─────────────────────────────────────────────────┘

User presses ↓ twice, Enter on Gemini

┌─────────────────────────────────────────────────┐
│ Configure Gemini API                            │
├─────────────────────────────────────────────────┤
│ [✓] Enable this backend                         │
│                                                 │
│ API Key: [(not set)]  ← Press Enter to edit    │
│ ...                                             │
└─────────────────────────────────────────────────┘

User presses Enter on API Key field

┌─────────────────────────────────────────────────┐
│ Enter API Key for Gemini API                    │
├─────────────────────────────────────────────────┤
│ API Key: [AIza***************************xyZ]  │
│                                                 │
│ Paste from clipboard: Ctrl+V                    │
└─────────────────────────────────────────────────┘

User pastes key, presses Enter

[System validates format, saves to staging, returns to config view]

┌─────────────────────────────────────────────────┐
│ Configure Gemini API                            │
├─────────────────────────────────────────────────┤
│ [✓] Enable this backend                         │
│                                                 │
│ API Key: ********xyZ  ✓                         │
│                                                 │
│ Model: [(not set)]  ← Press Enter to select    │
│ ...                                             │
└─────────────────────────────────────────────────┘

User presses Enter on Model field

[System queries Gemini API...]

┌─────────────────────────────────────────────────┐
│ Select Model for Gemini API                     │
│ Querying available models... ✓ Found 8          │
├─────────────────────────────────────────────────┤
│ > gemini-2.5-flash                              │
│   gemini-2.5-pro                                │
│   gemini-2.0-flash                              │
│   ...                                           │
└─────────────────────────────────────────────────┘

User selects gemini-2.5-flash, presses Enter

[Returns to config view with model set]

User presses Esc to return to main menu

┌─────────────────────────────────────────────────┐
│ LLM Backend Configuration                       │
│ Select a backend (↑/↓), Enter to edit          │
├─────────────────────────────────────────────────┤
│   [✓] OpenAI API                                │
│      Model: gpt-4o-2024-11-20                   │
│      API Key: ********k3J2                      │
│                                                 │
│ > [✓] Gemini API  *                             │
│      Model: gemini-2.5-flash  *                 │
│      API Key: ********xyZ  *                    │
│   ...                                           │
├─────────────────────────────────────────────────┤
│ [S] Save All & Exit  [D] Discard Changes        │
└─────────────────────────────────────────────────┘

Note: * indicates unsaved changes

User presses S to save

[System validates all configs, saves to disk]

┌─────────────────────────────────────────────────┐
│ Configuration saved successfully!               │
│                                                 │
│ Changes:                                        │
│ • Gemini API: Enabled, model set to            │
│   gemini-2.5-flash, API key configured         │
│                                                 │
│ Press any key to exit                           │
└─────────────────────────────────────────────────┘

User presses any key, returns to shell
```

---

## 12. Summary

This design provides:

✅ **Simple, keyboard-driven interface** for configuring 4 LLM backends  
✅ **Secure credential storage** with encryption  
✅ **Live model discovery** from each backend  
✅ **Special handling for Ollama** (local vs. remote modes)  
✅ **Robust error handling** for network/API failures  
✅ **Clear visual feedback** for all operations  
✅ **Global configuration** persisted to `~/.blueprint/config.json`  
✅ **Extensible architecture** for future enhancements (profiles, project overrides, usage tracking)  

**Next steps**: Implement in phases (see 8.3), starting with core config management and API clients, then building the TUI layer with `prompt_toolkit`.
