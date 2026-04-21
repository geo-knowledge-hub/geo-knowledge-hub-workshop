from dataclasses import dataclass

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from statsmodels.tsa.seasonal import STL


#
# Types
#
@dataclass
class StressWindow:
    start_step: int
    end_step: int
    max_z: float
    is_severe: bool


#
# Auxiliary functions
#
def _zscore_series(current: np.ndarray, hist_matrix: pd.DataFrame) -> np.ndarray:
    """Compute per-step z-score of current season vs. historical distribution.

    Args:
        current (np.ndarray): The current season.

        hist_matrix (pd.DataFrame): The historical seasons.

    Returns:
        np.ndarray: The z-scores.
    """
    mu = hist_matrix.mean(axis=0).to_numpy()
    sigma = hist_matrix.std(axis=0).to_numpy().copy()

    # avoid division by zero on columns where all historical seasons are the same
    sigma[sigma == 0] = np.nan

    return (current - mu) / sigma


def _find_stress_windows(
    z: np.ndarray,
    z_mild: float,
    z_severe: float,
    min_stress_run: int,
) -> list[StressWindow]:
    """Identify runs of at least min_stress_run consecutive steps with z < z_mild.

    Args:
        z (np.ndarray): The z-scores.

        z_mild (float): The mild stress threshold.

        z_severe (float): The severe stress threshold.

        min_stress_run (int): The minimum number of consecutive steps below z_mild to flag a stress window.

    Returns:
        list[StressWindow]: The stress windows.
    """
    windows = []
    run_start = None

    for i, zi in enumerate(z):
        # open a new run when z drops below mild threshold
        if not np.isnan(zi) and zi < z_mild:
            if run_start is None:
                run_start = i

        else:
            # close and record the run only if it meets the minimum length
            if run_start is not None and (i - run_start) >= min_stress_run:
                chunk = z[run_start:i]

                windows.append(
                    StressWindow(
                        start_step=run_start,
                        end_step=i - 1,
                        max_z=float(np.nanmin(chunk)),
                        is_severe=bool(np.nanmin(chunk) < z_severe),
                    )
                )

            run_start = None

    # handle a stress run that extends to the end of the series
    if run_start is not None and (len(z) - run_start) >= min_stress_run:
        chunk = z[run_start:]

        windows.append(
            StressWindow(
                start_step=run_start,
                end_step=len(z) - 1,
                max_z=float(np.nanmin(chunk)),
                is_severe=bool(np.nanmin(chunk) < z_severe),
            )
        )

    return windows


def _stl_residual(full_ndvi: pd.Series, period: int) -> pd.Series:
    """Fit STL on the full annual NDVI series; return the residual component.

    Args:
        full_ndvi (pd.Series): The full NDVI series.

        period (int): The number of observations per year for STL.

    Returns:
        pd.Series: The STL residual.
    """
    # drop NaN before STL
    # > statsmodels requires a contiguous series
    clean = full_ndvi.dropna()

    stl = STL(clean, period=period, robust=True)
    result = stl.fit()

    return pd.Series(result.resid, index=clean.index)


def _chirps_deviation(chirps_df: pd.DataFrame, current_year: int) -> pd.Series:
    """Compute raw CHIRPS dekad deviation for the current year.

    Args:
        chirps_df (pd.DataFrame): The CHIRPS series.

        current_year (int): The current year.

    Returns:
        pd.Series: The CHIRPS deviation.
    """
    hist = chirps_df.drop(index=current_year, errors="ignore")
    return chirps_df.loc[current_year] - hist.mean(axis=0)


#
# Public functions
#
def compute_zscore(
    smooth_mat: pd.DataFrame,
    current_year: int,
    z_mild: float = -1.0,
    z_severe: float = -2.0,
    min_stress_run: int = 3,
) -> tuple[np.ndarray, list[StressWindow]]:
    """Compute per-step z-score and identify stress windows for the current season.

    Args:
        smooth_mat (pd.DataFrame): The smoothed data matrix (rows = seasons, cols = steps).

        current_year (int): The season start year to treat as current.

        z_mild (float): The Z-score threshold for mild stress (default: -1.0).

        z_severe (float): The Z-score threshold for severe stress (default: -2.0).

        min_stress_run (int): The minimum number of consecutive steps below z_mild to flag a stress window.

    Returns:
        tuple[np.ndarray, list[StressWindow]]: The z-scores and stress windows.
    """
    current = smooth_mat.loc[current_year].to_numpy()
    historical = smooth_mat.drop(index=current_year, errors="ignore")

    # compute the z-scores
    z = _zscore_series(current, historical)

    # find the stress windows
    windows = _find_stress_windows(z, z_mild, z_severe, min_stress_run)

    # return!
    return z, windows


