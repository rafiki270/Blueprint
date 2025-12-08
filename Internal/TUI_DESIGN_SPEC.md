# Blueprint TUI Design Specification - NEW LAYOUT

## Overview

Blueprint's interactive mode uses a **2-column layout** with a toggleable context pane. The design prioritizes visible command input, no extra scrolling, and efficient use of terminal space.

This specification is written for implementation using **Textual 6.8.0** with its specific grid limitations.

---

## Design Principles

1. **Command Visibility**: User must always see where they're typing
2. **No Extra Scrolling**: Empty panels should not cause scrollbars
3. **Space Efficiency**: Maximize usable space for tasks and output
4. **Flexible Context**: Context pane toggles on/off to reclaim space
5. **Input Expansion**: Multi-line input grows downward, never upward
6. **Professional**: Clean, terminal-native aesthetic

---

## Visual Layout Structure

```
┌────────────────────────────────────────────────────────────────────┐
│ ≡  Blueprint - Feature: user-auth               [Status]        ≡ │  ← Top Bar (10-12% height)
│ blueprint> /start task-1_____________________________________      │  ← Input grows down here
├──────────────────┬─────────────────────────────────────────────────┤
│                  │                                                 │
│   TASKS          │              OUTPUT                             │  Main Area
│   (25-30%)       │              (70-75%)                           │  (88-90% height)
│                  │                                                 │
│ ○ task-1         │  [09:23:45] Starting task...                    │
│ ◐ task-2 ←       │  [09:23:46] Generating code...                  │
│ ○ task-3         │                                                 │
│ ● task-4         │  def authenticate(user):                        │
│ ○ task-5         │      return validate(user)                      │
│                  │                                                 │
│ 5 tasks          │  ✓ Code generated                               │
│ 1 completed      │  [09:24:12] Running review...                   │
│ 1 in progress    │                                                 │
│                  │                                                 │
└──────────────────┴─────────────────────────────────────────────────┘

WITH CONTEXT PANE OPEN (toggled by right button):

┌────────────────────────────────────────────────────────────────────┐
│ ≡  Blueprint - Feature: user-auth               [Status]        ≡ │
│ blueprint> /start task-1_____________________________________      │
├──────────────────┬─────────────────────────────────────────────────┤
│                  │                                                 │
│   TASKS          │              OUTPUT                             │  Reduced to
│   (25-30%)       │              (70-75%)                           │  60-65% height
│                  │                                                 │
│ ○ task-1         │  [09:23:45] Starting task...                    │
│ ◐ task-2 ←       │  [09:23:46] Generating code...                  │
│ ○ task-3         │                                                 │
├──────────────────┴─────────────────────────────────────────────────┤
│                                                                     │
│   CONTEXT / SPEC                                                    │  Context Pane
│   (Full width, 25-30% height)                                      │  (25-30% height)
│                                                                     │
│   Current Task: task-2                                             │
│   Type: code | Status: in-progress                                 │
│                                                                     │
│   Description: Create authentication service...                    │
│   Requirements: JWT tokens, bcrypt hashing                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Layout Proportions (Exact Specifications)

### Region Sizes

| Region          | Width      | Height (Context Closed) | Height (Context Open) |
|-----------------|------------|-------------------------|-----------------------|
| Top Bar         | 100%       | 10-12%                  | 10-12%                |
| Tasks Panel     | 25-30%     | 88-90%                  | 60-65%                |
| Output Panel    | 70-75%     | 88-90%                  | 60-65%                |
| Context Pane    | 100%       | Hidden (0%)             | 25-30%                |

### Key Measurements

- **Top Bar**: Minimum 3 lines (title + input line + padding)
- **Tasks Panel**: Minimum width 20 columns, maximum 40 columns
- **Output Panel**: Expands to fill remaining horizontal space
- **Context Pane**: When open, takes 25-30% from bottom of main area
- **Input Line**: Starts at 1 line, grows downward as needed (max 5 lines)

---

## Component Breakdown

### 1. Top Bar (10-12% height)

**Structure:**
```
┌────────────────────────────────────────────────────────────────┐
│ [≡]  Blueprint - Feature: user-auth     [Status]          [≡]  │  ← Title bar (1 line)
│ blueprint> /start task-1_________________________________       │  ← Input (1+ lines)
└────────────────────────────────────────────────────────────────┘
```

**Components:**
- **Left Button (≡)**: Opens burger menu (dropdown with commands)
- **Title/Status**: Center text showing feature name and current state
- **Right Button (≡)**: Toggles context pane visibility
- **Input Line**: Sits at bottom of top bar, grows downward into main area

**Behavior:**
- Input starts at 1 line tall
- When user types multiple lines, input expands **downward only**
- Expansion temporarily pushes main panels down/shrinks them
- After submission, input collapses back to 1 line
- Input must always be visible (never scroll off screen)

**CSS Targets:**
- `#top-bar` (container)
- `#menu-button-left` (left ≡ button)
- `#title-status` (center text)
- `#context-toggle-button` (right ≡ button)
- `#command-input` (input field)

