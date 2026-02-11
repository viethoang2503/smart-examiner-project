"""
FocusGuard - Anti-Cheat Tests
Tests for anti-cheat monitoring system
"""

import pytest
import os
import sys
import time
import threading
from unittest.mock import Mock, MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.anti_cheat import (
    AntiCheatMonitor, 
    CheatEvent, 
    CheatViolation,
    get_anti_cheat_monitor,
    IS_WINDOWS, 
    IS_LINUX
)


class TestCheatViolation:
    """Test CheatViolation dataclass"""
    
    def test_violation_creation(self):
        """Test creating a violation"""
        violation = CheatViolation(
            event_type=CheatEvent.WINDOW_FOCUS_LOST,
            timestamp=time.time(),
            details="Test violation"
        )
        
        assert violation.event_type == CheatEvent.WINDOW_FOCUS_LOST
        assert violation.details == "Test violation"
        assert violation.timestamp > 0
    
    def test_all_event_types(self):
        """Test all cheat event types exist"""
        events = [
            CheatEvent.WINDOW_FOCUS_LOST,
            CheatEvent.ALT_TAB_DETECTED,
            CheatEvent.MINIMIZE_DETECTED,
            CheatEvent.SCREEN_CAPTURE_DETECTED,
            CheatEvent.MULTIPLE_MONITORS,
            CheatEvent.WINDOW_MOVED
        ]
        
        for event in events:
            violation = CheatViolation(
                event_type=event,
                timestamp=time.time(),
                details=f"Test {event.value}"
            )
            assert violation.event_type == event
        
        print(f"✅ All {len(events)} event types work correctly")


class TestAntiCheatMonitor:
    """Test AntiCheatMonitor base class"""
    
    @pytest.fixture
    def monitor(self):
        """Create a test monitor"""
        return AntiCheatMonitor()
    
    def test_monitor_creation(self, monitor):
        """Test monitor initialization"""
        assert monitor is not None
        assert monitor.is_monitoring == False
        assert monitor._target_window is None
    
    def test_monitor_with_callback(self):
        """Test monitor with violation callback"""
        violations_received = []
        
        def on_violation(v):
            violations_received.append(v)
        
        monitor = AntiCheatMonitor(on_violation=on_violation)
        assert monitor.on_violation is not None
    
    def test_start_stop_monitoring(self, monitor):
        """Test start and stop monitoring"""
        monitor.start_monitoring()
        assert monitor.is_monitoring == True
        
        time.sleep(0.5)  # Let monitoring thread start
        
        monitor.stop_monitoring()
        assert monitor.is_monitoring == False
        
        print("✅ Start/stop monitoring works")
    
    def test_focus_lost_count(self, monitor):
        """Test focus lost counter"""
        assert monitor.get_focus_lost_count() == 0
        
        monitor._focus_lost_count = 5
        assert monitor.get_focus_lost_count() == 5
    
    def test_settings_configuration(self, monitor):
        """Test settings can be configured"""
        monitor.focus_grace_period = 5.0
        monitor.enable_focus_lock = True
        
        assert monitor.focus_grace_period == 5.0
        assert monitor.enable_focus_lock == True
    
    def test_report_violation_calls_callback(self):
        """Test that violation reporting calls callback"""
        callback_called = False
        received_violation = None
        
        def callback(v):
            nonlocal callback_called, received_violation
            callback_called = True
            received_violation = v
        
        monitor = AntiCheatMonitor(on_violation=callback)
        monitor._report_violation(CheatEvent.MINIMIZE_DETECTED, "Test minimize")
        
        assert callback_called == True
        assert received_violation.event_type == CheatEvent.MINIMIZE_DETECTED
        assert "minimize" in received_violation.details.lower()
        
        print("✅ Violation callback works correctly")


class TestFactoryFunction:
    """Test platform factory function"""
    
    def test_get_anti_cheat_monitor(self):
        """Test factory returns correct monitor type"""
        monitor = get_anti_cheat_monitor()
        
        assert monitor is not None
        assert isinstance(monitor, AntiCheatMonitor)
        
        print(f"✅ Factory returned: {type(monitor).__name__}")
    
    def test_factory_with_callback(self):
        """Test factory with callback"""
        def dummy_callback(v):
            pass
        
        monitor = get_anti_cheat_monitor(on_violation=dummy_callback)
        assert monitor.on_violation == dummy_callback


class TestMultipleMonitorDetection:
    """Test multiple monitor detection"""
    
    @pytest.fixture
    def monitor(self):
        return AntiCheatMonitor()
    
    def test_check_multiple_monitors_returns_boolean(self, monitor):
        """Test that check_multiple_monitors returns a boolean"""
        result = monitor.check_multiple_monitors()
        assert isinstance(result, bool)
        print(f"✅ Multiple monitor check returned: {result}")


class TestViolationCounting:
    """Test violation counting and tracking"""
    
    def test_violation_count_increments(self):
        """Test that violations are counted"""
        violations = []
        
        def callback(v):
            violations.append(v)
        
        monitor = AntiCheatMonitor(on_violation=callback)
        
        # Report multiple violations
        monitor._report_violation(CheatEvent.WINDOW_FOCUS_LOST, "Lost 1")
        monitor._report_violation(CheatEvent.WINDOW_FOCUS_LOST, "Lost 2")
        monitor._report_violation(CheatEvent.MINIMIZE_DETECTED, "Minimized")
        
        assert len(violations) == 3
        print(f"✅ Recorded {len(violations)} violations")
    
    def test_violation_types_tracked(self):
        """Test different violation types are tracked"""
        violations = []
        
        def callback(v):
            violations.append(v)
        
        monitor = AntiCheatMonitor(on_violation=callback)
        
        monitor._report_violation(CheatEvent.WINDOW_FOCUS_LOST, "Focus")
        monitor._report_violation(CheatEvent.ALT_TAB_DETECTED, "Alt+Tab")
        monitor._report_violation(CheatEvent.MINIMIZE_DETECTED, "Minimize")
        
        event_types = [v.event_type for v in violations]
        assert CheatEvent.WINDOW_FOCUS_LOST in event_types
        assert CheatEvent.ALT_TAB_DETECTED in event_types
        assert CheatEvent.MINIMIZE_DETECTED in event_types


class TestThreadSafety:
    """Test thread safety of anti-cheat monitor"""
    
    def test_concurrent_violations(self):
        """Test reporting violations from multiple threads"""
        violations = []
        lock = threading.Lock()
        
        def callback(v):
            with lock:
                violations.append(v)
        
        monitor = AntiCheatMonitor(on_violation=callback)
        
        def report_violations(count):
            for i in range(count):
                monitor._report_violation(
                    CheatEvent.WINDOW_FOCUS_LOST, 
                    f"Thread violation {i}"
                )
        
        # Start multiple threads
        threads = []
        for _ in range(5):
            t = threading.Thread(target=report_violations, args=(10,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        assert len(violations) == 50
        print(f"✅ Thread-safe: {len(violations)} violations from 5 threads")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
