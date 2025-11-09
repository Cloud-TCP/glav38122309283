"""Tkinter based user interface for the Shopot application."""
from __future__ import annotations

import base64
import math
import mimetypes
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import cast

from .document import ShopotDocument
from .keyfiles import KeyArray
from .passwords import password_to_key_material, validate_password


IMAGE_HEADER_PREFIX = "::image::"
IMAGE_FOOTER = "::end-image::"


@dataclass
class ImageBlockData:
    """Structured data for an embedded image block."""

    mime: str
    data: str
    caption: str


@dataclass
class ImageWidget:
    """Runtime metadata for an embedded image widget inside the editor."""

    frame: tk.Widget
    photo: tk.PhotoImage
    caption_var: tk.StringVar
    block: ImageBlockData


def _encode_caption(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


def _decode_caption(value: str) -> str:
    try:
        return base64.b64decode(value.encode("ascii")).decode("utf-8")
    except Exception:
        return value


def _build_image_header(block: ImageBlockData) -> str:
    caption64 = _encode_caption(block.caption)
    return f"{IMAGE_HEADER_PREFIX}mime={block.mime};caption64={caption64}"


def _parse_image_header(line: str) -> ImageBlockData | None:
    if not line.startswith(IMAGE_HEADER_PREFIX):
        return None
    content = line[len(IMAGE_HEADER_PREFIX) :]
    parts = content.split(";")
    values: dict[str, str] = {}
    for part in parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        values[key] = value
    mime = values.get("mime")
    caption64 = values.get("caption64", "")
    if not mime:
        return None
    caption = _decode_caption(caption64)
    return ImageBlockData(mime=mime, data="", caption=caption)


class ShopotApp(tk.Tk):
    """Main Tkinter application window."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Shopot File Viewer")
        self.geometry("900x600")

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        self.frames: dict[str, tk.Frame] = {}
        for FrameClass in (HomePage, DocumentEditorPage, KeyArrayPage):
            frame = FrameClass(parent=container, controller=self)
            frame.grid(row=0, column=0, sticky="nsew")
            self.frames[FrameClass.__name__] = frame

        self.show_frame("HomePage")

    def show_frame(self, name: str) -> None:
        frame = self.frames[name]
        frame.tkraise()

    # Navigation helpers -------------------------------------------------
    def open_document_flow(self) -> None:
        doc_path = filedialog.askopenfilename(
            title="Open Shopot document",
            filetypes=[("Shopot Document", "*.shpt"), ("All Files", "*")],
        )
        if not doc_path:
            return
        key_context = self._prompt_for_key_context()
        if key_context is None:
            return
        try:
            key_material = password_to_key_material(key_context.password, key_context.key_array)
            document = ShopotDocument.load(doc_path, key_material)
        except Exception as exc:
            messagebox.showerror("Failed to open", str(exc), parent=self)
            return
        editor = cast(DocumentEditorPage, self.frames["DocumentEditorPage"])
        editor.display_document(
            text=document.text,
            document_path=doc_path,
            key_array=key_context.key_array,
            key_path=key_context.key_path,
            password=key_context.password,
        )
        self.show_frame("DocumentEditorPage")

    def create_new_document(self) -> None:
        editor = cast(DocumentEditorPage, self.frames["DocumentEditorPage"])
        editor.display_document(text="", document_path=None, key_array=None, key_path=None, password=None)
        self.show_frame("DocumentEditorPage")

    def show_key_manager(self) -> None:
        self.show_frame("KeyArrayPage")

    # Internal utilities -------------------------------------------------
    def _prompt_for_key_context(self) -> "KeyContext | None":
        key_path = filedialog.askopenfilename(
            title="Select key array",
            filetypes=[("Shopot Key Array", "*.shptk"), ("All Files", "*")],
        )
        if not key_path:
            return None
        password = simpledialog.askstring(
            "Password", "Enter 10-digit password", parent=self, show="*"
        )
        if password is None:
            return None
        try:
            validate_password(password)
            key_array = KeyArray.load(key_path)
        except Exception as exc:
            messagebox.showerror("Invalid key", str(exc), parent=self)
            return None
        return KeyContext(key_array=key_array, password=password, key_path=key_path)


class HomePage(ttk.Frame):
    def __init__(self, parent: tk.Widget, controller: ShopotApp) -> None:
        super().__init__(parent)
        self.controller = controller

        title = ttk.Label(self, text="Shopot File Viewer", font=("TkDefaultFont", 20, "bold"))
        title.pack(pady=20)

        description = ttk.Label(
            self,
            text=(
                "Open encrypted Shopot documents or create new ones."
                " You will need both a key array (.shptk) and the 10-digit password"
                " associated with it to access documents."
            ),
            wraplength=600,
            justify="center",
        )
        description.pack(pady=10)

        button_frame = ttk.Frame(self)
        button_frame.pack(pady=30)

        ttk.Button(button_frame, text="Open document", command=self.controller.open_document_flow).grid(
            row=0, column=0, padx=10, pady=10
        )
        ttk.Button(button_frame, text="Create new document", command=self.controller.create_new_document).grid(
            row=0, column=1, padx=10, pady=10
        )
        ttk.Button(button_frame, text="Manage key arrays", command=self.controller.show_key_manager).grid(
            row=0, column=2, padx=10, pady=10
        )


class DocumentEditorPage(ttk.Frame):
    MAX_IMAGE_WIDTH = 600
    MAX_IMAGE_HEIGHT = 400

    def __init__(self, parent: tk.Widget, controller: ShopotApp) -> None:
        super().__init__(parent)
        self.controller = controller

        self.current_document_path: str | None = None
        self.current_key_path: str | None = None
        self.current_password: str | None = None
        self.key_array: KeyArray | None = None
        self._image_widgets: dict[str, ImageWidget] = {}

        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x")

        ttk.Button(toolbar, text="Back", command=lambda: controller.show_frame("HomePage")).pack(side="left", padx=5, pady=5)
        ttk.Button(toolbar, text="Open", command=controller.open_document_flow).pack(side="left", padx=5)
        ttk.Button(toolbar, text="Save", command=self.save_document).pack(side="left", padx=5)
        ttk.Button(toolbar, text="Save As", command=self.save_document_as).pack(side="left", padx=5)
        ttk.Button(toolbar, text="Set Key", command=self.set_key_context).pack(side="left", padx=5)

        format_toolbar = ttk.Frame(self)
        format_toolbar.pack(fill="x")

        ttk.Button(format_toolbar, text="Italic", command=self.apply_italic).pack(side="left", padx=5, pady=2)
        ttk.Button(format_toolbar, text="Bold", command=self.apply_bold).pack(side="left", padx=5, pady=2)
        ttk.Button(format_toolbar, text="Bold + Italic", command=self.apply_bold_italic).pack(side="left", padx=5, pady=2)
        ttk.Button(format_toolbar, text="H1", command=lambda: self.apply_heading(1)).pack(side="left", padx=5, pady=2)
        ttk.Button(format_toolbar, text="H2", command=lambda: self.apply_heading(2)).pack(side="left", padx=5, pady=2)
        ttk.Button(format_toolbar, text="Add Image", command=self.add_image).pack(side="left", padx=5, pady=2)

        self.status_var = tk.StringVar(value="No document loaded")
        ttk.Label(self, textvariable=self.status_var).pack(fill="x", padx=5, pady=5)

        self.text_widget = tk.Text(self, wrap=tk.WORD)
        self.text_widget.pack(fill="both", expand=True, padx=5, pady=5)

    # Display ------------------------------------------------------------
    def display_document(
        self,
        *,
        text: str,
        document_path: str | None,
        key_array: KeyArray | None,
        key_path: str | None,
        password: str | None,
    ) -> None:
        self._render_document_text(text)
        self.current_document_path = document_path
        self.key_array = key_array
        self.current_key_path = key_path
        self.current_password = password
        if document_path:
            status = f"Editing: {Path(document_path).name}"
        else:
            status = "Editing new document"
        if key_path:
            status += f" | Key: {Path(key_path).name}"
        self.status_var.set(status)

    # Key handling -------------------------------------------------------
    def set_key_context(self) -> None:
        key_path = filedialog.askopenfilename(
            title="Select key array",
            filetypes=[("Shopot Key Array", "*.shptk"), ("All Files", "*")],
        )
        if not key_path:
            return
        password = simpledialog.askstring(
            "Password", "Enter 10-digit password", parent=self, show="*"
        )
        if password is None:
            return
        try:
            key_array = KeyArray.load(key_path)
            password_to_key_material(password, key_array)
        except Exception as exc:
            messagebox.showerror("Invalid key", str(exc), parent=self)
            return
        self.key_array = key_array
        self.current_key_path = key_path
        self.current_password = password
        self.status_var.set(f"Key loaded: {Path(key_path).name}")

    # Saving -------------------------------------------------------------
    def save_document(self) -> None:
        if not self.current_document_path:
            self.save_document_as()
            return
        self._perform_save(self.current_document_path)

    def save_document_as(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save Shopot document",
            defaultextension=".shpt",
            filetypes=[("Shopot Document", "*.shpt"), ("All Files", "*")],
        )
        if not path:
            return
        self._perform_save(path)
        self.current_document_path = path
        self.status_var.set(f"Saved: {Path(path).name}")

    def _perform_save(self, path: str) -> None:
        if self.key_array is None or self.current_password is None:
            messagebox.showwarning("Missing key", "Please set a key array and password before saving.", parent=self)
            return
        try:
            key_material = password_to_key_material(self.current_password, self.key_array)
            document_text = self._serialize_document_text()
            document = ShopotDocument(text=document_text)
            document.save(path, key_material)
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc), parent=self)

    # Image helpers -----------------------------------------------------
    def add_image(self) -> None:
        path = filedialog.askopenfilename(
            title="Select image",
            filetypes=[("Image files", "*.png *.gif"), ("PNG", "*.png"), ("GIF", "*.gif"), ("All Files", "*")],
        )
        if not path:
            return
        mime, _ = mimetypes.guess_type(path)
        if mime not in {"image/png", "image/gif"}:
            messagebox.showerror("Unsupported image", "Only PNG and GIF images are supported for embedding.", parent=self)
            return
        try:
            data = Path(path).read_bytes()
        except OSError as exc:
            messagebox.showerror("Failed to read image", str(exc), parent=self)
            return
        encoded = base64.b64encode(data).decode("ascii")
        block = ImageBlockData(mime=mime or "image/png", data=encoded, caption="Image caption")
        try:
            self._insert_image_widget(block, self.text_widget.index("insert"))
        except Exception as exc:
            messagebox.showerror("Insert failed", str(exc), parent=self)

    def _render_document_text(self, text: str) -> None:
        self.text_widget.configure(state="normal")
        self.text_widget.delete("1.0", tk.END)
        self._image_widgets.clear()
        segments = self._parse_document_text(text)
        for kind, payload in segments:
            if kind == "text":
                if payload:
                    self.text_widget.insert(tk.END, payload)
            elif kind == "image":
                self._insert_image_widget(payload, self.text_widget.index(tk.END))
        self.text_widget.mark_set("insert", tk.END)
        self.text_widget.focus_set()

    def _parse_document_text(self, text: str) -> list[tuple[str, str | ImageBlockData]]:
        segments: list[tuple[str, str | ImageBlockData]] = []
        pos = 0
        while True:
            start = text.find(IMAGE_HEADER_PREFIX, pos)
            if start == -1:
                remaining = text[pos:]
                if remaining:
                    segments.append(("text", remaining))
                break
            before = text[pos:start]
            if before:
                segments.append(("text", before))
            header_end = text.find("\n", start)
            if header_end == -1:
                segments.append(("text", text[start:]))
                break
            header_line = text[start:header_end]
            data_start = header_end + 1
            footer_token = "\n" + IMAGE_FOOTER
            footer_pos = text.find(footer_token, data_start)
            if footer_pos == -1:
                segments.append(("text", text[start:]))
                break
            data = text[data_start:footer_pos]
            block_end = footer_pos + len(footer_token)
            trailing_newline = block_end < len(text) and text[block_end] == "\n"
            if trailing_newline:
                block_end += 1
            pos = block_end
            block = _parse_image_header(header_line)
            if block is None:
                raw = text[start:pos]
                segments.append(("text", raw))
                continue
            block.data = data.strip()
            segments.append(("image", block))
        return segments

    def _insert_image_widget(self, block: ImageBlockData, index: str) -> None:
        index = self._normalize_image_index(index)
        widget = self._create_image_frame(block)
        self.text_widget.window_create(index, window=widget.frame)
        after = self.text_widget.index(f"{index} +1c")
        self.text_widget.insert(after, "\n")
        self.text_widget.mark_set("insert", self.text_widget.index(f"{after} +1c"))

    def _normalize_image_index(self, index: str) -> str:
        index = self.text_widget.index(index)
        if index == tk.END:
            index = self.text_widget.index("end-1c")
        if index in {"0.0", "-1.0"}:
            index = "1.0"
        if index != "1.0":
            prev_char = self.text_widget.get(f"{index}-1c", index)
            if prev_char != "\n":
                self.text_widget.insert(index, "\n")
                index = self.text_widget.index("insert")
        line_start = self.text_widget.index(f"{index} linestart")
        line_end = self.text_widget.index(f"{index} lineend")
        line_text = self.text_widget.get(line_start, line_end)
        if line_text.strip():
            self.text_widget.insert(line_end, "\n")
            index = self.text_widget.index(f"{line_end}+1c")
        else:
            index = line_start
        return index

    def _create_image_frame(self, block: ImageBlockData) -> ImageWidget:
        frame = ttk.Frame(self.text_widget)
        try:
            photo = self._create_photo_image(block)
        except tk.TclError as exc:
            raise RuntimeError(f"Unable to display image: {exc}")
        image_label = ttk.Label(frame, image=photo)
        image_label.image = photo  # keep reference on the widget
        image_label.pack(padx=5, pady=(5, 0))

        caption_var = tk.StringVar(value=block.caption)
        caption_frame = ttk.Frame(frame)
        download_command = lambda b=block, v=caption_var: self._download_image(b, v)
        ttk.Button(caption_frame, text="Download Img", command=download_command).pack(side="left", padx=(0, 6))
        ttk.Entry(caption_frame, textvariable=caption_var, width=40).pack(side="left", fill="x", expand=True)
        caption_frame.pack(fill="x", padx=5, pady=(2, 8))

        widget = ImageWidget(frame=frame, photo=photo, caption_var=caption_var, block=block)
        self._image_widgets[str(frame)] = widget
        return widget

    def _create_photo_image(self, block: ImageBlockData) -> tk.PhotoImage:
        photo = tk.PhotoImage(data=block.data)
        width = photo.width()
        height = photo.height()
        widget_width = self.text_widget.winfo_width() or 800
        widget_height = self.text_widget.winfo_height() or 600
        max_width = min(self.MAX_IMAGE_WIDTH, max(250, int(widget_width * 0.6)))
        max_height = min(self.MAX_IMAGE_HEIGHT, max(250, int(widget_height * 0.6)))
        scale = max(width / max_width if max_width else 1, height / max_height if max_height else 1)
        if scale > 1:
            factor = max(1, math.ceil(scale))
            photo = photo.subsample(factor, factor)
        return photo

    def _download_image(self, block: ImageBlockData, caption_var: tk.StringVar) -> None:
        caption = caption_var.get().strip() or "shopot-image"
        safe_caption = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in caption)
        ext = mimetypes.guess_extension(block.mime) or ".img"
        path = filedialog.asksaveasfilename(
            title="Save image",
            defaultextension=ext,
            initialfile=f"{safe_caption}{ext}",
            filetypes=[(block.mime, f"*{ext}"), ("All Files", "*")],
        )
        if not path:
            return
        try:
            data = base64.b64decode(block.data.encode("ascii"))
            Path(path).write_bytes(data)
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc), parent=self)
            return
        messagebox.showinfo("Saved", f"Image saved to {path}", parent=self)

    def _gather_document_segments(self) -> list[tuple[str, str | ImageBlockData]]:
        segments: list[tuple[str, str | ImageBlockData]] = []
        buffer: list[str] = []
        for kind, value, _ in self.text_widget.dump("1.0", "end-1c", text=True, window=True):
            if kind == "text":
                buffer.append(value)
            elif kind == "window":
                if buffer:
                    segments.append(("text", "".join(buffer)))
                    buffer.clear()
                widget = self._image_widgets.get(value)
                if widget:
                    block = ImageBlockData(
                        mime=widget.block.mime,
                        data=widget.block.data,
                        caption=widget.caption_var.get().strip(),
                    )
                    segments.append(("image", block))
        if buffer:
            segments.append(("text", "".join(buffer)))
        return segments

    def _serialize_document_text(self) -> str:
        segments = self._gather_document_segments()
        parts: list[str] = []
        for kind, payload in segments:
            if kind == "text":
                parts.append(payload)
                continue
            block = payload  # type: ignore[assignment]
            caption = block.caption.replace("\n", " ")
            block.caption = caption
            if parts and not parts[-1].endswith("\n"):
                parts.append("\n")
            header = _build_image_header(block)
            parts.append(f"{header}\n{block.data}\n{IMAGE_FOOTER}\n")
        return "".join(parts)

    # Formatting helpers ------------------------------------------------
    def apply_italic(self) -> None:
        self._wrap_selection("*")

    def apply_bold(self) -> None:
        self._wrap_selection("**")

    def apply_bold_italic(self) -> None:
        self._wrap_selection("***")

    def apply_heading(self, level: int) -> None:
        prefix = "#" * level + " "
        line_start = self.text_widget.index("insert linestart")
        line_end = self.text_widget.index("insert lineend")
        line_text = self.text_widget.get(line_start, line_end)

        if "\uFFFC" in line_text:
            messagebox.showinfo("Invalid target", "Headings cannot be applied to image lines.", parent=self)
            return

        stripped = line_text.lstrip()
        if stripped.startswith("## "):
            content = stripped[3:]
        elif stripped.startswith("# "):
            content = stripped[2:]
        else:
            content = stripped

        new_line = prefix + content
        self.text_widget.delete(line_start, line_end)
        self.text_widget.insert(line_start, new_line)
        self.text_widget.mark_set("insert", f"{line_start}+{len(prefix)}c")
        self.text_widget.focus_set()

    def _wrap_selection(self, marker: str) -> None:
        try:
            start = self.text_widget.index("sel.first")
            end = self.text_widget.index("sel.last")
        except tk.TclError:
            messagebox.showinfo("No selection", "Highlight text before applying formatting.", parent=self)
            return

        if self._selection_contains_window(start, end):
            messagebox.showinfo("Invalid selection", "Formatting cannot span embedded images.", parent=self)
            return

        selected_text = self.text_widget.get(start, end)
        prefix = marker
        suffix = marker
        wrapped = f"{prefix}{selected_text}{suffix}"

        self.text_widget.delete(start, end)
        self.text_widget.insert(start, wrapped)

        self.text_widget.tag_remove("sel", "1.0", tk.END)
        self.text_widget.tag_add("sel", start, f"{start}+{len(wrapped)}c")
        self.text_widget.focus_set()

    def _selection_contains_window(self, start: str, end: str) -> bool:
        for kind, _, _ in self.text_widget.dump(start, end, text=False, window=True):
            if kind == "window":
                return True
        return False


class KeyArrayPage(ttk.Frame):
    def __init__(self, parent: tk.Widget, controller: ShopotApp) -> None:
        super().__init__(parent)
        self.controller = controller
        self.key_array: KeyArray | None = None
        self.current_layer = 0

        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x")

        ttk.Button(toolbar, text="Back", command=lambda: controller.show_frame("HomePage")).pack(side="left", padx=5, pady=5)
        ttk.Button(toolbar, text="Load", command=self.load_key_array).pack(side="left", padx=5)
        ttk.Button(toolbar, text="Generate new", command=self.generate_key_array).pack(side="left", padx=5)
        ttk.Button(toolbar, text="Save As", command=self.save_key_array).pack(side="left", padx=5)

        self.layer_label = ttk.Label(self, text="No key array loaded")
        self.layer_label.pack(pady=10)

        navigation = ttk.Frame(self)
        navigation.pack()
        ttk.Button(navigation, text="Previous", command=self.prev_layer).grid(row=0, column=0, padx=5)
        ttk.Button(navigation, text="Next", command=self.next_layer).grid(row=0, column=1, padx=5)

        self.text_widget = tk.Text(self, width=80, height=30, wrap="none")
        self.text_widget.configure(font=("Courier", 10))
        self.text_widget.pack(fill="both", expand=True, padx=10, pady=10)
        self.text_widget.configure(state="disabled")

        info = ttk.Label(
            self,
            text=(
                "Use this page to inspect or generate key arrays."
                " The viewer displays a single layer at a time."
            ),
            wraplength=600,
            justify="center",
        )
        info.pack(pady=10)

    # Key array management ----------------------------------------------
    def load_key_array(self) -> None:
        path = filedialog.askopenfilename(
            title="Open Shopot key array",
            filetypes=[("Shopot Key Array", "*.shptk"), ("All Files", "*")],
        )
        if not path:
            return
        try:
            self.key_array = KeyArray.load(path)
        except Exception as exc:
            messagebox.showerror("Failed to load", str(exc), parent=self)
            return
        self.current_layer = 0
        self._refresh_layer_display()

    def generate_key_array(self) -> None:
        self.key_array = KeyArray.generate()
        self.current_layer = 0
        self._refresh_layer_display()

    def save_key_array(self) -> None:
        if self.key_array is None:
            messagebox.showwarning("No key array", "Generate or load a key array first.", parent=self)
            return
        path = filedialog.asksaveasfilename(
            title="Save Shopot key array",
            defaultextension=".shptk",
            filetypes=[("Shopot Key Array", "*.shptk"), ("All Files", "*")],
        )
        if not path:
            return
        self.key_array.dump(path)
        messagebox.showinfo("Saved", f"Key array saved to {path}", parent=self)

    # Layer navigation ---------------------------------------------------
    def prev_layer(self) -> None:
        if self.key_array is None:
            return
        self.current_layer = (self.current_layer - 1) % len(self.key_array.layers)
        self._refresh_layer_display()

    def next_layer(self) -> None:
        if self.key_array is None:
            return
        self.current_layer = (self.current_layer + 1) % len(self.key_array.layers)
        self._refresh_layer_display()

    def _refresh_layer_display(self) -> None:
        if self.key_array is None:
            self.layer_label.config(text="No key array loaded")
            self._set_text("")
            return
        total = len(self.key_array.layers)
        self.layer_label.config(text=f"Layer {self.current_layer + 1} of {total}")
        text = self.key_array.as_text(self.current_layer)
        self._set_text(text)

    def _set_text(self, text: str) -> None:
        self.text_widget.configure(state="normal")
        self.text_widget.delete("1.0", tk.END)
        self.text_widget.insert("1.0", text)
        self.text_widget.configure(state="disabled")


@dataclass(frozen=True)
class KeyContext:
    key_array: KeyArray
    password: str
    key_path: str
