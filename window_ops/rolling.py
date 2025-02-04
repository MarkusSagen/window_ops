# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/rolling.ipynb.

# %% auto 0
__all__ = ['rolling_mean', 'rolling_std', 'rolling_max', 'rolling_min', 'rolling_correlation', 'rolling_cv',
           'rolling_mean_positive_only', 'rolling_kurtosis', 'rolling_average_days_with_sales', 'seasonal_rolling_mean',
           'seasonal_rolling_std', 'seasonal_rolling_max', 'seasonal_rolling_min']

# %% ../nbs/rolling.ipynb 3
from math import sqrt
from typing import Callable, Optional, Tuple

import numpy as np
from numba import njit  # type: ignore

from .utils import _gt, _lt, _validate_rolling_sizes, first_not_na

# %% ../nbs/rolling.ipynb 7
def _rolling_docstring(*args, **kwargs) -> Callable:
    base_docstring = """Compute the {} over the last non-na window_size samples of the input array starting at min_samples.

    Parameters
    ----------
    input_array : np.ndarray
        Input array
    window_size : int
        Size of the sliding window
    min_samples : int, optional (default=None)
        Minimum number of samples to produce a result, if `None` then it's set to window_size

    Returns
    -------
    np.ndarray
        Array with rolling computation
    """
    def docstring_decorator(function: Callable):
        function.__doc__ = base_docstring.format(function.__name__)
        return function
        
    return docstring_decorator(*args, **kwargs)

# %% ../nbs/rolling.ipynb 9
@njit
@_rolling_docstring
def rolling_mean(input_array: np.ndarray,
                 window_size: int,
                 min_samples: Optional[int] = None) -> np.ndarray:
    n_samples = input_array.size
    window_size, min_samples = _validate_rolling_sizes(window_size, min_samples)
    
    output_array = np.full_like(input_array, np.nan)
    start_idx = first_not_na(input_array)
    if start_idx + min_samples > n_samples:
        return output_array
    
    accum = 0.
    upper_limit = min(start_idx + window_size, n_samples)
    for i in range(start_idx, upper_limit):
        accum += input_array[i]
        if i + 1 >= start_idx + min_samples:
            output_array[i] = accum / (i - start_idx + 1)
            
    for i in range(start_idx + window_size, n_samples):
        accum += input_array[i] - input_array[i - window_size]
        output_array[i] = accum / window_size

    return output_array

# %% ../nbs/rolling.ipynb 11
@njit
def _rolling_std(input_array: np.ndarray, 
                 window_size: int,
                 min_samples: Optional[int] = None) -> Tuple[np.ndarray, float, float]:
    """Computes the rolling standard deviation using Welford's online algorithm.
    
    Reference: https://en.wikipedia.org/wiki/Algorithms_for_calculating_variance#Welford's_online_algorithm"""
    n_samples = input_array.size
    window_size, min_samples = _validate_rolling_sizes(window_size, min_samples)
    if min_samples < 2:  # type: ignore
        raise ValueError('min_samples must be greater than 1.')

    output_array = np.full_like(input_array, np.nan)
    start_idx = first_not_na(input_array)
    if start_idx + min_samples > n_samples:
        return output_array, 0, 0

    prev_avg = 0.
    curr_avg = input_array[start_idx]
    m2 = 0.
    upper_limit = min(start_idx + window_size, n_samples)
    for i in range(start_idx + 1, upper_limit):
        prev_avg = curr_avg
        curr_avg = prev_avg + (input_array[i] - prev_avg) / (i - start_idx + 1)
        m2 += (input_array[i] - prev_avg) * (input_array[i] - curr_avg)
        m2 = max(m2, 0.0)
        if i + 1 >= start_idx + min_samples:
            output_array[i] = sqrt(m2 / (i - start_idx))
            
    for i in range(start_idx + window_size, n_samples):
        prev_avg = curr_avg
        new_minus_old = input_array[i] - input_array[i-window_size]
        curr_avg = prev_avg + new_minus_old / window_size
        m2 += new_minus_old * (input_array[i] - curr_avg + input_array[i-window_size] - prev_avg)
        m2 = max(m2, 0.0)
        output_array[i] = sqrt(m2 / (window_size - 1))
        
    return output_array, curr_avg, m2

# %% ../nbs/rolling.ipynb 12
@njit
@_rolling_docstring
def rolling_std(input_array: np.ndarray, 
                window_size: int,
                min_samples: Optional[int] = None) -> np.ndarray:
    output_array, _, _ = _rolling_std(input_array, window_size, min_samples)
    return output_array

