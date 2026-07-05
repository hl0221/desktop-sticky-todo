import calendar
import ctypes
import json
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox


APP_DIR = Path(__file__).resolve().parent
DATA_FILE = APP_DIR / "sticky_todo_data.json"
COLLAPSED_BUTTON_TOP_GAP = 26
COLLAPSED_WINDOW_HEIGHT = 128
COLLAPSED_DATE_WINDOW_HEIGHT = 206
WINDOW_CORNER_RADIUS = 20


TEXT = {
    "default_title": "\u5f85\u8fa6\u4e8b\u9805",
    "window_title": "\u5f85\u8fa6\u4fbf\u7c64",
    "date_unset": "\U0001f5d3",
    "today": "\u4eca\u5929",
    "clear": "\u6e05\u7a7a",
    "hide": "\u6536\u8d77",
    "important": "\u2b50",
    "urgent": "\u23f0",
    "pin": "\U0001f4cc",
    "keep_one_title": "\u4fdd\u7559\u4e00\u5f35\u4fbf\u7c64",
    "keep_one_body": "\u81f3\u5c11\u9700\u8981\u4fdd\u7559\u4e00\u5f35\u5f85\u8fa6\u4fbf\u7c64\u3002",
    "delete_title": "\u522a\u9664\u6b64\u4fbf\u7c64",
    "delete_body": "\u78ba\u5b9a\u8981\u522a\u9664\u9019\u5f35\u4fbf\u7c64\u55ce\uff1f",
    "year": "\u5e74",
    "month": "\u6708",
    "day": "\u65e5",
    "status": "\u72c0\u614b",
    "add": "+",
    "collapse": "\u2304",
    "expand": "\u2303",
    "minimize": "-",
    "close": "\u00d7",
    "today_icon": "\u25ce",
    "clear_icon": "\u232b",
    "hide_icon": "\u2303",
    "important_tip": "\u91cd\u8981",
    "urgent_tip": "\u7dca\u6025",
    "date_tip": "\u5b8c\u6210\u65e5\u671f",
    "add_tip": "\u65b0\u589e\u4fbf\u7c64",
    "pin_tip": "\u7f6e\u9802",
    "collapse_tip": "\u6536\u8d77\u8f38\u5165\u5340",
    "expand_tip": "\u5c55\u958b\u8f38\u5165\u5340",
    "close_tip": "\u95dc\u9589",
}

MOJIBAKE_FIXES = {
    "\u5bf0\u5443\u775b\u6d5c\u5b2e\u7221": TEXT["default_title"],
    "\u5bf0\u5443\u775b\u6e1a\u8de8\u5821": TEXT["window_title"],
    "\u5bf0\u5470\u775b\u6d5c\u5b2e\u7221": TEXT["default_title"],
    "\u5bf0\u5470\u775b\u6e1a\u8de8\u5821": TEXT["window_title"],
}

COLORS = {
    "mica": "#eaf4ff",
    "glass": "#ffffff",
    "glass_soft": "#f8fbff",
    "line": "#d7e2f0",
    "text": "#172033",
    "muted": "#667085",
    "soft_text": "#42526e",
    "accent": "#6d5dfc",
    "accent_hover": "#5b50dd",
    "blue": "#2f80ed",
    "danger": "#c42b1c",
    "danger_hover": "#a81f14",
    "danger_soft": "#fff2f2",
    "important": "#d99000",
    "important_soft": "#fff7db",
}

STATUS_CONFIG = {
    "todo": {"label": "\u672a\u5b8c\u6210", "color": "#8a8f98", "soft": "#f1f3f6"},
    "doing": {"label": "\u9032\u884c\u4e2d", "color": "#2f80ed", "soft": "#eaf4ff"},
    "done": {"label": "\u5df2\u5b8c\u6210", "color": "#2ea44f", "soft": "#eaf8ee"},
}


def parse_iso_date(value):
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except (AttributeError, ValueError):
        return None


def fix_text(value, fallback=""):
    if not value:
        return fallback
    return MOJIBAKE_FIXES.get(value, value)


def format_date_for_button(value):
    selected = parse_iso_date(value)
    if not selected:
        return TEXT["date_unset"]
    return selected.strftime("%Y.%m.%d")


def rounded_rectangle(canvas, x1, y1, x2, y2, radius, **kwargs):
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


