import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from scipy.signal import savgol_filter


#
# Auxiliary functions
#
def _smooth_row(row: pd.Series, window: int, polyorder: int) -> np.ndarray:
    """Apply Savitzky-Golay filter to one season row, preserving NaN positions.

    Args:
        row (pd.Series): The row to smooth.

        window (int): The window size for the Savitzky-Golay filter.

        polyorder (int): The polynomial order for the Savitzky-Golay filter.

    Returns:
        np.ndarray: The smoothed row.
    """
    values = row.to_numpy(dtype=float)
    mask = np.isnan(values)

    if mask.all():
        return values

    # interpolate gaps before filtering so savgol doesn't choke on NaN, then restore them
    filled = pd.Series(values).interpolate(limit_direction="both").to_numpy()

    smoothed = savgol_filter(filled, window_length=window, polyorder=polyorder)
    smoothed[mask] = np.nan

    return smoothed


def _threshold_crossing(values: np.ndarray, threshold: float, direction: str) -> int | None:
    """Return index where values first cross threshold from given direction (rise/fall).

    Args:
        values (np.ndarray): The values to check.

        threshold (float): The threshold to check.

        direction (str): The direction to check (rise/fall).

    Returns:
        int | None: The index where the values first cross the threshold.
    """
    for i in range(len(values) - 1):
        if np.isnan(values[i]) or np.isnan(values[i + 1]):
            continue

        if direction == "rise" and values[i] < threshold <= values[i + 1]:
            return i + 1

        if direction == "fall" and values[i] >= threshold > values[i + 1]:
            return i + 1

    return None


def _phenology_for_row(
    season_year: int,
    values: np.ndarray,
    sos_threshold: float,
    eos_threshold: float,
) -> dict:
    """Extract SOS, peak, EOS and derived metrics from a smoothed season curve.

    Args:
        season_year (int): The season year.

        values (np.ndarray): The values to check.

        sos_threshold (float): The SOS threshold.

        eos_threshold (float): The EOS threshold.

    Returns:
        dict: The phenology metrics.
    """
    valid = values[~np.isnan(values)]

    if len(valid) < 3:
        return {
            "season_year": season_year,
            "sos_step": None,
            "peak_step": None,
            "peak_ndvi": None,
            "eos_step": None,
            "los": None,
        }

    # threshold = base + fraction x amplitude
    # > same rule applied for SOS and EOS
    amplitude = float(np.nanmax(values) - np.nanmin(values))
    base = float(np.nanmin(values))

    sos_thresh = base + sos_threshold * amplitude
    eos_thresh = base + eos_threshold * amplitude

    # peak is the global maximum
    peak_step = int(np.nanargmax(values))
    peak_ndvi = float(values[peak_step])

    sos_step = _threshold_crossing(values, sos_thresh, "rise")
    eos_step = _threshold_crossing(values[peak_step:], eos_thresh, "fall")

    if eos_step is not None:
        eos_step += peak_step

    los = (eos_step - sos_step) if (sos_step is not None and eos_step is not None) else None

    # return phenology
    return {
        "season_year": season_year,
        "sos_step": sos_step,
        "peak_step": peak_step,
        "peak_ndvi": peak_ndvi,
        "eos_step": eos_step,
        "los": los,
    }


def _build_normal_band(smooth_matrix: pd.DataFrame) -> pd.DataFrame:
    """Compute p25/p50/p75 across historical seasons.

    Args:
        smooth_matrix (pd.DataFrame): The smoothed NDVI matrix.

    Returns:
        pd.DataFrame: The normal band.
    """
    return smooth_matrix.quantile([0.25, 0.50, 0.75]).T.rename(columns={0.25: "p25", 0.50: "p50", 0.75: "p75"})


