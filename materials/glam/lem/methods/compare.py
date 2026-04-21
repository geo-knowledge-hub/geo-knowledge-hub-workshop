import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from dtaidistance import dtw
from matplotlib.figure import Figure


#
# Auxiliary functions
#
def _align_lengths(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Trim the longer array to match the shorter for step-aligned comparison.

    Args:
        a (np.ndarray): The first array.

        b (np.ndarray): The second array.

    Returns:
        tuple[np.ndarray, np.ndarray]: The aligned arrays.
    """
    n = min(len(a), len(b))

    return a[:n], b[:n]


def _pearson_rank(current: np.ndarray, hist_matrix: pd.DataFrame) -> pd.Series:
    """Compute Pearson r between current and every historical season.

    Args:
        current (np.ndarray): The current season.

        hist_matrix (pd.DataFrame): The historical seasons.

    Returns:
        pd.Series: The Pearson r scores.
    """
    scores = {}
    for yr in hist_matrix.index:
        ref = hist_matrix.loc[yr].to_numpy()

        # trim to the shorter length so partial current seasons compare fairly
        a, b = _align_lengths(current, ref)

        # require at least 5 valid overlapping points for a good correlation
        mask = ~(np.isnan(a) | np.isnan(b))

        if mask.sum() < 5:
            continue

        scores[yr] = float(np.corrcoef(a[mask], b[mask])[0, 1])

    return pd.Series(scores).sort_values(ascending=False)


def _dtw_rank(current: np.ndarray, hist_matrix: pd.DataFrame) -> pd.Series:
    """Compute DTW distance between current and every historical season.

    Args:
        current (np.ndarray): The current season.

        hist_matrix (pd.DataFrame): The historical seasons.

    Returns:
        pd.Series: The DTW distance scores.
    """
    scores = {}
    cur = current.astype(np.float64)

    for yr in hist_matrix.index:
        ref = hist_matrix.loc[yr].to_numpy(dtype=np.float64).copy()

        a, b = _align_lengths(cur, ref)

        mask = ~(np.isnan(a) | np.isnan(b))

        if mask.sum() < 5:
            continue

        scores[yr] = float(dtw.distance_fast(a[mask], b[mask]))

    return pd.Series(scores).sort_values(ascending=True)


#
# Public functions
#
def rank_analogs(
    smooth_mat: pd.DataFrame,
    current_year: int,
) -> tuple[pd.Series, pd.Series]:
    """Rank historical seasons by similarity to the current season.

    Args:
        smooth_mat (pd.DataFrame): The smoothed data matrix (rows = seasons, cols = steps).

        current_year (int): The season start year to treat as current.

    Returns:
        tuple[pd.Series, pd.Series]: The Pearson and DTW rank Series.
    """
    current = smooth_mat.loc[current_year].to_numpy()
    historical = smooth_mat.drop(index=current_year, errors="ignore")

    return _pearson_rank(current, historical), _dtw_rank(current, historical)


def summary_table(
    pearson: pd.Series,
    dtw: pd.Series,
    top_n: int = 3,
) -> pd.DataFrame:
    """Build a combined top-N comparison table from both Pearson and DTW ranking methods.

    Args:
        pearson (pd.Series): The Pearson rank Series (descending, best first).

        dtw (pd.Series): The DTW rank Series (ascending, best first).

        top_n (int): Number of top analogs to include.

    Returns:
        pd.DataFrame: The combined top-N comparison table.
    """
    rows = []

    for rank in range(1, top_n + 1):
        py = pearson.index[rank - 1] if len(pearson) >= rank else None
        pr = pearson.iloc[rank - 1] if len(pearson) >= rank else float("nan")

        dy = dtw.index[rank - 1] if len(dtw) >= rank else None
        dr = dtw.iloc[rank - 1] if len(dtw) >= rank else float("nan")

        rows.append(
            {
                "rank": rank,
                "pearson_year": py,
                "pearson_r": round(pr, 3),
                "dtw_year": dy,
                "dtw_dist": round(dr, 3),
            }
        )

    return pd.DataFrame(rows).set_index("rank")


def plot_compare(
    smooth_mat: pd.DataFrame,
    pearson: pd.Series,
    dtw: pd.Series,
    current_year: int,
    top_n: int = 3,
) -> Figure:
    """Plot current season and top-N analogs per method.

    Args:
        smooth_mat (pd.DataFrame): The smoothed data matrix.

        pearson (pd.Series): The Pearson rank Series.

        dtw (pd.Series): The DTW rank Series.

        current_year (int): The current season start year.

        top_n (int): Number of top analogs to overlay.

    Returns:
        Figure: Matplotlib Figure with two side-by-side axes.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), sharey=True)

    current = smooth_mat.loc[current_year].values
    steps = np.arange(len(current))

    for ax, ranks, title, metric_label in [
        (ax1, pearson, "Pearson r", "r"),
        (ax2, dtw, "DTW distance", "dist"),
    ]:
        ax.plot(steps, current, color="crimson", linewidth=2.2, label=f"Current ({current_year}–{current_year + 1})")
        palette = ["steelblue", "seagreen", "darkorange"]

        for i, (yr, score) in enumerate(ranks.head(top_n).items()):
            if yr not in smooth_mat.index:
                continue

            n = min(len(smooth_mat.loc[yr].values), len(steps))

            ax.plot(
                steps[:n],
                smooth_mat.loc[yr].values[:n],
                color=palette[i % len(palette)],
                linewidth=1.3,
                linestyle="--",
                label=f"{yr}–{yr + 1} ({metric_label}={score:.3f})",
            )

        ax.set_title(f"Top-{top_n} analogs — {title}")
        ax.set_xlabel("Step index")
        ax.legend(fontsize=8)

    ax1.set_ylabel("NDVI (smoothed)")
    fig.suptitle(f"LEM {current_year}–{current_year + 1}: season analogs", fontsize=11)
    fig.tight_layout()

    return fig
