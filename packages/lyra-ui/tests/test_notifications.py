"""Tests for notification system."""

from lyra_ui import (
    NotificationHistory,
    NotificationLevel,
    NotificationSystem,
    ToastNotification,
)

# Notification System Tests


def test_notification_system_init():
    """Test notification system initialization."""
    system = NotificationSystem()
    assert system.console is not None
    assert len(system.notifications) == 0
    assert system.max_history == 100
    assert system.enable_sound is True


def test_notification_system_custom_settings():
    """Test notification system with custom settings."""
    system = NotificationSystem(max_history=50, enable_sound=False)
    assert system.max_history == 50
    assert system.enable_sound is False


def test_create_notification():
    """Test creating notification."""
    system = NotificationSystem()
    notif = system.notify(
        NotificationLevel.INFO,
        "Test",
        "Test message",
    )
    assert notif.level == NotificationLevel.INFO
    assert notif.title == "Test"
    assert notif.message == "Test message"
    assert len(system.notifications) == 1


def test_info_notification():
    """Test info notification."""
    system = NotificationSystem()
    notif = system.info("Info", "Info message")
    assert notif.level == NotificationLevel.INFO


def test_success_notification():
    """Test success notification."""
    system = NotificationSystem()
    notif = system.success("Success", "Success message")
    assert notif.level == NotificationLevel.SUCCESS


def test_warning_notification():
    """Test warning notification."""
    system = NotificationSystem()
    notif = system.warning("Warning", "Warning message")
    assert notif.level == NotificationLevel.WARNING


def test_error_notification():
    """Test error notification."""
    system = NotificationSystem()
    notif = system.error("Error", "Error message")
    assert notif.level == NotificationLevel.ERROR


def test_notification_with_action():
    """Test notification with action."""
    system = NotificationSystem()
    notif = system.info("Test", "Message", action="View details")
    assert notif.action == "View details"


def test_display_toast():
    """Test displaying toast notification."""
    system = NotificationSystem()
    notif = system.info("Test", "Message")
    # Should not raise error
    system.display_toast(notif)


def test_get_history():
    """Test getting notification history."""
    system = NotificationSystem()
    system.info("Info 1", "Message 1")
    system.success("Success 1", "Message 2")
    system.error("Error 1", "Message 3")

    history = system.get_history()
    assert len(history) == 3


def test_get_history_by_level():
    """Test getting history by level."""
    system = NotificationSystem()
    system.info("Info 1", "Message 1")
    system.success("Success 1", "Message 2")
    system.error("Error 1", "Message 3")

    errors = system.get_history(level=NotificationLevel.ERROR)
    assert len(errors) == 1
    assert errors[0].level == NotificationLevel.ERROR


def test_get_history_unread_only():
    """Test getting unread notifications."""
    system = NotificationSystem()
    notif1 = system.info("Info 1", "Message 1")
    system.info("Info 2", "Message 2")

    system.mark_read(notif1.id)

    unread = system.get_history(unread_only=True)
    assert len(unread) == 1


def test_get_history_with_limit():
    """Test getting history with limit."""
    system = NotificationSystem()
    for i in range(20):
        system.info(f"Info {i}", f"Message {i}")

    history = system.get_history(limit=5)
    assert len(history) == 5


def test_mark_read():
    """Test marking notification as read."""
    system = NotificationSystem()
    notif = system.info("Test", "Message")
    assert notif.read is False

    system.mark_read(notif.id)
    assert notif.read is True


def test_mark_all_read():
    """Test marking all notifications as read."""
    system = NotificationSystem()
    system.info("Info 1", "Message 1")
    system.info("Info 2", "Message 2")

    system.mark_all_read()

    for notif in system.notifications:
        assert notif.read is True


def test_clear_history():
    """Test clearing notification history."""
    system = NotificationSystem()
    system.info("Info 1", "Message 1")
    system.info("Info 2", "Message 2")

    system.clear_history()
    assert len(system.notifications) == 0


def test_get_unread_count():
    """Test getting unread count."""
    system = NotificationSystem()
    notif1 = system.info("Info 1", "Message 1")
    system.info("Info 2", "Message 2")
    system.info("Info 3", "Message 3")

    assert system.get_unread_count() == 3

    system.mark_read(notif1.id)
    assert system.get_unread_count() == 2


def test_max_history_limit():
    """Test max history limit."""
    system = NotificationSystem(max_history=10)

    for i in range(20):
        system.info(f"Info {i}", f"Message {i}")

    assert len(system.notifications) == 10


# Toast Notification Tests


def test_toast_notification_init():
    """Test toast notification initialization."""
    toast = ToastNotification()
    assert toast.console is not None


def test_toast_show():
    """Test showing toast notification."""
    toast = ToastNotification()
    # Should not raise error
    toast.show("Test message")


def test_toast_show_with_level():
    """Test showing toast with level."""
    toast = ToastNotification()
    # Should not raise error
    toast.show("Success message", level=NotificationLevel.SUCCESS)


# Notification History Tests


def test_notification_history_init():
    """Test notification history initialization."""
    history = NotificationHistory()
    assert history.console is not None


def test_notification_history_display_empty():
    """Test displaying empty history."""
    history = NotificationHistory()
    # Should not raise error
    history.display([])


def test_notification_history_display():
    """Test displaying notification history."""
    system = NotificationSystem()
    system.info("Info 1", "Message 1")
    system.success("Success 1", "Message 2")

    history = NotificationHistory()
    # Should not raise error
    history.display(system.notifications)


# Integration Tests


def test_complete_notification_workflow():
    """Test complete notification workflow."""
    system = NotificationSystem()

    # Create notifications
    notif1 = system.info("Task Started", "Research task has started")
    notif2 = system.success("Task Completed", "Research task completed successfully")
    system.warning("Low Memory", "Memory usage is high")
    system.error("Task Failed", "Analysis task failed")

    # Display toasts
    system.display_toast(notif1)
    system.display_toast(notif2)

    # Check history
    assert len(system.notifications) == 4
    assert system.get_unread_count() == 4

    # Mark some as read
    system.mark_read(notif1.id)
    system.mark_read(notif2.id)
    assert system.get_unread_count() == 2

    # Get unread
    unread = system.get_history(unread_only=True)
    assert len(unread) == 2

    # Get errors only
    errors = system.get_history(level=NotificationLevel.ERROR)
    assert len(errors) == 1

    # Display history
    history = NotificationHistory()
    history.display(system.notifications)


def test_notification_levels():
    """Test all notification levels."""
    system = NotificationSystem()

    levels = [
        NotificationLevel.INFO,
        NotificationLevel.SUCCESS,
        NotificationLevel.WARNING,
        NotificationLevel.ERROR,
    ]

    for level in levels:
        notif = system.notify(level, f"{level.value} title", f"{level.value} message")
        assert notif.level == level


def test_notification_persistence():
    """Test notification persistence across operations."""
    system = NotificationSystem()

    # Create notifications
    for i in range(5):
        system.info(f"Task {i}", f"Message {i}")

    # Mark some as read
    system.mark_read(system.notifications[0].id)
    system.mark_read(system.notifications[1].id)

    # Verify state persists
    assert system.notifications[0].read is True
    assert system.notifications[1].read is True
    assert system.notifications[2].read is False

    # Get unread
    unread = system.get_history(unread_only=True)
    assert len(unread) == 3
