"""Entry point for the Shopot File Viewer application."""
from __future__ import annotations

from shopot.gui import ShopotApp


def main() -> None:
    app = ShopotApp()
    app.mainloop()


if __name__ == "__main__":
    main()
