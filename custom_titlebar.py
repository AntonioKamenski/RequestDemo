# ── Toggle: set to False to use the native Windows title bar ──
CUSTOM_TITLEBAR = True

import ctypes
import ctypes.wintypes

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt, QPoint, QEvent
from PyQt6.QtGui import QIcon

TITLEBAR_HEIGHT = 38   # px – height of the custom title bar
RESIZE_BORDER   = 6    # px – edge/corner resize grip thickness

# Win32 WM_NCHITTEST return codes
HTCLIENT      = 1
HTCAPTION     = 2
HTLEFT        = 10
HTRIGHT       = 11
HTTOP         = 12
HTTOPLEFT     = 13
HTTOPRIGHT    = 14
HTBOTTOM      = 15
HTBOTTOMLEFT  = 16
HTBOTTOMRIGHT = 17


class _MARGINS(ctypes.Structure):
    _fields_ = [
        ("cxLeftWidth",    ctypes.c_int),
        ("cxRightWidth",   ctypes.c_int),
        ("cyTopHeight",    ctypes.c_int),
        ("cyBottomHeight", ctypes.c_int),
    ]


class CustomTitleBar(QWidget):
    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.setFixedHeight(TITLEBAR_HEIGHT)
        self.setObjectName("customTitleBar")
        self._win = parent_window

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 0, 0)
        layout.setSpacing(0)

        self._icon_lbl = QLabel()
        self._icon_lbl.setPixmap(QIcon("resources/icons/icon.png").pixmap(28, 28))
        self._icon_lbl.setFixedSize(36, TITLEBAR_HEIGHT)
        self._icon_lbl.setObjectName("titleBarIcon")
        layout.addWidget(self._icon_lbl)

        title_lbl = QLabel("Just Dance Song Requests")
        title_lbl.setObjectName("titleBarTitle")
        layout.addWidget(title_lbl, 1)

        self._min_btn   = self._make_btn("—", "titleBarBtn",      parent_window.showMinimized)
        self._max_btn   = self._make_btn("☐", "titleBarBtn",      self._toggle_max)
        self._close_btn = self._make_btn("✕", "titleBarCloseBtn", parent_window.close)
        for btn in (self._min_btn, self._max_btn, self._close_btn):
            layout.addWidget(btn)

    def _make_btn(self, text, obj_name, slot):
        btn = QPushButton(text)
        btn.setObjectName(obj_name)
        btn.setFixedSize(44, TITLEBAR_HEIGHT)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.clicked.connect(slot)
        return btn

    def _toggle_max(self):
        if self._win.isMaximized():
            self._win.showNormal()
        else:
            self._win.showMaximized()

    def sync_max_btn(self):
        self._max_btn.setText("❐" if self._win.isMaximized() else "☐")

    def update_icon(self, pixmap):
        self._icon_lbl.setPixmap(pixmap)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self._win.windowHandle()
            if handle is not None:
                handle.startSystemMove()
        super().mousePressEvent(event)


class TitleBarMixin:
    """
    Mixin for QMainWindow that replaces the native title bar with a themed
    custom one while keeping full Windows snapping and edge-resize support.

    How it works:
      - WM_NCCALCSIZE returning 0 extends Qt's client area to fill the whole
        window frame, hiding the native title bar visually.
      - WS_THICKFRAME is preserved (we do NOT use FramelessWindowHint), so
        Aero Snap, snap layouts (Win+Z), and edge-resize all keep working.
      - WM_NCHITTEST tells Windows which region the cursor is in, giving us
        drag-to-move on the title bar and resize grips on the edges.
      - DwmExtendFrameIntoClientArea restores the DWM drop shadow.

    Usage:
      1. Inherit as  class MainWindow(TitleBarMixin, QMainWindow)
      2. Call self._setup_titlebar() in __init__ after super().__init__()
      3. In init_ui, wrap your central widget using _build_central(scroll_area)
    """

    def _setup_titlebar(self):
        if not CUSTOM_TITLEBAR:
            return
        self._titlebar = CustomTitleBar(self)

    def _build_central(self, scroll_area):
        """Return the widget to pass to setCentralWidget."""
        if not CUSTOM_TITLEBAR:
            return scroll_area

        wrapper = QWidget()
        wrapper.setObjectName("titleBarWrapper")
        from PyQt6.QtWidgets import QVBoxLayout
        lay = QVBoxLayout(wrapper)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._titlebar)
        lay.addWidget(scroll_area)
        return wrapper

    # ── Qt event overrides ─────────────────────────────────────────────────

    def showEvent(self, event):
        if CUSTOM_TITLEBAR:
            # Restore DWM drop shadow — lost when WM_NCCALCSIZE returns 0.
            try:
                dwm = ctypes.WinDLL("dwmapi")
                m = _MARGINS(1, 1, 1, 1)
                dwm.DwmExtendFrameIntoClientArea(int(self.winId()), ctypes.byref(m))
            except Exception:
                pass
        super().showEvent(event)

    def changeEvent(self, event):
        if CUSTOM_TITLEBAR and hasattr(self, '_titlebar') and \
                event.type() == QEvent.Type.WindowStateChange:
            self._titlebar.sync_max_btn()
            # When maximized, Windows offsets the window ~8 px outside the
            # screen to hide the resize border.  Add a top margin so the
            # title bar content stays inside the visible area.
            top = 8 if self.isMaximized() else 0
            self._titlebar.layout().setContentsMargins(8, top, 0, 0)
        super().changeEvent(event)

    def nativeEvent(self, event_type, message):
        if not CUSTOM_TITLEBAR or event_type != b"windows_generic_MSG":
            return super().nativeEvent(event_type, message)

        msg = ctypes.wintypes.MSG.from_address(int(message))

        # WM_NCCALCSIZE — extend the client area to cover the whole frame.
        if msg.message == 0x0083:
            if msg.wParam:
                return True, 0
            return False, 0

        # WM_NCHITTEST — define drag / resize regions for the OS.
        if msg.message == 0x0084:
            sx = ctypes.c_int16(msg.lParam & 0xFFFF).value
            sy = ctypes.c_int16((msg.lParam >> 16) & 0xFFFF).value
            pos = self.mapFromGlobal(QPoint(sx, sy))
            x, y = pos.x(), pos.y()
            w, h = self.width(), self.height()
            b = RESIZE_BORDER

            if not self.isMaximized():
                if x < b     and y < b:      return True, HTTOPLEFT
                if x >= w-b  and y < b:      return True, HTTOPRIGHT
                if x < b     and y >= h-b:   return True, HTBOTTOMLEFT
                if x >= w-b  and y >= h-b:   return True, HTBOTTOMRIGHT
                if y < b:                    return True, HTTOP
                if y >= h-b:                 return True, HTBOTTOM
                if x < b:                    return True, HTLEFT
                if x >= w-b:                 return True, HTRIGHT

            title_bottom = TITLEBAR_HEIGHT + (8 if self.isMaximized() else 0)
            if 0 <= y < title_bottom:
                if hasattr(self, '_titlebar'):
                    local = self._titlebar.mapFromGlobal(QPoint(sx, sy))
                    if isinstance(self._titlebar.childAt(local), QPushButton):
                        return True, HTCLIENT
                return True, HTCAPTION

            return True, HTCLIENT

        return False, 0