#
# Public functions
#
def smooth_matrix(ndvi_matrix: pd.DataFrame, window: int = 5, polyorder: int = 2) -> pd.DataFrame:
    """Apply Savitzky-Golay smoothing row-wise to a season x step NDVI matrix.

    Args:
        ndvi_matrix (pd.DataFrame): The NDVI matrix.

        window (int): The Savitzky-Golay filter window length in steps (must be odd).

        polyorder (int): The polynomial order for the filter (must be < window).

    Returns:
        pd.DataFrame: The smoothed NDVI matrix.
    """
    smoothed = ndvi_matrix.apply(_smooth_row, axis=1, result_type="expand", args=(window, polyorder))
    smoothed.columns = ndvi_matrix.columns

    return smoothed


def compute_phenology(
    smooth_mat: pd.DataFrame,
    sos_threshold: float = 0.3,
    eos_threshold: float = 0.3,
) -> pd.DataFrame:
    """Extract phenology metrics for every season in the smoothed matrix.

    Args:
        smooth_mat (pd.DataFrame): The smoothed NDVI matrix (output of smooth_matrix).

        sos_threshold (float): The fraction of seasonal amplitude used to define Start-of-Season.

        eos_threshold (float): The fraction of seasonal amplitude used to define End-of-Season.

    Returns:
        pd.DataFrame: The phenology metrics.
    """
    # compute the phenology metrics for each season
    rows = [
        _phenology_for_row(yr, smooth_mat.loc[yr].to_numpy(), sos_threshold, eos_threshold) for yr in smooth_mat.index
    ]

    return pd.DataFrame(rows).set_index("season_year")


def plot_smooth_and_phenology(
    smooth_mat: pd.DataFrame,
    phenology: pd.DataFrame,
    current_year: int,
) -> Figure:
    """Plot current-season curve against the historical normal band.

    Args:
        smooth_mat (pd.DataFrame): The full smoothed NDVI matrix (all seasons).

        phenology (pd.DataFrame): The output of compute_phenology.

        current_year (int): The season start year to highlight as the current season.

    Returns:
        Figure: Matplotlib Figure with a single axes.
    """
    # get the historical normal band
    historical = smooth_mat.drop(index=current_year, errors="ignore")

    band = _build_normal_band(historical)

    # get the current season and previous season
    current = smooth_mat.loc[current_year]
    prev_year = current_year - 1

    # plot!
    fig, ax = plt.subplots(figsize=(12, 5))
    steps = np.arange(len(band))

    # plot the historical normal band
    ax.fill_between(
        steps,
        band["p25"],
        band["p75"],
        alpha=0.25,
        color="steelblue",
        label="p25-p75 normal",
    )

    ax.plot(
        steps,
        band["p50"],
        color="steelblue",
        linewidth=1.5,
        linestyle="--",
        label="p50 normal",
    )

    # plot the previous season
    if prev_year in smooth_mat.index:
        ax.plot(
            steps,
            smooth_mat.loc[prev_year].values,
            color="grey",
            linewidth=1.2,
            linestyle="--",
            label=f"{prev_year}–{prev_year + 1}",
        )

    # plot the current season
    ax.plot(
        steps,
        current.values,
        color="crimson",
        linewidth=2.2,
        label=f"{current_year}–{current_year + 1}",
    )

    # plot the phenology metrics
    p = phenology.loc[current_year] if current_year in phenology.index else None

    if p is not None:
        if pd.notna(p["sos_step"]):
            ax.axvline(
                p["sos_step"],
                color="green",
                linestyle=":",
                alpha=0.7,
                label="SOS",
            )

        if pd.notna(p["peak_step"]):
            ax.axvline(
                p["peak_step"],
                color="orange",
                linestyle=":",
                alpha=0.7,
                label="Peak",
            )

        if pd.notna(p["eos_step"]):
            ax.axvline(
                p["eos_step"],
                color="purple",
                linestyle=":",
                alpha=0.7,
                label="EOS",
            )

    # set the plot labels and title
    ax.set_xlabel("Step index (0 = Nov 1)")
    ax.set_ylabel("NDVI (zonal mean)")
    ax.set_title(f"LEM — Season {current_year}-{current_year + 1} vs. historical normal")

    # add the legend
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()

    return fig
