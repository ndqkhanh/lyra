"""Mobile Engineer Skill — mobile app development best practices validation.

Analyzes mobile applications for:
- Platform-specific patterns (iOS/Android)
- Performance optimization (battery, memory, network)
- Offline capability and data persistence
- Push notification implementation
- App store compliance
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class MobileSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MobileCategory(StrEnum):
    PERFORMANCE = "performance"
    OFFLINE = "offline"
    SECURITY = "security"
    UX = "ux"
    COMPLIANCE = "compliance"


@dataclass(frozen=True)
class MobileIssue:
    category: MobileCategory
    severity: MobileSeverity
    platform: str
    message: str
    suggestion: str


class MobileEngineerSkill:
    """Analyzes mobile applications for platform best practices and performance."""

    def __init__(self) -> None:
        self._issues: list[MobileIssue] = []

    def run(self, input_data: dict) -> dict:
        """Run mobile app analysis.

        Args:
            input_data: Dictionary with keys:
                - source: Source code string to analyze
                - platform: Target platform (ios, android, react-native, flutter)
                - app_config: Optional app configuration

        Returns:
            Dictionary with analysis report data.
        """
        source = input_data.get("source", "")
        platform = input_data.get("platform", "unknown")
        app_config = input_data.get("app_config", {})

        self._issues.clear()

        # Platform-specific checks
        if platform in ("ios", "react-native", "flutter"):
            self._check_ios_patterns(source)
        if platform in ("android", "react-native", "flutter"):
            self._check_android_patterns(source)

        # Cross-platform checks
        self._check_performance(source, platform)
        self._check_offline_capability(source)
        self._check_security(source, platform)
        self._check_ux_patterns(source, platform)
        self._check_compliance(source, app_config, platform)

        score = self._compute_score()

        return {
            "platform": platform,
            "issues": [i.__dict__ for i in self._issues],
            "score": score,
            "total_issues": len(self._issues),
            "critical_count": len([i for i in self._issues if i.severity == MobileSeverity.CRITICAL]),
        }

    def _check_ios_patterns(self, source: str) -> None:
        """Check iOS-specific patterns."""
        # Check for memory leaks
        if "self." in source and "closure" in source.lower() and "[weak self]" not in source:
            self._issues.append(
                MobileIssue(
                    category=MobileCategory.PERFORMANCE,
                    severity=MobileSeverity.HIGH,
                    platform="iOS",
                    message="Potential retain cycle in closure",
                    suggestion="Use [weak self] or [unowned self] in closures to prevent memory leaks",
                )
            )

        # Check for main thread blocking
        if re.search(r"DispatchQueue\.main\.sync", source):
            self._issues.append(
                MobileIssue(
                    category=MobileCategory.PERFORMANCE,
                    severity=MobileSeverity.CRITICAL,
                    platform="iOS",
                    message="Synchronous dispatch on main queue can cause deadlock",
                    suggestion="Use DispatchQueue.main.async for UI updates",
                )
            )

    def _check_android_patterns(self, source: str) -> None:
        """Check Android-specific patterns."""
        # Check for context leaks
        if "Context" in source and "static" in source:
            self._issues.append(
                MobileIssue(
                    category=MobileCategory.PERFORMANCE,
                    severity=MobileSeverity.HIGH,
                    platform="Android",
                    message="Static reference to Context can cause memory leak",
                    suggestion="Use ApplicationContext or WeakReference for long-lived objects",
                )
            )

        # Check for ANR risks
        if re.search(r"Thread\.sleep\(|\.get\(\)", source) and "AsyncTask" not in source:
            self._issues.append(
                MobileIssue(
                    category=MobileCategory.PERFORMANCE,
                    severity=MobileSeverity.CRITICAL,
                    platform="Android",
                    message="Blocking operation on main thread (ANR risk)",
                    suggestion="Move long operations to background thread with coroutines or WorkManager",
                )
            )

    def _check_performance(self, source: str, platform: str) -> None:
        """Check performance patterns."""
        # Check for excessive re-renders
        if "setState" in source or "notifyDataSetChanged" in source:
            count = source.count("setState") + source.count("notifyDataSetChanged")
            if count > 10:
                self._issues.append(
                    MobileIssue(
                        category=MobileCategory.PERFORMANCE,
                        severity=MobileSeverity.MEDIUM,
                        platform=platform,
                        message=f"Excessive state updates detected ({count} calls)",
                        suggestion="Batch state updates or use memoization to reduce re-renders",
                    )
                )

        # Check for image optimization
        if "Image" in source and "resize" not in source.lower() and "cache" not in source.lower():
            self._issues.append(
                MobileIssue(
                    category=MobileCategory.PERFORMANCE,
                    severity=MobileSeverity.MEDIUM,
                    platform=platform,
                    message="No image optimization detected",
                    suggestion="Implement image caching and resizing for better performance",
                )
            )

        # Check for list optimization
        if ("FlatList" in source or "RecyclerView" in source) and "getItemLayout" not in source:
            self._issues.append(
                MobileIssue(
                    category=MobileCategory.PERFORMANCE,
                    severity=MobileSeverity.LOW,
                    platform=platform,
                    message="List rendering without layout optimization",
                    suggestion="Implement getItemLayout for better scroll performance",
                )
            )

    def _check_offline_capability(self, source: str) -> None:
        """Check offline capability and data persistence."""
        has_storage = (
            "AsyncStorage" in source
            or "SQLite" in source
            or "Realm" in source
            or "CoreData" in source
            or "Room" in source
        )

        has_network_check = (
            "NetInfo" in source
            or "Reachability" in source
            or "ConnectivityManager" in source
        )

        if not has_storage and len(source) > 1000:
            self._issues.append(
                MobileIssue(
                    category=MobileCategory.OFFLINE,
                    severity=MobileSeverity.HIGH,
                    platform="cross-platform",
                    message="No local data persistence detected",
                    suggestion="Implement local storage for offline capability",
                )
            )

        if not has_network_check and ("fetch" in source or "http" in source.lower()):
            self._issues.append(
                MobileIssue(
                    category=MobileCategory.OFFLINE,
                    severity=MobileSeverity.MEDIUM,
                    platform="cross-platform",
                    message="No network connectivity check before API calls",
                    suggestion="Check network status before making requests",
                )
            )

    def _check_security(self, source: str, platform: str) -> None:
        """Check security patterns."""
        # Check for insecure storage
        if "password" in source.lower() and "Keychain" not in source and "KeyStore" not in source:
            self._issues.append(
                MobileIssue(
                    category=MobileCategory.SECURITY,
                    severity=MobileSeverity.CRITICAL,
                    platform=platform,
                    message="Sensitive data not stored in secure storage",
                    suggestion="Use Keychain (iOS) or KeyStore (Android) for credentials",
                )
            )

        # Check for SSL pinning
        if ("https://" in source or "http" in source.lower()) and "pinning" not in source.lower():
            self._issues.append(
                MobileIssue(
                    category=MobileCategory.SECURITY,
                    severity=MobileSeverity.MEDIUM,
                    platform=platform,
                    message="No SSL certificate pinning detected",
                    suggestion="Implement SSL pinning for production API calls",
                )
            )

    def _check_ux_patterns(self, source: str, platform: str) -> None:
        """Check UX patterns."""
        # Check for loading states
        has_loading = "loading" in source.lower() or "spinner" in source.lower()
        has_api_call = "fetch" in source or "http" in source.lower()

        if has_api_call and not has_loading:
            self._issues.append(
                MobileIssue(
                    category=MobileCategory.UX,
                    severity=MobileSeverity.MEDIUM,
                    platform=platform,
                    message="No loading indicator for async operations",
                    suggestion="Add loading states for better user feedback",
                )
            )

        # Check for error handling
        has_error_ui = "error" in source.lower() and ("Text" in source or "View" in source)
        if has_api_call and not has_error_ui:
            self._issues.append(
                MobileIssue(
                    category=MobileCategory.UX,
                    severity=MobileSeverity.HIGH,
                    platform=platform,
                    message="No error UI for failed operations",
                    suggestion="Display user-friendly error messages",
                )
            )

    def _check_compliance(self, source: str, app_config: dict, platform: str) -> None:
        """Check app store compliance."""
        # Check for privacy policy
        has_privacy = app_config.get("has_privacy_policy", False)
        collects_data = "location" in source.lower() or "camera" in source.lower()

        if collects_data and not has_privacy:
            self._issues.append(
                MobileIssue(
                    category=MobileCategory.COMPLIANCE,
                    severity=MobileSeverity.CRITICAL,
                    platform=platform,
                    message="App collects sensitive data without privacy policy",
                    suggestion="Add privacy policy and request user consent",
                )
            )

        # Check for permission requests
        if "camera" in source.lower() and "permission" not in source.lower():
            self._issues.append(
                MobileIssue(
                    category=MobileCategory.COMPLIANCE,
                    severity=MobileSeverity.HIGH,
                    platform=platform,
                    message="Camera access without permission request",
                    suggestion="Request camera permission before access",
                )
            )

    def _compute_score(self) -> int:
        """Compute overall mobile app quality score (0-100)."""
        return max(
            0,
            100
            - len([i for i in self._issues if i.severity == MobileSeverity.CRITICAL]) * 25
            - len([i for i in self._issues if i.severity == MobileSeverity.HIGH]) * 15
            - len([i for i in self._issues if i.severity == MobileSeverity.MEDIUM]) * 8
            - len([i for i in self._issues if i.severity == MobileSeverity.LOW]) * 3,
        )
