# Textual 6.8.0 — Layout & Styling API Summary

## 📐 Layout & Grid CSS-style Properties
- `layout: grid` — declare grid layout on a container.
- `grid-size: <cols> [<rows>]` — columns required, rows optional (rows auto-computed if omitted).
- `grid-columns: <scalar>+` — column widths (e.g., `1fr 2fr 1fr`), values repeat if fewer than columns.
- `grid-rows: <scalar>+` — row heights (e.g., `auto 1fr auto`), values repeat if fewer than rows.
- `grid-gutter: <int> [<int>]` — gap between cells; one value for both, or vertical then horizontal.
- `column-span: <int>` — child spans N columns.
- `row-span: <int>` — child spans N rows.
- Placement is by document/yield order, left-to-right, top-to-bottom, with spans consuming subsequent cells.

## ⚠️ Limitations / Unsupported vs full CSS Grid
- No explicit positioning (no `grid-row-start`, `grid-column-start`, `grid-template-areas`, named lines/areas).
- No overlap/holes; order + spans only.
- Alignment inside cells can be limited; may need extra containers for precise alignment.

## 🎨 Basic Styling & Widget CSS Concepts
- Selectors: type, class, id, combinators; CSS variables supported.
- Common props: `width`, `height`, `padding`, `border`, `background`, `color`, `content-align`.
- Widgets follow cascade/specificity; custom widgets can be styled the same way.

## 🧩 Common Built-in Widgets (useful for TUI)
- `RichLog` (streaming/log output), `Markdown`, `ListView`, `Input` (and variants), plus Button, Static, Label, DataTable, ProgressBar, etc.
- Widgets handle focus/keybindings/events; asynchronous-friendly.

## 🆕 Notes vs older 0.4x
- Grid API (size/rows/cols/spans/gutter) remains the same; still limited to order+span placement.
- Styling system and widget catalog are more mature; more built-ins documented.

## 🧑‍💻 Minimal 3x3 Layout Example
```python
class MyApp(App):
    CSS = '''
    Screen {
        layout: grid;
        grid-size: 3 3;
        grid-rows: auto 1fr auto;
        grid-columns: 1fr 1fr 1fr;
        grid-gutter: 0 1;
    }

    Header { column-span: 3; }
    #command-bar { column-span: 3; height: 1; }
    '''

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Left", id="left")
        yield Static("Center", id="center")
        yield Static("Right", id="right")
        yield Static("Cmd", id="command-bar")
```
Order matters: header spans row 1; next three widgets fill row 2 (cols 1–3); last spans row 3 across all columns.

## 📚 Official Examples
- Textual’s official example gallery (source): https://github.com/Textualize/textual/tree/main/examples — useful for patterns of grids, layouts, and widget usage on current versions.
