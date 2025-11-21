#!/usr/bin/env python3
"""
Mediator Exclusion Scanner
==========================
Automated tool to detect mediator leakage in causal analysis code.

This is a CRITICAL validation tool that scans all analysis code
to ensure mediator variables are never included in total effect models.

Author: QA Lead
Date: 2025-01-10
"""

import os
import re
import ast
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple
from datetime import datetime

# Define mediator variables that MUST be excluded
MEDIATORS = {
    'P_calldata_gas', 'P_blob_gas', 'P_calldata', 'P_blob',
    'p_calldata', 'p_blob', 'calldata_gas_price', 'blob_gas_price',
    'calldata_price', 'blob_price', 'posting_gas', 'posting_price',
    'P_t', 'p_t'  # Generic posting price notation
}

# Additional patterns that might indicate mediator usage
MEDIATOR_PATTERNS = [
    r'[Pp]_(?:calldata|blob)',
    r'(?:calldata|blob)_(?:gas_)?price',
    r'posting_(?:gas|price)',
    r'[Pp]_t(?:\s|,|\)|$)'  # P_t or p_t as variable
]

# Contexts where mediators should NOT appear
FORBIDDEN_CONTEXTS = [
    'corr', 'correlation', 'regression', 'model', 'X_vars', 'x_vars',
    'predictors', 'features', 'controls', 'regressors', 'covariates',
    'independent', 'explanatory', 'fit', 'LinearRegression', 'OLS',
    'statsmodels', 'sklearn', 'panel', 'fixed_effects', 'random_effects'
]

# Safe contexts (where mediators can appear)
SAFE_CONTEXTS = [
    'exclude', 'excluded', 'not in', 'remove', 'drop', 'filter out',
    'mediator', 'indirect', 'decomposition', 'comment', 'doc', 'print',
    'warning', 'note', 'TODO', 'FIXME'
]


