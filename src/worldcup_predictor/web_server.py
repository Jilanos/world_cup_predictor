from __future__ import annotations

import argparse
import json
import shutil
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import unquote

import pandas as pd

from .cli import run as run_predictions
from .config import (
    DEFAULT_ELO_PATH,
    DEFAULT_FIFA_PATH,
    DEFAULT_FIXTURES_PATH,
    DEFAULT_ODDS_PATH,
    DEFAULT_PREDICTIONS_CSV,
    DEFAULT_PREDICTIONS_MD,
    DEFAULT_RESULTS_PATH,
    MIN_RESULTS_FOR_RELIABLE,
    OUTPUT_DIR,
    PROJECT_ROOT,
)


WEB_DIR = PROJECT_ROOT / "web"
EXAMPLES_DIR = PROJECT_ROOT / "examples"

DATA_FILES = {
    "fixtures": {
        "label": "Fixtures",
        "path": DEFAULT_FIXTURES_PATH,
        "required": True,
        "columns": ["date", "home_team", "away_team"],
        "example": EXAMPLES_DIR / "fixtures.csv",
    },
    "results": {
        "label": "Historical results",
        "path": DEFAULT_RESULTS_PATH,
        "required": True,
        "columns": ["date", "home_team", "away_team", "home_score", "away_score"],
        "example": EXAMPLES_DIR / "international_results.csv",
    },
    "elo": {
        "label": "Elo rankings",
        "path": DEFAULT_ELO_PATH,
        "required": False,
        "columns": ["team", "elo"],
        "example": EXAMPLES_DIR / "elo_rankings.csv",
    },
    "fifa": {
        "label": "FIFA rankings",
        "path": DEFAULT_FIFA_PATH,
        "required": False,
        "columns": ["team", "rank"],
        "example": EXAMPLES_DIR / "fifa_rankings.csv",
    },
    "odds": {
        "label": "Bookmaker odds",
        "path": DEFAULT_ODDS_PATH,
        "required": False,
        "columns": ["date", "home_team", "away_team", "home_odds", "draw_odds", "away_odds"],
        "example": EXAMPLES_DIR / "bookmaker_odds.csv",
    },
}

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local World Cup Predictor dashboard.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    return parser.parse_args()


def _relative(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT))


def _file_status(key: str, config: dict[str, object]) -> dict[str, object]:
    path = config["path"]
    assert isinstance(path, Path)
    required_columns = list(config["columns"])
    exists = path.exists()
    status: dict[str, object] = {
        "key": key,
        "label": config["label"],
        "path": _relative(path),
        "required": config["required"],
        "exists": exists,
        "rows": 0,
        "columns": [],
        "required_columns": required_columns,
        "missing_columns": required_columns,
        "preview": [],
        "error": None,
        "updated_at": None,
    }
    if not exists:
        return status

    try:
        df = pd.read_csv(path)
        status["rows"] = int(len(df))
        status["columns"] = list(df.columns)
        status["missing_columns"] = [column for column in required_columns if column not in df.columns]
        status["preview"] = df.head(8).fillna("").astype(str).to_dict(orient="records")
        status["updated_at"] = pd.Timestamp(path.stat().st_mtime, unit="s").isoformat()
    except Exception as exc:  # pragma: no cover - surfaced in the UI
        status["error"] = str(exc)
    return status


def dashboard_status() -> dict[str, object]:
    files = [_file_status(key, config) for key, config in DATA_FILES.items()]
    outputs = [_file_status("predictions", {
        "label": "Predictions CSV",
        "path": DEFAULT_PREDICTIONS_CSV,
        "required": False,
        "columns": [
            "date",
            "home_team",
            "away_team",
            "predicted_result",
            "predicted_winner_or_draw",
            "probability_home_win",
            "probability_draw",
            "probability_away_win",
            "confidence_level",
            "short_explanation",
        ],
    })]
    ready = all(file["exists"] and not file["missing_columns"] and not file["error"] for file in files if file["required"])
    results_file = next((file for file in files if file["key"] == "results"), None)
    n_results = int(results_file["rows"]) if results_file else 0
    reliability = {
        "ok": n_results >= MIN_RESULTS_FOR_RELIABLE,
        "n_matches": n_results,
        "threshold": MIN_RESULTS_FOR_RELIABLE,
        "message": (
            f"Dataset OK: {n_results} historical matches."
            if n_results >= MIN_RESULTS_FOR_RELIABLE
            else (
                f"UNRELIABLE: only {n_results} historical matches "
                f"(< {MIN_RESULTS_FOR_RELIABLE}). Run scripts/fetch_results.py "
                "to download the full dataset before trusting predictions."
            )
        ),
    }
    return {
        "ready": ready,
        "files": files,
        "outputs": outputs,
        "output_dir": _relative(OUTPUT_DIR),
        "reliability": reliability,
    }


def copy_example_data() -> dict[str, object]:
    copied = []
    for config in DATA_FILES.values():
        source = config["example"]
        target = config["path"]
        assert isinstance(source, Path)
        assert isinstance(target, Path)
        if source.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            copied.append(_relative(target))
    return {"copied": copied, "status": dashboard_status()}


def run_from_options(payload: dict[str, object]) -> dict[str, object]:
    disabled_dir = PROJECT_ROOT / ".disabled-inputs"
    args = SimpleNamespace(
        fixtures=DEFAULT_FIXTURES_PATH,
        results=DEFAULT_RESULTS_PATH,
        elo=DEFAULT_ELO_PATH if payload.get("use_elo", True) else disabled_dir / "elo_rankings.csv",
        fifa=DEFAULT_FIFA_PATH if payload.get("use_fifa", True) else disabled_dir / "fifa_rankings.csv",
        odds=DEFAULT_ODDS_PATH if payload.get("use_odds", True) else disabled_dir / "bookmaker_odds.csv",
        output_csv=DEFAULT_PREDICTIONS_CSV,
        output_md=DEFAULT_PREDICTIONS_MD,
        market_weight=float(payload.get("market_weight", 0.35)),
    )
    predictions = run_predictions(args)
    return {
        "rows": int(len(predictions)),
        "csv": _relative(DEFAULT_PREDICTIONS_CSV),
        "markdown": _relative(DEFAULT_PREDICTIONS_MD),
        "status": dashboard_status(),
    }


class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")

    def do_GET(self) -> None:
        if self.path == "/api/status":
            self._send_json(dashboard_status())
            return
        if self.path.startswith("/outputs/"):
            self._send_file(PROJECT_ROOT / unquote(self.path.lstrip("/")))
            return
        route = "index.html" if self.path in {"/", "/index.html"} else unquote(self.path.lstrip("/"))
        self._send_file(WEB_DIR / route)

    def do_POST(self) -> None:
        if self.path == "/api/load-examples":
            self._send_json(copy_example_data())
            return
        if self.path == "/api/run":
            try:
                payload = self._read_json()
                self._send_json(run_from_options(payload))
            except Exception as exc:  # pragma: no cover - surfaced in the UI
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def _read_json(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _send_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        resolved = path.resolve()
        allowed_roots = [WEB_DIR.resolve(), OUTPUT_DIR.resolve()]
        if not any(resolved == root or root in resolved.parents for root in allowed_roots):
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if not resolved.exists() or not resolved.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = resolved.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", CONTENT_TYPES.get(resolved.suffix, "text/plain; charset=utf-8"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    print(f"World Cup Predictor dashboard: http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
