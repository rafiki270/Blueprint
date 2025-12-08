# Blueprint TUI Design Specification

## Overview

Blueprint's interactive mode uses a multi-panel TUI (Terminal User Interface) built with Textual. The interface is designed for clarity, efficiency, and real-time feedback during multi-LLM orchestration.

## Design Principles

1. **Information Density**: Show all critical info without overwhelming
2. **Live Updates**: Real-time streaming output from LLM processes
3. **Clear Status**: Always know what's happening and where you are
4. **Quick Actions**: Common operations accessible via commands and keybinds
5. **Non-Blocking**: UI remains responsive during long operations
6. **Professional**: Clean, terminal-native aesthetic

---

## Layout Structure

### Full Screen Layout (3x3 Grid)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Blueprint - Feature: user-authentication                            [Help F1]│
├─────────────────┬───────────────────────────────────────────────────────────┤
│                 │                                                             │
│   TASK LIST     │              OUTPUT STREAM                                 │
│   (Left Panel)  │              (Top Right Panel)                             │
│                 │                                                             │
│   ○ task-1      │  [09:23:45] Starting task: Implement user login            │
│   ◐ task-2 ←    │  [09:23:46] Using DeepSeek for code generation...         │
│   ○ task-3      │  [09:23:47] Generating authentication module...           │
│   ● task-4      │                                                             │
│   ○ task-5      │  ```python                                                 │
│   ⚠ task-6      │  class AuthService:                                        │
│   ○ task-7      │      def __init__(self):                                   │
│   ○ task-8      │          self.sessions = {}                                │
│                 │  ```                                                        │
│   8 total       │                                                             │
│   2 completed   │  ✓ Code generated (245 lines)                             │
│   1 in progress │  [09:24:12] Running Codex review...                       │
│                 │                                                             │
├─────────────────┼─────────────────────────────────────────────────────────┤
│                 │                                                             │
│                 │              CONTEXT / SPEC                                │
│                 │              (Bottom Right Panel)                          │
│                 │                                                             │
│                 │  Current Task: Implement user login                        │
│                 │  Type: code                                                │
│                 │  Status: in-progress                                       │
│                 │                                                             │
│                 │  Description:                                              │
│                 │  Create a user authentication service that handles         │
│                 │  login, logout, and session management. Should use         │
│                 │  JWT tokens and bcrypt for password hashing.               │
│                 │                                                             │
├─────────────────┴─────────────────────────────────────────────────────────┤
│ blueprint> /start                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
│ Ctrl+S Stop | Ctrl+U Usage | F1 Help | Ctrl+C Exit                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Panel Details

