# PR3DICT Agent Instructions

This document helps AI coding assistants understand and work with this codebase.

## Project Overview

PR3DICT is a multi-strategy prediction market trading system. Current focus: **Dispute Prediction** on Polymarket.

**Important Principles:**
1. This is a multi-strategy repo - only modify dispute strategy related code
2. Arbitrage strategy and trading engine are separate - don't touch them
3. Only build features that have been discussed and verified
4. All credentials must be gitignored

## Architecture

```
src/
├── data/           # Market data ingestion (DISPUTE FOCUS)
│   ├── scanner.py  # Fetches markets from Polymarket Gamma API
│   └── database.py # SQLite storage for markets & analyses
├── strategies/     # Trading strategies (arbitrage is separate)
├── platforms/      # API wrappers (Polymarket, Kalshi)
├── engine/         # Core trading engine (not dispute-related)
└── risk/           # Position sizing (not dispute-related)
```

## What's Been Built & Verified (Dispute Strategy)

### Market Scanner (`src/data/scanner.py`)
- Polls Polymarket Gamma API for markets in target liquidity range
- Stores markets in SQLite for tracking
- **Tested and working** - no auth needed for read-only access
- Run: `python -m src.data.scanner --show-unanalyzed`

### Database (`src/data/database.py`)
- SQLite schema for `markets` and `analyses` tables
- Tracks which markets have been analyzed
- **Tested and working**

### Strategy Documentation
- `docs/DISPUTE_PREDICTION_STRATEGY.md` - Strategy overview
- `docs/APPENDIX_KELLY_CRITERION.md` - Position sizing theory

## What's NOT Built Yet (Dispute Strategy)
- LLM analysis pipeline (Tier 1 screening, Tier 2 deep analysis)
- Dispute probability scoring
- Trade execution for dispute strategy
- RAG/Vector database for learning

## Setup & Commands

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run market scanner
python -m src.data.scanner --show-unanalyzed

# Query database
sqlite3 data/markets.db "SELECT question, liquidity FROM markets ORDER BY liquidity DESC LIMIT 10;"
```

## Polymarket API Notes

- **Gamma API** (read-only, no auth): `https://gamma-api.polymarket.com`
- Requires `User-Agent` header or returns 403
- Key fields: `question`, `description`, `resolutionSource`, `umaResolutionStatus`, `liquidityNum`

## Credentials

All credentials are gitignored. To set up:
```bash
cp config/example.env config/.env
# Edit with your credentials
```

## Development Guidelines

- **Don't over-build** - only implement features that have been discussed
- **Test before committing** - verify new code works
- **Update this doc** - after adding verified features
