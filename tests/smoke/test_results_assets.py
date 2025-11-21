from pathlib import Path

RESULT_FILES = [
    Path("results/figures/publication/fig09_bsts_counterfactual.pdf"),
    Path("results/power/fig_power_post_dencun.pdf"),
    Path("results/bsts/bsts_natural_scale_results.csv"),
    Path("results/its_diagnostics/diagnostics_log_C_fee.png"),
]


def test_key_results_present():
    missing = [str(p) for p in RESULT_FILES if not p.exists()]
    assert not missing, f"Missing expected result files: {missing}"