# %% ../nbs/rolling.ipynb 14
@njit 
def _rolling_comp(comp: Callable,
                  input_array: np.ndarray, 
                  window_size: int,
                  min_samples: Optional[int] = None) -> np.ndarray:
    n_samples = input_array.size
    window_size, min_samples = _validate_rolling_sizes(window_size, min_samples)
    
    output_array = np.full_like(input_array, np.nan)
    start_idx = first_not_na(input_array)
    if start_idx + min_samples > n_samples:
        return output_array
    
    upper_limit = min(start_idx + window_size, n_samples)
    pivot = input_array[start_idx]
    for i in range(start_idx, upper_limit):
        if comp(input_array[i], pivot) > 0:
            pivot = input_array[i]
        if i + 1 >= start_idx + min_samples:
            output_array[i] = pivot
    
    for i in range(start_idx + window_size, n_samples):
        pivot = input_array[i]
        for j in range(1, window_size):
            if comp(input_array[i - j], pivot) > 0:
                pivot = input_array[i - j]
        output_array[i] = pivot
    return output_array

# %% ../nbs/rolling.ipynb 15
@njit
@_rolling_docstring
def rolling_max(input_array: np.ndarray,
                window_size: int,
                min_samples: Optional[int] = None) -> np.ndarray:
    return _rolling_comp(_gt, input_array, window_size, min_samples)

# %% ../nbs/rolling.ipynb 17
@njit
@_rolling_docstring
def rolling_min(x: np.ndarray,
                window_size: int,
                min_samples: Optional[int] = None) -> np.ndarray:
    return _rolling_comp(_lt, x, window_size, min_samples)

@njit
@_rolling_docstring
def rolling_sum(input_array: np.ndarray, window_size: int, min_samples: int | None = None) -> np.ndarray:
    n_samples = input_array.size
    window_size, min_samples = _validate_rolling_sizes(window_size, min_samples)

    output_array = np.full_like(input_array, np.nan)
    start_idx = first_not_na(input_array)
    if start_idx + min_samples > n_samples:
        return output_array

    accum = 0.0
    upper_limit = min(start_idx + window_size, n_samples)
    for i in range(start_idx, upper_limit):
        accum += input_array[i]
        if i + 1 >= start_idx + min_samples:
            output_array[i] = accum

    for i in range(start_idx + window_size, n_samples):
        accum += input_array[i] - input_array[i - window_size]
        output_array[i] = accum

    return output_array

# %% ../nbs/rolling.ipynb 19
@njit
def rolling_correlation(x: np.ndarray, window_size: int) -> np.ndarray:
    """Calculates the rolling correlation of a time series.

    Parameters
    ----------
    x : np.ndarray
        Array of time series data.
    window_size : int
        Size of the sliding window.
    
    Returns
    -------
    np.ndarray
        Array with the rolling correlation for each point in time.
    """
    n = len(x)
    result = np.full(n, np.nan)  # Initializes the result with NaNs
    for i in range(window_size, n):
        x1 = x[i - window_size : i]
        x2 = x[i - window_size + 1 : i + 1]
        mean_x1 = np.mean(x1)
        mean_x2 = np.mean(x2)
        std_x1 = np.std(x1)
        std_x2 = np.std(x2)
        if std_x1 == 0.0 or std_x2 == 0.0:
            result[i] = 0.0  # Avoids division by zero
        else:
            cov = np.mean((x1 - mean_x1) * (x2 - mean_x2))
            corr = cov / (std_x1 * std_x2)
            result[i] = corr
    return result

# %% ../nbs/rolling.ipynb 21
@njit
def rolling_cv(x: np.ndarray, window_size: int) -> np.ndarray:
    """Calculates the rolling coefficient of variation (CV) over a specified window.
    
    Parameters
    ----------
    x : np.ndarray
        Array of time series data.
    window_size : int
        Size of the sliding window.
    
    Returns
    -------
    np.ndarray
        An array with the rolling CV for each point in time.
    """
    n = len(x)
    result = np.full(n, 0.0)  # Initializes with 0.0 instead of NaN
    for i in range(window_size - 1, n):
        window_data = x[i - window_size + 1:i + 1]
        sum_data = 0.0
        sum_squares = 0.0
        for val in window_data:
            sum_data += val
            sum_squares += val * val
        mean = sum_data / window_size if window_size > 0 else 0.0
        if mean == 0.0:
            result[i] = 0.0  # Avoids division by zero
        else:
            std = np.sqrt(sum_squares / window_size - mean * mean)
            result[i] = std / mean
    return result

# %% ../nbs/rolling.ipynb 23
@njit
def rolling_mean_positive_only(x: np.ndarray, window_size: int) -> np.ndarray:
    """Calculates the rolling mean considering only positive sales days, ignoring effects of zero demand.
    
    Parameters
    ----------
    x : np.ndarray
        Array of sales data.
    window_size : int
        Size of the sliding window.
    
    Returns
    -------
    np.ndarray
        An array with the rolling mean for each point in time, considering only days with positive sales.
    """
    n = len(x)
    result = np.full(n, 0.0)  # Initializes with 0.0 instead of NaN
    for i in range(window_size - 1, n):
        window_data = x[i - window_size + 1 : i + 1]
        sum_data = 0.0
        count = 0
        for val in window_data:
            if val > 0:
                sum_data += val
                count += 1
        if count > 0:
            result[i] = sum_data / count
        else:
            result[i] = 0.0  # window_size without positive values, mean is 0
    return result