class MediatorLeakageScanner:
    """Scan codebase for mediator leakage in total effect models."""

    def __init__(self, project_root: Path):
        """Initialize scanner with project root."""
        self.project_root = project_root
        self.src_dir = project_root / 'src'
        self.results = {
            'scan_timestamp': datetime.now().isoformat(),
            'files_scanned': [],
            'violations': [],
            'warnings': [],
            'info': [],
            'leakage_detected': False
        }

    def scan_file(self, filepath: Path) -> List[Dict]:
        """Scan a single file for mediator references."""
        violations = []

        if not filepath.exists() or not filepath.suffix == '.py':
            return violations

        print(f"Scanning: {filepath.name}")
        self.results['files_scanned'].append(str(filepath))

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

            # Parse AST for more accurate detection
            try:
                tree = ast.parse(content)
                violations.extend(self._analyze_ast(tree, filepath))
            except SyntaxError:
                print(f"  Warning: Could not parse AST for {filepath.name}")

            # Line-by-line analysis
            for line_num, line in enumerate(lines, 1):
                line_violations = self._analyze_line(line, line_num, filepath)
                violations.extend(line_violations)

        except Exception as e:
            print(f"  Error scanning {filepath}: {e}")

        return violations

    def _analyze_ast(self, tree: ast.AST, filepath: Path) -> List[Dict]:
        """Analyze AST for mediator usage in dangerous contexts."""
        violations = []

        class MediatorVisitor(ast.NodeVisitor):
            def __init__(self, scanner, filepath):
                self.scanner = scanner
                self.filepath = filepath
                self.violations = []

            def visit_Call(self, node):
                """Check function calls for regression/model fitting."""
                if hasattr(node.func, 'attr'):
                    # Check for model fitting methods
                    if node.func.attr in ['fit', 'predict', 'transform']:
                        # Check arguments for mediators
                        for arg in node.args:
                            if isinstance(arg, ast.Name) and arg.id in MEDIATORS:
                                self.violations.append({
                                    'file': self.filepath.name,
                                    'line': node.lineno,
                                    'type': 'AST_MODEL_FIT',
                                    'severity': 'CRITICAL',
                                    'mediator': arg.id,
                                    'context': f"{node.func.attr} call"
                                })

                self.generic_visit(node)

            def visit_Assign(self, node):
                """Check variable assignments."""
                # Check if assigning to X_vars, predictors, etc.
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if any(context in target.id.lower() for context in ['x_vars', 'predictors', 'features']):
                            # Check if mediators in the value
                            mediators_found = self._find_mediators_in_node(node.value)
                            if mediators_found:
                                self.violations.append({
                                    'file': self.filepath.name,
                                    'line': node.lineno,
                                    'type': 'AST_ASSIGNMENT',
                                    'severity': 'CRITICAL',
                                    'variable': target.id,
                                    'mediators': list(mediators_found),
                                    'context': f"Assignment to {target.id}"
                                })

                self.generic_visit(node)

            def _find_mediators_in_node(self, node):
                """Recursively find mediator references in a node."""
                mediators_found = set()

                if isinstance(node, ast.Name) and node.id in MEDIATORS:
                    mediators_found.add(node.id)
                elif isinstance(node, ast.Str) and node.s in MEDIATORS:
                    mediators_found.add(node.s)
                elif isinstance(node, ast.List):
                    for elt in node.elts:
                        mediators_found.update(self._find_mediators_in_node(elt))
                elif isinstance(node, ast.Tuple):
                    for elt in node.elts:
                        mediators_found.update(self._find_mediators_in_node(elt))

                return mediators_found

        visitor = MediatorVisitor(self, filepath)
        visitor.visit(tree)
        violations.extend(visitor.violations)

        return violations

    def _analyze_line(self, line: str, line_num: int, filepath: Path) -> List[Dict]:
        """Analyze a single line for mediator references."""
        violations = []

        # Skip comments and docstrings
        stripped = line.strip()
        if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
            return violations

        # Check for mediator mentions
        line_lower = line.lower()

        # Direct mediator check
        for mediator in MEDIATORS:
            if mediator.lower() in line_lower:
                # Determine context
                context = self._determine_context(line)
                severity = self._determine_severity(line, context)

                if severity in ['CRITICAL', 'HIGH']:
                    violation = {
                        'file': filepath.name,
                        'line': line_num,
                        'type': 'LINE_SCAN',
                        'severity': severity,
                        'mediator': mediator,
                        'code': line.strip()[:100],  # First 100 chars
                        'context': context
                    }
                    violations.append(violation)

        # Pattern-based check
        for pattern in MEDIATOR_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                context = self._determine_context(line)
                severity = self._determine_severity(line, context)

                if severity in ['CRITICAL', 'HIGH']:
                    violation = {
                        'file': filepath.name,
                        'line': line_num,
                        'type': 'PATTERN_MATCH',
                        'severity': severity,
                        'pattern': pattern,
                        'code': line.strip()[:100],
                        'context': context
                    }
                    violations.append(violation)

        return violations

    def _determine_context(self, line: str) -> str:
        """Determine the context of mediator usage."""
        line_lower = line.lower()

        # Check for safe contexts first
        for safe in SAFE_CONTEXTS:
            if safe in line_lower:
                return f"SAFE: {safe}"

        # Check for forbidden contexts
        for forbidden in FORBIDDEN_CONTEXTS:
            if forbidden in line_lower:
                return f"FORBIDDEN: {forbidden}"

        # Check for specific patterns
        if 'df[' in line or 'df[[' in line:
            return "DataFrame indexing"
        elif '=' in line and any(var in line for var in ['X', 'features', 'predictors']):
            return "Variable assignment"
        elif '.corr(' in line or 'correlation' in line_lower:
            return "Correlation analysis"
        elif '.fit(' in line or 'regression' in line_lower:
            return "Model fitting"

        return "Unknown"

    def _determine_severity(self, line: str, context: str) -> str:
        """Determine severity of potential violation."""
        if context.startswith("SAFE"):
            return "INFO"

        if context.startswith("FORBIDDEN"):
            return "CRITICAL"

        # Specific high-risk patterns
        high_risk_patterns = [
            r'X_vars.*=',
            r'predictors.*=',
            r'\.fit\(',
            r'LinearRegression',
            r'OLS\(',
            r'panel.*model',
            r'correlation.*matrix'
        ]

        for pattern in high_risk_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return "CRITICAL"

        # Medium risk
        if any(term in line.lower() for term in ['model', 'regression', 'analysis']):
            return "HIGH"

        return "LOW"

    def scan_directory(self, directory: Path) -> None:
        """Recursively scan directory for Python files."""
        print(f"\nScanning directory: {directory}")

        py_files = list(directory.rglob("*.py"))
        print(f"Found {len(py_files)} Python files")

        for py_file in py_files:
            # Skip test files and this scanner itself
            if 'test' in py_file.name.lower() or py_file.name == 'mediator_exclusion_scanner.py':
                continue

            violations = self.scan_file(py_file)

            for violation in violations:
                if violation['severity'] == 'CRITICAL':
                    self.results['violations'].append(violation)
                    self.results['leakage_detected'] = True
                elif violation['severity'] == 'HIGH':
                    self.results['warnings'].append(violation)
                else:
                    self.results['info'].append(violation)

    def scan_notebooks(self, directory: Path) -> None:
        """Scan Jupyter notebooks for mediator leakage."""
        print(f"\nScanning notebooks in: {directory}")

        notebooks = list(directory.rglob("*.ipynb"))
        print(f"Found {len(notebooks)} notebooks")

        for notebook_path in notebooks:
            try:
                with open(notebook_path, 'r') as f:
                    nb_content = json.load(f)

                for cell_idx, cell in enumerate(nb_content.get('cells', [])):
                    if cell.get('cell_type') == 'code':
                        source = ''.join(cell.get('source', []))

                        # Create temporary analysis
                        lines = source.split('\n')
                        for line_num, line in enumerate(lines, 1):
                            violations = self._analyze_line(line, line_num, notebook_path)

                            for violation in violations:
                                violation['cell'] = cell_idx
                                if violation['severity'] == 'CRITICAL':
                                    self.results['violations'].append(violation)
                                    self.results['leakage_detected'] = True

            except Exception as e:
                print(f"  Error scanning notebook {notebook_path}: {e}")

    def generate_report(self) -> str:
        """Generate detailed scan report."""
        report = []

        report.append("=" * 80)
        report.append("MEDIATOR EXCLUSION SCAN REPORT")
        report.append("=" * 80)
        report.append(f"Scan timestamp: {self.results['scan_timestamp']}")
        report.append(f"Files scanned: {len(self.results['files_scanned'])}")
        report.append("")

        # Summary
        report.append("SUMMARY")
        report.append("-" * 40)
        report.append(f"Critical violations: {len(self.results['violations'])}")
        report.append(f"Warnings: {len(self.results['warnings'])}")
        report.append(f"Info messages: {len(self.results['info'])}")
        report.append(f"LEAKAGE DETECTED: {'YES - BLOCKING' if self.results['leakage_detected'] else 'NO'}")
        report.append("")

        # Critical violations
        if self.results['violations']:
            report.append("CRITICAL VIOLATIONS (Must Fix)")
            report.append("-" * 40)
            for v in self.results['violations'][:20]:  # Show first 20
                report.append(f"File: {v['file']}, Line: {v['line']}")
                report.append(f"  Mediator: {v.get('mediator', v.get('pattern', 'unknown'))}")
                report.append(f"  Context: {v['context']}")
                report.append(f"  Code: {v.get('code', 'N/A')}")
                report.append("")

        # Warnings
        if self.results['warnings']:
            report.append("WARNINGS (Review Needed)")
            report.append("-" * 40)
            for w in self.results['warnings'][:10]:  # Show first 10
                report.append(f"File: {w['file']}, Line: {w['line']}")
                report.append(f"  Context: {w['context']}")
                report.append("")

        # Recommendation
        report.append("RECOMMENDATIONS")
        report.append("-" * 40)
        if self.results['leakage_detected']:
            report.append("⚠️  CRITICAL: Mediator leakage detected!")
            report.append("1. Remove all mediator variables from total effect models")
            report.append("2. Mediators can only appear in mediation analysis")
            report.append("3. Re-run this scanner after fixes")
            report.append("4. Gate G3 will remain FAILED until resolved")
        else:
            report.append("✅ No mediator leakage detected")
            report.append("Gate G3 validation PASSED")

        return "\n".join(report)

    def save_results(self, output_dir: Path) -> None:
        """Save scan results to files."""
        output_dir.mkdir(exist_ok=True, parents=True)

        # Save JSON results
        json_path = output_dir / f"mediator_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)

        # Save text report
        report = self.generate_report()
        report_path = output_dir / f"mediator_scan_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_path, 'w') as f:
            f.write(report)

        print(f"\nResults saved to:")
        print(f"  - {json_path}")
        print(f"  - {report_path}")


