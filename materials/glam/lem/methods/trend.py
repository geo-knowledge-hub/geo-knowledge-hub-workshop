
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from dtaidistance import dtw
from matplotlib.figure import Figure

#
# Auxiliary functions
#
def _fill_row(row: pd.Series) -> np.ndarray:
    """Forward/backward fill NaN and return float64 array for DTW.

    Args:
        row (pd.Series): The row to fill.

    Returns:
        np.ndarray: The filled row.
    """
    return row.ffill().bfill().to_numpy(dtype=np.float64).copy()


def _rolling_dtw_variance(data: pd.DataFrame, rolling_window: int) -> pd.Series:
    """Per-season mean DTW distance to its neighbours.

    Args:
        data (pd.DataFrame): The data matrix.
        
        rolling_window (int): The number of neighbour seasons on each side.

    Returns:
        pd.Series: The DTW variance scores.

    Notes:
        - Higher values mean the season is less similar to surrounding years.
    """
    years = data.index.tolist()
    
    n = len(years)
    scores = {}
    
    for i, yr in enumerate(years):
        # clamp window to array bounds
        lo = max(0, i - rolling_window)
        hi = min(n, i + rolling_window + 1)

        neighbors = [j for j in range(lo, hi) if j != i]
        if not neighbors:
            scores[yr] = float("nan")
            continue
        
        row_i = _fill_row(data.iloc[i])
        
        # average DTW distance to all neighbours in the window
        dists = [dtw.distance_fast(row_i, _fill_row(data.iloc[j])) for j in neighbors]
        scores[yr] = float(np.mean(dists))
    
    return pd.Series(scores)


#
# Public functions
#
def compute_dtw_series(data: pd.DataFrame, rolling_window: int = 3) -> pd.Series:
    """Compute a year-by-year DTW consistency score for each season.

    For each season, the score is the mean DTW distance to its nearest
    ``rolling_window`` neighbours. A higher score means the season looks less
    like its surrounding years (a signal of anomalous variability).

    Args:
        data (pd.DataFrame): The data matrix.

        rolling_window (int): The number of neighbour seasons on each side (default: 3).

    Returns:
        pd.Series: The DTW consistency scores.
    """
    return _rolling_dtw_variance(data, rolling_window)


def plot_trend(dtw_series: pd.Series, current_year: int) -> Figure:
    """Bar chart of year-by-year DTW consistency, current year highlighted.

    Args:
        dtw_series (pd.Series): The DTW consistency scores.
        
        current_year (int): The season start year to highlight in crimson.

    Returns:
        Figure: Matplotlib Figure with a single axes.
    """
    fig, ax = plt.subplots(figsize=(12, 4))

    years = dtw_series.index.tolist()
    values = dtw_series.values
    colors = ["crimson" if yr == current_year else "steelblue" for yr in years]

    ax.bar(years, values, color=colors, alpha=0.85)
    ax.axhline(np.nanmean(values), color="grey", linewidth=0.8, linestyle="--", label="mean")
    ax.set_xlabel("Season start year")
    ax.set_ylabel("Mean DTW distance to neighbours")
    ax.set_title("LEM season consistency — DTW distance to neighbouring years")
    
    ax.legend(fontsize=8)
    fig.tight_layout()
    
    return fig