# %% ../nbs/rolling.ipynb 25
@njit
def rolling_kurtosis(x: np.ndarray, window_size: int) -> np.ndarray:
    """Calculates the rolling kurtosis, helping identify the presence of outliers in sales and how data deviates from a normal distribution.
    
    Parameters
    ----------
    x : np.ndarray
        Array of sales data.
    window_size : int
        Size of the sliding window.
    
    Returns
    -------
    np.ndarray
        Array with the rolling kurtosis for each point in time.
    """
    n = len(x)
    result = np.full(n, 0.0)  # Initializes with 0.0 instead of NaN
    for i in range(window_size - 1, n):
        window_data = x[i - window_size + 1:i + 1]
        mean = np.mean(window_data)
        std = np.std(window_data)
        if std > 0:
            kurtosis = np.mean((window_data - mean) ** 4) / (std ** 4) - 3
        else:
            kurtosis = 0.0
        result[i] = kurtosis
    return result

# %% ../nbs/rolling.ipynb 27
@njit
def rolling_average_days_with_sales(x: np.ndarray, window_size: int) -> np.ndarray:
    """Calculates the average number of days with sales over a window.
    Useful for understanding the sales frequency of each SKU.
    
    Parameters
    ----------
    x : np.ndarray
        Array of sales data.
    window_size : int
        Size of the sliding window.
    
    Returns
    -------
    np.ndarray
        Array with the average number of days with sales for each point in time.
    """
    n = len(x)
    result = np.zeros(n)  # Initializes the result with zeros instead of NaN
    for i in range(window_size - 1, n):
        sum_positive_sales = np.sum(x[i - window_size + 1:i + 1] > 0)
        result[i] = sum_positive_sales / window_size if window_size > 0 else 0.0
    return result

# %% ../nbs/rolling.ipynb 30
def _seasonal_rolling_docstring(*args, **kwargs) -> Callable:
    base_docstring = """Compute the {} over the last non-na window_size samples for each seasonal period of the input array starting at min_samples.

    Parameters
    ----------
    input_array : np.ndarray
        Input array
    season_length : int
        Length of the seasonal period
    window_size : int
        Size of the sliding window
    min_samples : int, optional (default=None)
        Minimum number of samples to produce a result, if `None` then it's set to window_size

    Returns
    -------
    np.ndarray
        Array with rolling computation
    """
    def docstring_decorator(function: Callable):
        function.__doc__ = base_docstring.format(function.__name__)
        return function
        
    return docstring_decorator(*args, **kwargs)

@njit
def _seasonal_rolling_op(rolling_op: Callable,
                         input_array: np.ndarray,
                         season_length: int,
                         window_size: int,
                         min_samples: Optional[int] = None) -> np.ndarray: 
    n_samples = input_array.size
    output_array = np.full_like(input_array, np.nan)
    for season in range(season_length):
        output_array[season::season_length] = rolling_op(input_array[season::season_length], window_size, min_samples)
    return output_array

# %% ../nbs/rolling.ipynb 33
@njit
@_seasonal_rolling_docstring
def seasonal_rolling_mean(input_array: np.ndarray,
                          season_length: int,
                          window_size: int,
                          min_samples: Optional[int] = None) -> np.ndarray:
    return _seasonal_rolling_op(rolling_mean, input_array, season_length, window_size, min_samples)

# %% ../nbs/rolling.ipynb 35
@njit
@_seasonal_rolling_docstring
def seasonal_rolling_std(input_array: np.ndarray,
                         season_length: int,
                         window_size: int,
                         min_samples: Optional[int] = None) -> np.ndarray:
    return _seasonal_rolling_op(rolling_std, input_array, season_length, window_size, min_samples)

# %% ../nbs/rolling.ipynb 37
@njit
@_seasonal_rolling_docstring
def seasonal_rolling_max(input_array: np.ndarray,
                         season_length: int,
                         window_size: int,
                         min_samples: Optional[int] = None) -> np.ndarray:
    return _seasonal_rolling_op(rolling_max, input_array, season_length, window_size, min_samples)

# %% ../nbs/rolling.ipynb 39
@njit
@_seasonal_rolling_docstring
def seasonal_rolling_min(x: np.ndarray,
                         season_length: int,
                         window_size: int,
                         min_samples: Optional[int] = None) -> np.ndarray:
    return _seasonal_rolling_op(rolling_min, x, season_length, window_size, min_samples)
