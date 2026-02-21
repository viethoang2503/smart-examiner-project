"""
FocusGuard Anti-Cheat Module
Monitors and prevents cheating behaviors at OS level
"""

import sys
import os
import time
import threading
from typing import Callable, Optional
from dataclasses import dataclass
from enum import Enum

# Platform detection
IS_WINDOWS = sys.platform == 'win32'
IS_LINUX = sys.platform.startswith('linux')
IS_MAC = sys.platform == 'darwin'


class CheatEvent(Enum):
    """Types of cheat events"""
    WINDOW_FOCUS_LOST = "window_focus_lost"
    ALT_TAB_DETECTED = "alt_tab_detected"
    MINIMIZE_DETECTED = "minimize_detected"
    SCREEN_CAPTURE_DETECTED = "screen_capture_detected"
    MULTIPLE_MONITORS = "multiple_monitors"
    WINDOW_MOVED = "window_moved"


@dataclass
class CheatViolation:
    """Represents a detected cheat violation"""
    event_type: CheatEvent
    timestamp: float
    details: str


class AntiCheatMonitor:
    """
    Cross-platform anti-cheat monitoring system
    Detects when user switches away from exam window
    """
    
    def __init__(self, on_violation: Optional[Callable[[CheatViolation], None]] = None):
        """
        Initialize anti-cheat monitor
        
        Args:
            on_violation: Callback function when violation detected
        """
        self.on_violation = on_violation
        self.is_monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._target_window = None
        self._last_focus_time = time.time()
        self._focus_lost_count = 0
        
        # Settings
        self.focus_grace_period = 2.0  # Seconds before reporting focus loss
        self.enable_focus_lock = False  # Force window to front
        
    def start_monitoring(self, window=None):
        """
        Start anti-cheat monitoring
        
        Args:
            window: PyQt window to monitor (optional)
        """
        self._target_window = window
        self.is_monitoring = True
        self._focus_lost_count = 0
        
        # Start monitoring thread
        self._monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitor_thread.start()
        
        print("[AntiCheat] Monitoring started")
        
    def stop_monitoring(self):
        """Stop anti-cheat monitoring"""
        self.is_monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
        print("[AntiCheat] Monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                self._check_focus()
                time.sleep(0.5)  # Check every 500ms
            except Exception as e:
                print(f"[AntiCheat] Error: {e}")
    
    def _check_focus(self):
        """Check if exam window has focus"""
        if self._target_window is None:
            return
            
        try:
            # PyQt6 focus check
            is_active = self._target_window.isActiveWindow()
            is_visible = self._target_window.isVisible()
            is_minimized = self._target_window.isMinimized()
            
            if is_minimized:
                self._report_violation(CheatEvent.MINIMIZE_DETECTED, "Exam window was minimized")
                if self.enable_focus_lock:
                    self._restore_window()
                    
            elif not is_active:
                current_time = time.time()
                if current_time - self._last_focus_time > self.focus_grace_period:
                    self._focus_lost_count += 1
                    self._report_violation(
                        CheatEvent.WINDOW_FOCUS_LOST, 
                        f"Focus lost (count: {self._focus_lost_count})"
                    )
                    if self.enable_focus_lock:
                        self._bring_to_front()
            else:
                self._last_focus_time = time.time()
                
        except Exception as e:
            print(f"[AntiCheat] Focus check error: {e}")
    
    def _restore_window(self):
        """Restore minimized window"""
        try:
            if self._target_window:
                self._target_window.showNormal()
                self._target_window.raise_()
                self._target_window.activateWindow()
        except Exception as e:
            print(f"[AntiCheat] Restore error: {e}")
    
    def _bring_to_front(self):
        """Bring window to front"""
        try:
            if self._target_window:
                self._target_window.raise_()
                self._target_window.activateWindow()
        except Exception as e:
            print(f"[AntiCheat] Bring to front error: {e}")
    
    def _report_violation(self, event_type: CheatEvent, details: str):
        """Report a cheat violation"""
        violation = CheatViolation(
            event_type=event_type,
            timestamp=time.time(),
            details=details
        )
        
        print(f"[AntiCheat] VIOLATION: {event_type.value} - {details}")
        
        if self.on_violation:
            try:
                self.on_violation(violation)
            except Exception as e:
                print(f"[AntiCheat] Callback error: {e}")
    
    def check_multiple_monitors(self) -> bool:
        """
        Check if multiple monitors are connected
        Returns True if multiple monitors detected
        """
        try:
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtGui import QScreen
            
            app = QApplication.instance()
            if app:
                screens = app.screens()
                if len(screens) > 1:
                    self._report_violation(
                        CheatEvent.MULTIPLE_MONITORS,
                        f"Detected {len(screens)} monitors"
                    )
                    return True
        except Exception as e:
            print(f"[AntiCheat] Monitor check error: {e}")
        
        return False
    
    def get_focus_lost_count(self) -> int:
        """Get number of times focus was lost"""
        return self._focus_lost_count


class WindowsAntiCheat(AntiCheatMonitor):
    """Windows-specific anti-cheat features"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._keyboard_hook = None
        
    def block_alt_tab(self, enable: bool = True):
        """
        Block Alt+Tab key combination (Windows only)
        Note: Requires admin privileges to fully work
        """
        if not IS_WINDOWS:
            print("[AntiCheat] Alt+Tab blocking only works on Windows")
            return
            
        try:
            import ctypes
            from ctypes import wintypes
            
            user32 = ctypes.windll.user32
            
            if enable:
                if getattr(self, '_keyboard_hook', None) is not None:
                    return # Already hooked
                    
                # Constants mapping
                WH_KEYBOARD_LL = 13
                WM_KEYDOWN = 0x0100
                WM_SYSKEYDOWN = 0x0104
                
                VK_TAB = 0x09
                VK_LWIN = 0x5B
                VK_RWIN = 0x5C
                VK_ESCAPE = 0x1B
                LLKHF_ALTDOWN = 0x20
                
                class KBDLLHOOKSTRUCT(ctypes.Structure):
                    _fields_ = [
                        ("vkCode", wintypes.DWORD),
                        ("scanCode", wintypes.DWORD),
                        ("flags", wintypes.DWORD),
                        ("time", wintypes.DWORD),
                        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))
                    ]
                
                CMPFUNC = ctypes.WINFUNCTYPE(wintypes.LPARAM, wintypes.INT, wintypes.WPARAM, ctypes.POINTER(KBDLLHOOKSTRUCT))
                
                def hook_callback(nCode, wParam, lParam):
                    if nCode >= 0:
                        vk = lParam.contents.vkCode
                        flags = lParam.contents.flags
                        is_keydown = wParam == WM_KEYDOWN or wParam == WM_SYSKEYDOWN
                        
                        # Block Alt+Tab and Alt+Esc
                        if (flags & LLKHF_ALTDOWN) and vk in (VK_TAB, VK_ESCAPE):
                            if is_keydown:
                                self._report_violation(CheatEvent.ALT_TAB_DETECTED, "OS Shortcut blocked: Alt+Tab/Esc")
                            return 1 # Swallows the key event
                            
                        # Block Windows keys (Start Menu shortcut)
                        if vk in (VK_LWIN, VK_RWIN):
                            if is_keydown:
                                self._report_violation(CheatEvent.ALT_TAB_DETECTED, "OS Shortcut blocked: Windows Key")
                            return 1
                            
                        # Block Ctrl+Esc (Another Start Menu shortcut)
                        if vk == VK_ESCAPE and (user32.GetAsyncKeyState(0x11) & 0x8000): # 0x11 is VK_CONTROL
                            if is_keydown:
                                self._report_violation(CheatEvent.ALT_TAB_DETECTED, "OS Shortcut blocked: Ctrl+Esc")
                            return 1
                            
                    return user32.CallNextHookEx(self._keyboard_hook, nCode, wParam, lParam)
                
                # We MUST store the pointer to prevent Python Garbage Collector from sweeping it
                self._hook_func_pointer = CMPFUNC(hook_callback)
                
                # 0 is the thread ID for global hook, GetModuleHandleW(None) gets current EXE handle
                kernel32 = ctypes.windll.kernel32
                hMod = kernel32.GetModuleHandleW(None)
                
                self._keyboard_hook = user32.SetWindowsHookExW(
                    WH_KEYBOARD_LL, 
                    self._hook_func_pointer, 
                    hMod, 
                    0
                )
                
                if not self._keyboard_hook:
                    print(f"[AntiCheat] Failed to install keyboard hook. Error: {ctypes.GetLastError()}")
                else:
                    print("[AntiCheat] 🛡️ Alt+Tab & Windows Key blocking ENFORCED!")
                    
            else:
                if getattr(self, '_keyboard_hook', None) is not None:
                    user32.UnhookWindowsHookEx(self._keyboard_hook)
                    self._keyboard_hook = None
                    self._hook_func_pointer = None
                    print("[AntiCheat] 🔓 OS shortcut blocking disabled")
                    
        except Exception as e:
            print(f"[AntiCheat] Alt+Tab block error: {e}")
    
    def disable_task_manager(self, disable: bool = True):
        """
        Disable Task Manager access (Windows only)
        Note: Requires admin privileges
        """
        if not IS_WINDOWS:
            return
            
        try:
            import winreg
            
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Policies\System"
            
            try:
                # Need KEY_SET_VALUE access
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            except FileNotFoundError:
                try:
                    # Create if it doesn't exist
                    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
                except Exception as create_e:
                    print(f"[AntiCheat] Cannot create registry key (needs Admin prep): {create_e}")
                    return
            
            value = 1 if disable else 0
            winreg.SetValueEx(key, "DisableTaskMgr", 0, winreg.REG_DWORD, value)
            winreg.CloseKey(key)
            
            print(f"[AntiCheat] 🛡️ Task Manager {'DISABLED (Locked)' if disable else 'Enabled'}!")
            
        except PermissionError:
            print("[AntiCheat] ⚠️ Cannot disable Task Manager: Administrator privileges required.")
        except Exception as e:
            print(f"[AntiCheat] Task Manager control error: {e}")


class LinuxAntiCheat(AntiCheatMonitor):
    """Linux-specific anti-cheat features"""
    
    def set_always_on_top(self, enable: bool = True):
        """Set window to always be on top"""
        if self._target_window:
            try:
                from PyQt6.QtCore import Qt
                if enable:
                    self._target_window.setWindowFlags(
                        self._target_window.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
                    )
                else:
                    self._target_window.setWindowFlags(
                        self._target_window.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint
                    )
                self._target_window.show()
            except Exception as e:
                print(f"[AntiCheat] Always on top error: {e}")


def get_anti_cheat_monitor(on_violation: Optional[Callable] = None) -> AntiCheatMonitor:
    """
    Factory function to get platform-appropriate anti-cheat monitor
    
    Args:
        on_violation: Callback when violation detected
        
    Returns:
        AntiCheatMonitor instance for current platform
    """
    if IS_WINDOWS:
        return WindowsAntiCheat(on_violation=on_violation)
    elif IS_LINUX:
        return LinuxAntiCheat(on_violation=on_violation)
    else:
        return AntiCheatMonitor(on_violation=on_violation)


# Test
if __name__ == "__main__":
    def on_cheat(violation):
        print(f"🚨 CHEAT DETECTED: {violation}")
    
    monitor = get_anti_cheat_monitor(on_violation=on_cheat)
    
    # Test multiple monitor detection
    has_multi = monitor.check_multiple_monitors()
    print(f"Multiple monitors: {has_multi}")
    
    print("\nAnti-cheat module loaded successfully!")
    print(f"Platform: {'Windows' if IS_WINDOWS else 'Linux' if IS_LINUX else 'macOS'}")
