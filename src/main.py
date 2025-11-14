"""Friday Screener - Stock Screening Tool for Indonesian Market.

Main entry point untuk CLI application.
"""

import warnings

from src.cli.commands import cli

# Suppress all warnings untuk clean output
warnings.filterwarnings("ignore")

if __name__ == "__main__":
    cli()
