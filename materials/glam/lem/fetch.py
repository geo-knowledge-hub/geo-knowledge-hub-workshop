import logging
from pathlib import Path

import pandas as pd
import pydash as py_
import requests

#
# Constant - GLAM API
#
GLAM_BASE_URL = "https://98e2zjiicz.us-west-2.awsapprunner.com"

#
# Constant - Maximum consecutive NaN steps to fill by linear interpolation before analysis.
#
MAX_GAP_STEPS = 2


#
# Logger
#
log = logging.getLogger(__name__)


#
# Auxiliary functions
#
def _glam_get(url: str, params: dict | None = None) -> dict | list:
    """Single HTTP GET to the GLAM API.

    Args:
        url (str): The URL to GET.

        params (dict | None): The query parameters to pass to the URL.

    Returns:
        dict | list: The JSON response from the API.
    """
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()

    return r.json()


def _walk_pages(url: str, params: dict | None = None) -> list[dict]:
    """Collect all results from a paginated endpoint.

    Args:
        url (str): The URL to GET.

        params (dict | None): The query parameters to pass to the URL.

    Returns:
        list[dict]: The list of results from the API.
    """
    out = []
    first = True

    # init pagination url
    next_url = url

    # paginate!
    while next_url:
        # pass query params only on the first request
        response = _glam_get(next_url, params=params if first else None)

        if isinstance(response, list):
            return response

        out.extend(response.get("results", []))
        next_url = response.get("next")

        first = False

    return out


def _is_canonical_dekad(date_str: str) -> bool:
    """Return True only for canonical CHIRPS dekad starts (DD = 01, 11, or 21).

    Args:
        date_str (str): The date string to check.

    Returns:
        bool: Flag indicating if the date string is a canonical CHIRPS dekad start, False otherwise.
    """
    return date_str[8:] in ("01", "11", "21")


def _list_dates(product: str, start_date: str, end_date: str) -> list[str]:
    """List available dataset dates for a product.

    Args:
        product (str): The product ID.

        start_date (str): The start date.

        end_date (str): The end date.

    Returns:
        list[str]: The list of dates.
    """
    pages = _walk_pages(
        f"{GLAM_BASE_URL}/datasets/",
        {"product_id": product, "start_date": start_date, "end_date": end_date},
    )

    # extract dates from pages
    dates = sorted(py_.map_(pages, "date"))

    if "chirps" in product:
        # keep only canonical dekad dates
        dates = [d for d in dates if _is_canonical_dekad(d)]

    return dates


def _fetch_date(
    product: str,
    date: str,
    cropmask: str,
    layer: str,
    feature: int | str,
) -> dict:
    """Fetch zonal stats for one product / date / feature combination.

    Args:
        product (str): The product ID.

        date (str): The date.

        cropmask (str): The cropmask ID.

        layer (str): The layer ID.

        feature (int | str): The feature ID.

    Returns:
        dict: A row dict with keys: date, min, mean, max, std.
    """
    nan = float("nan")

    # build url
    url = f"{GLAM_BASE_URL}/query/{product}/{date}/{cropmask}/{layer}/{feature}/"

    # print(f"Querying URL: {url}")

    # fetch data
    try:
        # fetch data
        data = _glam_get(url)

        # check if data is valid
        if isinstance(data, dict) and "mean" in data:
            return {
                "date": date,
                "min": py_.get(data, "min", nan),
                "mean": py_.get(data, "mean", nan),
                "max": py_.get(data, "max", nan),
                "std": py_.get(data, "std", nan),
            }

    except requests.HTTPError as exc:
        log.warning("GLAM query failed %s %s: %s", product, date, exc)

    # fallback: date with no data
    return {"date": date, "min": nan, "mean": nan, "max": nan, "std": nan}


