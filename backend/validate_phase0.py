#!/usr/bin/env python3
"""
Phase 0 Validation Script

Run this script to validate that Phase 0 setup is complete.
No pytest required - this is a standalone validation script.

Usage:
    python validate_phase0.py
"""

import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))


def check_dependencies():
    """Check that required packages are installed."""
    print("Checking dependencies...")
    required = [
        'pandas',
        'pydantic',
        'pydantic_settings',
        'pyreadstat'
    ]

    missing = []
    for package in required:
        try:
            __import__(package)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} - NOT INSTALLED")
            missing.append(package)

    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print("   Install with: pip install -r requirements.txt")
        return False

    print("  ✓ All dependencies installed\n")
    return True


def check_configuration():
    """Check that configuration loads correctly."""
    print("Checking configuration...")

    try:
        from app.config import get_settings

        settings = get_settings()
        print(f"  ✓ App Name: {settings.APP_NAME}")
        print(f"  ✓ Version: {settings.APP_VERSION}")
        print(f"  ✓ Data Path: {settings.GSS_DATA_PATH}")

        # Check if GSS data exists
        if settings.GSS_DATA_PATH.exists():
            size_mb = settings.GSS_DATA_PATH.stat().st_size / 1024 / 1024
            print(f"  ✓ GSS data file exists ({size_mb:.0f} MB)")
        else:
            print(f"  ✗ GSS data file NOT FOUND at {settings.GSS_DATA_PATH}")
            print("     Expected location: ../data/GSS_stata/gss7224_r2.dta")
            return False

        # Check API keys
        print(f"\n  API Keys configured:")
        api_keys = {
            'OpenAI': settings.OPENAI_API_KEY,
            'Anthropic': settings.ANTHROPIC_API_KEY,
            'Perplexity': settings.PERPLEXITY_API_KEY
        }

        has_key = False
        for name, key in api_keys.items():
            if key:
                print(f"    ✓ {name}: {key[:20]}...")
                has_key = True
            else:
                print(f"    - {name}: Not configured")

        if not has_key:
            print("\n  ⚠️  No API keys configured (required for Phase 1+)")
            print("     Add keys to .env file (see .env.example)")

        print()
        return True

    except Exception as e:
        print(f"  ✗ Configuration error: {e}\n")
        return False


def check_gss_loader():
    """Check that GSS data can be loaded."""
    print("Checking GSS data loader...")

    try:
        from app.data.gss_loader import GSSLoader

        loader = GSSLoader()
        print(f"  ✓ GSSLoader initialized")

        # Try loading a small sample (2022 only)
        print(f"  Loading GSS 2022 data...")
        df = loader.load(years=[2022])

        print(f"  ✓ Data loaded: {len(df):,} rows, {len(df.columns)} columns")

        # Check critical variables
        critical_vars = ['year', 'id', 'age', 'sex', 'race', 'polviews']
        missing_vars = [v for v in critical_vars if v not in df.columns]

        if missing_vars:
            print(f"  ✗ Missing critical variables: {missing_vars}")
            return False

        print(f"  ✓ All {len(critical_vars)} critical variables present")

        # Validation
        validation = loader.validate_data()
        if validation['valid']:
            print(f"  ✓ Data validation: PASSED")
        else:
            print(f"  ⚠️  Data validation: PASSED WITH WARNINGS")
            for issue in validation['issues']:
                print(f"     - {issue}")

        # Summary stats
        stats = loader.get_summary_stats()
        print(f"\n  Summary Statistics:")
        print(f"    Years available: {stats['years']}")
        print(f"    Total rows: {stats['total_rows']:,}")
        print(f"    Variables: {len(stats['variables'])}")

        print()
        return True

    except FileNotFoundError as e:
        print(f"  ✗ GSS data file not found")
        print(f"     {e}\n")
        return False
    except Exception as e:
        print(f"  ✗ Error loading GSS data: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def check_labels():
    """Check that label mappings work."""
    print("Checking label mappings...")

    try:
        from app.data.gss_labels import (
            get_label,
            format_value,
            get_age_group,
            SEX_LABELS,
            POLVIEWS_LABELS
        )

        # Test some mappings
        assert get_label('sex', 1) == "Male"
        assert get_label('sex', 2) == "Female"
        print(f"  ✓ Sex labels working")

        assert get_label('polviews', 1) == "Extremely liberal"
        assert get_label('polviews', 7) == "Extremely conservative"
        print(f"  ✓ Political views labels working")

        assert format_value('polviews', 2, simplified=True) == "Liberal"
        print(f"  ✓ Simplified formatting working")

        assert get_age_group(25) == "18-29"
        assert get_age_group(55) == "45-64"
        print(f"  ✓ Age grouping working")

        print(f"  ✓ All label mappings working\n")
        return True

    except Exception as e:
        print(f"  ✗ Error with labels: {e}\n")
        return False


def check_sampling_prep():
    """Check data preparation for sampling."""
    print("Checking sampling preparation...")

    try:
        from app.data.gss_loader import load_gss_for_sampling

        print(f"  Loading data for sampling (2022)...")
        df = load_gss_for_sampling(years=[2022])

        print(f"  ✓ Loaded {len(df):,} rows ready for sampling")

        # Check completeness of required variables
        required = ['age', 'sex', 'race', 'polviews', 'educ']
        for var in required:
            complete = len(df) - df[var].isna().sum()
            pct = (complete / len(df)) * 100
            print(f"    {var}: {complete:,}/{len(df):,} complete ({pct:.1f}%)")

        print()
        return True

    except Exception as e:
        print(f"  ✗ Error preparing sampling data: {e}\n")
        return False


def print_summary(results):
    """Print final summary."""
    print("=" * 70)
    print("PHASE 0 VALIDATION SUMMARY")
    print("=" * 70)

    all_passed = all(results.values())

    for check_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status:12} {check_name}")

    print("=" * 70)

    if all_passed:
        print("\n🎉 Phase 0 setup complete! All checks passed.")
        print("\nNext steps:")
        print("1. Add API keys to .env (if not done)")
        print("2. Review Phase 1 requirements in DEVELOPMENT_PLAN.md")
        print("3. Begin implementing the Citizen Forge\n")
        return 0
    else:
        print("\n❌ Phase 0 setup incomplete. Please fix the issues above.\n")
        return 1


def main():
    """Run all validation checks."""
    print("\n" + "=" * 70)
    print("SILICON CITIZENS' ASSEMBLY - PHASE 0 VALIDATION")
    print("=" * 70 + "\n")

    results = {
        'Dependencies': check_dependencies(),
        'Configuration': check_configuration(),
        'GSS Data Loader': check_gss_loader(),
        'Label Mappings': check_labels(),
        'Sampling Prep': check_sampling_prep(),
    }

    return print_summary(results)


if __name__ == "__main__":
    sys.exit(main())
