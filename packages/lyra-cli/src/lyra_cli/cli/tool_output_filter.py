"""Tool Output Filter — Phase C (RTK-inspired).

Filters tool/command output before it enters the context window.
Strips ANSI, removes noise, truncates large outputs, dedups lines.
Evidence: RTK (48.4k★) achieves 60-90% token reduction on terminal output.
"""

from __future__ import annotations

import re
from typing import ClassVar


class ToolOutputFilter:
    """Compresses tool/command results before context injection."""

    MAX_FILE_LINES: ClassVar[int] = 200
    MAX_TEST_FAILURE_LINES: ClassVar[int] = 150
    MAX_GREP_RESULTS: ClassVar[int] = 50
    MAX_LISTING_LINES: ClassVar[int] = 100
    MAX_DIFF_CHANGES: ClassVar[int] = 200
    MAX_GENERIC_CHARS: ClassVar[int] = 8_000

    _ANSI_RE: ClassVar[re.Pattern] = re.compile(
        r'\x1b(?:\[[0-9;]*[mKJHABCDEFGSTfhilu]|\[[?][0-9;]*[hl]|[()][0-2AB])'
    )
    _BLANK_RUN_RE: ClassVar[re.Pattern] = re.compile(r'\n{3,}')

    _TOOL_MAP: ClassVar[dict[str, str]] = {
        'ls': '_filter_listing',
        'find': '_filter_listing',
        'tree': '_filter_listing',
        'cat': '_filter_file',
        'read_file': '_filter_file',
        'head': '_filter_file',
        'tail': '_filter_file',
        'grep': '_filter_search',
        'rg': '_filter_search',
        'ag': '_filter_search',
        'git_diff': '_filter_diff',
        'git diff': '_filter_diff',
        'git_status': '_filter_git_status',
        'git status': '_filter_git_status',
        'pytest': '_filter_test',
        'npm test': '_filter_test',
        'cargo test': '_filter_test',
        'python -m pytest': '_filter_test',
        'make test': '_filter_test',
        'go test': '_filter_test',
    }

    def __init__(self) -> None:
        self._total_original_chars: int = 0
        self._total_filtered_chars: int = 0
        self._calls: int = 0

    def filter(self, tool_name: str, output: str) -> str:
        """Filter tool output. Returns compressed version."""
        if not output:
            return output

        self._total_original_chars += len(output)
        self._calls += 1

        clean = self._ANSI_RE.sub('', output)
        clean = self._BLANK_RUN_RE.sub('\n\n', clean)

        method_name = self._TOOL_MAP.get(tool_name.lower(), '_filter_generic')
        method = getattr(self, method_name, self._filter_generic)
        filtered = method(clean)

        self._total_filtered_chars += len(filtered)
        return filtered

    def compression_ratio(self) -> float:
        if self._total_original_chars == 0:
            return 1.0
        return self._total_filtered_chars / self._total_original_chars

    def session_stats(self) -> dict:
        saved = self._total_original_chars - self._total_filtered_chars
        return {
            'calls': self._calls,
            'original_chars': self._total_original_chars,
            'filtered_chars': self._total_filtered_chars,
            'compression_ratio': round(self.compression_ratio(), 3),
            'chars_saved': saved,
            'tokens_saved_est': saved // 4,
        }

    # ── Filter implementations ─────────────────────────────────────────

    def _filter_listing(self, output: str) -> str:
        lines = output.splitlines()
        if len(lines) <= self.MAX_LISTING_LINES:
            return output
        kept = lines[:self.MAX_LISTING_LINES]
        kept.append(f'... [{len(lines) - self.MAX_LISTING_LINES} more entries omitted]')
        return '\n'.join(kept)

    def _filter_file(self, output: str) -> str:
        lines = output.splitlines()
        if len(lines) <= self.MAX_FILE_LINES:
            return output
        half = self.MAX_FILE_LINES // 2
        head = lines[:half]
        tail = lines[-half:]
        omitted = len(lines) - self.MAX_FILE_LINES
        return '\n'.join(head) + f'\n\n... [{omitted} lines omitted] ...\n\n' + '\n'.join(tail)

    def _filter_search(self, output: str) -> str:
        lines = output.splitlines()
        if len(lines) <= self.MAX_GREP_RESULTS:
            return output
        kept = lines[:self.MAX_GREP_RESULTS]
        kept.append(f'... [{len(lines) - self.MAX_GREP_RESULTS} more matches omitted]')
        return '\n'.join(kept)

    def _filter_diff(self, output: str) -> str:
        if len(output) <= 12_000:
            return output
        lines = output.splitlines()
        kept: list[str] = []
        change_count = 0
        for line in lines:
            if line.startswith(('diff ', '---', '+++', '@@', 'index ')):
                kept.append(line)
            elif line and line[0] in ('+', '-'):
                if change_count < self.MAX_DIFF_CHANGES:
                    kept.append(line)
                    change_count += 1
                elif change_count == self.MAX_DIFF_CHANGES:
                    kept.append(f'... [diff truncated at {self.MAX_DIFF_CHANGES} changed lines]')
                    change_count += 1
            else:
                kept.append(line)
        return '\n'.join(kept)

    def _filter_git_status(self, output: str) -> str:
        lines = output.splitlines()
        if len(lines) <= 30:
            return output
        kept = [l for l in lines if l.strip() and not l.startswith('\t')]
        return '\n'.join(kept[:50])

    def _filter_test(self, output: str) -> str:
        lines = output.splitlines()
        failure_lines: list[str] = []
        summary_lines: list[str] = []
        in_failure_block = False

        for line in lines:
            lower = line.lower()
            is_failure = any(kw in lower for kw in ('failed', 'error:', 'assert', 'traceback'))
            is_failure = is_failure or 'FAILED' in line or 'ERROR' in line
            is_summary = any(kw in lower for kw in ('passed', 'failed', 'error', 'warning'))
            is_summary = is_summary and len(line) < 200

            if is_failure:
                in_failure_block = True
            if in_failure_block:
                failure_lines.append(line)
                if len(failure_lines) >= self.MAX_TEST_FAILURE_LINES:
                    failure_lines.append('... [failure output truncated]')
                    in_failure_block = False
            if is_summary:
                summary_lines.append(line)

        if not failure_lines and not summary_lines:
            return self._filter_generic(output)

        parts = failure_lines[:self.MAX_TEST_FAILURE_LINES]
        if summary_lines:
            parts += [''] + summary_lines[-5:]
        return '\n'.join(parts)

    def _filter_generic(self, output: str) -> str:
        if len(output) <= self.MAX_GENERIC_CHARS:
            return output
        half = self.MAX_GENERIC_CHARS // 2
        omitted = len(output) - self.MAX_GENERIC_CHARS
        return (
            output[:half]
            + f'\n\n... [{omitted} chars omitted] ...\n\n'
            + output[-half:]
        )