---

### 2. Tasks Panel (Left, 25-30% width)

**Structure:**
```
┌──────────────────┐
│   Tasks          │  ← Header (1 line)
├──────────────────┤
│ ○ task-1         │  ← Task list (scrollable)
│ ◐ task-2 ←       │
│ ○ task-3         │
│ ● task-4         │
│ ○ task-5         │
│                  │
│ 5 tasks          │  ← Summary footer (3-4 lines)
│ 1 completed      │
│ 1 in progress    │
└──────────────────┘
```

**Status Symbols:**
- `○` Pending (gray)
- `◐` In Progress (yellow, animated spinner)
- `●` Completed (green)
- `⚠` Blocked (red)
- `⊘` Skipped (dim gray)

**Behavior:**
- Scrollable list
- Current task highlighted with `←` arrow
- Auto-scrolls to current task
- Updates in real-time

**CSS Targets:**
- `#task-list-widget`
- `#task-list-header`
- `#task-list-content`
- `#task-list-footer`

---

### 3. Output Panel (Right, 70-75% width)

**Structure:**
```
┌─────────────────────────────────────────────────────────┐
│   Output                                        [Clear] │  ← Header (1 line)
├─────────────────────────────────────────────────────────┤
│ [09:23:45] Starting task: Implement login               │  ← Streaming output
│ [09:23:46] Using DeepSeek for generation...             │
│                                                          │
│ def authenticate(user):                                 │
│     return validate(user)                               │
│                                                          │
│ ✓ Code generated (245 lines)                            │
│ [09:24:12] Running review...                            │
│                                                          │
│ █                                                        │  ← Auto-scroll indicator
└─────────────────────────────────────────────────────────┘
```

**Content Types:**
- Timestamped log messages
- Streaming LLM output (line-by-line)
- Code blocks (syntax highlighted)
- Status indicators (✓ ✗ ⚠ ℹ)

**Behavior:**
- Auto-scrolls to bottom as new content arrives
- Preserves ANSI colors
- Copy/paste support
- Clear button to empty output

**CSS Targets:**
- `#output-panel`
- `#output-header`
- `#output-content` (RichLog widget)

---

### 4. Context Pane (Bottom, Toggleable, 25-30% height)

