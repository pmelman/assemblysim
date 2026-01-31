"""
GSS Data Loading and Validation Module

This module handles loading the General Social Survey dataset and
extracting the key variables needed for persona generation.
"""

import pandas as pd
from pathlib import Path
from typing import Optional
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)


class GSSLoader:
    """Handles loading and filtering GSS data."""

    # Core variables needed for persona generation
    CORE_VARIABLES = [
        # Identifiers
        'year', 'id',

        # Demographics (Required)
        'age', 'sex', 'race', 'region', 'educ', 'degree', 'income16',

        # Demographics (High Priority)
        'marital', 'wrkstat', 'sibs', 'childs',

        # Political/Ideological (Critical)
        'polviews', 'partyid', 'relig', 'attend',

        # Issue Attitudes (Topic-dependent, but useful)
        'natenvir', 'natheal', 'natfare', 'natcity', 'nateduc', 'natrace',
        'gunlaw', 'cappun', 'abany', 'grass', 'homosex',
        'eqwlth', 'helpblk', 'affrmact',

        # Social attitudes
        'trust', 'helpful', 'fair', 'happy', 'life',

        # Additional context
        'born', 'res16', 'mobile16', 'union',
    ]

    def __init__(self, data_path: Optional[Path] = None):
        """
        Initialize GSS loader.

        Args:
            data_path: Path to GSS .dta file. If None, uses config default.
        """
        self.settings = get_settings()
        self.data_path = data_path or self.settings.GSS_DATA_PATH
        self._data: Optional[pd.DataFrame] = None

    def load(
        self,
        convert_categoricals: bool = False,
        years: Optional[list[int]] = None
    ) -> pd.DataFrame:
        """
        Load GSS data from Stata file.

        Args:
            convert_categoricals: Whether to convert categorical variables
                                 (can be slow for large files)
            years: Optional list of years to filter to (e.g., [2018, 2021, 2022, 2024])

        Returns:
            DataFrame with GSS data
        """
        logger.info(f"Loading GSS data from {self.data_path}")

        if not self.data_path.exists():
            raise FileNotFoundError(
                f"GSS data file not found at {self.data_path}. "
                f"Please ensure the data is in the correct location."
            )

        try:
            # Load the data
            self._data = pd.read_stata(
                self.data_path,
                convert_categoricals=convert_categoricals,
                columns=self._get_available_columns()
            )

            logger.info(f"Loaded {len(self._data):,} rows")

            # Filter to specific years if requested
            if years:
                self._data = self._data[self._data['year'].isin(years)]
                logger.info(f"Filtered to {len(self._data):,} rows for years {years}")

            return self._data

        except Exception as e:
            logger.error(f"Error loading GSS data: {e}")
            raise

    def _get_available_columns(self) -> list[str]:
        """
        Get list of columns to load from GSS file.
        Returns all CORE_VARIABLES that exist in the file.
        """
        # For now, return all core variables
        # In production, we'd check which actually exist in the file
        return self.CORE_VARIABLES

    def get_summary_stats(self) -> dict:
        """
        Get summary statistics about loaded data.

        Returns:
            Dictionary with summary information
        """
        if self._data is None:
            raise ValueError("No data loaded. Call load() first.")

        return {
            'total_rows': len(self._data),
            'years': sorted(self._data['year'].unique().tolist()),
            'year_counts': self._data['year'].value_counts().to_dict(),
            'variables': list(self._data.columns),
            'missing_summary': {
                col: self._data[col].isna().sum()
                for col in self.CORE_VARIABLES
                if col in self._data.columns
            }
        }

    def get_filtered_sample(
        self,
        year: Optional[int] = None,
        min_year: Optional[int] = None,
        complete_cases_only: bool = False,
        required_vars: Optional[list[str]] = None
    ) -> pd.DataFrame:
        """
        Get filtered subset of GSS data suitable for sampling.

        Args:
            year: Specific year to filter to
            min_year: Minimum year (inclusive)
            complete_cases_only: Only return rows with no missing values
            required_vars: Variables that must be non-missing

        Returns:
            Filtered DataFrame
        """
        if self._data is None:
            raise ValueError("No data loaded. Call load() first.")

        df = self._data.copy()

        # Year filters
        if year:
            df = df[df['year'] == year]
        elif min_year:
            df = df[df['year'] >= min_year]

        # Complete cases filter
        if complete_cases_only:
            df = df.dropna()
        elif required_vars:
            df = df.dropna(subset=required_vars)

        logger.info(f"Filtered sample: {len(df):,} rows")
        return df

    def validate_data(self) -> dict:
        """
        Validate that the loaded data has expected structure.

        Returns:
            Dictionary with validation results
        """
        if self._data is None:
            raise ValueError("No data loaded. Call load() first.")

        issues = []

        # Check critical variables exist
        critical_vars = ['year', 'id', 'age', 'sex', 'race', 'polviews']
        for var in critical_vars:
            if var not in self._data.columns:
                issues.append(f"Critical variable missing: {var}")

        # Check for reasonable value ranges
        if 'age' in self._data.columns:
            age_range = (self._data['age'].min(), self._data['age'].max())
            if age_range[0] < 18 or age_range[1] > 100:
                issues.append(f"Unusual age range: {age_range}")

        if 'year' in self._data.columns:
            year_range = (self._data['year'].min(), self._data['year'].max())
            if year_range[0] < 1972 or year_range[1] > 2025:
                issues.append(f"Unusual year range: {year_range}")

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': self._get_warnings()
        }

    def _get_warnings(self) -> list[str]:
        """Get non-critical warnings about the data."""
        warnings = []

        # Check missingness rates
        for var in ['polviews', 'partyid', 'income16']:
            if var in self._data.columns:
                missing_pct = self._data[var].isna().sum() / len(self._data) * 100
                if missing_pct > 20:
                    warnings.append(
                        f"High missingness in {var}: {missing_pct:.1f}%"
                    )

        return warnings


def load_gss_for_sampling(
    years: Optional[list[int]] = None,
    required_vars: Optional[list[str]] = None
) -> pd.DataFrame:
    """
    Convenience function to load GSS data ready for persona sampling.

    Args:
        years: Years to include (default: recent complete years)
        required_vars: Variables that must be non-missing

    Returns:
        Filtered DataFrame ready for sampling
    """
    # Default to recent complete years
    if years is None:
        years = [2018, 2021, 2022, 2024]

    # Default required variables for persona generation
    if required_vars is None:
        required_vars = ['age', 'sex', 'race', 'polviews', 'educ']

    loader = GSSLoader()
    loader.load(years=years)

    # Validate
    validation = loader.validate_data()
    if not validation['valid']:
        logger.warning(f"Data validation issues: {validation['issues']}")

    if validation['warnings']:
        for warning in validation['warnings']:
            logger.warning(warning)

    # Get filtered sample
    df = loader.get_filtered_sample(required_vars=required_vars)

    logger.info(f"Ready for sampling: {len(df):,} rows with complete core variables")
    return df
