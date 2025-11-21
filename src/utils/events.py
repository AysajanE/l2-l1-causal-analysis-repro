#!/usr/bin/env python3
"""
Event dummy builders from curated YAML registry
-----------------------------------------------

Parses data/l2_events_registry.yaml and returns date-aligned daily
dummy variables for analysis use (airdrops, outages via data/external,
and major campaign days). Designed to complement the shock_* dummies
already present in the core panel.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable
import pandas as pd
import yaml


REGISTRY = Path('data/l2_events_registry.yaml')
OUTAGES = Path('data/external/l2_outages.csv')


def _load_yaml_dates(section: dict) -> pd.DatetimeIndex:
    dates = []
    for key, meta in section.items():
        d = meta.get('date')
        if d:
            try:
                dates.append(pd.to_datetime(d).normalize())
            except Exception:
                continue
    return pd.DatetimeIndex(dates)


def build_event_dummies_from_registry(dates: Iterable[pd.Timestamp]) -> pd.DataFrame:
    """Build day dummies from YAML registry and outages file.

    Returns columns:
      ['date', 'any_airdrop_d0', 'optimism_airdrop_d0', 'arbitrum_airdrop_d0',
       'zksync_airdrop_d0', 'base_onchain_summer_d0', 'any_outage_d0']
    Missing inputs degrade gracefully (columns filled with 0).
    """
    base = pd.DataFrame({'date': pd.to_datetime(list(dates)).normalize()})
    base = base.drop_duplicates().sort_values('date').reset_index(drop=True)
    # Initialize columns
    cols = [
        'any_airdrop_d0', 'optimism_airdrop_d0', 'arbitrum_airdrop_d0', 'zksync_airdrop_d0',
        'base_onchain_summer_d0', 'any_outage_d0'
    ]
    for c in cols:
        base[c] = 0

    # YAML registry
    if REGISTRY.exists():
        with open(REGISTRY, 'r') as f:
            reg = yaml.safe_load(f)

        # Airdrops
        airdrops = reg.get('major_airdrops', {}) or {}
        ad_idx = _load_yaml_dates(airdrops)
        if len(ad_idx) > 0:
            base.loc[base['date'].isin(ad_idx), 'any_airdrop_d0'] = 1

        # Chain-specific airdrops if present
        def mark_if_present(slug: str, col: str):
            if slug in airdrops:
                try:
                    d = pd.to_datetime(airdrops[slug].get('date')).normalize()
                    base.loc[base['date'].eq(d), col] = 1
                except Exception:
                    pass

        mark_if_present('optimism_airdrop_1', 'optimism_airdrop_d0')
        mark_if_present('optimism_airdrop_2', 'optimism_airdrop_d0')
        mark_if_present('optimism_airdrop_3', 'optimism_airdrop_d0')
        mark_if_present('optimism_airdrop_4', 'optimism_airdrop_d0')
        mark_if_present('arbitrum_airdrop', 'arbitrum_airdrop_d0')
        mark_if_present('zksync_airdrop', 'zksync_airdrop_d0')

        # Major campaigns
        campaigns = reg.get('major_campaigns', {}) or {}
        if 'base_onchain_summer' in campaigns:
            try:
                d = pd.to_datetime(campaigns['base_onchain_summer'].get('date')).normalize()
                base.loc[base['date'].eq(d), 'base_onchain_summer_d0'] = 1
            except Exception:
                pass

    # Outages file (any chain)
    if OUTAGES.exists():
        df = pd.read_csv(OUTAGES)
        try:
            mask = pd.to_numeric(df.get('hours_down', 0), errors='coerce').fillna(0) > 0
            out_dates = pd.to_datetime(df['date'][mask], errors='coerce').dropna().dt.normalize().unique()
            base.loc[base['date'].isin(out_dates), 'any_outage_d0'] = 1
        except Exception:
            pass

    # Ensure integer type
    for c in cols:
        base[c] = base[c].astype('Int64')

    return base