**Structure:**
```
┌─────────────────────────────────────────────────────────┐
│   Context                                   [Task][Spec]│  ← Header with tabs
├─────────────────────────────────────────────────────────┤
│ Current Task: Implement user login                      │  ← Content area
│ ──────────────────────────────────────────────────      │
│ ID: task-2                                              │
│ Type: code | Status: in-progress                        │
│ Model: DeepSeek                                         │
│                                                          │
│ Description:                                            │
│ Create user authentication service...                   │
│                                                          │
│ Requirements:                                           │
│ • JWT token generation                                  │
│ • Password hashing with bcrypt                          │
│ • Session management                                    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Tab Views:**
- **[Task]**: Current task details (ID, type, status, description, requirements)
- **[Spec]**: Full specification viewer with markdown rendering

**Behavior:**
- Toggles on/off via right button in top bar
- When closed: completely hidden (height: 0)
- When open: takes 25-30% of screen height from bottom
- Main panels (tasks + output) shrink proportionally when open
- Scrollable for long content

**CSS Targets:**
- `#context-pane` (with `display: none` when hidden)
- `#context-header`
- `#context-tabs`
- `#context-content`

---

## Textual 6.8.0 Grid Implementation Guide

### Supported CSS Properties (ONLY THESE WORK)

```css
/* Grid Container */
layout: grid;
grid-size: <cols> <rows>;          /* e.g., grid-size: 2 3; */
grid-columns: <sizes...>;          /* e.g., 1fr 3fr */
grid-rows: <sizes...>;             /* e.g., auto 1fr auto */
grid-gutter: <vertical> <horizontal>; /* e.g., 0 1 */

/* Grid Children */
column-span: <int>;                /* e.g., column-span: 2; */
row-span: <int>;                   /* e.g., row-span: 1; */

/* Size Values */
auto                               /* Size to content */
1fr, 2fr, 3fr                      /* Fractional units */
<int>                              /* Fixed lines/columns */
```

### NOT Supported (Will NOT Work)

```css
/* ❌ These do NOT exist in Textual 6.8.0 */
grid-row-start: 2;                 /* No explicit positioning */
grid-column-start: 1;              /* No explicit positioning */
grid-template-areas: "...";        /* No named areas */
grid-row: 1 / 3;                   /* No shorthand positioning */
place-items: center;               /* No alignment shortcuts */
```

### Layout Rules

1. **Placement is by document order**: First yielded widget goes in first grid cell, second goes in second cell, etc.
2. **Left-to-right, top-to-bottom**: Fills columns first, then moves to next row
3. **Spans consume cells**: If a widget spans 3 columns, next widget starts after those 3 columns
4. **Rows auto-expand**: If you yield more widgets than grid cells, new rows are created automatically

---

## Implementation Steps (For LLM Following This Spec)

### STEP 1: Create TopBar Widget

**File**: `src/blueprint/interactive/widgets/top_bar.py`

**Requirements:**
- Create a custom `TopBar` widget that inherits from `Widget`
- Contains 3 components in a horizontal layout:
  1. Left button (Static with "≡" text)
  2. Title/status (Static with dynamic text)
  3. Right button (Static with "≡" text)
- Contains 1 input line at bottom:
  4. Input field (Input widget)

**Layout Structure:**
```python
class TopBar(Widget):
    def compose(self):
        with Horizontal(id="top-bar-header"):
            yield Static("≡", id="menu-button-left")
            yield Static("Blueprint - Feature: X", id="title-status")
            yield Static("≡", id="context-toggle-button")
        yield Input(placeholder="Enter command", id="command-input")
```

**CSS (in widget):**
```css
TopBar {
    height: auto;
    dock: top;
}

#top-bar-header {
    height: 1;
    background: $primary;
}

#menu-button-left, #context-toggle-button {
    width: 3;
    text-align: center;
    background: $primary;
}

#title-status {
    width: 1fr;
    text-align: center;
    background: $primary;
}

#command-input {
    height: auto;
    min-height: 1;
    max-height: 5;
    border: none;
    background: $surface;
}
```

**Events to Handle:**
- Click on left button → post `MenuToggled` message
- Click on right button → post `ContextToggled` message
- Input submitted → post `CommandSubmitted` message

**Behavior:**
- Input should auto-expand as user types multiple lines
- Max height: 5 lines (then scroll within input)
- After submit, clear and collapse to 1 line

---

