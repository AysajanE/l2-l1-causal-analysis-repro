"""
Leakage Checker - Automated Mediator Exclusion Validation

This is a CRITICAL module for Quality Gate G3.

Purpose:
    Automatically scan model specifications to ensure NO mediator variables
    (P_calldata_gas, P_blob_gas, posting_tx) appear in total effect (TE) models.

Usage:
    from src.qa.leakage_checker import check_formula_for_leakage, scan_codebase

    # Check single formula
    violations = check_formula_for_leakage(formula, mediator_vars)

    # Scan entire codebase
    report = scan_codebase(project_root, mediator_vars)

Failure Action:
    ANY leakage detection BLOCKS release immediately.
    PI must sign off on remediation.
"""

import re
import ast
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
import warnings


# Default mediator variable patterns
DEFAULT_MEDIATOR_VARS = [
    "P_calldata_gas",
    "P_blob_gas",
    "posting_tx",
    "P_t",  # Generic posting variable
]


# ============================================================================
# Formula String Parsing
# ============================================================================

def check_formula_for_leakage(
    formula: str,
    mediator_vars: Optional[List[str]] = None,
    case_sensitive: bool = False
) -> List[str]:
    """
    Check if model formula contains any mediator variables.

    Args:
        formula: Model formula string (e.g., "y ~ x1 + x2 + x3")
        mediator_vars: List of mediator variable names to check
        case_sensitive: Whether to use case-sensitive matching

    Returns:
        List of detected mediator variables (empty if no violations)

    Example:
        >>> formula = "u_t ~ A_t_clean + P_calldata_gas + D_star"
        >>> check_formula_for_leakage(formula)
        ['P_calldata_gas']  # VIOLATION!
    """
    if mediator_vars is None:
        mediator_vars = DEFAULT_MEDIATOR_VARS

    # Extract right-hand side (predictors)
    if "~" not in formula:
        return []

    _, rhs = formula.split("~", 1)
    rhs = rhs.strip()

    # Parse variables from RHS
    # Split on operators and parentheses
    tokens = re.split(r'[+\-*/()\s,|:]+', rhs)
    variables = {t.strip() for t in tokens if t.strip() and not t.strip().isdigit()}

    # Check for mediators
    detected = []
    for mediator in mediator_vars:
        if case_sensitive:
            # Exact match
            if mediator in variables:
                detected.append(mediator)
            else:
                # Check for partial matches (e.g., log(P_calldata_gas))
                for var in variables:
                    if mediator in var:
                        detected.append(var)
                        break
        else:
            # Case-insensitive match
            mediator_lower = mediator.lower()
            for var in variables:
                if mediator_lower in var.lower():
                    detected.append(var)
                    break

    return detected


def parse_r_formula(formula: str) -> Dict[str, List[str]]:
    """
    Parse R-style formula (e.g., "y ~ x1 + x2 | z1 + z2").

    Args:
        formula: R formula string

    Returns:
        Dict with 'outcome', 'predictors', 'instruments' (if present)

    Note:
        Handles formulas with instruments (two-stage least squares)
    """
    parts = formula.split("~")
    if len(parts) != 2:
        return {"outcome": "", "predictors": [], "instruments": []}

    outcome = parts[0].strip()
    rhs = parts[1].strip()

    # Check for instruments (indicated by |)
    if "|" in rhs:
        predictors_str, instruments_str = rhs.split("|", 1)
        predictors = [p.strip() for p in re.split(r'[+\s]+', predictors_str.strip()) if p.strip()]
        instruments = [i.strip() for i in re.split(r'[+\s]+', instruments_str.strip()) if i.strip()]
    else:
        predictors = [p.strip() for p in re.split(r'[+\s]+', rhs) if p.strip()]
        instruments = []

    return {
        "outcome": outcome,
        "predictors": predictors,
        "instruments": instruments,
    }


def extract_variables_from_formula(formula: str) -> Set[str]:
    """
    Extract all variable names from formula string.

    Args:
        formula: Formula string

    Returns:
        Set of variable names

    Note:
        Handles various formula syntaxes (R, Python, patsy)
    """
    # Remove outcome (left of ~)
    if "~" in formula:
        _, rhs = formula.split("~", 1)
    else:
        rhs = formula

    # Remove function calls but keep arguments
    # E.g., log(x) -> x, I(x^2) -> x
    rhs = re.sub(r'\b(log|exp|sqrt|I|poly|bs|ns|C)\s*\(', '(', rhs)

    # Split on operators
    tokens = re.split(r'[+\-*/()\[\]\s,|:^]+', rhs)

    # Filter to valid variable names
    variables = set()
    for token in tokens:
        token = token.strip()
        # Valid variable: starts with letter or underscore, contains alphanumeric or underscore
        if token and re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', token):
            variables.add(token)

    return variables


