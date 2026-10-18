"""Rebuild everything: data, metric tables, experiments, and the Excel model."""

import sys

from lab import analyze, build_db, excel_model, experiments


def main() -> None:
    if "--skip-download" not in sys.argv:
        build_db.download()
    build_db.build()
    analyze.run()
    experiments.report()
    print(excel_model.build())


if __name__ == "__main__":
    main()
