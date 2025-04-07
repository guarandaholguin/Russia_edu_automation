"""
Custom widget components for the Russia-Edu Status Checker application.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable, Any, List, Dict, Tuple
import threading
import time

import customtkinter as ctk
from PIL import Image, ImageTk

class ScrollableFrame(ctk.CTkFrame):
    """A frame with a scrollbar."""
    
    def __init__(self, master, **kwargs):
        """
        Initialize the scrollable frame.
        
        Args:
            master: Parent widget.
            **kwargs: Additional arguments for the frame.
        """
        super().__init__(master, **kwargs)
        
        # Create a canvas and scrollbar
        self.canvas = tk.Canvas(self, bg=self._fg_color, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ctk.CTkFrame(self.canvas)
        
        # Configure canvas
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Pack widgets
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel event
        self.bind_mousewheel()
    
    def bind_mousewheel(self):
        """Bind mousewheel event to scroll the frame."""
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        # Bind for different platforms
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)  # Windows and macOS
        self.canvas.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))  # Linux
        self.canvas.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))  # Linux
    
    def unbind_mousewheel(self):
        """Unbind mousewheel event."""
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")


class LabeledEntry(ctk.CTkFrame):
    """A labeled entry widget."""
    
    def __init__(self, master, label_text: str, width: int = 200, **kwargs):
        """
        Initialize the labeled entry.
        
        Args:
            master: Parent widget.
            label_text (str): Label text.
            width (int, optional): Width of the entry. Defaults to 200.
            **kwargs: Additional arguments for the entry.
        """
        super().__init__(master)
        
        # Create label and entry
        self.label = ctk.CTkLabel(self, text=label_text)
        self.entry = ctk.CTkEntry(self, width=width, **kwargs)
        
        # Pack widgets
        self.label.pack(anchor="w", padx=5, pady=(5, 0))
        self.entry.pack(fill="x", padx=5, pady=(0, 5))
    
    def get(self) -> str:
        """
        Get the entry value.
        
        Returns:
            str: Entry value.
        """
        return self.entry.get()
    
    def set(self, value: str):
        """
        Set the entry value.
        
        Args:
            value (str): Value to set.
        """
        self.entry.delete(0, tk.END)
        self.entry.insert(0, value)


class StatusBar(ctk.CTkFrame):
    """A status bar widget with message and progress indicator."""
    
    def __init__(self, master, **kwargs):
        """
        Initialize the status bar.
        
        Args:
            master: Parent widget.
            **kwargs: Additional arguments for the frame.
        """
        super().__init__(master, **kwargs)
        
        # Status variables
        self.status_text = tk.StringVar(value="Ready")
        self.is_busy = False
        self.busy_thread = None
        
        # Create widgets
        self.status_label = ctk.CTkLabel(self, textvariable=self.status_text, anchor="w")
        self.busy_indicator = tk.Label(self, text="●", fg="gray")
        
        # Pack widgets
        self.busy_indicator.pack(side="right", padx=5)
        self.status_label.pack(side="left", fill="x", expand=True, padx=5)
    
    def set_status(self, message: str, is_busy: bool = False):
        """
        Set the status message and busy state.
        
        Args:
            message (str): Status message.
            is_busy (bool, optional): Whether the application is busy. Defaults to False.
        """
        self.status_text.set(message)
        
        if is_busy != self.is_busy:
            self.is_busy = is_busy
            
            # Stop existing thread if any
            if self.busy_thread and self.busy_thread.is_alive():
                self.busy_thread = None
            
            # Start or stop busy indicator
            if is_busy:
                self.busy_thread = threading.Thread(target=self._animate_busy, daemon=True)
                self.busy_thread.start()
            else:
                self.busy_indicator.config(fg="gray", text="●")
    
    def _animate_busy(self):
        """Animate the busy indicator."""
        colors = ["#4a6984", "#3a7ebf", "#1f538d", "#3a7ebf"]
        i = 0
        
        while self.is_busy and self.busy_thread:
            self.busy_indicator.config(fg=colors[i], text="●")
            i = (i + 1) % len(colors)
            time.sleep(0.5)


class IconButton(ctk.CTkButton):
    """A button with an icon."""
    
    def __init__(self, master, icon_path: str, hover_text: str = "", command: Optional[Callable] = None, **kwargs):
        """
        Initialize the icon button.
        
        Args:
            master: Parent widget.
            icon_path (str): Path to the icon image.
            hover_text (str, optional): Hover text. Defaults to "".
            command (Callable, optional): Button command. Defaults to None.
            **kwargs: Additional arguments for the button.
        """
        # Load icon
        try:
            icon = ctk.CTkImage(
                light_image=Image.open(icon_path),
                dark_image=Image.open(icon_path),
                size=(20, 20)
            )
            kwargs["image"] = icon
        except Exception as e:
            print(f"Error loading icon: {e}")
        
        # Initialize button
        super().__init__(master, command=command, text="", **kwargs)
        
        # Add tooltip if hover_text is provided
        if hover_text:
            self._create_tooltip(hover_text)
    
    def _create_tooltip(self, text: str):
        """
        Create a tooltip for the button.
        
        Args:
            text (str): Tooltip text.
        """
        tooltip = tk.Label(self.winfo_toplevel(), text=text, background="#ffffe0", relief="solid", borderwidth=1)
        tooltip.withdraw()
        
        def enter(event):
            x, y, _, _ = self.bbox("all")
            x += self.winfo_rootx() + 25
            y += self.winfo_rooty() + 25
            tooltip.geometry(f"+{x}+{y}")
            tooltip.deiconify()
        
        def leave(event):
            tooltip.withdraw()
        
        self.bind("<Enter>", enter)
        self.bind("<Leave>", leave)


class ConfirmDialog(ctk.CTkToplevel):
    """A dialog to confirm an action."""
    
    def __init__(self, master, title: str, message: str):
        """
        Initialize the confirm dialog.
        
        Args:
            master: Parent widget.
            title (str): Dialog title.
            message (str): Dialog message.
        """
        super().__init__(master)
        self.title(title)
        self.geometry("300x150")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        
        # Center the dialog
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = master.winfo_rootx() + (master.winfo_width() // 2) - (width // 2)
        y = master.winfo_rooty() + (master.winfo_height() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")
        
        # Result variable
        self.result = False
        
        # Create widgets
        ctk.CTkLabel(self, text=message, wraplength=250).pack(padx=20, pady=20)
        
        # Button frame
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=20, pady=10)
        
        # Buttons
        ctk.CTkButton(
            button_frame, text="Yes", command=self._on_yes, fg_color="green", hover_color="darkgreen"
        ).pack(side="left", padx=10, expand=True)
        
        ctk.CTkButton(
            button_frame, text="No", command=self._on_no
        ).pack(side="right", padx=10, expand=True)
    
    def _on_yes(self):
        """Handle Yes button click."""
        self.result = True
        self.destroy()
    
    def _on_no(self):
        """Handle No button click."""
        self.result = False
        self.destroy()
    
    @staticmethod
    def ask(master, title: str, message: str) -> bool:
        """
        Show a confirm dialog and return the result.
        
        Args:
            master: Parent widget.
            title (str): Dialog title.
            message (str): Dialog message.
            
        Returns:
            bool: True if Yes was clicked, False otherwise.
        """
        dialog = ConfirmDialog(master, title, message)
        dialog.wait_window()
        return dialog.result


class HyperlinkLabel(ctk.CTkLabel):
    """A label that behaves like a hyperlink."""
    
    def __init__(self, master, text: str, url: str, **kwargs):
        """
        Initialize the hyperlink label.
        
        Args:
            master: Parent widget.
            text (str): Label text.
            url (str): URL to open when clicked.
            **kwargs: Additional arguments for the label.
        """
        super().__init__(master, text=text, cursor="hand2", **kwargs)
        
        # Store URL
        self.url = url
        
        # Set appearance
        self.configure(text_color="#3a7ebf")
        
        # Bind click event
        self.bind("<Button-1>", self._open_url)
    
    def _open_url(self, event):
        """
        Open the URL when the label is clicked.
        
        Args:
            event: Click event.
        """
        import webbrowser
        webbrowser.open(self.url)