### 1. Header Bar (Top)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Blueprint - Feature: user-authentication                            [Help F1]│
└─────────────────────────────────────────────────────────────────────────────┘
```

**Purpose**: Show context and quick help access

**Contents**:
- App name: "Blueprint"
- Current feature name
- Quick help indicator

**Style**:
- Background: Blue (#0066CC)
- Text: White
- Bold font

---

### 2. Task List Panel (Left, spans 2 rows)

```
┌─────────────────┐
│   Tasks         │
├─────────────────┤
│ ○ [task-1] Impl │
│ ◐ [task-2] Add  │  ← Current task (highlighted)
│ ○ [task-3] Crea │
│ ● [task-4] Revi │  ← Completed (green)
│ ○ [task-5] Writ │
│ ⚠ [task-6] Fix  │  ← Blocked (red)
│ ○ [task-7] Test │
│ ○ [task-8] Depl │
│                 │
│ 8 total         │
│ 2 completed     │
│ 1 in progress   │
│ 1 blocked       │
│ 4 pending       │
└─────────────────┘
```

**Purpose**: Show all tasks at a glance with status

**Visual Elements**:

**Status Symbols**:
- `○` Pending (gray)
- `◐` In Progress (yellow, with spinner animation)
- `●` Completed (green)
- `⚠` Blocked (red)
- `⊘` Skipped (dim gray)

**Current Task Indicator**:
- Arrow `←` or highlight background
- Bold text
- Underline

**Task Format**:
```
[symbol] [task-id] Title (truncated to fit)
```

**Summary Footer**:
Shows counts at bottom:
```
8 total
2 completed
1 in progress
...
```

**Behavior**:
- Auto-scrolls to current task
- Clicking a task shows details in context panel
- Updates in real-time as tasks progress

**Colors**:
- Border: Cyan
- Pending: Dim white
- In Progress: Yellow (bright)
- Completed: Green
- Blocked: Red
- Skipped: Gray (dim)

---

### 3. Output Stream Panel (Top Right)

```
┌───────────────────────────────────────────────────────────┐
│   Output                                           [Clear] │
├───────────────────────────────────────────────────────────┤
│ [09:23:45] Starting task: Implement user login            │
│ [09:23:46] Using DeepSeek for code generation...          │
│ [09:23:47] ─────────────────────────────────────          │
│                                                            │
│ [09:23:48] Generating authentication module...            │
│                                                            │
│ ```python                                                  │
│ class AuthService:                                         │
│     def __init__(self):                                    │
│         self.sessions = {}                                 │
│                                                            │
│     def login(self, username: str, password: str):         │
│         # Hash password and verify                         │
│         hashed = bcrypt.hashpw(password.encode())          │
│         ...                                                │
│ ```                                                        │
│                                                            │
│ ✓ Code generated (245 lines)                              │
│ [09:24:12] Running Codex review...                        │
│ [09:24:15] Review: Code quality excellent                 │
│ ✓ Task completed                                           │
│                                                            │
│ █                                                          │  ← Auto-scroll indicator
└───────────────────────────────────────────────────────────┘
```

**Purpose**: Real-time streaming output from LLM processes

**Visual Elements**:

**Timestamps**: `[HH:MM:SS]` in dim gray

**Status Indicators**:
- `✓` Success (green)
- `✗` Error (red)
- `⚠` Warning (yellow)
- `ℹ` Info (blue)
- `▶` Starting (blue)
- `■` Stopped (gray)

**Content Types**:

1. **Log Messages**:
   ```
   [09:23:45] Starting task: Implement user login
   ```

2. **Code Blocks** (syntax highlighted):
   ```python
   class AuthService:
       def __init__(self):
           self.sessions = {}
   ```

3. **Section Dividers**:
   ```
   ─────────────────────────────────────
   ```

4. **Progress Indicators**:
   ```
   [████████░░] 80% Complete
   ```

5. **Model Output** (streamed line-by-line):
   ```
   Generating authentication logic...
   Adding password hashing...
   Implementing session management...
   ```

**Behavior**:
- Auto-scrolls to bottom as new content arrives
- Syntax highlighting for code blocks
- Preserve ANSI colors from LLM output
- Copy/paste support
- Search capability (Ctrl+F)

**Colors**:
- Border: Blue
- Timestamps: Dim gray
- Success: Green
- Error: Red
- Warning: Yellow
- Info: Cyan
- Code: Syntax highlighted (monokai theme)

---

### 4. Context Panel (Bottom Right)

```
┌───────────────────────────────────────────────────────────┐
│   Context                                     [Spec] [Task]│
├───────────────────────────────────────────────────────────┤
│ Current Task: Implement user login                         │
│ ──────────────────────────────────────────────────────────│
│ ID: task-2                                                 │
│ Type: code                                                 │
│ Status: in-progress                                        │
│ Model: DeepSeek                                            │
│                                                            │
│ Description:                                               │
│ Create a user authentication service that handles login,  │
│ logout, and session management. Should use JWT tokens     │
│ and bcrypt for password hashing.                           │
│                                                            │
│ Requirements:                                              │
│ • JWT token generation and validation                      │
│ • Password hashing with bcrypt                             │
│ • Session management                                       │
│ • Login/logout endpoints                                   │
│                                                            │
│ Dependencies:                                              │
│ • task-1 (Database models)                                 │
│                                                            │
│ ──────────────────────────────────────────────────────────│
│ Relevant Spec Section:                                     │
│                                                            │
│ ## Authentication                                          │
│ Users authenticate via username/password. System generates │
│ JWT tokens valid for 24 hours...                           │
│                                                            │
└───────────────────────────────────────────────────────────┘
```

**Purpose**: Show current task details and relevant spec sections

**Tab Views**:
- **[Task]** - Current task details
- **[Spec]** - Full specification viewer

**Content Sections**:

1. **Task Header**:
   - Title (bold)
   - ID, Type, Status, Model

2. **Description**:
   - Full task description
   - Formatted markdown

3. **Requirements** (if present):
   - Bullet list of specific requirements

4. **Dependencies** (if present):
   - Links to other tasks

5. **Spec Section** (if viewing spec):
   - Relevant markdown rendered
   - Scrollable
   - Search capability

**Behavior**:
- Updates when task changes
- Tabs switch between task and spec views
- Markdown rendering for rich text
- Scrollable for long content
- Links clickable to jump to related tasks

**Colors**:
- Border: Magenta
- Headers: Bold white
- Task ID: Cyan
- Status: Color-coded (same as task list)
- Markdown: Rendered with colors

---

### 5. Command Bar (Bottom)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ blueprint> /start task-3                                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Purpose**: Command input with history and autocomplete

**Visual Elements**:

**Prompt**: `blueprint>` in cyan

**Input Field**:
- White text
- Placeholder: "Enter command (type /help for commands)" in dim gray

**Autocomplete Popup** (appears above when typing):
```
╔═══════════════════╗
║ /start           ║  ← Current match
║ /stop            ║
║ /status          ║
╚═══════════════════╝
```

**Behavior**:
- Command history (↑/↓ arrows)
- Tab completion for commands
- Ctrl+C to clear input
- Enter to submit
- Shows autocomplete as you type
- Validates command syntax before submit

**Colors**:
- Background: Dark gray
- Prompt: Cyan
- Input text: White
- Placeholder: Dim gray
- Autocomplete: White on dark blue

---

### 6. Footer Bar (Bottom)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Ctrl+S Stop | Ctrl+U Usage | F1 Help | Ctrl+C Exit                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Purpose**: Quick reference for key bindings

**Content**:
- Most commonly used shortcuts
- Context-sensitive (changes based on state)

**States**:

**Idle State**:
```
F1 Help | Ctrl+U Usage | Ctrl+C Exit
```

**Task Running**:
```
Ctrl+S Stop | F1 Help | Ctrl+C Exit
```

**Error State**:
```
/correct to fix | F1 Help | Ctrl+C Exit
```

**Colors**:
- Background: Dark blue
- Text: White
- Keybinds: Bold cyan

---

## Modal Overlays

### Usage Dashboard Modal

```
                  ┌─────────────────────────────────────────┐
                  │  Usage Dashboard                   [X] │
                  ├─────────────────────────────────────────┤
                  │                                         │
                  │  Today's Usage                          │
                  │  ──────────────────────────────────     │
                  │  Claude Calls:        12                │
                  │  Estimated Tokens:    ~45,000           │
                  │                                         │
                  │  Gemini Input:        23,450 tokens     │
                  │  Gemini Output:       8,120 tokens      │
                  │                                         │
                  │  DeepSeek Calls:      8                 │
                  │  Codex Calls:         5                 │
                  │                                         │
                  │  ──────────────────────────────────     │
                  │  7-Day Trend                            │
                  │  ──────────────────────────────────     │
                  │  Model     Calls    Trend               │
                  │  ───────────────────────────            │
                  │  Claude      82     ↑ 15%               │
                  │  Gemini      156    ↓ 8%                │
                  │  DeepSeek    45     → 0%                │
                  │  Codex       38     ↑ 22%               │
                  │                                         │
                  │  ──────────────────────────────────     │
                  │  Suggestions                            │
                  │  ──────────────────────────────────     │
                  │  • High Gemini use - consider DeepSeek  │
                  │  • Ollama running efficiently           │
                  │                                         │
                  │             [Close]                     │
                  │                                         │
                  └─────────────────────────────────────────┘
