# Desktop Sticky Todo

A small Windows desktop sticky-note todo app with resizable notes, due dates, status colors, urgency/importance flags, always-on-top mode, and a compact collapsed layout.

## Features

- Desktop sticky todo window
- Resizable and movable note card
- Compact collapsed mode
- Status selector: not started, in progress, done
- Due date picker
- Auto urgent flag when the due date is near
- Important and urgent buttons
- Always-on-top pin
- Multiple sticky notes
- Local auto-save

## Run

On Windows, double-click:

```text
啟動待辦便籤.bat
```

You can also run it from a terminal:

```powershell
python sticky_todo.py
```

## Local Data

The app stores local note data in:

```text
sticky_todo_data.json
```

This data file is ignored by Git so personal notes are not published.

## Requirements

- Windows
- Python 3 with Tkinter

## License

MIT
