import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from dtaidistance import dtw
from matplotlib.figure import Figure
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


#
# Auxiliary functions
#
def _fill_matrix(mat: pd.DataFrame) -> np.ndarray:
    """Forward/backward fill NaN gaps and return float64 array.

    Args:
        mat (pd.DataFrame): The matrix to fill.

    Returns:
        np.ndarray: The filled matrix.
    """
    filled = mat.ffill(axis=1).bfill(axis=1)
    row_means = filled.mean(axis=1)

    # remaining NaN after ffill/bfill means the entire column is missing;
    # use row mean
    for col in filled.columns:
        mask = filled[col].isna()
        filled.loc[mask, col] = row_means[mask]

    return filled.to_numpy(dtype=np.float64).copy()


def _dtw_distance_matrix(data: np.ndarray) -> np.ndarray:
    """Compute DTW distance matrix.

    Args:
        data (np.ndarray): The data to compute the DTW distance matrix for.

    Returns:
        np.ndarray: The DTW distance matrix.
    """
    n = len(data)
    dist = np.zeros((n, n))

    # compute upper triangle only and mirror to lower to avoid redundant computations
    for i in range(n):
        for j in range(i + 1, n):
            d = dtw.distance_fast(data[i], data[j])

            dist[i, j] = d
            dist[j, i] = d

    return dist


#
# Public functions
#
def compute_dtw_matrix(data: np.ndarray) -> np.ndarray:
    """Compute the NxN pairwise DTW distance matrix for all seasons.

    Args:
        data (np.ndarray): The data to compute the DTW distance matrix for.

    Returns:
        np.ndarray: The DTW distance matrix.
    """
    return _dtw_distance_matrix(_fill_matrix(data))


def compute_kmeans_clusters(data: np.ndarray, n_clusters: int = 3) -> np.ndarray:
    """K-means clustering on standardised season curves.

    Args:
        data (np.ndarray): The data to compute the K-means clusters for.

        n_clusters (int): Number of clusters (default: 3).

    Returns:
        Cluster label array (0-indexed), one entry per season.
    """
    data = _fill_matrix(data)

    return KMeans(n_clusters=n_clusters, random_state=42, n_init=10).fit_predict(StandardScaler().fit_transform(data))


def plot_cluster(
    data: np.ndarray,
    dist: np.ndarray,
    kmeans_labels: np.ndarray,
    current_year: int,
) -> Figure:
    """DTW distance heatmap (left) and K-means cluster curves (right).

    Args:
        data: The data to plot the cluster for.

        dist: The DTW distance matrix.

        kmeans_labels: K-means labels from compute_kmeans_clusters.

        current_year: Season to highlight in the curves panel.

    Returns:
        Matplotlib Figure with two side-by-side axes.
    """
    years = data.index.tolist()
    data = _fill_matrix(data)

    palette = ["#e41a1c", "#377eb8", "#4daf4a", "#984ea3"]

    fig, (ax_heat, ax_km) = plt.subplots(1, 2, figsize=(14, 6))

    im = ax_heat.imshow(dist, aspect="auto", cmap="YlOrRd")
    ax_heat.set_xticks(range(len(years)))
    ax_heat.set_xticklabels([str(y) for y in years], rotation=90, fontsize=6)
    ax_heat.set_yticks(range(len(years)))
    ax_heat.set_yticklabels([str(y) for y in years], fontsize=6)
    ax_heat.set_title("Pairwise DTW distances")
    fig.colorbar(im, ax=ax_heat, shrink=0.8, label="DTW distance")

    steps = np.arange(data.shape[1])
    seen_labels: set[int] = set()
    for i, (yr, row) in enumerate(zip(years, data)):
        lbl = int(kmeans_labels[i])
        label = f"Cluster {lbl}" if lbl not in seen_labels else ""

        color = palette[lbl % len(palette)]
        lw = 2.2 if yr == current_year else 0.9
        alpha = 1.0 if yr == current_year else 0.55

        seen_labels.add(lbl)
        ax_km.plot(steps, row, color=color, linewidth=lw, alpha=alpha, label=label)

    if current_year in years:
        ci = years.index(current_year)
        ax_km.plot(
            steps,
            data[ci],
            color=palette[int(kmeans_labels[ci]) % len(palette)],
            linewidth=2.5,
            linestyle="--",
            zorder=5,
            label=f"Current ({current_year})",
        )

    ax_km.set_title(f"K-means clusters (k={len(set(kmeans_labels))})")
    ax_km.set_xlabel("Step index")
    ax_km.set_ylabel("NDVI (smoothed)")
    ax_km.legend(fontsize=8)

    fig.suptitle("LEM season clustering", fontsize=11)
    fig.tight_layout()

    return fig
