"""3スクリプトを順次実行し、各段階の成否とエラーをログに残す。"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "run.log"

# charts ステップだけは base 環境の python を使う
BASE_PYTHON = r"C:\Users\koich\anaconda3\python.exe"

STEPS = [
    ("fetch", SCRIPTS_DIR / "fetch_data.py", BASE_PYTHON),
    ("fetch_wb", SCRIPTS_DIR / "fetch_worldbank.py", sys.executable),
    ("charts", SCRIPTS_DIR / "build_charts.py", BASE_PYTHON),
    ("html", SCRIPTS_DIR / "export_html.py", sys.executable),
]


def setup_logger() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("crisis_frontier")
    logger.setLevel(logging.INFO)
    # 二重ハンドラ防止
    if not logger.handlers:
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
        fh.setFormatter(fmt)
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        logger.addHandler(fh)
        logger.addHandler(sh)
    return logger


def run_step(logger: logging.Logger, name: str, script: Path, python_exe: str) -> bool:
    logger.info(f"=== STEP {name} 開始: {script.name} (python={python_exe}) ===")
    try:
        # check=False にして戻り値で判定（標準出力もログへ流す）
        result = subprocess.run(
            [python_exe, str(script)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="cp932",
        )
        if result.stdout:
            for line in result.stdout.rstrip().splitlines():
                logger.info(f"[{name} stdout] {line}")
        if result.stderr:
            for line in result.stderr.rstrip().splitlines():
                logger.warning(f"[{name} stderr] {line}")
        if result.returncode == 0:
            logger.info(f"=== STEP {name} 成功 ===")
            return True
        logger.error(f"=== STEP {name} 失敗 (exit={result.returncode}) ===")
        return False
    except Exception as e:
        logger.exception(f"=== STEP {name} 例外: {e!r} ===")
        return False


def main() -> int:
    logger = setup_logger()
    logger.info("###### run_all.py 開始 ######")
    overall_ok = True
    for name, script, python_exe in STEPS:
        ok = run_step(logger, name, script, python_exe)
        if not ok:
            overall_ok = False
            # 取得が全滅の場合、後段の意味はないが描画/HTMLは独立に試行する
            # （既存DBや既存PNGがあれば部分的に成果が出る）
    if overall_ok:
        logger.info("###### run_all.py 全STEP成功 ######")
        return 0
    logger.warning("###### run_all.py 一部STEP失敗 ######")
    return 1


if __name__ == "__main__":
    sys.exit(main())
