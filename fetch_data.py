#!/usr/bin/env python3
"""
BetAnalytics Pro V10 - GitHub Actions Data Fetcher
Foloseste TOATE endpoint-urile BSD API: predictions, live, events, leagues, teams.
"""

import os
import json
import requests
from datetime import datetime, timezone, timedelta

TOKEN = os.environ.get('BSD_TOKEN', '')
API_BASE = 'https://sports.bzzoiro.com'
HEADERS = {'Authorization': f'Token {TOKEN}'}
TZ = 'Europe/Bucharest'

V1_BASE = 'https://balty1991.github.io/BetAnalyticsPro/data'

def fetch_url(url, use_token=True):
    headers = HEADERS if use_token else {}
    for attempt in range(3):
        try:
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"  Attempt {attempt+1} failed for {url}: {e}")
            if attempt == 2:
                return None
    return None

def fetch_all_pages(endpoint, extra_params=''):
    all_results = []
    next_url = f"{API_BASE}{endpoint}{extra_params}"
    page_count = 0
    while next_url:
        page_count += 1
        print(f"  Page {page_count}: {next_url}")
        data = fetch_url(next_url)
        if not data:
            break
        if isinstance(data, list):
            all_results.extend(data)
            break
        results = data.get('results', [])
        all_results.extend(results)
        next_url = data.get('next')
        if next_url and next_url.startswith('http://'):
            next_url = next_url.replace('http://', 'https://', 1)
    return all_results

def fetch_from_v1(filename):
    url = f"{V1_BASE}/{filename}?t={int(datetime.now().timestamp())}"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        print(f"  Fallback V1 OK: {url}")
        return r.json()
    except Exception as e:
        print(f"  Fallback V1 FAIL: {e}")
        return None

def save_json(data, filename):
    os.makedirs('data', exist_ok=True)
    path = f'data/{filename}'
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    size = os.path.getsize(path)
    print(f"  Salvat: {path} ({size} bytes)")

def main():
    print(f"=== BetAnalytics V10 Fetch [{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}] ===")

    all_predictions = []
    all_live = []
    all_leagues = []
    all_upcoming_events = []

    if TOKEN:
        # ── 1. Predictions (cu paginare completa) ──────────────────────
        print("\n[1/4] Fetching predictions...")
        all_predictions = fetch_all_pages(f'/api/predictions/?tz={TZ}&upcoming=true')
        print(f"  Total predictions: {len(all_predictions)}")

        # ── 2. Live (cu incidents + live_stats) ─────────────────────────
        print("\n[2/4] Fetching live...")
        all_live = fetch_all_pages(f'/api/live/?tz={TZ}')
        print(f"  Total live: {len(all_live)}")

        # ── 3. Leagues ────────────────────────────────────────────────
        print("\n[3/4] Fetching leagues...")
        all_leagues = fetch_all_pages('/api/leagues/')
        print(f"  Total leagues: {len(all_leagues)}")

        # ── 4. Upcoming events (next 3 days) ──────────────────────────
        print("\n[4/4] Fetching upcoming events...")
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        future = (datetime.now(timezone.utc) + timedelta(days=3)).strftime('%Y-%m-%d')
        all_upcoming_events = fetch_all_pages(
            f'/api/events/?tz={TZ}&date_from={today}&date_to={future}&status=notstarted'
        )
        print(f"  Total upcoming events: {len(all_upcoming_events)}")

    else:
        print("WARN: BSD_TOKEN nu este setat - folosim fallback V1")

    # ── Fallback la V1 daca lipsesc datele principale ──────────────
    if not all_predictions:
        print("Fallback: citire predictions din V1...")
        v1_data = fetch_from_v1('predictions.json')
        if v1_data:
            all_predictions = v1_data.get('results', v1_data) if isinstance(v1_data, (dict, list)) else []

    if not all_live:
        print("Fallback: citire live din V1...")
        v1_live = fetch_from_v1('live.json')
        if v1_live:
            all_live = v1_live.get('results', v1_live) if isinstance(v1_live, (dict, list)) else []

    # ── Salvare fisiere JSON ───────────────────────────────────────
    save_json(all_predictions, 'predictions.json')
    save_json(all_live, 'live.json')
    save_json(all_leagues, 'leagues.json')
    save_json(all_upcoming_events, 'events.json')

    # ── Metadata extinsa ──────────────────────────────────────────
    meta = {
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'predictions_count': len(all_predictions),
        'live_count': len(all_live),
        'leagues_count': len(all_leagues),
        'events_count': len(all_upcoming_events),
        'status': 'ok',
        'version': 'v10'
    }
    save_json(meta, 'meta.json')
    print(f"\nMeta: {meta}")
    print("=== Done ===")

if __name__ == '__main__':
    main()