```

**Trigger**: `/usage` command or Ctrl+U

**Behavior**:
- Centers on screen
- Semi-transparent background overlay
- Escape or click X to close
- Button focus with Tab

**Colors**:
- Border: Bright blue
- Background: Dark gray
- Headers: Bold white
- Numbers: Bright cyan
- Trends up: Green
- Trends down: Yellow
- Trends flat: Gray

### Help Modal

```
                  ┌─────────────────────────────────────────┐
                  │  Blueprint Commands               [X]  │
                  ├─────────────────────────────────────────┤
                  │                                         │
                  │  Task Management                        │
                  │  ──────────────────────────────────     │
                  │  /tasks        List all tasks           │
                  │  /done <id>    Mark task completed      │
                  │  /delete <id>  Delete task              │
                  │  /redo <id>    Mark incomplete          │
                  │  /missing      Show incomplete tasks    │
                  │  /next         Next task                │
                  │  /task <id>    Jump to task             │
                  │                                         │
                  │  Execution                              │
                  │  ──────────────────────────────────     │
                  │  /start        Start next task          │
                  │  /stop         Stop current (Ctrl+S)    │
                  │  /correct      Correction mode          │
                  │  /resume       Resume current           │
                  │                                         │
                  │  Other                                  │
                  │  ──────────────────────────────────     │
                  │  /usage        Usage stats (Ctrl+U)     │
                  │  /spec         View specification       │
                  │  /logs         View logs                │
                  │  /exit         Exit Blueprint           │
                  │                                         │
                  │             [Close]                     │
                  │                                         │
                  └─────────────────────────────────────────┘
