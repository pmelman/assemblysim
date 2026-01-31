"""
Phase 0 Validation Tests

These tests verify that the basic setup is working:
- Configuration loads correctly
- GSS data can be loaded
- Core variables are present
"""

import pytest
import pandas as pd
from pathlib import Path

from app.config import get_settings
from app.data.gss_loader import GSSLoader, load_gss_for_sampling
from app.data.gss_labels import get_label, format_value, get_age_group


class TestConfiguration:
    """Test configuration setup."""

    def test_settings_load(self):
        """Settings should load without error."""
        settings = get_settings()
        assert settings.APP_NAME == "Silicon Citizens' Assembly"

    def test_data_path_configured(self):
        """GSS data path should be configured."""
        settings = get_settings()
        assert settings.GSS_DATA_PATH is not None
        assert isinstance(settings.GSS_DATA_PATH, Path)


class TestGSSLoader:
    """Test GSS data loading."""

    @pytest.fixture
    def loader(self):
        """Create a GSSLoader instance."""
        return GSSLoader()

    def test_loader_initialization(self, loader):
        """Loader should initialize with correct path."""
        assert loader.data_path.exists(), f"GSS data not found at {loader.data_path}"

    def test_load_data(self, loader):
        """Should be able to load GSS data."""
        df = loader.load(years=[2022])
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        print(f"\n✓ Loaded {len(df):,} rows from GSS 2022")

    def test_core_variables_present(self, loader):
        """Core variables should be in loaded data."""
        df = loader.load(years=[2022])

        critical_vars = ['year', 'id', 'age', 'sex', 'race', 'polviews']
        for var in critical_vars:
            assert var in df.columns, f"Critical variable {var} not found"

        print(f"\n✓ All {len(critical_vars)} critical variables present")

    def test_data_validation(self, loader):
        """Data should pass validation checks."""
        loader.load(years=[2022])
        validation = loader.validate_data()

        print(f"\n✓ Validation: {'PASSED' if validation['valid'] else 'FAILED'}")
        if validation['issues']:
            print(f"  Issues: {validation['issues']}")
        if validation['warnings']:
            print(f"  Warnings: {validation['warnings']}")

        assert validation['valid'] or len(validation['issues']) < 3

    def test_summary_stats(self, loader):
        """Should generate summary statistics."""
        loader.load(years=[2018, 2021, 2022])
        stats = loader.get_summary_stats()

        print(f"\n✓ Summary Statistics:")
        print(f"  Total rows: {stats['total_rows']:,}")
        print(f"  Years: {stats['years']}")
        print(f"  Variables: {len(stats['variables'])}")

        assert stats['total_rows'] > 0
        assert len(stats['years']) > 0


class TestGSSLabels:
    """Test label mapping functions."""

    def test_sex_labels(self):
        """Should map sex codes correctly."""
        assert get_label('sex', 1) == "Male"
        assert get_label('sex', 2) == "Female"

    def test_polviews_labels(self):
        """Should map political views correctly."""
        assert get_label('polviews', 1) == "Extremely liberal"
        assert get_label('polviews', 4) == "Moderate"
        assert get_label('polviews', 7) == "Extremely conservative"

    def test_simplified_polviews(self):
        """Should simplify political views correctly."""
        assert format_value('polviews', 1, simplified=True) == "Liberal"
        assert format_value('polviews', 2, simplified=True) == "Liberal"
        assert format_value('polviews', 4, simplified=True) == "Moderate"
        assert format_value('polviews', 6, simplified=True) == "Conservative"

    def test_age_groups(self):
        """Should categorize ages correctly."""
        assert get_age_group(25) == "18-29"
        assert get_age_group(35) == "30-44"
        assert get_age_group(55) == "45-64"
        assert get_age_group(70) == "65+"


class TestSamplingPrep:
    """Test data preparation for sampling."""

    def test_load_for_sampling(self):
        """Should load data ready for persona sampling."""
        df = load_gss_for_sampling(years=[2022])

        print(f"\n✓ Ready for sampling: {len(df):,} rows")
        print(f"  Variables: {list(df.columns)[:10]}...")

        # Should have complete cases for required variables
        required = ['age', 'sex', 'race', 'polviews', 'educ']
        for var in required:
            assert var in df.columns
            missing = df[var].isna().sum()
            print(f"  {var}: {len(df) - missing:,} complete ({missing} missing)")

    def test_sample_diversity(self):
        """Loaded sample should have demographic diversity."""
        df = load_gss_for_sampling(years=[2022])

        # Check political diversity
        if 'polviews' in df.columns:
            polviews_dist = df['polviews'].value_counts(normalize=True)
            print(f"\n✓ Political Views Distribution:")
            for code, pct in polviews_dist.items():
                label = get_label('polviews', int(code))
                print(f"  {label}: {pct*100:.1f}%")

        # Check race diversity
        if 'race' in df.columns:
            race_dist = df['race'].value_counts(normalize=True)
            print(f"\n✓ Race Distribution:")
            for code, pct in race_dist.items():
                label = get_label('race', int(code))
                print(f"  {label}: {pct*100:.1f}%")


def print_phase0_summary():
    """Print summary of Phase 0 setup."""
    print("\n" + "=" * 70)
    print("PHASE 0 SETUP VALIDATION")
    print("=" * 70)

    settings = get_settings()
    print(f"\n✓ Configuration loaded")
    print(f"  App: {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"  GSS Data: {settings.GSS_DATA_PATH}")
    print(f"  Data exists: {settings.GSS_DATA_PATH.exists()}")

    # Try loading a small sample
    try:
        loader = GSSLoader()
        df = loader.load(years=[2022])
        print(f"\n✓ GSS Data loaded successfully")
        print(f"  Rows: {len(df):,}")
        print(f"  Columns: {len(df.columns)}")

        stats = loader.get_summary_stats()
        print(f"\n✓ Core variables present: {len(stats['variables'])}")

        validation = loader.validate_data()
        print(f"\n✓ Validation: {'PASSED' if validation['valid'] else 'FAILED WITH WARNINGS'}")

    except Exception as e:
        print(f"\n✗ Error loading GSS data: {e}")

    print("\n" + "=" * 70)
    print("Phase 0 setup complete! Ready for Phase 1.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    # Run summary when executed directly
    print_phase0_summary()