def _fetch_missing(
    product: str,
    dates: list[str],
    cropmask: str,
    layer: str,
    feature: int | str,
) -> list[dict]:
    """Fetch a list of dates not yet in the cache.

    Args:
        product (str): The product ID.

        dates (list[str]): The list of dates to fetch.

        cropmask (str): The cropmask ID.

        layer (str): The layer ID.

        feature (int | str): The feature ID.

    Returns:
        list[dict]: The list of fetched data.
    """
    return py_.map_(dates, lambda date: _fetch_date(product, date, cropmask, layer, feature))


#
# Cache
#
def _cache_path(cache_dir: Path, product: str, feature: int | str) -> Path:
    """Build cache path.

    Args:
        cache_dir (Path): The cache directory.

        product (str): The product ID.

        feature (int | str): The feature ID.

    Returns:
        Path: The cache path.
    """
    return cache_dir / f"{product}_{feature}.parquet"


def _load_cache(cache_dir: Path, product: str, feature: int | str) -> pd.DataFrame:
    """Load the cached parquet.

    Args:
        cache_dir (Path): The cache directory.

        product (str): The product ID.

        feature (int | str): The feature ID.

    Returns:
        pd.DataFrame: The cached data.
    """
    # build path
    path = _cache_path(cache_dir, product, feature)

    # check if file exists
    if not path.exists():
        return pd.DataFrame(columns=["date", "min", "mean", "max", "std"])

    # load data
    return pd.read_parquet(path)


