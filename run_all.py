"""
Run the whole pipeline in order.

    python run_all.py            # real data: download from CMS, then analyse
    python run_all.py --sample   # synthetic test data (no internet needed)
    python run_all.py --mirror   # real data from this repo's GitHub release
                                 # (for networks where data.cms.gov is blocked)
    python run_all.py --skip-download   # reuse CSVs already in data/raw/
"""
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).parent / "src"
steps = ["02_clean.py", "03_market_sizing.py", "04_segmentation.py",
         "05_forecast.py", "06_charts.py", "07_tableau_extracts.py"]
if "--sample" in sys.argv:
    steps = ["00_make_sample_data.py"] + steps
elif "--skip-download" not in sys.argv:
    steps = ["01_download.py"] + steps

for step in steps:
    print(f"\n=== {step} ===")
    extra = ["--mirror"] if step == "01_download.py" and "--mirror" in sys.argv else []
    subprocess.run([sys.executable, str(SRC / step)] + extra, check=True, cwd=SRC)