```

**Trigger**: `/help` command or F1

**Behavior**:
- Centers on screen
- Scrollable for long content
- Grouped by category
- Syntax highlighting for commands

### Confirmation Modal

```
              ┌───────────────────────────────────────┐
              │  Confirm Action                      │
              ├───────────────────────────────────────┤
              │                                       │
              │  Delete task-3?                       │
              │                                       │
              │  This action cannot be undone.        │
              │                                       │
              │        [Cancel]  [Delete]             │
              │                                       │
              └───────────────────────────────────────┘
```

**Trigger**: Destructive operations (delete, exit with unsaved work)

**Behavior**:
- Modal dialog
- Cancel = default focus
- Enter confirms
- Escape cancels

---

## Visual Feedback

### Loading States

**Spinner Animation** (for in-progress tasks):
```
◐  Task running...
◓  Task running...
◑  Task running...
◒  Task running...
```

**Progress Bar** (when percentage known):
```
[████████░░] 80% Complete
```

**Streaming Indicator**:
```
▶ Streaming output...
```

### State Changes

**Task Status Change**:
```
Before: ○ [task-2] Implement login
After:  ◐ [task-2] Implement login  ← Animated transition
```

**Flash Highlight**:
- Brief yellow highlight on changes
- Fades to normal after 0.5s

### Errors

**Error Message in Output**:
```
✗ Error: Failed to execute task
  DeepSeek CLI not available
  Run 'ollama list' to verify installation
```

**Style**:
- Red text
- Indented details
- Actionable suggestions

---

## Color Palette

### Base Colors
```
Background:     #1E1E1E (dark gray)
Foreground:     #D4D4D4 (light gray)
Border:         #3C3C3C (medium gray)
```

### Semantic Colors
```
Success:        #00FF00 (green)
Error:          #FF0000 (red)
Warning:        #FFFF00 (yellow)
Info:           #00BFFF (cyan)
```

### Status Colors
```
Pending:        #808080 (gray)
In Progress:    #FFD700 (gold)
Completed:      #00FF00 (green)
Blocked:        #FF4500 (orange-red)
Skipped:        #696969 (dim gray)
```

### Accent Colors
```
Primary:        #0066CC (blue)
Secondary:      #9370DB (purple)
Highlight:      #FFD700 (gold)
```

### Syntax Highlighting (Monokai Theme)
```
Keyword:        #F92672 (pink)
String:         #E6DB74 (yellow)
Number:         #AE81FF (purple)
Comment:        #75715E (gray)
Function:       #A6E22E (green)
```

---

## Keyboard Shortcuts

### Global
```
Ctrl+C          Exit Blueprint
F1              Show help
Ctrl+U          Usage dashboard
Ctrl+L          Clear output
Ctrl+F          Search output
```

### Task Navigation
```
↑               Previous task in list
↓               Next task in list
Enter           Select task
Tab             Switch context panel tabs
```

### Execution Control
```
Ctrl+S          Stop current task
Ctrl+R          Resume/retry
Ctrl+N          Next task
```

### Command Bar
```
/               Focus command bar
↑               Previous command (history)
↓               Next command (history)
Tab             Autocomplete
Ctrl+K          Clear command
```

---

## Responsive Behavior

### Minimum Terminal Size
```
Width:  80 columns
Height: 24 rows
```

### Small Terminal (<100 cols)
- Task list narrows
- IDs hidden, only status symbols shown
- Truncate long titles with `...`

### Medium Terminal (100-120 cols)
- Standard layout
- All panels visible

### Large Terminal (>120 cols)
- Wider panels
- More content visible
- Less scrolling needed

### Vertical Resize
- Panels expand/contract proportionally
- Task list and output get most space
- Context panel minimum: 8 rows

---

## Animation & Transitions

### Smooth Transitions
- Panel resizing: 200ms ease
- Status changes: 300ms fade
- Modal open/close: 150ms slide

### Loading Animations
- Spinner: 8 frames, 125ms per frame
- Progress bar: Update every 100ms
- Pulse effect on active elements

### Feedback
- Flash on successful operation: 500ms yellow → normal
- Shake on error: 3 micro-shakes, 50ms each
- Fade in for new content: 200ms

---

## Accessibility

### Screen Readers
- All panels have descriptive labels
- Status changes announced
- Error messages read immediately

### High Contrast Mode
- Increase contrast ratios to 7:1
- Bolder borders
- Thicker text

### Keyboard-Only Navigation
- All functions accessible via keyboard
- Clear focus indicators
- Tab order logical (top-left to bottom-right)

---

## Edge Cases

### No Active Feature
```
┌─────────────────────────────────────────────────────────────────┐
│ Blueprint                                                  [F1] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                    No Active Feature                            │
│                                                                 │
│                    Run 'blueprint' to create                    │
│                    or resume a feature.                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### All Tasks Complete
```
┌─────────────┐
│   Tasks     │
├─────────────┤
│ ● task-1    │
│ ● task-2    │
│ ● task-3    │
│             │
│ 🎉 All Done!│
│             │
│ 3 total     │
│ 3 completed │
└─────────────┘
```