class ToolTip:
    def __init__(self, widget, text_getter):
        self.widget = widget
        self.text_getter = text_getter
        self.tip = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _event=None):
        self.hide()
        text = self.text_getter() if callable(self.text_getter) else str(self.text_getter)
        if not text:
            return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.attributes("-topmost", True)
        self.tip.geometry(f"+{x}+{y}")
        label = tk.Label(
            self.tip,
            text=text,
            bg="#1f2937",
            fg="white",
            padx=8,
            pady=4,
            font=("Microsoft JhengHei UI", 9),
        )
        label.pack()

    def hide(self, _event=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


class RoundedButton(tk.Canvas):
    def __init__(
        self,
        parent,
        text,
        command=None,
        width=62,
        height=34,
        radius=9,
        fill="#ffffff",
        hover_fill="#edf6ff",
        fg=None,
        parent_bg=None,
        font=("Microsoft JhengHei UI", 10),
        circle=False,
    ):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=parent_bg or parent.cget("bg"),
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self.button_text = text
        self.command = command
        self.button_width = width
        self.button_height = height
        self.radius = radius
        self.fill = fill
        self.hover_fill = hover_fill
        self.fg = fg or COLORS["text"]
        self.font = font
        self.circle = circle
        self.bind("<Button-1>", self.on_click)
        self.bind("<Enter>", lambda _event: self.draw(self.hover_fill))
        self.bind("<Leave>", lambda _event: self.draw(self.fill))
        self.draw(self.fill)

    def draw(self, fill):
        self.delete("all")
        if self.circle:
            margin = 4
            self.create_oval(
                margin,
                margin,
                self.button_width - margin,
                self.button_height - margin,
                fill=self.fg,
                outline="",
            )
        else:
            rounded_rectangle(
                self,
                1,
                1,
                self.button_width - 1,
                self.button_height - 1,
                self.radius,
                fill=fill,
                outline="",
            )
            self.create_text(
                self.button_width / 2,
                self.button_height / 2,
                text=self.button_text,
                fill=self.fg,
                font=self.font,
            )
    def set_text(self, text):
        self.button_text = text
        self.draw(self.fill)

    def set_style(self, fill=None, hover_fill=None, fg=None):
        if fill is not None:
            self.fill = fill
        if hover_fill is not None:
            self.hover_fill = hover_fill
        if fg is not None:
            self.fg = fg
        self.draw(self.fill)

    def on_click(self, _event=None):
        if self.command:
            self.command()


class RoundedPanel(tk.Canvas):
    def __init__(self, parent, fill, radius=14, parent_bg=None):
        super().__init__(parent, bg=parent_bg or parent.cget("bg"), highlightthickness=0, bd=0)
        self.fill = fill
        self.radius = radius
        self.inner = tk.Frame(self, bg=fill)
        self.window_item = self.create_window(0, 0, window=self.inner, anchor="nw")
        self.bind("<Configure>", self.redraw)

    def redraw(self, _event=None):
        width = max(self.winfo_width(), 1)
        height = max(self.winfo_height(), 1)
        self.delete("panel")
        rounded_rectangle(
            self,
            0,
            0,
            width,
            height,
            self.radius,
            fill=self.fill,
            outline="",
            tags="panel",
        )
        self.tag_lower("panel")
        self.coords(self.window_item, 0, 0)
        self.itemconfigure(self.window_item, width=width, height=height)


@dataclass
class NoteData:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = TEXT["default_title"]
    text: str = ""
    status: str = "todo"
    important: bool = False
    urgent: bool = False
    completed_date: str = ""
    geometry: str = "390x520+120+120"
    always_on_top: bool = True
    text_expanded: bool = True

    @classmethod
    def from_dict(cls, data):
        note = cls()
        for key in note.__dataclass_fields__:
            if key in data:
                setattr(note, key, data[key])
        note.title = fix_text(note.title, TEXT["default_title"])
        note.text = fix_text(note.text, "")
        if note.status not in STATUS_CONFIG:
            note.status = "todo"
        return note

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "text": self.text,
            "status": self.status,
            "important": self.important,
            "urgent": self.urgent,
            "completed_date": self.completed_date,
            "geometry": self.geometry,
            "always_on_top": self.always_on_top,
            "text_expanded": self.text_expanded,
        }


class StickyTodoApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.windows = {}
        self.last_add_at = 0
        self.notes = self.load_notes()
        if not self.notes:
            self.notes = [NoteData()]
        for index, note in enumerate(self.notes, start=1):
            self.open_note(note, index)

    def load_notes(self):
        if not DATA_FILE.exists():
            return []
        try:
            data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            return [NoteData.from_dict(item) for item in data.get("notes", [])]
        except (json.JSONDecodeError, OSError):
            backup = DATA_FILE.with_suffix(".broken.json")
            try:
                DATA_FILE.replace(backup)
            except OSError:
                pass
            return []

    def save_notes(self):
        data = {"notes": [note.to_dict() for note in self.notes]}
        DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def open_note(self, note, index=None):
        window = NoteWindow(self, note, index or len(self.windows) + 1)
        self.windows[note.id] = window

    def add_note(self, source_window=None):
        now = time.monotonic()
        if now - self.last_add_at < 0.45:
            return
        self.last_add_at = now
        note = NoteData()
        note.text_expanded = False
        if source_window:
            x = source_window.window.winfo_x() + 28
            y = source_window.window.winfo_y() + 28
            width = min(max(source_window.window.winfo_width(), 360), 430)
            note.geometry = f"{width}x{COLLAPSED_WINDOW_HEIGHT}+{x}+{y}"
        else:
            note.geometry = f"390x{COLLAPSED_WINDOW_HEIGHT}+120+120"
        self.notes.append(note)
        self.save_notes()
        self.open_note(note)

    def delete_note(self, note_id):
        if len(self.notes) == 1:
            messagebox.showinfo(TEXT["keep_one_title"], TEXT["keep_one_body"])
            return
        window = self.windows.get(note_id)
        if not messagebox.askyesno(TEXT["delete_title"], TEXT["delete_body"]):
            return
        self.notes = [note for note in self.notes if note.id != note_id]
        self.save_notes()
        if window:
            window.close(destroy_only=True)

    def close_window(self, note_id):
        self.windows.pop(note_id, None)
        if not self.windows:
            self.root.destroy()

    def run(self):
        self.root.mainloop()