def main():
    """Run mediator exclusion scan."""
    import argparse

    parser = argparse.ArgumentParser(description="Scan for mediator leakage in causal analysis code")
    parser.add_argument('--root', type=str, help='Project root directory')
    parser.add_argument('--src', type=str, help='Source directory to scan')
    parser.add_argument('--output', type=str, help='Output directory for results')
    parser.add_argument('--include-notebooks', action='store_true', help='Include Jupyter notebooks')

    args = parser.parse_args()

    # Determine paths
    if args.root:
        project_root = Path(args.root)
    else:
        project_root = Path(__file__).resolve().parents[2]

    if args.src:
        src_dir = Path(args.src)
    else:
        src_dir = project_root / 'src'

    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = project_root / 'results' / 'qa'

    print("=" * 80)
    print("MEDIATOR EXCLUSION SCANNER")
    print("=" * 80)
    print(f"Project root: {project_root}")
    print(f"Scanning: {src_dir}")
    print(f"Output: {output_dir}")

    # Initialize scanner
    scanner = MediatorLeakageScanner(project_root)

    # Scan source directory
    if src_dir.exists():
        scanner.scan_directory(src_dir)
    else:
        print(f"Warning: Source directory not found: {src_dir}")

    # Scan notebooks if requested
    if args.include_notebooks:
        scanner.scan_notebooks(project_root)

    # Generate and print report
    report = scanner.generate_report()
    print("\n" + report)

    # Save results
    scanner.save_results(output_dir)

    # Exit with appropriate code
    if scanner.results['leakage_detected']:
        print("\n❌ GATE G3 FAILED - Mediator leakage detected")
        return 1
    else:
        print("\n✅ GATE G3 PASSED - No mediator leakage")
        return 0


if __name__ == "__main__":
    exit(main())