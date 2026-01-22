# PR3DICT

**Automated Prediction Market Trading System**

---

## Executive Summary

PR3DICT applies the battle-tested ST0CK methodology to prediction markets. It leverages the unified trading engine architecture, systematic risk management, and multi-platform API integration to exploit inefficiencies in this rapidly growing $200B+ industry.

### Target Platforms
- **Kalshi** — CFTC-regulated, REST/WebSocket/FIX APIs, Market Maker Program
- **Polymarket** — Blockchain-native (Polygon/USDC), high liquidity on political/crypto events

### Core Strategy Edges
1. **Arbitrage** — Binary complement, cross-platform, latency
2. **Market Making** — Bid-ask spread capture, inventory management
3. **Behavioral** — Longshot bias exploitation, overreaction reversion
4. **Informational** — AI-driven probability forecasting

### Architecture (from ST0CK)
| Component | Application |
|-----------|-------------|
| Unified Engine | Strategy pattern for parallel signal testing |
| Redis Cache | Multi-TTL for orderbooks, probability trends, metadata |
| Risk Management | Kelly Criterion + Portfolio Heat + Daily Loss Limits |
| API Layer | Unified wrappers for cross-platform operations |

---

## Project Structure

```
PR3DICT/
├── src/
│   ├── engine/          # Core trading engine
│   ├── strategies/      # Arbitrage, market-making, behavioral
│   ├── platforms/       # Kalshi, Polymarket API wrappers
│   ├── data/            # Market data ingestion & caching
│   └── risk/            # Position sizing, kill-switches
├── config/              # Platform credentials, strategy params
├── tests/               # Unit + integration tests
└── docs/                # Strategy documentation
```

---

## Quick Start

```bash
# Clone and install
git clone <repo-url>
cd PR3DICT
pip install -r requirements.txt

# Configure credentials
cp config/example.env config/.env
# Edit .env with Kalshi/Polymarket API keys

# Run (paper mode)
python -m src.engine.main --mode paper
```

---

## Status

🚧 **Phase 1: Foundation** — Building core engine and platform integrations.

---

## License

Proprietary. All rights reserved.