class NoteWindow:
    def __init__(self, app, note, index):
        self.app = app
        self.note = note
        self.index = index
        self.save_after_id = None
        self.round_after_id = None
        self.last_rounded_size = None
        self.last_configure_size = None
        self.date_panel_visible = False
        self.status_menu = None
        self.drag_start = None
        self.resize_start = None
        self.text_expanded = bool(note.text_expanded)
        self.expanded_height = max(self.geometry_height(note.geometry), 520)

        self.window = tk.Toplevel(self.app.root)
        self.window.overrideredirect(True)
        self.window.title(note.title or f"{TEXT['window_title']} {index}")
        self.window.geometry(self.safe_geometry(note.geometry))
        self.window.minsize(330, COLLAPSED_WINDOW_HEIGHT)
        self.window.configure(bg=COLORS["mica"])
        self.window.attributes("-topmost", bool(note.always_on_top))
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        self.title_var = tk.StringVar(value=note.title or TEXT["default_title"])
        self.status_var = tk.StringVar(value=note.status)
        self.important_var = tk.BooleanVar(value=note.important)
        self.urgent_var = tk.BooleanVar(value=note.urgent)
        self.date_var = tk.StringVar(value=note.completed_date)
        self.top_var = tk.BooleanVar(value=note.always_on_top)

        selected_date = parse_iso_date(note.completed_date) or date.today()
        self.year_var = tk.IntVar(value=selected_date.year)
        self.month_var = tk.IntVar(value=selected_date.month)
        self.day_var = tk.IntVar(value=selected_date.day)
        self.year_page_start = (selected_date.year // 12) * 12

        self.build_ui()
        self.apply_status_style()
        self.update_date_summary()
        self.update_flags_style()
        self.update_top_style()
        self.bind_changes()
        self.window.after(50, lambda: self.apply_window_rounding(force=True))

    def safe_geometry(self, geometry):
        match = re.match(r"^(\d+)x(\d+)([+-]\d+)([+-]\d+)$", str(geometry))
        if match:
            width, height, x, y = [int(value) for value in match.groups()]
        else:
            width, height, x, y = 390, 520, 120, 120

        screen_width = max(self.window.winfo_screenwidth(), 800)
        screen_height = max(self.window.winfo_screenheight(), 600)
        width = min(max(width, 330), screen_width - 40)
        min_height = COLLAPSED_WINDOW_HEIGHT if not self.text_expanded else 260
        height = min(max(height, min_height), screen_height - 40)

        if x < 0 or y < 0 or x > screen_width - 80 or y > screen_height - 80:
            x, y = 120, 120
        return f"{width}x{height}+{x}+{y}"

    def build_ui(self):
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)

        self.shell = tk.Frame(self.window, bg=COLORS["mica"], padx=14, pady=14)
        self.shell.grid(row=0, column=0, sticky="nsew")
        self.shell.columnconfigure(0, weight=1)
        self.shell.rowconfigure(1, weight=1)

        header = tk.Frame(self.shell, bg=COLORS["mica"])
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)
        self.bind_drag_handle(header)

        self.status_button = RoundedButton(
            header,
            "",
            command=self.toggle_status_menu,
            width=30,
            height=30,
            circle=True,
            fg=STATUS_CONFIG[self.status_var.get()]["color"],
            parent_bg=COLORS["mica"],
        )
        self.status_button.grid(row=0, column=0, sticky="w", padx=(0, 8))
        ToolTip(self.status_button, self.status_tooltip_text)

        self.title_entry = tk.Entry(
            header,
            textvariable=self.title_var,
            font=("Microsoft JhengHei UI", 16, "bold"),
            bg=COLORS["mica"],
            fg=COLORS["text"],
            insertbackground=COLORS["accent"],
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
        )
        self.title_entry.grid(row=0, column=1, sticky="ew", ipady=4)
        self.bind_drag_handle(self.title_entry)

        title_buttons = tk.Frame(header, bg=COLORS["mica"])
        title_buttons.grid(row=0, column=2, sticky="e")
        self.fold_button = RoundedButton(
            title_buttons,
            TEXT["collapse"],
            command=self.toggle_text_panel,
            width=34,
            height=30,
            radius=8,
            fill=COLORS["mica"],
            hover_fill="#dbeafe",
            parent_bg=COLORS["mica"],
            font=("Segoe UI Symbol", 12),
        )
        self.fold_button.grid(row=0, column=0, padx=(0, 4))
        ToolTip(self.fold_button, self.fold_tooltip_text)
        self.top_button = RoundedButton(
            title_buttons,
            TEXT["pin"],
            command=self.toggle_top,
            width=34,
            height=30,
            radius=8,
            fill=COLORS["mica"],
            hover_fill="#dbeafe",
            parent_bg=COLORS["mica"],
            font=("Segoe UI Emoji", 11),
        )
        self.top_button.grid(row=0, column=1, padx=(0, 4))
        ToolTip(self.top_button, lambda: TEXT["pin_tip"])
        self.close_button = RoundedButton(
            title_buttons,
            TEXT["close"],
            command=self.close,
            width=34,
            height=30,
            radius=8,
            fill=COLORS["mica"],
            hover_fill=COLORS["danger_soft"],
            fg=COLORS["text"],
            parent_bg=COLORS["mica"],
            font=("Segoe UI Symbol", 13),
        )
        self.close_button.grid(row=0, column=2)
        ToolTip(self.close_button, lambda: TEXT["close_tip"])

        self.text_panel = RoundedPanel(self.shell, COLORS["glass"], radius=18, parent_bg=COLORS["mica"])
        self.text_panel.grid(row=1, column=0, sticky="nsew", pady=(12, 10))
        self.text_panel.inner.columnconfigure(0, weight=1)
        self.text_panel.inner.rowconfigure(0, weight=1)

        self.text = tk.Text(
            self.text_panel.inner,
            wrap="word",
            undo=True,
            font=("Microsoft JhengHei UI", 16),
            bg=COLORS["glass"],
            fg=COLORS["text"],
            insertbackground=COLORS["accent"],
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=18,
            pady=18,
            spacing1=4,
            spacing2=4,
            spacing3=6,
        )
        self.text.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        self.text.insert("1.0", self.note.text)

        self.date_panel = RoundedPanel(self.shell, COLORS["glass"], radius=14, parent_bg=COLORS["mica"])
        self.date_panel.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self.date_panel.inner.columnconfigure(0, weight=1)
        self.date_panel.grid_remove()
        self.build_date_panel()

        self.bottom = tk.Frame(self.shell, bg=COLORS["mica"])
        self.bottom.grid(row=3, column=0, sticky="ew")
        self.bottom.columnconfigure(0, weight=1)

        self.flag_controls = tk.Frame(self.bottom, bg=COLORS["mica"])
        self.flag_controls.grid(row=0, column=0, sticky="w")
        self.important_button = RoundedButton(
            self.flag_controls,
            TEXT["important"],
            command=lambda: self.toggle_flag(self.important_var, self.on_flag_changed),
            width=46,
            height=38,
            radius=10,
            parent_bg=COLORS["mica"],
            font=("Segoe UI Emoji", 13),
        )
        self.important_button.grid(row=0, column=0, padx=(0, 8))
        ToolTip(self.important_button, lambda: TEXT["important_tip"])
        self.urgent_button = RoundedButton(
            self.flag_controls,
            TEXT["urgent"],
            command=lambda: self.toggle_flag(self.urgent_var, self.on_flag_changed),
            width=46,
            height=38,
            radius=10,
            parent_bg=COLORS["mica"],
            font=("Segoe UI Emoji", 13),
        )
        self.urgent_button.grid(row=0, column=1)
        ToolTip(self.urgent_button, lambda: TEXT["urgent_tip"])

        self.controls = tk.Frame(self.bottom, bg=COLORS["mica"])
        self.controls.grid(row=0, column=1, sticky="e")
        self.date_pill = RoundedButton(
            self.controls,
            "",
            command=self.toggle_date_panel,
            width=112,
            height=38,
            radius=10,
            parent_bg=COLORS["mica"],
            font=("Segoe UI Emoji", 13),
        )
        self.date_pill.grid(row=0, column=0, padx=(0, 8))
        ToolTip(self.date_pill, self.date_tooltip_text)
        self.add_button = RoundedButton(
            self.controls,
            TEXT["add"],
            command=lambda: self.app.add_note(self),
            width=42,
            height=38,
            radius=10,
            fill=COLORS["accent"],
            hover_fill=COLORS["accent_hover"],
            fg="white",
            parent_bg=COLORS["mica"],
            font=("Segoe UI", 16, "bold"),
        )
        self.add_button.grid(row=0, column=1)
        ToolTip(self.add_button, lambda: TEXT["add_tip"])

        self.resize_grip = tk.Frame(self.window, bg=COLORS["mica"], cursor="size_nw_se", width=8, height=8)
        self.resize_grip.place(relx=1, rely=1, anchor="se")
        self.resize_grip.bind("<ButtonPress-1>", self.start_resize)
        self.resize_grip.bind("<B1-Motion>", self.resize_window)
        self.bind_wide_drag_areas()
        self.apply_text_panel_state(adjust_window=not self.text_expanded)

    def build_date_panel(self):
        top = tk.Frame(self.date_panel.inner, bg=COLORS["glass"])
        top.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 8))
        top.columnconfigure(0, weight=1)

        date_group = tk.Frame(top, bg=COLORS["glass"])
        date_group.grid(row=0, column=0, sticky="w")
        self.year_button = RoundedButton(
            date_group,
            "",
            command=lambda: self.show_date_grid("year"),
            width=88,
            height=32,
            radius=9,
            fill=COLORS["glass_soft"],
            hover_fill="#eaf4ff",
            parent_bg=COLORS["glass"],
            font=("Microsoft JhengHei UI", 9),
        )
        self.year_button.grid(row=0, column=0, padx=(0, 6))
        self.month_button = RoundedButton(
            date_group,
            "",
            command=lambda: self.show_date_grid("month"),
            width=62,
            height=32,
            radius=9,
            fill=COLORS["glass_soft"],
            hover_fill="#eaf4ff",
            parent_bg=COLORS["glass"],
            font=("Microsoft JhengHei UI", 9),
        )
        self.month_button.grid(row=0, column=1, padx=(0, 6))
        self.day_button = RoundedButton(
            date_group,
            "",
            command=lambda: self.show_date_grid("day"),
            width=62,
            height=32,
            radius=9,
            fill=COLORS["glass_soft"],
            hover_fill="#eaf4ff",
            parent_bg=COLORS["glass"],
            font=("Microsoft JhengHei UI", 9),
        )
        self.day_button.grid(row=0, column=2)

        actions = tk.Frame(top, bg=COLORS["glass"])
        actions.grid(row=0, column=1, sticky="e")
        self.today_button = RoundedButton(
            actions,
            TEXT["today_icon"],
            command=self.set_today,
            width=38,
            height=32,
            radius=9,
            fill=COLORS["glass_soft"],
            hover_fill="#eaf4ff",
            parent_bg=COLORS["glass"],
            font=("Segoe UI Symbol", 12),
        )
        self.today_button.grid(row=0, column=0, padx=(0, 6))
        ToolTip(self.today_button, lambda: TEXT["today"])
        self.clear_button = RoundedButton(
            actions,
            TEXT["clear_icon"],
            command=self.clear_date,
            width=38,
            height=32,
            radius=9,
            fill=COLORS["glass_soft"],
            hover_fill="#eaf4ff",
            parent_bg=COLORS["glass"],
            font=("Segoe UI Symbol", 12),
        )
        self.clear_button.grid(row=0, column=1, padx=(0, 6))
        ToolTip(self.clear_button, lambda: TEXT["clear"])
        self.hide_button = RoundedButton(
            actions,
            TEXT["hide_icon"],
            command=self.hide_date_panel,
            width=38,
            height=32,
            radius=9,
            fill=COLORS["glass_soft"],
            hover_fill="#eaf4ff",
            parent_bg=COLORS["glass"],
            font=("Segoe UI Symbol", 12),
        )
        self.hide_button.grid(row=0, column=2)
        ToolTip(self.hide_button, lambda: TEXT["hide"])

        self.refresh_date_buttons()
        self.date_grid = tk.Frame(self.date_panel.inner, bg=COLORS["glass"])
        self.date_grid.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))
        for column in range(7):
            self.date_grid.columnconfigure(column, weight=1)
        self.date_grid.grid_remove()

    def bind_changes(self):
        self.text.bind("<<Modified>>", self.on_text_modified)
        self.title_var.trace_add("write", lambda *_: self.on_title_changed())
        self.date_var.trace_add("write", lambda *_: self.on_date_changed())
        self.window.bind("<Configure>", self.on_configure)
        self.window.bind("<Map>", self.on_map)

    def bind_drag_handle(self, widget):
        widget.bind("<ButtonPress-1>", self.start_drag, add="+")
        widget.bind("<B1-Motion>", self.drag_window, add="+")

    def bind_wide_drag_areas(self):
        for widget in (
            self.window,
            self.shell,
            self.text_panel,
            self.text_panel.inner,
            self.text,
            self.date_panel,
            self.date_panel.inner,
            self.bottom,
            self.flag_controls,
            self.controls,
        ):
            self.bind_drag_handle(widget)

    def geometry_height(self, geometry):
        try:
            size = geometry.split("+", 1)[0]
            return int(size.split("x", 1)[1])
        except (IndexError, ValueError, AttributeError):
            return 520

    def set_window_height(self, height):
        width = max(self.window.winfo_width(), 330)
        x = self.window.winfo_x()
        y = self.window.winfo_y()
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        self.schedule_rounding(force=True)

    def toggle_text_panel(self):
        self.text_expanded = not self.text_expanded
        self.apply_text_panel_state(adjust_window=True)
        self.schedule_rounding(force=True)
        self.schedule_save()

    def apply_text_panel_state(self, adjust_window=True):
        if not hasattr(self, "text_panel"):
            return
        if self.text_expanded:
            self.shell.rowconfigure(1, weight=1)
            self.bottom.grid_configure(pady=(0, 0))
            self.text_panel.grid(row=1, column=0, sticky="nsew", pady=(12, 10))
            self.text.configure(height=8)
            if hasattr(self, "fold_button"):
                self.fold_button.set_text(TEXT["collapse"])
            if adjust_window:
                self.set_window_height(max(self.expanded_height, 520))
        else:
            self.expanded_height = max(self.window.winfo_height(), 430)
            self.hide_date_panel()
            self.shell.rowconfigure(1, weight=0)
            self.text_panel.grid_remove()
            self.bottom.grid_configure(pady=(COLLAPSED_BUTTON_TOP_GAP, 0))
            if hasattr(self, "fold_button"):
                self.fold_button.set_text(TEXT["expand"])
            if adjust_window:
                self.window.update_idletasks()
                self.set_window_height(COLLAPSED_WINDOW_HEIGHT)

    def start_drag(self, event):
        self.drag_start = (event.x_root, event.y_root, self.window.winfo_x(), self.window.winfo_y())

    def drag_window(self, event):
        if not self.drag_start:
            return
        start_x, start_y, win_x, win_y = self.drag_start
        self.window.geometry(f"+{win_x + event.x_root - start_x}+{win_y + event.y_root - start_y}")

    def start_resize(self, event):
        self.resize_start = (
            event.x_root,
            event.y_root,
            self.window.winfo_width(),
            self.window.winfo_height(),
        )

    def resize_window(self, event):
        if not self.resize_start:
            return
        start_x, start_y, width, height = self.resize_start
        new_width = max(330, width + event.x_root - start_x)
        min_height = 260 if self.text_expanded else COLLAPSED_WINDOW_HEIGHT
        new_height = max(min_height, height + event.y_root - start_y)
        if self.text_expanded:
            self.expanded_height = new_height
        self.window.geometry(f"{new_width}x{new_height}")
        self.schedule_rounding(force=True)

    def apply_window_rounding(self, force=False):
        self.round_after_id = None
        try:
            self.window.update_idletasks()
            width = self.window.winfo_width()
            height = self.window.winfo_height()
            current_size = (width, height)
            if not force and self.last_rounded_size == current_size:
                return
            self.last_rounded_size = current_size
            hwnd = self.window.winfo_id()
            handles = [hwnd]
            parent_hwnd = ctypes.windll.user32.GetParent(hwnd)
            if parent_hwnd and parent_hwnd != hwnd:
                handles.append(parent_hwnd)
            for handle in handles:
                region = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, width + 1, height + 1, WINDOW_CORNER_RADIUS, WINDOW_CORNER_RADIUS)
                ctypes.windll.user32.SetWindowRgn(handle, region, True)
                corner_preference = ctypes.c_int(2)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    handle,
                    33,
                    ctypes.byref(corner_preference),
                    ctypes.sizeof(corner_preference),
                )
        except Exception:
            pass

    def schedule_rounding(self, force=False):
        if self.round_after_id:
            self.window.after_cancel(self.round_after_id)
        self.round_after_id = self.window.after(80, lambda: self.apply_window_rounding(force=force))

    def minimize_window(self):
        self.window.overrideredirect(False)
        self.window.iconify()

    def on_map(self, _event=None):
        self.window.after(80, self.restore_borderless)

    def restore_borderless(self):
        try:
            if self.window.state() != "iconic":
                self.window.overrideredirect(True)
                self.apply_window_rounding(force=True)
        except tk.TclError:
            pass

    def toggle_date_panel(self):
        if self.date_panel_visible:
            self.hide_date_panel()
        else:
            self.show_date_panel()

    def show_date_panel(self):
        self.date_panel_visible = True
        self.date_panel.grid()
        if not self.text_expanded:
            self.set_window_height(COLLAPSED_DATE_WINDOW_HEIGHT)
        else:
            self.schedule_rounding()

    def hide_date_panel(self):
        self.date_panel_visible = False
        self.date_panel.grid_remove()
        self.date_grid.grid_remove()
        if not self.text_expanded:
            self.set_window_height(COLLAPSED_WINDOW_HEIGHT)
        self.schedule_rounding()
        self.schedule_save()

    def toggle_status_menu(self):
        if self.status_menu:
            self.close_status_menu()
            return
        self.status_menu = tk.Toplevel(self.window)
        self.status_menu.wm_overrideredirect(True)
        self.status_menu.attributes("-topmost", True)
        x = self.status_button.winfo_rootx() - 6
        y = self.status_button.winfo_rooty() + 32
        self.status_menu.geometry(f"+{x}+{y}")
        panel = RoundedPanel(self.status_menu, COLORS["glass"], radius=12, parent_bg=COLORS["glass"])
        panel.pack(fill="both", expand=True)
        for row, (status, config) in enumerate(STATUS_CONFIG.items()):
            button = RoundedButton(
                panel.inner,
                "\u25cf",
                command=lambda value=status: self.choose_status(value),
                width=46,
                height=34,
                radius=9,
                fill=config["soft"] if status == self.status_var.get() else COLORS["glass"],
                hover_fill=config["soft"],
                fg=config["color"],
                parent_bg=COLORS["glass"],
                font=("Segoe UI Symbol", 14),
            )
            button.grid(row=row, column=0, sticky="ew", padx=6, pady=(6 if row == 0 else 0, 6))
            ToolTip(button, lambda value=config["label"]: value)
        self.status_menu.focus_force()

    def close_status_menu(self):
        if self.status_menu:
            self.status_menu.destroy()
            self.status_menu = None

    def choose_status(self, status):
        self.close_status_menu()
        self.set_status(status)

    def status_tooltip_text(self):
        return f"{TEXT['status']}\uff1a{STATUS_CONFIG[self.status_var.get()]['label']}"

    def fold_tooltip_text(self):
        return TEXT["collapse_tip"] if self.text_expanded else TEXT["expand_tip"]

    def date_tooltip_text(self):
        selected = parse_iso_date(self.date_var.get())
        if selected:
            return f"{TEXT['date_tip']}\uff1a{selected.strftime('%Y.%m.%d')}"
        return TEXT["date_tip"]

    def apply_status_style(self):
        config = STATUS_CONFIG[self.status_var.get()]
        self.status_button.set_style(fg=config["color"])

    def show_date_grid(self, mode):
        for child in self.date_grid.winfo_children():
            child.destroy()
        self.date_grid.grid()
        if not self.text_expanded:
            self.set_window_height(302)
        if mode == "year":
            self.render_year_grid()
        elif mode == "month":
            self.render_month_grid()
        else:
            self.render_day_grid()
        self.schedule_rounding()

    def render_year_grid(self):
        prev_button = self.make_grid_button("<", self.previous_year_page)
        prev_button.grid(row=0, column=0, sticky="ew", padx=2, pady=2)
        label = tk.Label(
            self.date_grid,
            text=f"{self.year_page_start}-{self.year_page_start + 11}",
            bg=COLORS["glass"],
            fg=COLORS["muted"],
            font=("Microsoft JhengHei UI", 9, "bold"),
        )
        label.grid(row=0, column=1, columnspan=2, sticky="ew", padx=2, pady=2)
        next_button = self.make_grid_button(">", self.next_year_page)
        next_button.grid(row=0, column=3, sticky="ew", padx=2, pady=2)
        for index in range(12):
            year = self.year_page_start + index
            button = self.make_grid_button(str(year), lambda value=year: self.select_year(value), year == self.year_var.get())
            button.grid(row=1 + index // 4, column=index % 4, sticky="ew", padx=2, pady=2)

    def render_month_grid(self):
        for index in range(12):
            month = index + 1
            button = self.make_grid_button(
                f"{month}{TEXT['month']}",
                lambda value=month: self.select_month(value),
                month == self.month_var.get(),
            )
            button.grid(row=index // 4, column=index % 4, sticky="ew", padx=2, pady=2)

    def render_day_grid(self):
        year = int(self.year_var.get())
        month = int(self.month_var.get())
        first_weekday, days_in_month = calendar.monthrange(year, month)
        weekdays = ["\u4e00", "\u4e8c", "\u4e09", "\u56db", "\u4e94", "\u516d", "\u65e5"]
        for column, label_text in enumerate(weekdays):
            label = tk.Label(
                self.date_grid,
                text=label_text,
                bg=COLORS["glass"],
                fg=COLORS["muted"],
                font=("Microsoft JhengHei UI", 8),
            )
            label.grid(row=0, column=column, sticky="ew", padx=1, pady=1)
        for day in range(1, days_in_month + 1):
            position = first_weekday + day - 1
            button = self.make_grid_button(str(day), lambda value=day: self.select_day(value), day == self.day_var.get())
            button.grid(row=1 + position // 7, column=position % 7, sticky="ew", padx=1, pady=1)

    def make_grid_button(self, text, command, selected=False):
        return RoundedButton(
            self.date_grid,
            text,
            command=command,
            width=42,
            height=30,
            radius=8,
            fill=COLORS["accent"] if selected else COLORS["glass_soft"],
            hover_fill=COLORS["accent_hover"] if selected else "#eaf4ff",
            fg="white" if selected else COLORS["text"],
            parent_bg=COLORS["glass"],
            font=("Microsoft JhengHei UI", 9),
        )

    def previous_year_page(self):
        self.year_page_start -= 12
        self.show_date_grid("year")

    def next_year_page(self):
        self.year_page_start += 12
        self.show_date_grid("year")

    def select_year(self, year):
        self.year_var.set(year)
        self.commit_selected_date()
        self.show_date_grid("month")

    def select_month(self, month):
        self.month_var.set(month)
        self.commit_selected_date()
        self.show_date_grid("day")

    def select_day(self, day):
        self.day_var.set(day)
        self.commit_selected_date()
        self.date_grid.grid_remove()
        self.schedule_rounding()

    def commit_selected_date(self):
        selected = self.read_selected_date()
        self.set_date_parts(selected)
        self.date_var.set(selected.isoformat())
        self.refresh_date_buttons()

    def refresh_date_buttons(self):
        if hasattr(self, "year_button"):
            self.year_button.set_text(f"{self.year_var.get()}{TEXT['year']}")
            self.month_button.set_text(f"{self.month_var.get()}{TEXT['month']}")
            self.day_button.set_text(f"{self.day_var.get()}{TEXT['day']}")

    def set_status(self, status):
        self.status_var.set(status)
        if status == "done" and not self.date_var.get().strip():
            self.set_today()
        self.apply_status_style()
        self.update_date_summary()
        self.auto_mark_urgent()
        self.schedule_save()

    def on_title_changed(self):
        title = self.title_var.get().strip() or TEXT["window_title"]
        self.window.title(title)
        self.schedule_save()

    def read_selected_date(self):
        today = date.today()
        try:
            year = int(self.year_var.get())
        except (tk.TclError, ValueError):
            year = today.year
        try:
            month = int(self.month_var.get())
        except (tk.TclError, ValueError):
            month = today.month
        try:
            day = int(self.day_var.get())
        except (tk.TclError, ValueError):
            day = today.day
        year = min(max(year, 2000), 2100)
        month = min(max(month, 1), 12)
        day = min(max(day, 1), calendar.monthrange(year, month)[1])
        return date(year, month, day)

    def set_date_parts(self, selected):
        self.year_var.set(selected.year)
        self.month_var.set(selected.month)
        self.day_var.set(selected.day)
        self.refresh_date_buttons()

    def set_today(self):
        today = date.today()
        self.set_date_parts(today)
        self.date_var.set(today.isoformat())
        self.show_date_grid("day")

    def clear_date(self):
        self.date_var.set("")
        self.update_date_summary()
        self.schedule_save()

    def on_date_changed(self):
        selected = parse_iso_date(self.date_var.get())
        if selected:
            self.set_date_parts(selected)
        self.update_date_summary()
        self.auto_mark_urgent()
        self.schedule_save()

    def update_date_summary(self):
        selected = parse_iso_date(self.date_var.get())
        text = format_date_for_button(self.date_var.get())
        if not selected:
            self.date_pill.set_text(text)
            self.date_pill.set_style(fill="#ffffff", hover_fill="#edf6ff", fg=COLORS["muted"])
            self.update_flags_style()
            return
        fill = "#ffffff"
        fg = COLORS["soft_text"]
        if self.status_var.get() != "done" and (selected - date.today()).days <= 2:
            fill = COLORS["danger_soft"]
            fg = COLORS["danger"]
        self.date_pill.set_text(text)
        self.date_pill.set_style(fill=fill, hover_fill="#edf6ff", fg=fg)
        self.update_flags_style()

    def toggle_flag(self, variable, callback):
        variable.set(not variable.get())
        callback()

    def update_flags_style(self):
        if not hasattr(self, "important_button"):
            return
        self.style_toggle_button(
            self.important_button,
            self.important_var.get(),
            COLORS["important"],
            off_hover=COLORS["important_soft"],
            off_fg=COLORS["important"],
        )
        self.style_toggle_button(
            self.urgent_button,
            self.urgent_var.get(),
            COLORS["danger"],
            off_hover=COLORS["danger_soft"],
            off_fg=COLORS["danger"],
        )

    def style_toggle_button(self, button, selected, color, off_hover="#edf6ff", off_fg=None):
        if selected:
            button.set_style(fill=color, hover_fill=color, fg="white")
        else:
            button.set_style(fill="#ffffff", hover_fill=off_hover, fg=off_fg or COLORS["soft_text"])

    def auto_mark_urgent(self):
        selected = parse_iso_date(self.date_var.get())
        if not selected or self.status_var.get() == "done":
            self.update_flags_style()
            return
        if (selected - date.today()).days <= 2 and not self.urgent_var.get():
            self.urgent_var.set(True)
        self.update_flags_style()

    def on_flag_changed(self):
        self.update_flags_style()
        self.schedule_save()

    def toggle_top(self):
        self.top_var.set(not self.top_var.get())
        self.on_top_changed()

    def update_top_style(self):
        if not hasattr(self, "top_button"):
            return
        if self.top_var.get():
            self.top_button.set_style(fill=COLORS["accent"], hover_fill=COLORS["accent_hover"], fg="white")
        else:
            self.top_button.set_style(fill=COLORS["mica"], hover_fill="#dbeafe", fg=COLORS["soft_text"])

    def on_top_changed(self):
        self.window.attributes("-topmost", bool(self.top_var.get()))
        self.update_top_style()
        self.schedule_save()

    def on_text_modified(self, _event=None):
        if self.text.edit_modified():
            self.text.edit_modified(False)
            self.schedule_save()

    def on_configure(self, _event=None):
        current_size = (self.window.winfo_width(), self.window.winfo_height())
        if self.last_configure_size != current_size:
            self.last_configure_size = current_size
            self.schedule_rounding()
        self.schedule_save()

    def schedule_save(self):
        if self.save_after_id:
            self.window.after_cancel(self.save_after_id)
        self.save_after_id = self.window.after(250, self.save)

    def save(self):
        self.save_after_id = None
        self.note.title = self.title_var.get().strip() or TEXT["default_title"]
        self.note.text = self.text.get("1.0", "end-1c")
        self.note.status = self.status_var.get()
        self.note.important = bool(self.important_var.get())
        self.note.urgent = bool(self.urgent_var.get())
        self.note.completed_date = self.date_var.get().strip()
        self.note.always_on_top = bool(self.top_var.get())
        self.note.text_expanded = bool(self.text_expanded)
        self.note.geometry = self.window.geometry()
        self.app.save_notes()

    def close(self, destroy_only=False):
        self.close_status_menu()
        if self.save_after_id:
            self.window.after_cancel(self.save_after_id)
            self.save_after_id = None
        if self.round_after_id:
            self.window.after_cancel(self.round_after_id)
            self.round_after_id = None
        if not destroy_only:
            self.save()
        self.window.destroy()
        self.app.close_window(self.note.id)


if __name__ == "__main__":
    StickyTodoApp().run()
