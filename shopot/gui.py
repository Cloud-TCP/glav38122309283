"""Tkinter based user interface for the Shopot application."""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from dataclasses import dataclass
from typing import cast

from .document import ShopotDocument
from .keyfiles import KeyArray
from .passwords import password_to_key_material, validate_password


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
    def __init__(self, parent: tk.Widget, controller: ShopotApp) -> None:
        super().__init__(parent)
        self.controller = controller

        self.current_document_path: str | None = None
        self.current_key_path: str | None = None
        self.current_password: str | None = None
        self.key_array: KeyArray | None = None

        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x")

        ttk.Button(toolbar, text="Back", command=lambda: controller.show_frame("HomePage")).pack(side="left", padx=5, pady=5)
        ttk.Button(toolbar, text="Open", command=controller.open_document_flow).pack(side="left", padx=5)
        ttk.Button(toolbar, text="Save", command=self.save_document).pack(side="left", padx=5)
        ttk.Button(toolbar, text="Save As", command=self.save_document_as).pack(side="left", padx=5)
        ttk.Button(toolbar, text="Set Key", command=self.set_key_context).pack(side="left", padx=5)

        self.status_var = tk.StringVar(value="No document loaded")
        ttk.Label(self, textvariable=self.status_var).pack(fill="x", padx=5, pady=5)

        self.text_widget = tk.Text(self, wrap="word")
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
        self.text_widget.delete("1.0", tk.END)
        self.text_widget.insert("1.0", text)
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
            document = ShopotDocument(text=self.text_widget.get("1.0", tk.END))
            document.save(path, key_material)
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc), parent=self)


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
