from .base import Display, Screen, ScreenMode, Canvas

from pyglet.libs.win32 import kernel32, user32, types, constants
from pyglet.libs.win32.constants import *
from pyglet.libs.win32.types import *


class Win32Display(Display):

    def get_screens(self):
        screens = list()

        def enum_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
            r = lprcMonitor.contents
            width = r.right - r.left
            height = r.bottom - r.top
            screens.append(
                Win32Screen(self, hMonitor, r.left, r.top, width, height))
            return True
        enum_proc_ptr = MONITORENUMPROC(enum_proc)
        user32.EnumDisplayMonitors(None, None, enum_proc_ptr, 0)
        return screens


class Win32Screen(Screen):
    _initial_mode = None

    def __init__(self, display, handle, x, y, width, height):
        super().__init__(display, x, y, width, height)
        self._handle = handle

    def get_matching_configs(self, template):
        canvas = Win32Canvas(self.display, 0, user32.GetDC(0))
        configs = template.match(canvas)
        # TODO: deprecate config's being screen-specific
        for config in configs:
            config.screen = self
        return configs

    def get_device_name(self):
        info = MONITORINFOEX()
        info.cbSize = sizeof(MONITORINFOEX)
        user32.GetMonitorInfoW(self._handle, byref(info))
        return info.szDevice

    def get_modes(self):
        device_name = self.get_device_name()
        i = 0
        modes = list()
        while True:
            mode = DEVMODE()
            mode.dmSize = sizeof(DEVMODE)
            r = user32.EnumDisplaySettingsW(device_name, i, byref(mode))
            if not r:
                break

            modes.append(Win32ScreenMode(self, mode))
            i += 1

        return modes

    def get_mode(self):
        mode = DEVMODE()
        mode.dmSize = sizeof(DEVMODE)
        user32.EnumDisplaySettingsW(self.get_device_name(),
                                     ENUM_CURRENT_SETTINGS,
                                     byref(mode))
        return Win32ScreenMode(self, mode)

    def set_mode(self, mode):
        assert mode.screen is self

        if not self._initial_mode:
            self._initial_mode = self.get_mode()
        r = user32.ChangeDisplaySettingsExW(self.get_device_name(),
                                             byref(mode._mode),
                                             None,
                                             CDS_FULLSCREEN,
                                             None)
        if r == DISP_CHANGE_SUCCESSFUL:
            self.width = mode.width
            self.height = mode.height

    def restore_mode(self):
        if self._initial_mode:
            self.set_mode(self._initial_mode)


class Win32ScreenMode(ScreenMode):

    def __init__(self, screen, mode):
        super().__init__(screen)
        self._mode = mode
        self.width = mode.dmPelsWidth
        self.height = mode.dmPelsHeight
        self.depth = mode.dmBitsPerPel
        self.rate = mode.dmDisplayFrequency


class Win32Canvas(Canvas):

    def __init__(self, display, hwnd, hdc):
        super().__init__(display)
        self.hwnd = hwnd
        self.hdc = hdc