### STEP 2: Update Main App Layout

**File**: `src/blueprint/interactive/app.py`

**Requirements:**
- Remove old 3-column grid
- Create new 2-column grid with optional 3rd row for context
- Use dynamic grid sizing (2 rows when context closed, 3 rows when open)

**Grid Structure (Context Closed):**
```
grid-size: 2 2
grid-rows: auto 1fr
grid-columns: 1fr 3fr

Row 1: TopBar (spans 2 columns)
Row 2: TaskList | OutputPanel
```

**Grid Structure (Context Open):**
```
grid-size: 2 3
grid-rows: auto 1fr auto
grid-columns: 1fr 3fr

Row 1: TopBar (spans 2 columns)
Row 2: TaskList | OutputPanel
Row 3: ContextPane (spans 2 columns)
```

**Compose Method:**
```python
def compose(self) -> ComposeResult:
    yield TopBar(id="top-bar")
    yield TaskListWidget(id="task-list")
    yield OutputPanel(id="output-panel")
    # Context pane initially hidden
    yield ContextPane(id="context-pane")
```

**Initial CSS:**
```css
Screen {
    layout: grid;
    grid-size: 2 2;
    grid-rows: auto 1fr;
    grid-columns: 1fr 3fr;
}

#top-bar {
    column-span: 2;
}

#task-list {
    border: tall;
    width: 1fr;
}

#output-panel {
    border: tall;
    width: 3fr;
}

#context-pane {
    display: none;  /* Initially hidden */
    column-span: 2;
    height: 0;
}
```

---

### STEP 3: Implement Context Toggle Logic

**File**: `src/blueprint/interactive/app.py`

**Requirements:**
- Add boolean state: `self.context_visible = False`
- Listen for `ContextToggled` message from TopBar
- Toggle context pane visibility
- Update grid layout dynamically

**Implementation:**
```python
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.context_visible = False
    # ... other init

async def on_top_bar_context_toggled(self) -> None:
    """Handle context pane toggle from TopBar."""
    self.context_visible = not self.context_visible

    context_pane = self.query_one("#context-pane")

    if self.context_visible:
        # Show context pane
        context_pane.styles.display = "block"
        context_pane.styles.height = "30%"
        # Update grid to 3 rows
        self.styles.grid_size = (2, 3)
        self.styles.grid_rows = "auto 1fr auto"
    else:
        # Hide context pane
        context_pane.styles.display = "none"
        context_pane.styles.height = "0"
        # Update grid to 2 rows
        self.styles.grid_size = (2, 2)
        self.styles.grid_rows = "auto 1fr"
```

**Important Notes:**
- When context is hidden, it must have `height: 0` AND `display: none`
- When context is shown, grid-rows must change to include the 3rd row
- Main panels will automatically shrink because `1fr` distributes remaining space

---

### STEP 4: Remove Old CommandBar Widget

**Files to Modify:**
- `src/blueprint/interactive/app.py`
- `src/blueprint/interactive/widgets/__init__.py`

**Actions:**
- Delete `src/blueprint/interactive/widgets/command_bar.py` (or leave for reference)
- Remove `CommandBar` imports from app.py
- Remove `CommandBar` from compose method
- Move command handling logic to TopBar

**Migration:**
- Command history → Move to TopBar.command_input
- Command submission → TopBar posts `CommandSubmitted`
- Focus logic → Move to TopBar's Input widget

---

### STEP 5: Update Proportions and Borders

**File**: `src/blueprint/interactive/app.py` (CSS section)

**Column Width Tuning:**
```css
/* Adjust these to get 25-30% vs 70-75% split */
grid-columns: 1fr 3fr;    /* Gives ~25% / 75% split */

/* OR for different proportions: */
grid-columns: 3fr 7fr;    /* More precise 30% / 70% split */
```

**Border Considerations:**
- Borders add 2 lines/columns of space
- `border: tall` = 2 lines top/bottom
- `border: wide` = 2 columns left/right
- If using borders, fractional widths should account for this

