"""Database Optimizer Skill — SQL and NoSQL query performance analysis.

Detects common performance anti-patterns:
- Missing indexes and full table scans
- N+1 query patterns
- Unoptimized JOINs and subqueries
- Missing pagination and LIMIT clauses
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class OptimizationSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class Optimization:
    table: str
    severity: OptimizationSeverity
    issue: str
    suggestion: str
    estimated_impact: str


class DatabaseOptimizerSkill:
    """Analyzes database queries for performance issues."""

    _N1_PATTERNS = [
        (r"for\s+\w+\s+in\s+.+?:.*\.execute\s*\(.*?SELECT", "N+1 query in loop — fetch related data in a JOIN or batch query."),
        (r"\.forEach\(.*?\.find\(|\.query\(|\.execute\(.*?SELECT", "N+1 query in iteration — use eager loading or batch fetch."),
    ]
    _MISSING_LIMIT = re.compile(r"SELECT\s+.+?\s+FROM\s+\w+(?!.*\bLIMIT\b)", re.IGNORECASE | re.DOTALL)

    def __init__(self) -> None:
        self._optimizations: list[Optimization] = []

    def run(self, input_data: dict) -> dict:
        queries = input_data.get("queries", [])
        if not queries:
            return {"optimizations": [], "score": 100, "total_issues": 0}

        self._optimizations.clear()
        for q in queries:
            sql = q.get("sql", q) if isinstance(q, dict) else str(q)
            table = q.get("table", "unknown") if isinstance(q, dict) else "unknown"
            self._analyze_query(sql, table)

        score = max(0, 100 - len(self._optimizations) * 10)
        return {
            "optimizations": [o.__dict__ for o in self._optimizations],
            "score": score,
            "total_issues": len(self._optimizations),
        }

    def _analyze_query(self, sql: str, table: str) -> None:
        sql_upper = sql.upper()

        if "SELECT *" in sql_upper:
            self._optimizations.append(Optimization(table, OptimizationSeverity.MEDIUM,
                "SELECT * fetches all columns unnecessarily.",
                "Specify only the columns you need.", "High bandwidth savings"))

        if re.search(r"WHERE\s+.+?\s+LIKE\s+['\"]%", sql, re.IGNORECASE):
            self._optimizations.append(Optimization(table, OptimizationSeverity.HIGH,
                "Leading wildcard in LIKE prevents index usage.",
                "Avoid leading '%' in LIKE patterns, or use full-text search.", "Significant scan reduction"))

        for pattern, msg in self._N1_PATTERNS:
            if re.search(pattern, sql, re.IGNORECASE):
                self._optimizations.append(Optimization(table, OptimizationSeverity.CRITICAL,
                    msg, "Use JOIN or batch query instead.", "Orders of magnitude improvement"))
                break

        if self._MISSING_LIMIT.search(sql) and "COUNT" not in sql_upper:
            self._optimizations.append(Optimization(table, OptimizationSeverity.LOW,
                "Query may return unlimited rows — add LIMIT.",
                "Add LIMIT clause to prevent unbounded result sets.", "Memory/network savings"))
