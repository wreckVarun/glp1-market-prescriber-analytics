"""
Run the whole pipeline in order.

    python run_all.py            # real data: download from CMS, then analyse
    python run_all.py --sample   # synthetic test data (no internet needed)
"""
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).parent / "src"
steps = ["02_clean.py", "03_market_sizing.py", "04_segmentation.py",
         "05_forecast.py", "06_charts.py", "07_tableau_extracts.py"]
first = "00_make_sample_data.py" if "--sample" in sys.argv else "01_download.py"

for step in [first] + steps:
    print(f"\n=== {step} ===")
    subprocess.run([sys.executable, str(SRC / step)], check=True, cwd=SRC)