**Recommended Border Strategy:**
```css
#task-list {
    border: tall;           /* Keep vertical borders */
    border-right: solid;    /* Only right edge */
}

#output-panel {
    border: tall;           /* Keep vertical borders */
    border-left: none;      /* No left (overlaps with task-list) */
}
```

**Context Pane Height When Open:**
```css
#context-pane {
    height: 30%;            /* Takes exactly 30% of screen */
    min-height: 8;          /* At least 8 lines minimum */
    border: tall;
    padding: 0 1;
}
```

---

### STEP 6: Handle Input Growth Behavior

**File**: `src/blueprint/interactive/widgets/top_bar.py`

**Requirements:**
- Input starts at 1 line height
- Grows as user types (multi-line input)
- Max 5 lines, then scrolls internally
- After submit, collapses back to 1 line

**Implementation:**
```python
class TopBar(Widget):
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input text changes to adjust height."""
        input_widget = event.input
        lines = input_widget.value.count('\n') + 1

        # Cap at 5 lines
        new_height = min(lines, 5)
        input_widget.styles.height = new_height

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle command submission."""
        command = event.value.strip()

        if command:
            self.post_message(self.CommandSubmitted(command))

        # Clear and reset height
        event.input.value = ""
        event.input.styles.height = 1
```

**CSS:**
```css
#command-input {
    height: 1;              /* Start at 1 line */
    min-height: 1;
    max-height: 5;          /* Cap at 5 lines */
    overflow-y: auto;       /* Scroll if >5 lines */
}
```

---

### STEP 7: Test Layout Without Scrolling

**Validation Checklist:**

1. **Empty Panels Test**:
   - Launch app with no tasks
   - Verify NO vertical scrollbar appears on screen
   - All panels should be visible without scrolling

2. **Command Input Visibility Test**:
   - Type in command input
   - Verify you can see the cursor/caret
   - Verify typed text is visible
   - Verify input is not cut off or scrolled away

3. **Multi-line Input Test**:
   - Type a multi-line command (press Enter multiple times)
   - Verify input grows downward
   - Verify it does NOT grow upward into title bar
   - Verify main panels shrink slightly to accommodate

4. **Context Toggle Test**:
   - Click right button (≡) in top bar
   - Context pane should appear at bottom
   - Main panels should shrink proportionally
   - No scrollbar should appear

5. **Context Close Test**:
   - Click right button again
   - Context pane should disappear completely
   - Main panels should expand back to full height
   - No extra space or scrollbar at bottom

6. **Proportions Test**:
   - Measure task panel width: should be ~25-30% of terminal width
   - Measure output panel width: should be ~70-75% of terminal width
   - Measure top bar height: should be ~10-12% of terminal height
   - Measure context pane (when open): should be ~25-30% of terminal height

7. **Border Overlap Test**:
   - Verify borders don't create double-lines between panels
   - Verify borders don't add unexpected scrollbars

---

## Common Pitfalls and Solutions

### Problem 1: Extra Scrollbar with Empty Panels

**Cause**: Borders, padding, or fixed heights exceed available space

**Solution**:
- Use `height: auto` on flexible containers
- Use `grid-rows: auto 1fr auto` (not fixed numbers)
- Remove unnecessary borders
- Set `padding: 0` on containers that don't need it

### Problem 2: Command Input Not Visible

**Cause**: Input pushed off-screen or height set to 0

**Solution**:
- Set `min-height: 1` on input
- Use `dock: top` on TopBar to keep it at top
- Ensure TopBar has `height: auto` (not fixed)
- Verify input is inside TopBar, not in grid cells

### Problem 3: Context Pane Doesn't Toggle

**Cause**: Display property not changing, or grid not updating

