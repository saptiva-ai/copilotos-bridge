"""
SQL Security Validator for NL2SQL Pipeline

This module implements defense-in-depth security validation for dynamically
generated SQL queries.

Security Layers:
    1. Keyword blacklist (DDL/DML prevention)
    2. Table whitelist enforcement
    3. Pattern detection (injection attempts)
    4. Query sanitization (LIMIT injection)

Design Philosophy:
    - Fail closed: Reject if uncertain
    - Defense in depth: Multiple validation layers
    - Clear error messages: Help developers debug
"""

import re
from typing import List, Set, Optional, Tuple
import structlog

from ..specs import ValidationResult

logger = structlog.get_logger(__name__)


class SqlValidator:
    """
    SQL security validator with multi-layer defense.

    Architecture:
        Input SQL → Keyword Check → Table Check → Pattern Check → Sanitization → Output

    Usage:
        validator = SqlValidator(allowed_tables=["monthly_kpis"])
        result = validator.validate(sql)
        if result.valid:
            execute(result.sanitized_sql)
        else:
            log_error(result.error_message)
    """

    # =========================================================================
    # SECURITY: FORBIDDEN KEYWORDS
    # =========================================================================
    # DDL/DML operations that modify data or schema
    # Any query containing these will be REJECTED

    FORBIDDEN_KEYWORDS: Set[str] = {
        # Data Manipulation Language (DML)
        "INSERT", "UPDATE", "DELETE", "MERGE", "REPLACE",

        # Data Definition Language (DDL)
        "CREATE", "ALTER", "DROP", "TRUNCATE", "RENAME",

        # Execution and procedural
        "EXEC", "EXECUTE", "CALL", "DO",

        # Dangerous operations
        "UNION", "INTO", "OUTFILE", "DUMPFILE",

        # Comment injection vectors
        "--", "/*", "*/", "#",

        # Control flow that could bypass filters
        "IF", "CASE", "WHILE", "LOOP",

        # System functions
        "LOAD_FILE", "PG_READ_FILE", "PG_LS_DIR",
    }

    # =========================================================================
    # SECURITY: ALLOWED TABLES
    # =========================================================================
    # Default whitelist - can be overridden in __init__

    DEFAULT_ALLOWED_TABLES: Set[str] = {
        "monthly_kpis",
        "metricas_cartera_segmentada",
        "metricas_financieras_ext",
    }

    # =========================================================================
    # SECURITY: SUSPICIOUS PATTERNS
    # =========================================================================
    # Regex patterns that indicate potential injection attempts

    SUSPICIOUS_PATTERNS: List[re.Pattern] = [
        re.compile(r";.*\b(DROP|DELETE|UPDATE|INSERT)\b", re.IGNORECASE),  # Stacked queries
        re.compile(r"\b(AND|OR)\s+\d+\s*=\s*\d+", re.IGNORECASE),          # Boolean injection (1=1)
        re.compile(r"'.*\bOR\b.*'", re.IGNORECASE),                         # String injection
        re.compile(r"\bUNION\b.*\bSELECT\b", re.IGNORECASE),               # UNION injection
        re.compile(r"\bEXEC\b.*\(", re.IGNORECASE),                        # Stored proc execution
        re.compile(r"['\"].*\\\\'", re.IGNORECASE),                        # Escaped quote injection
    ]

    def __init__(self, allowed_tables: List[str] = None):
        """
        Initialize validator with table whitelist.

        Args:
            allowed_tables: List of allowed table names. Defaults to DEFAULT_ALLOWED_TABLES.
        """
        self.allowed_tables = set(allowed_tables) if allowed_tables else self.DEFAULT_ALLOWED_TABLES
        logger.info(
            "sql_validator.initialized",
            allowed_tables=list(self.allowed_tables),
            forbidden_keywords_count=len(self.FORBIDDEN_KEYWORDS)
        )

    def validate(self, sql: str) -> ValidationResult:
        """
        Validate SQL query for security and correctness.

        Validation Steps:
            1. Normalize SQL (uppercase, strip)
            2. Check for forbidden keywords
            3. Verify SELECT-only
            4. Validate table whitelist
            5. Detect suspicious patterns
            6. Sanitize (add LIMIT if needed)

        Args:
            sql: SQL query string to validate

        Returns:
            ValidationResult with validation status and sanitized SQL

        Examples:
            >>> validator = SqlValidator()
            >>> result = validator.validate("SELECT * FROM monthly_kpis")
            >>> assert result.valid == True

            >>> result = validator.validate("DROP TABLE monthly_kpis")
            >>> assert result.valid == False
            >>> assert "DROP" in result.error_message
        """
        if not sql or not sql.strip():
            return ValidationResult(
                valid=False,
                error_message="Empty SQL query"
            )

        # Normalize
        sql_normalized = sql.strip()
        sql_upper = sql_normalized.upper()

        # Step 1: Check forbidden keywords
        forbidden_found = self._check_forbidden_keywords(sql_upper)
        if forbidden_found:
            logger.warning(
                "sql_validator.forbidden_keyword",
                keyword=forbidden_found,
                sql_preview=sql[:100]
            )
            return ValidationResult(
                valid=False,
                error_message=f"Forbidden keyword detected: {forbidden_found}"
            )

        # Step 2: Verify SELECT-only
        if not sql_upper.strip().startswith("SELECT"):
            logger.warning(
                "sql_validator.not_select",
                sql_preview=sql[:100]
            )
            return ValidationResult(
                valid=False,
                error_message="Only SELECT queries are allowed"
            )

        # Step 3: Validate table whitelist
        tables_used = self._extract_table_names(sql_normalized)
        invalid_tables = tables_used - self.allowed_tables
        if invalid_tables:
            logger.warning(
                "sql_validator.invalid_tables",
                invalid_tables=list(invalid_tables),
                allowed_tables=list(self.allowed_tables)
            )
            return ValidationResult(
                valid=False,
                error_message=f"Invalid tables: {', '.join(invalid_tables)}. Allowed: {', '.join(self.allowed_tables)}"
            )

        # Step 4: Detect suspicious patterns
        suspicious_match = self._detect_suspicious_patterns(sql_normalized)
        if suspicious_match:
            logger.warning(
                "sql_validator.suspicious_pattern",
                pattern=suspicious_match,
                sql_preview=sql[:100]
            )
            return ValidationResult(
                valid=False,
                error_message=f"Suspicious pattern detected: {suspicious_match}"
            )

        # Step 5: Sanitize (add LIMIT if missing)
        sanitized_sql, warnings = self._sanitize_sql(sql_normalized)

        logger.info(
            "sql_validator.success",
            tables_used=list(tables_used),
            has_limit="LIMIT" in sql_upper,
            warnings_count=len(warnings)
        )

        return ValidationResult(
            valid=True,
            sanitized_sql=sanitized_sql,
            warnings=warnings
        )

    def _check_forbidden_keywords(self, sql_upper: str) -> Optional[str]:
        """
        Check for forbidden keywords in SQL.

        Args:
            sql_upper: SQL query in uppercase

        Returns:
            First forbidden keyword found, or None
        """
        for keyword in self.FORBIDDEN_KEYWORDS:
            # For keywords with word characters (alphanumeric), use word boundaries
            # For special characters (like --, /*, #), just check if they're in the string
            if keyword.isalnum() or "_" in keyword:
                # Use word boundary to avoid false positives
                # e.g., "SELECT_INTO" should NOT match "INTO"
                pattern = rf"\b{re.escape(keyword)}\b"
                if re.search(pattern, sql_upper):
                    return keyword
            else:
                # For special characters, just check if they exist
                if keyword in sql_upper:
                    return keyword
        return None

    def _extract_table_names(self, sql: str) -> Set[str]:
        """
        Extract table names from SQL query.

        Strategy:
            - Find "FROM table_name" patterns
            - Find "JOIN table_name" patterns
            - Normalize to lowercase for comparison

        Args:
            sql: SQL query string

        Returns:
            Set of table names found in query

        Note:
            This is a heuristic approach. For complex queries with subqueries,
            it may not be 100% accurate, but it's sufficient for our use case.
        """
        tables = set()

        # Pattern: FROM table_name or JOIN table_name
        # Captures: table_name (optionally with alias)
        from_pattern = r"\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)"

        matches = re.findall(from_pattern, sql, re.IGNORECASE)
        for match in matches:
            tables.add(match.lower())

        return tables

    def _detect_suspicious_patterns(self, sql: str) -> Optional[str]:
        """
        Detect suspicious SQL injection patterns.

        Args:
            sql: SQL query string

        Returns:
            Description of first suspicious pattern found, or None
        """
        for pattern in self.SUSPICIOUS_PATTERNS:
            match = pattern.search(sql)
            if match:
                return f"Pattern: {match.group(0)[:50]}"
        return None

    def _sanitize_sql(self, sql: str) -> Tuple[str, List[str]]:
        """
        Sanitize SQL query by adding safety constraints.

        Modifications:
            1. Add LIMIT 1000 if query has no LIMIT and is not aggregated

        Args:
            sql: SQL query string

        Returns:
            Tuple of (sanitized_sql, warnings)
        """
        sanitized = sql.strip()
        warnings = []

        # Check if query has LIMIT
        has_limit = bool(re.search(r"\bLIMIT\s+\d+", sanitized, re.IGNORECASE))

        # Check if query is aggregated (has GROUP BY or aggregate functions)
        is_aggregated = bool(
            re.search(r"\b(GROUP\s+BY|COUNT|SUM|AVG|MAX|MIN)\b", sanitized, re.IGNORECASE)
        )

        # Add LIMIT if missing and not aggregated
        if not has_limit and not is_aggregated:
            # Find semicolon or end of string
            if sanitized.endswith(";"):
                sanitized = sanitized[:-1] + " LIMIT 1000;"
            else:
                sanitized = sanitized + " LIMIT 1000"

            warnings.append("Added LIMIT 1000 to unbounded query")
            logger.info("sql_validator.limit_injected")

        return sanitized, warnings


# =========================================================================
# CONVENIENCE FUNCTIONS
# =========================================================================

def validate_sql(sql: str, allowed_tables: List[str] = None) -> ValidationResult:
    """
    Convenience function for one-off SQL validation.

    Args:
        sql: SQL query string
        allowed_tables: List of allowed table names

    Returns:
        ValidationResult

    Example:
        >>> result = validate_sql("SELECT * FROM monthly_kpis")
        >>> if result.valid:
        ...     execute(result.sanitized_sql)
    """
    validator = SqlValidator(allowed_tables=allowed_tables)
    return validator.validate(sql)
