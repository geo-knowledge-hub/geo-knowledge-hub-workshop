import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from minisom import MiniSom
from sklearn.preprocessing import StandardScaler


#
# Auxiliary functions
#
def _prepare_matrix(mat: pd.DataFrame) -> np.ndarray:
    """Forward/backward fill NaN gaps and return float32 array for SOM training.

    Args:
        mat (pd.DataFrame): The matrix to fill.

    Returns:
        np.ndarray: The filled matrix.
    """
    filled = mat.ffill(axis=1).bfill(axis=1)
    row_means = filled.mean(axis=1)

    # any column still NaN after ffill/bfill
    # > (entire column is NaN) falls back to row mean
    for col in filled.columns:
        mask = filled[col].isna()
        filled.loc[mask, col] = row_means[mask]

    return filled.to_numpy(dtype=np.float32)


def _train_som(
    data: np.ndarray,
    rows: int,
    cols: int,
    sigma: float,
    lr: float,
    iterations: int,
) -> tuple[MiniSom, StandardScaler]:
    """Train a MiniSom on normalized season data.

    Args:
        data (np.ndarray): The data to train the SOM on.

        rows (int): The number of rows in the SOM grid.

        cols (int): The number of columns in the SOM grid.

        sigma (float): The sigma parameter for the SOM.

        lr (float): The learning rate for the SOM.

        iterations (int): The number of iterations to train the SOM.

    Returns:
        tuple[MiniSom, StandardScaler]: The trained SOM and the fitted StandardScaler.
    """
    # normalize so different NDVI scales across seasons don't dominate the distance metric
    scaler = StandardScaler()
    normed = scaler.fit_transform(data)

    som = MiniSom(rows, cols, normed.shape[1], sigma=sigma, learning_rate=lr, random_seed=42)
    som.train_random(normed, iterations)

    return som, scaler


def _bmu_map(som: MiniSom, scaler: StandardScaler, data: np.ndarray) -> list[tuple[int, int]]:
    """Return Best Matching Unit (row, col) for each season.

    Args:
        som (MiniSom): The trained SOM.

        scaler (StandardScaler): The fitted StandardScaler.

        data (np.ndarray): The data to map.

    Returns:
        list[tuple[int, int]]: The Best Matching Unit (row, col) for each season.
    """
    # reuse the same scaler from training so vectors are in the same space
    normed = scaler.transform(data)

    # return the Best Matching Unit (row, col) for each season
    return [som.winner(row) for row in normed]


def _cell_mean_profiles(
    bmus: list[tuple[int, int]],
    data: np.ndarray,
    rows: int,
    cols: int,
) -> np.ndarray:
    """Compute mean NDVI profile of seasons assigned to each SOM cell.

    Args:
        bmus (list[tuple[int, int]]): The Best Matching Unit (row, col) for each season.

        data (np.ndarray): The data to compute the mean profiles for.

        rows (int): The number of rows in the SOM grid.

        cols (int): The number of columns in the SOM grid.

    Returns:
        np.ndarray: The mean profiles.
    """
    profiles = np.full((rows, cols, data.shape[1]), np.nan)
    counts = np.zeros((rows, cols), dtype=int)

    for i, (r, c) in enumerate(bmus):
        # incremental mean update
        # > avoids storing all seasons per cell
        profiles[r, c] = np.where(
            np.isnan(profiles[r, c]),
            data[i],
            (profiles[r, c] * counts[r, c] + data[i]) / (counts[r, c] + 1),
        )

        counts[r, c] += 1

    return profiles


#
# Public functions
#
def fit_som(
    ndvi_matrix: pd.DataFrame,
    rows: int = 4,
    cols: int = 4,
    sigma: float = 1.0,
    lr: float = 0.5,
    iterations: int = 5000,
) -> tuple[MiniSom, StandardScaler, np.ndarray]:
    """Train SOM on all seasons in the NDVI matrix.

    Args:
        ndvi_matrix (pd.DataFrame): The smoothed NDVI matrix (rows = seasons, cols = steps).

        rows (int): Number of SOM grid rows.

        cols (int): Number of SOM grid columns.

        sigma (float): The neighbourhood radius for SOM training.

        lr (float): The initial learning rate.

        iterations (int): The number of training iterations.

    Returns:
        tuple[MiniSom, StandardScaler, np.ndarray]: The trained MiniSom, fitted StandardScaler,
        and the gap-filled float32 data array used for training.
    """
    data = _prepare_matrix(ndvi_matrix)
    som, scaler = _train_som(data, rows, cols, sigma, lr, iterations)

    return som, scaler, data


def plot_map(
    ndvi_matrix: pd.DataFrame,
    som: MiniSom,
    scaler: StandardScaler,
    data: np.ndarray,
    current_year: int,
) -> Figure:
    """SOM grid with one sparkline per cell and current year highlighted.

    Args:
        ndvi_matrix (pd.DataFrame): The smoothed NDVI matrix.

        som (MiniSom): The trained MiniSom from fit_som.

        scaler (StandardScaler): The fitted StandardScaler from fit_som.

        data (np.ndarray): The gap-filled data array from fit_som.

        current_year (int): The season to highlight.

    Returns:
        Figure: Matplotlib Figure with a single axes showing the SOM grid.
    """
    # get the years and BMUs
    years = ndvi_matrix.index.tolist()
    bmus = _bmu_map(som, scaler, data)

    # get the current year index and BMU
    current_idx = years.index(current_year) if current_year in years else None
    current_bmu = bmus[current_idx] if current_idx is not None else None

    # get the weights and shape
    weights = som.get_weights()
    som_rows, som_cols = weights.shape[:2]

    # compute the mean profiles
    profiles = _cell_mean_profiles(bmus, data, som_rows, som_cols)

    # get the number of steps
    n_steps = data.shape[1]

    # plot!
    fig, ax = plt.subplots(figsize=(12, 12))

    for r in range(som_rows):
        for c in range(som_cols):
            xs = [c + 0.05 + i * 0.9 / n_steps for i in range(n_steps)]
            ys_raw = profiles[r, c]

            if np.isnan(ys_raw).all():
                continue

            ys_norm = (ys_raw - np.nanmin(ys_raw)) / (np.nanmax(ys_raw) - np.nanmin(ys_raw) + 1e-9)
            ys = r + 0.05 + ys_norm * 0.9

            members = [years[i] for i, b in enumerate(bmus) if b == (r, c)]
            is_current_cell = (r, c) == current_bmu
            color = "crimson" if is_current_cell else "steelblue"
            lw = 2.2 if is_current_cell else 1.0

            ax.plot(xs, ys, color=color, linewidth=lw)
            ax.text(
                c + 0.5,
                r + 0.03,
                " ".join(str(y) for y in members),
                ha="center",
                va="bottom",
                fontsize=8,
                color="#333333",
            )

            border_color = "crimson" if is_current_cell else "#cccccc"
            border_lw = 2.0 if is_current_cell else 0.5

            rect = Rectangle((c + 0.01, r + 0.01), 0.98, 0.98, fill=False, edgecolor=border_color, linewidth=border_lw)
            ax.add_patch(rect)

    ax.set_xlim(0, som_cols)
    ax.set_ylim(0, som_rows)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(
        f"SOM ({som_rows}x{som_cols}) — season {current_year}-{current_year + 1} highlighted",
        fontsize=11,
    )

    fig.tight_layout()

    return fig