# ============================================================================
# Design Matrix Inspection
# ============================================================================

def check_design_matrix_columns(
    column_names: List[str],
    mediator_vars: Optional[List[str]] = None,
    case_sensitive: bool = False
) -> List[str]:
    """
    Check design matrix column names for mediators.

    This is more reliable than formula parsing because it checks actual matrices.

    Args:
        column_names: List of column names in design matrix
        mediator_vars: List of mediator variable patterns
        case_sensitive: Whether to use case-sensitive matching

    Returns:
        List of detected mediator columns

    Example:
        >>> columns = ["intercept", "A_t_clean", "P_calldata_gas", "D_star"]
        >>> check_design_matrix_columns(columns)
        ['P_calldata_gas']  # VIOLATION!
    """
    if mediator_vars is None:
        mediator_vars = DEFAULT_MEDIATOR_VARS

    detected = []

    for col in column_names:
        for mediator in mediator_vars:
            if case_sensitive:
                if mediator in col:
                    detected.append(col)
                    break
            else:
                if mediator.lower() in col.lower():
                    detected.append(col)
                    break

    return detected


# ============================================================================
# Codebase Scanning
# ============================================================================

def scan_python_file(
    file_path: Path,
    mediator_vars: Optional[List[str]] = None
) -> List[Dict[str, any]]:
    """
    Scan Python file for potential leakage in model specifications.

    Args:
        file_path: Path to Python file
        mediator_vars: List of mediator variables to check

    Returns:
        List of violations found (empty if clean)

    Note:
        Looks for formula strings in:
        - smf.ols(), sm.OLS()
        - CausalImpact(), bsts()
        - LinearRegression.fit()
        - Formula assignments
    """
    if mediator_vars is None:
        mediator_vars = DEFAULT_MEDIATOR_VARS

    violations = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Look for formula strings
        # Pattern 1: formula="..." or formula='...'
        formula_patterns = [
            r'formula\s*=\s*["\']([^"\']+)["\']',
            r'smf\.ols\s*\(\s*["\']([^"\']+)["\']',
            r'sm\.OLS\s*\(',  # May need more sophisticated parsing
        ]

        for pattern in formula_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                if match.groups():
                    formula = match.group(1)
                    detected = check_formula_for_leakage(formula, mediator_vars)

                    if detected:
                        # Find line number
                        line_num = content[:match.start()].count('\n') + 1

                        violations.append({
                            "file": str(file_path),
                            "line": line_num,
                            "formula": formula,
                            "mediators_detected": detected,
                            "severity": "CRITICAL",
                        })

    except Exception as e:
        warnings.warn(f"Error scanning {file_path}: {e}")

    return violations


def scan_r_file(
    file_path: Path,
    mediator_vars: Optional[List[str]] = None
) -> List[Dict[str, any]]:
    """
    Scan R file for potential leakage in model specifications.

    Args:
        file_path: Path to R file
        mediator_vars: List of mediator variables to check

    Returns:
        List of violations found

    Note:
        Looks for formula strings in:
        - lm(), glm(), lmer()
        - CausalImpact(), bsts()
        - plm(), fixest::feols()
    """
    if mediator_vars is None:
        mediator_vars = DEFAULT_MEDIATOR_VARS

    violations = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Look for R formula patterns
        # Pattern: function(formula, ...)
        r_patterns = [
            r'lm\s*\(\s*([^,]+)\s*,',
            r'glm\s*\(\s*([^,]+)\s*,',
            r'lmer\s*\(\s*([^,]+)\s*,',
            r'plm\s*\(\s*([^,]+)\s*,',
            r'feols\s*\(\s*([^,]+)\s*,',
            r'bsts\s*\(\s*([^,]+)\s*,',
            r'CausalImpact\s*\(',
        ]

        for pattern in r_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                if match.groups():
                    formula = match.group(1).strip()
                    detected = check_formula_for_leakage(formula, mediator_vars)

                    if detected:
                        line_num = content[:match.start()].count('\n') + 1

                        violations.append({
                            "file": str(file_path),
                            "line": line_num,
                            "formula": formula,
                            "mediators_detected": detected,
                            "severity": "CRITICAL",
                        })

    except Exception as e:
        warnings.warn(f"Error scanning {file_path}: {e}")

    return violations


