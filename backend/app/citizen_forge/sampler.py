"""
Stratified Sampling Module

Implements sampling strategies to select representative GSS respondents
for the Citizens' Assembly. Ensures demographic and ideological diversity.
"""

import pandas as pd
import numpy as np
from typing import Optional
import logging

from app.data.gss_loader import GSSLoader
from app.data.gss_labels import get_age_group, POLVIEWS_SIMPLIFIED

logger = logging.getLogger(__name__)


class StratifiedSampler:
    """
    Sample GSS respondents with demographic quotas to ensure representation.

    Supports multiple sampling strategies:
    - stratified: Match target demographic proportions
    - quota: Exact counts per category
    - random: Simple random sample (for testing)
    """

    # Default quotas approximate US adult population
    DEFAULT_QUOTAS = {
        # Political views (simplified to 3 categories)
        'polviews_group': {
            'Liberal': 0.30,      # ~30%
            'Moderate': 0.35,     # ~35%
            'Conservative': 0.35  # ~35%
        },
        # Race
        'race': {
            1: 0.60,  # White ~60%
            2: 0.13,  # Black ~13%
            3: 0.27   # Other (includes Hispanic, Asian, etc.) ~27%
        },
        # Age groups
        'age_group': {
            '18-29': 0.20,
            '30-44': 0.25,
            '45-64': 0.30,
            '65+': 0.25
        }
    }

    def __init__(
        self,
        gss_data: Optional[pd.DataFrame] = None,
        target_n: int = 40
    ):
        """
        Initialize the sampler.

        Args:
            gss_data: Pre-loaded GSS data, or None to load fresh
            target_n: Number of citizens to sample (default 40)
        """
        self.target_n = target_n
        self._data = gss_data
        self._prepared = False

    def load_data(
        self,
        years: Optional[list[int]] = None,
        required_vars: Optional[list[str]] = None
    ) -> pd.DataFrame:
        """
        Load GSS data for sampling.

        Args:
            years: Years to include (default: recent complete years)
            required_vars: Variables that must be non-missing

        Returns:
            Loaded DataFrame
        """
        if years is None:
            years = [2018, 2021, 2022, 2024]

        if required_vars is None:
            required_vars = ['age', 'sex', 'race', 'polviews', 'educ', 'region']

        loader = GSSLoader()
        loader.load(years=years)
        self._data = loader.get_filtered_sample(required_vars=required_vars)

        logger.info(f"Loaded {len(self._data):,} rows for sampling")
        return self._data

    def prepare_data(self) -> pd.DataFrame:
        """
        Prepare data with derived columns for stratification.

        Creates:
        - age_group: Binned age categories
        - polviews_group: Simplified political views (Liberal/Moderate/Conservative)
        """
        if self._data is None:
            self.load_data()

        df = self._data.copy()

        # Create age groups
        df['age_group'] = df['age'].apply(get_age_group)

        # Create simplified political views
        df['polviews_group'] = df['polviews'].apply(
            lambda x: POLVIEWS_SIMPLIFIED.get(int(x), 'Unknown') if pd.notna(x) else 'Unknown'
        )

        # Filter out Unknown political views
        df = df[df['polviews_group'] != 'Unknown']

        self._data = df
        self._prepared = True

        logger.info(f"Prepared {len(df):,} rows with derived columns")
        return df

    def sample(
        self,
        strategy: str = 'stratified',
        quotas: Optional[dict] = None,
        seed: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Sample respondents from GSS data.

        Args:
            strategy: 'stratified', 'quota', or 'random'
            quotas: Custom quotas (overrides defaults)
            seed: Random seed for reproducibility

        Returns:
            DataFrame with sampled respondents
        """
        if not self._prepared:
            self.prepare_data()

        if seed is not None:
            np.random.seed(seed)

        quotas = quotas or self.DEFAULT_QUOTAS

        if strategy == 'random':
            return self._random_sample()
        elif strategy == 'stratified':
            return self._stratified_sample(quotas)
        elif strategy == 'quota':
            return self._quota_sample(quotas)
        else:
            raise ValueError(f"Unknown sampling strategy: {strategy}")

    def _random_sample(self) -> pd.DataFrame:
        """Simple random sample."""
        return self._data.sample(n=min(self.target_n, len(self._data)))

    def _stratified_sample(self, quotas: dict) -> pd.DataFrame:
        """
        Stratified sample matching target proportions.

        Uses political views as primary stratification variable,
        then ensures diversity within each stratum.
        """
        df = self._data.copy()
        sampled = []

        # Primary stratification by political views
        polviews_quotas = quotas.get('polviews_group', self.DEFAULT_QUOTAS['polviews_group'])

        for group, proportion in polviews_quotas.items():
            group_n = int(self.target_n * proportion)
            group_df = df[df['polviews_group'] == group]

            if len(group_df) >= group_n:
                # Sample with diversity in age and race
                group_sample = self._diverse_subsample(group_df, group_n)
                sampled.append(group_sample)
            else:
                # Not enough respondents, take all available
                sampled.append(group_df)
                logger.warning(
                    f"Only {len(group_df)} respondents available for {group} "
                    f"(requested {group_n})"
                )

        result = pd.concat(sampled, ignore_index=True)

        # If we're short, fill with random sample from remaining
        if len(result) < self.target_n:
            remaining = df[~df.index.isin(result.index)]
            additional_n = self.target_n - len(result)
            if len(remaining) >= additional_n:
                additional = remaining.sample(n=additional_n)
                result = pd.concat([result, additional], ignore_index=True)

        logger.info(f"Stratified sample: {len(result)} respondents")
        self._log_sample_composition(result)

        return result

    def _diverse_subsample(self, df: pd.DataFrame, n: int) -> pd.DataFrame:
        """
        Sample from a group while maximizing demographic diversity.

        Tries to include variety in age, race, sex, and region.
        """
        if len(df) <= n:
            return df

        # Score each row by how "rare" its combination of attributes is
        # This helps ensure we don't oversample common demographics
        df = df.copy()

        # Count frequencies of each attribute value
        for col in ['age_group', 'race', 'sex', 'region']:
            if col in df.columns:
                freq = df[col].value_counts(normalize=True)
                df[f'{col}_weight'] = df[col].map(lambda x: 1.0 / (freq.get(x, 1.0) + 0.01))

        # Combine weights
        weight_cols = [c for c in df.columns if c.endswith('_weight')]
        if weight_cols:
            df['sample_weight'] = df[weight_cols].mean(axis=1)
            # Normalize weights
            df['sample_weight'] = df['sample_weight'] / df['sample_weight'].sum()

            # Sample using weights
            result = df.sample(n=n, weights='sample_weight', replace=False)

            # Clean up weight columns
            result = result.drop(columns=weight_cols + ['sample_weight'])
            return result
        else:
            return df.sample(n=n)

    def _quota_sample(self, quotas: dict) -> pd.DataFrame:
        """
        Exact quota sampling - hit exact counts per category.

        More rigid than stratified sampling.
        """
        df = self._data.copy()
        sampled_indices = set()

        # Process each quota category
        for category, category_quotas in quotas.items():
            if category not in df.columns:
                continue

            for value, proportion in category_quotas.items():
                target_count = int(self.target_n * proportion)

                # Find eligible rows (matching value, not already sampled)
                eligible = df[
                    (df[category] == value) &
                    (~df.index.isin(sampled_indices))
                ]

                if len(eligible) >= target_count:
                    new_samples = eligible.sample(n=target_count).index
                else:
                    new_samples = eligible.index
                    logger.warning(
                        f"Only {len(eligible)} available for {category}={value} "
                        f"(requested {target_count})"
                    )

                sampled_indices.update(new_samples)

        result = df.loc[list(sampled_indices)].drop_duplicates()

        logger.info(f"Quota sample: {len(result)} respondents")
        return result

    def _log_sample_composition(self, df: pd.DataFrame):
        """Log the demographic composition of the sample."""
        logger.info("Sample composition:")

        if 'polviews_group' in df.columns:
            pol_dist = df['polviews_group'].value_counts(normalize=True)
            logger.info(f"  Political: {pol_dist.to_dict()}")

        if 'race' in df.columns:
            race_dist = df['race'].value_counts(normalize=True)
            logger.info(f"  Race: {race_dist.to_dict()}")

        if 'age_group' in df.columns:
            age_dist = df['age_group'].value_counts(normalize=True)
            logger.info(f"  Age: {age_dist.to_dict()}")

        if 'sex' in df.columns:
            sex_dist = df['sex'].value_counts(normalize=True)
            logger.info(f"  Sex: {sex_dist.to_dict()}")

    def get_sample_summary(self, df: pd.DataFrame) -> dict:
        """
        Get a summary of sample composition.

        Returns:
            Dictionary with demographic breakdowns
        """
        summary = {
            'total': len(df),
            'political': {},
            'race': {},
            'age': {},
            'sex': {},
            'region': {}
        }

        if 'polviews_group' in df.columns:
            summary['political'] = df['polviews_group'].value_counts().to_dict()

        if 'race' in df.columns:
            summary['race'] = df['race'].value_counts().to_dict()

        if 'age_group' in df.columns:
            summary['age'] = df['age_group'].value_counts().to_dict()

        if 'sex' in df.columns:
            summary['sex'] = df['sex'].value_counts().to_dict()

        if 'region' in df.columns:
            summary['region'] = df['region'].value_counts().to_dict()

        return summary


def sample_citizens(
    n: int = 40,
    years: Optional[list[int]] = None,
    strategy: str = 'stratified',
    seed: Optional[int] = None
) -> pd.DataFrame:
    """
    Convenience function to sample citizens from GSS.

    Args:
        n: Number of citizens to sample
        years: GSS years to include
        strategy: Sampling strategy
        seed: Random seed

    Returns:
        DataFrame with sampled respondents
    """
    sampler = StratifiedSampler(target_n=n)
    sampler.load_data(years=years)
    return sampler.sample(strategy=strategy, seed=seed)
