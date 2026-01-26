# PR3DICT

**Multi-Strategy Prediction Market Trading System**

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/aerichmo/PR3DICT.git
cd PR3DICT

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure credentials (for trading - not needed for scanning)
cp config/example.env config/.env
# Edit .env with your API keys
```

---

## Strategies

| Strategy | Platform | Status |
|----------|----------|--------|
| **Arbitrage** | Kalshi, Polymarket | 🔵 Implemented |
| **Dispute Prediction** | Polymarket | 🔨 In Development |

### Arbitrage Strategy
Exploits price inefficiencies:
- Binary complement (YES + NO < $1.00)
- Cross-platform differentials

### Dispute Prediction Strategy (In Development)
Exploits Polymarket resolution mechanism:
- Identify markets likely to be disputed
- Position before resolution chaos
- See `docs/DISPUTE_PREDICTION_STRATEGY.md`

---

## Dispute Strategy: Current Progress

```bash
# Scan Polymarket for markets (no API key needed)
python -m src.data.scanner --show-unanalyzed

# View stored markets
sqlite3 data/markets.db "SELECT question, liquidity FROM markets ORDER BY liquidity DESC LIMIT 10;"
```

**What's working:**
- [x] Market scanner (Polymarket Gamma API)
- [x] SQLite database for tracking markets
- [x] Strategy documentation

**What's next:**
- [ ] LLM analysis pipeline
- [ ] Dispute probability scoring
- [ ] Trade execution

---

## Project Structure

```
PR3DICT/
├── src/
│   ├── data/            # Market scanner & database
│   ├── strategies/      # Trading strategies
│   ├── platforms/       # Kalshi, Polymarket APIs
│   ├── engine/          # Core trading engine
│   └── risk/            # Position sizing
├── data/                # SQLite database (gitignored)
├── config/              # Environment config
└── docs/                # Strategy documentation
```

---

## Documentation

| Document | Description |
|----------|-------------|
| `docs/DISPUTE_PREDICTION_STRATEGY.md` | Dispute strategy overview |
| `docs/APPENDIX_KELLY_CRITERION.md` | Position sizing theory |
| `AGENTS.md` | AI assistant instructions |

---

## Collaboration

Multi-contributor repo. Each partner can:
- Create `.gitignore.local` for personal ignores
- Use `local/` directory for scratch files
- Prefix personal files with initials (e.g., `nate_notes.md`)

### Security: Credentials Are Local Only

**Never commit credentials.** These are gitignored:
- `config/.env` — API keys, wallet private keys
- `*.env` — All environment files
- `data/*.db` — Local database

---

## License

Proprietary. All rights reserved.