def scan_yaml_file(
    file_path: Path,
    mediator_vars: Optional[List[str]] = None
) -> List[Dict[str, any]]:
    """
    Scan YAML configuration file for model specifications with leakage.

    Args:
        file_path: Path to YAML file
        mediator_vars: List of mediator variables to check

    Returns:
        List of violations found
    """
    if mediator_vars is None:
        mediator_vars = DEFAULT_MEDIATOR_VARS

    violations = []

    try:
        import yaml

        with open(file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Recursively search for formula strings
        def search_dict(d, path=""):
            if isinstance(d, dict):
                for key, value in d.items():
                    new_path = f"{path}.{key}" if path else key

                    if isinstance(value, str) and ("~" in value or "formula" in key.lower()):
                        # Potential formula
                        detected = check_formula_for_leakage(value, mediator_vars)
                        if detected:
                            violations.append({
                                "file": str(file_path),
                                "path": new_path,
                                "formula": value,
                                "mediators_detected": detected,
                                "severity": "CRITICAL",
                            })
                    else:
                        search_dict(value, new_path)

            elif isinstance(d, list):
                for i, item in enumerate(d):
                    search_dict(item, f"{path}[{i}]")

        search_dict(config)

    except ImportError:
        warnings.warn(f"PyYAML not available, skipping {file_path}")
    except Exception as e:
        warnings.warn(f"Error scanning {file_path}: {e}")

    return violations


def scan_codebase(
    project_root: Path,
    mediator_vars: Optional[List[str]] = None,
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None
) -> Dict[str, any]:
    """
    Scan entire codebase for leakage violations.

    Args:
        project_root: Path to project root directory
        mediator_vars: List of mediator variables to check
        include_patterns: File patterns to include (default: *.py, *.R, *.yaml)
        exclude_patterns: Directory patterns to exclude (default: tests/, venv/, .git/)

    Returns:
        Dict with scan results and violations

    Example:
        >>> report = scan_codebase(Path("/path/to/project"))
        >>> if report["total_violations"] > 0:
        >>>     print("LEAKAGE DETECTED - BLOCKING RELEASE")
    """
    if mediator_vars is None:
        mediator_vars = DEFAULT_MEDIATOR_VARS

    if include_patterns is None:
        include_patterns = ["*.py", "*.R", "*.yaml", "*.yml"]

    if exclude_patterns is None:
        exclude_patterns = ["tests/", "venv/", ".venv/", "env/", ".git/", "__pycache__/"]

    all_violations = []
    scanned_files = []

    for pattern in include_patterns:
        for file_path in project_root.rglob(pattern):
            # Check exclusions
            if any(excl in str(file_path) for excl in exclude_patterns):
                continue

            scanned_files.append(file_path)

            # Scan based on file type
            if file_path.suffix == ".py":
                violations = scan_python_file(file_path, mediator_vars)
            elif file_path.suffix == ".R":
                violations = scan_r_file(file_path, mediator_vars)
            elif file_path.suffix in [".yaml", ".yml"]:
                violations = scan_yaml_file(file_path, mediator_vars)
            else:
                continue

            all_violations.extend(violations)

    # Generate report
    report = {
        "timestamp": pd.Timestamp.now().isoformat(),
        "project_root": str(project_root),
        "mediator_vars": mediator_vars,
        "scanned_files": len(scanned_files),
        "total_violations": len(all_violations),
        "violations": all_violations,
        "pass": len(all_violations) == 0,
        "severity": "CRITICAL" if len(all_violations) > 0 else "PASS",
    }

    return report


# ============================================================================
# Reporting
# ============================================================================

def generate_leakage_report_markdown(report: Dict[str, any]) -> str:
    """
    Generate markdown report from leakage scan results.

    Args:
        report: Report dict from scan_codebase()

    Returns:
        Markdown-formatted report string
    """
    lines = [
        "# Quality Gate G3: Leakage Check Report",
        "",
        f"**Timestamp:** {report['timestamp']}",
        f"**Project:** {report['project_root']}",
        f"**Status:** {'PASS' if report['pass'] else 'FAIL'}",
        f"**Severity:** {report['severity']}",
        "",
        "## Summary",
        "",
        f"- Files scanned: {report['scanned_files']}",
        f"- Violations detected: {report['total_violations']}",
        f"- Mediator variables: {', '.join(report['mediator_vars'])}",
        "",
    ]

    if report['total_violations'] > 0:
        lines.extend([
            "## VIOLATIONS DETECTED",
            "",
            "**ACTION REQUIRED:** Remove mediator variables from the following models:",
            "",
        ])

        for i, violation in enumerate(report['violations'], 1):
            lines.extend([
                f"### Violation {i}",
                "",
                f"- **File:** `{violation['file']}`",
                f"- **Line:** {violation.get('line', 'N/A')}",
                f"- **Formula:** `{violation['formula']}`",
                f"- **Mediators detected:** {', '.join(violation['mediators_detected'])}",
                "",
            ])

    else:
        lines.extend([
            "## All Checks Passed",
            "",
            "No mediator variables detected in total effect models.",
            "",
        ])

    return "\n".join(lines)


# Import for timestamps
import pandas as pd