def compute_stl_residual(
    full_ndvi_df: pd.DataFrame,
    current_year: int,
    period: int = 46,
) -> pd.Series:
    """Extract the STL residual for the current season from the full NDVI series.

    Args:
        full_ndvi_df (pd.DataFrame): The full NDVI flat DataFrame with columns ``date`` and ``mean``.

        current_year (int): The season start year to extract the STL residual for.

        period (int): The number of observations per year for STL (default: 46 for 8-day MODIS).

    Returns:
        Series of STL residuals indexed by date for the current season.
    """
    series = full_ndvi_df.set_index("date")["mean"].sort_index()
    resid = _stl_residual(series, period)

    season_start = f"{current_year}-11-01"
    season_end = f"{current_year + 1}-04-30"

    return resid[season_start:season_end]


def plot_zscore_and_stl_residual(
    z_scores: np.ndarray,
    stl_resid: pd.Series,
    stress_windows: list[StressWindow],
    chirps_matrix: pd.DataFrame,
    current_year: int,
    z_mild: float = -1.0,
    z_severe: float = -2.0,
) -> Figure:
    """Two-panel plot: z-score bars (top) and STL residual + CHIRPS deviation (bottom).

    Args:
        z_scores (np.ndarray): The per-step z-score array for the current season.

        stl_resid (pd.Series): The STL residual Series for the current season.

        stress_windows (list[StressWindow]): The stress window list from compute_zscore.

        chirps_matrix (pd.DataFrame): The CHIRPS season matrix for CHIRPS deviation overlay.

        current_year (int): The season start year (for titles).

        z_mild (float): The threshold for mild stress shading (default: -1.0).

        z_severe (float): The threshold for severe stress shading (default: -2.0).

    Returns:
        Figure: Matplotlib Figure with two axes stacked vertically.
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=False)
    steps = np.arange(len(z_scores))
    colors = ["tomato" if z < z_severe else ("goldenrod" if z < z_mild else "steelblue") for z in z_scores]

    ax1.bar(steps, z_scores, color=colors, alpha=0.85)
    ax1.axhline(z_mild, color="goldenrod", linestyle="--", linewidth=0.9, label=f"z = {z_mild}")
    ax1.axhline(z_severe, color="tomato", linestyle="--", linewidth=0.9, label=f"z = {z_severe}")

    for sw in stress_windows:
        ax1.axvspan(
            sw.start_step - 0.5,
            sw.end_step + 0.5,
            alpha=0.12,
            color="tomato" if sw.is_severe else "goldenrod",
        )

    ax1.set_ylabel("Z-score")
    ax1.set_title(f"LEM {current_year}–{current_year + 1} — Z-score anomaly")
    ax1.legend(fontsize=8)

    if not stl_resid.empty:
        ax2.plot(stl_resid.values, color="darkorange", linewidth=1.8, label="STL residual")
        ax2.axhline(0, color="grey", linewidth=0.7)
        ax2.set_ylabel("STL residual")
        ax2.set_title("STL residual (trend + seasonal removed)")
        ax2.set_xlabel("Date index within season")

    if current_year in chirps_matrix.index:
        chirps_dev = _chirps_deviation(chirps_matrix, current_year)

        ax2_twin = ax2.twinx()
        ax2_twin.bar(
            np.arange(len(chirps_dev)),
            chirps_dev.values,
            alpha=0.25,
            color="royalblue",
            label="CHIRPS deviation",
        )

        ax2_twin.set_ylabel("CHIRPS Δ mm", color="royalblue", fontsize=8)
        ax2_twin.tick_params(axis="y", labelcolor="royalblue")

    fig.tight_layout()
    return fig