**Solution**:
- Toggle both `display` AND `height`
- Update `grid-size` when toggling (2x2 vs 2x3)
- Update `grid-rows` when toggling
- Use `self.refresh(layout=True)` after CSS changes

### Problem 4: Panels Wrong Proportions

**Cause**: Grid columns not adding up correctly

**Solution**:
- Use fractional units: `1fr 3fr` gives 25%/75%
- Use `3fr 7fr` for exact 30%/70%
- Don't mix `fr` units with fixed widths unless necessary
- Account for border widths when calculating

### Problem 5: Input Doesn't Grow on Multi-line

**Cause**: Height is fixed or max-height prevents growth

**Solution**:
- Remove `height` property (use `auto`)
- Set `max-height: 5` but not `height: 1`
- Dynamically update height in `on_input_changed` handler
- Use `overflow-y: auto` for scrolling after max-height

### Problem 6: Grid Changes Don't Apply

**Cause**: Textual caches layout, needs explicit refresh

**Solution**:
- Call `self.refresh(layout=True)` after changing grid CSS
- Use `self.styles.grid_size = (2, 3)` not CSS string
- Ensure changes happen in async method with `await`

---

## File Structure Summary

**New/Modified Files:**

```
src/blueprint/interactive/
├── app.py                              # Main app, updated grid layout
├── widgets/
│   ├── __init__.py                     # Updated imports
│   ├── top_bar.py                      # NEW - TopBar widget
│   ├── task_list.py                    # Existing, no major changes
│   ├── output_panel.py                 # Existing, no major changes
│   ├── context_panel.py                # Modified for toggle behavior
│   └── command_bar.py                  # DEPRECATED/REMOVED
```

**Critical Files:**

1. **top_bar.py**: Implements menu buttons, title, and command input
2. **app.py**: Grid layout, context toggle logic, CSS
3. **context_panel.py**: Ensures proper show/hide behavior

---

## Testing Strategy

### Manual Testing

1. **Launch app**: `blueprint` (or however you run it)
2. **Visual check**: Verify all panels visible, no scrollbar
3. **Type command**: Verify input is visible and responsive
4. **Submit command**: Verify input clears and resets to 1 line
5. **Toggle context**: Click right ≡ button, verify pane appears/disappears
6. **Multi-line input**: Type multiple lines, verify downward growth
7. **Resize terminal**: Make larger/smaller, verify proportions maintained

### Automated Testing (If Applicable)

```python
# Test context toggle
app = BlueprintApp("test-feature")
assert app.context_visible == False
app.on_top_bar_context_toggled()
assert app.context_visible == True
context = app.query_one("#context-pane")
assert context.styles.display == "block"
```

---

## Success Criteria

✅ **No extra scrollbar** when panels are empty
✅ **Command input always visible** at bottom of top bar
✅ **User can see cursor** and typed text in input
✅ **Multi-line input grows downward** (never up)
✅ **Context pane toggles** on/off with right button
✅ **Proportions match spec**: 25-30% tasks, 70-75% output
✅ **Top bar is 10-12%** of terminal height
✅ **Context pane is 25-30%** when open
✅ **Main panels shrink/grow** when context toggles
✅ **Layout works in Textual 6.8.0** (no unsupported CSS)

---

## Final Notes for Implementation

1. **Start with TopBar**: Get the top bar working first with static layout
2. **Then Grid**: Update app.py grid to 2-column layout
3. **Then Toggle**: Implement context pane toggle logic
4. **Then Refinement**: Adjust proportions, borders, padding
5. **Test Incrementally**: After each step, verify no scrollbar appears

**Key Principle**: If you see a scrollbar with empty panels, something has a fixed height that exceeds available space. Use `auto` and `1fr` instead.

**Remember**: Textual 6.8.0 grid is simple - just `grid-size`, `grid-rows`, `grid-columns`, `grid-gutter`, `column-span`, `row-span`. Nothing else works. Widgets are placed in document order (yield order) automatically.

---

END OF SPECIFICATION