def _save_cache(df: pd.DataFrame, cache_dir: Path, product: str, feature: int | str) -> None:
    """Save the cached parquet.

    Args:
        df (pd.DataFrame): The data to save.

        cache_dir (Path): The cache directory.

        product (str): The product ID.

        feature (int | str): The feature ID.

    Returns:
        None: Called for side effects.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)

    df.to_parquet(_cache_path(cache_dir, product, feature), index=False)


def _fetch_series(
    product: str,
    start_date: str,
    end_date: str,
    cropmask: str,
    layer: str,
    feature: int | str,
    cache_dir: Path,
) -> pd.DataFrame:
    """Fetch zonal-stats time series.

    Args:
        product (str): The product ID.

        start_date (str): The start date.

        end_date (str): The end date.

        cropmask (str): The cropmask ID.

        layer (str): The layer ID.

        feature (int | str): The feature ID.

        cache_dir (Path): The cache directory.

    Returns:
        pd.DataFrame: The fetched data.
    """
    # load cached data
    cached = _load_cache(cache_dir, product, feature)

    # check which dates are already cached
    already = set(cached["date"].tolist())

    # get all dates
    all_dates = _list_dates(product, start_date, end_date)

    # define missing dates
    missing = [d for d in all_dates if d not in already]

    # if there are missing dates, fetch them
    if missing:
        # fetch missing dates
        new_rows = _fetch_missing(product, missing, cropmask, layer, feature)

        # update cached data
        updated = (
            pd.concat([cached, pd.DataFrame(new_rows)], ignore_index=True)
            .drop_duplicates("date")
            .sort_values("date")
            .reset_index(drop=True)
        )

        # save updated data
        _save_cache(updated, cache_dir, product, feature)

        # silent update =)
        cached = updated

    # return!
    return cached[cached["date"].between(start_date, end_date)].copy()


#
# Season data
#
def _assign_season_year(
    dates: pd.Series,
    season_start_month: int,
    season_end_month: int,
) -> pd.Series:
    """Map each date to its season start year.

    Args:
        dates (pd.Series): The dates to map.

        season_start_month (int): The start month of the season.

        season_end_month (int): The end month of the season.

    Returns:
        pd.Series: The mapped dates.
    """
    dt = pd.to_datetime(dates)
    result = pd.Series(pd.NA, index=dates.index, dtype="Int64")

    # dates in the season start month or later belong to
    # the current year
    in_autumn = dt.dt.month >= season_start_month

    # dates in the season end month or earlier belong to
    # the previous year
    in_spring = dt.dt.month <= season_end_month

    result[in_autumn] = dt.dt.year[in_autumn].values
    result[in_spring] = (dt.dt.year[in_spring] - 1).values

    return result


def _interpolate_row(row: pd.Series, **kwargs: dict) -> pd.Series:
    """Fill NaN gaps by linear interpolation.

    Args:
        row (pd.Series): The row to interpolate.

        **kwargs: Additional keyword arguments to pass to the interpolation method.

    Returns:
        pd.Series: The interpolated row.
    """
    kwargs.setdefault("limit", MAX_GAP_STEPS)
    kwargs.setdefault("limit_direction", "both")

    # force linear method
    kwargs = py_.omit(kwargs, "method")

    return row.interpolate(method="linear", **kwargs)


def _to_season_matrix(
    df: pd.DataFrame,
    season_start_month: int,
    season_end_month: int,
) -> pd.DataFrame:
    """Pivot a flat date/mean time series into a season_year x step_index matrix.

    Args:
        df (pd.DataFrame): The data to pivot.

        season_start_month (int): The start month of the season.

        season_end_month (int): The end month of the season.

    Returns:
        pd.DataFrame: The pivoted data.
    """
    df = df.copy()

    # assign each date to the season it belongs to
    df["season_year"] = _assign_season_year(df["date"], season_start_month, season_end_month)

    # drop dates that are not in the season
    df = df.dropna(subset=["season_year"])
    df["season_year"] = df["season_year"].astype(int)
    df = df.sort_values(["season_year", "date"])

    # sequential step index within each season
    df["step"] = df.groupby("season_year").cumcount()

    return (
        df.pivot(index="season_year", columns="step", values="mean")
        .sort_index()
        .rename_axis(index="season_year", columns="step")
    )


def _build_season_matrix(
    df: pd.DataFrame,
    season_start_month: int,
    season_end_month: int,
) -> pd.DataFrame:
    """Build and interpolate a season x step matrix from a flat time series.

    Args:
        df (pd.DataFrame): The data to pivot.

        season_start_month (int): The start month of the season.

        season_end_month (int): The end month of the season.

    Returns:
        pd.DataFrame: The pivoted data.
    """
    return _to_season_matrix(df, season_start_month, season_end_month).apply(_interpolate_row, axis=1)


#
# Public functions
#
def glam_get_data(
    cache_dir: Path,
    ndvi_product: str,
    chirps_product: str,
    feature_id: int | str,
    boundary_layer: str,
    cropmask: str,
    season_start_month: int = 11,
    season_end_month: int = 4,
    history_end: str = "2025-04-30",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load NDVI and CHIRPS season data.

    Args:
        cache_dir (Path): Directory for parquet cache files.

        ndvi_product (str): GLAM product identifier for NDVI (e.g. ``"mod09q1-ndvi"``).

        chirps_product (str): GLAM product identifier for precipitation (e.g. ``"chirps-precip"``).

        feature_id (int | str): GLAM boundary feature ID (IBGE code for Brazilian municipalities).

        boundary_layer (str): GLAM boundary layer identifier.

        cropmask (str): Crop mask identifier (``"no-mask"`` if unsure).

        season_start_month (int): Month the season begins (default: 11 = November).

        season_end_month (int): Month the season ends (default: 4 = April).

        history_end (str): ISO date string for the end of the period to include.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: The NDVI and CHIRPS season data.
    """

    # NDVI
    ndvi = _fetch_series(
        ndvi_product,
        "2000-01-01",
        history_end,
        cropmask,
        boundary_layer,
        feature_id,
        cache_dir,
    )
    ndvi = _build_season_matrix(ndvi, season_start_month, season_end_month)

    # CHIRPS
    chirps = _fetch_series(
        chirps_product,
        "2000-01-01",
        history_end,
        cropmask,
        boundary_layer,
        feature_id,
        cache_dir,
    )
    chirps = _build_season_matrix(chirps, season_start_month, season_end_month)

    return ndvi, chirps
