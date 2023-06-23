import logging
import sys
from pathlib import Path
from typing import Optional, Union

try:
    import importlib.metadata as importlib_metadata
except ImportError:
    import importlib_metadata

import click
from rich.console import Console
from rich.logging import RichHandler

import ms2pip.core
from ms2pip.constants import MODELS, SUPPORTED_OUTPUT_FORMATS
from ms2pip.exceptions import (
    InvalidXGBoostModelError,
    UnknownModelError,
    UnknownOutputFormatError,
    UnresolvableModificationError,
)
from ms2pip.result import correlations_to_csv, results_to_csv

__version__ = importlib_metadata.version("ms2pip")

logger = logging.getLogger(__name__)


def print_logo():
    print(
        f"\nMS²PIP v{__version__}\n"
        "CompOmics, VIB / Ghent University, Belgium\n"
        "https://github.com/compomics/ms2pip\n"
    )


def _infer_output_name(
    input_filename: str,
    output_name: Optional[str] = None,
) -> Path:
    """Infer output filename from input filename if output_filename was not defined."""
    if output_name:
        return Path(output_name)
    else:
        return Path(input_filename).with_suffix("")


@click.group()
@click.version_option(version=__version__)
def cli(*args, **kwargs):
    pass


@cli.command(help=ms2pip.core.predict_single.__doc__)
def predict_single(*args, **kwargs):
    ms2pip.core.predict_single(*args, **kwargs)


@cli.command(help=ms2pip.core.predict_batch.__doc__)
@click.argument("psms", required=True)
@click.option("--output-name", "-o", type=str)
@click.option("--output-format", "-f", type=click.Choice(SUPPORTED_OUTPUT_FORMATS))
@click.option("--add-retention-time", "-r", is_flag=True)
@click.option("--model", type=click.Choice(MODELS), default="HCD")
@click.option("--model-dir")
@click.option("--processes", "-n", type=int)
def predict_batch(*args, **kwargs):
    # Parse arguments
    output_name = kwargs.pop("output_name")
    output_format = kwargs.pop("output_format")
    output_name = _infer_output_name(kwargs["psms"], output_name)

    # Run
    predictions = ms2pip.core.predict_batch(*args, **kwargs)

    # Write output
    output_name_csv = output_name.with_name(output_name.stem + "_predictions").with_suffix(".csv")
    logger.info(f"Writing output to {output_name_csv}")
    results_to_csv(predictions, output_name_csv)


@cli.command(help=ms2pip.core.predict_library.__doc__)
def predict_library(*args, **kwargs):
    ms2pip.core.predict_library(*args, **kwargs)


@cli.command(help=ms2pip.core.correlate.__doc__)
@click.argument("psms", required=True)
@click.argument("spectrum_file", required=True)
@click.option("--output-name", "-o", type=str)
@click.option("--spectrum-id-pattern", "-p")
@click.option("--compute-correlations", "-x", is_flag=True)
@click.option("--add-retention-time", "-r", is_flag=True)
@click.option("--model", type=click.Choice(MODELS), default="HCD")
@click.option("--model-dir")
@click.option("--ms2-tolerance", type=float, default=0.02)
@click.option("--processes", "-n", type=int)
def correlate(*args, **kwargs):
    # Parse arguments
    output_name = kwargs.pop("output_name")
    output_name = _infer_output_name(kwargs["psms"], output_name)

    # Run
    results = ms2pip.core.correlate(*args, **kwargs)

    # Write output
    output_name_int = output_name.with_name(output_name.stem + "_predictions").with_suffix(".csv")
    logger.info(f"Writing intensities to {output_name_int}")
    results_to_csv(results, output_name_int)

    # Write correlations
    if kwargs["compute_correlations"]:
        output_name_corr = output_name.with_name(output_name.stem + "_correlations")
        output_name_corr = output_name_corr.with_suffix(".csv")
        logger.info(f"Writing correlations to {output_name_corr}")
        correlations_to_csv(results, output_name_corr)


@cli.command(help=ms2pip.core.get_training_data.__doc__)
def get_training_data(*args, **kwargs):
    ms2pip.core.get_training_data(*args, **kwargs)


def main():
    logging.basicConfig(
        format="%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.DEBUG,
        handlers=[
            RichHandler(rich_tracebacks=True, console=Console(), show_level=True, show_path=False)
        ],
    )
    logger = logging.getLogger(__name__)

    # print_logo()

    try:
        cli()
    except UnresolvableModificationError as e:
        logger.critical(
            "Unresolvable modification: `%s`. See [TODO: URL TO DOCS] for more info.", e
        )
        sys.exit(1)
    except UnknownOutputFormatError as o:
        logger.critical(
            f"Unknown output format: `{o}` (supported formats: `{SUPPORTED_OUTPUT_FORMATS}`)"
        )
        sys.exit(1)
    except UnknownModelError as f:
        logger.critical(f"Unknown model: `{f}` (supported models: {set(MODELS.keys())})")
        sys.exit(1)
    except InvalidXGBoostModelError:
        logger.critical(f"Could not download XGBoost model properly\nTry a manual download.")
        sys.exit(1)
    except Exception:
        logger.exception("An unexpected error occurred in MS²PIP.")
        sys.exit(1)


if __name__ == "__main__":
    main()