### Connection Lost to LLM
```
[Output Panel]
✗ Connection lost to DeepSeek
  Ollama may not be running

  Suggestions:
  • Run 'ollama serve' in another terminal
  • Check 'ollama list' for available models
  • Use /switch-model to change coder

  Type /resume to retry
```

---

## Example Workflows

### Starting Interactive Mode

1. Launch: `blueprint`
2. Select feature (if multiple)
3. TUI opens showing:
   - Task list (all tasks)
   - Empty output panel
   - Spec in context panel
4. User types `/start`
5. First task begins:
   - Task list highlights task-1
   - Output streams live
   - Context shows task-1 details

### During Task Execution

1. Output panel streams LLM output
2. Spinner animates in task list
3. User can:
   - Stop (Ctrl+S)
   - View usage (Ctrl+U)
   - Check other tasks (click or arrow keys)

### Task Completion

1. Success message in output
2. Task status changes to ●
3. Flash green highlight
4. Auto-advance to next task
5. Update summary counts

---

## Implementation Notes

### Textual Widgets to Use

```python
from textual.widgets import (
    Header,          # Top bar
    Footer,          # Bottom bar
    RichLog,         # Output streaming
    ListView,        # Task list
    Markdown,        # Context/spec
    Input,           # Command bar
    Static,          # Headers, labels
    DataTable,       # Usage stats
)

from textual.containers import (
    Container,       # Layout containers
    Horizontal,      # Side-by-side
    Vertical,        # Stacked
    VerticalScroll,  # Scrollable areas
)

from textual.screen import (
    ModalScreen,     # Modal overlays
)
```

### Layout Grid

```python
CSS = """
Screen {
    layout: grid;
    grid-size: 3 3;
    grid-rows: auto 1fr 1fr auto auto;
}

#header {
    column-span: 3;
    row-span: 1;
}

#task-list {
    column-span: 1;
    row-span: 2;
}

#output-panel {
    column-span: 2;
    row-span: 1;
}

#context-panel {
    column-span: 2;
    row-span: 1;
}

#command-bar {
    column-span: 3;
    row-span: 1;
}

#footer {
    column-span: 3;
    row-span: 1;
}
"""
```

---

## Success Criteria

✅ **Clarity**: User always knows current state
✅ **Responsiveness**: UI never freezes during LLM operations
✅ **Informativeness**: All critical info visible
✅ **Efficiency**: Common actions are quick
✅ **Professional**: Clean, terminal-native look
✅ **Accessible**: Keyboard-only operation works well
✅ **Helpful**: Errors include suggestions
✅ **Real-time**: Live streaming output
✅ **Non-intrusive**: Modals don't block unnecessarily
✅ **Recoverable**: Can stop/resume/correct easily

---

This design provides a powerful, usable TUI for orchestrating multiple LLMs while maintaining clarity and control throughout the development workflow.
