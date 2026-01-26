"""
PR3DICT: SQLite Database for Market Tracking

Stores Polymarket listings and their dispute analysis results.
"""
import aiosqlite
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Default database path (gitignored)
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "data" / "markets.db"


class MarketDatabase:
    """
    SQLite database for tracking Polymarket listings and dispute analyses.
    
    Tables:
    - markets: Raw market data from Polymarket Gamma API
    - analyses: LLM analysis results with dispute probability scores
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._connection: Optional[aiosqlite.Connection] = None
    
    async def connect(self) -> None:
        """Initialize database connection and create tables."""
        # Ensure data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row
        
        await self._create_tables()
        logger.info(f"Connected to database: {self.db_path}")
    
    async def close(self) -> None:
        """Close database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None
    
    async def _create_tables(self) -> None:
        """Create database schema."""
        await self._connection.executescript("""
            -- Raw market data from Polymarket
            CREATE TABLE IF NOT EXISTS markets (
                id TEXT PRIMARY KEY,              -- Polymarket condition_id
                question TEXT NOT NULL,
                description TEXT,
                resolution_source TEXT,
                slug TEXT,
                
                -- Pricing
                yes_price REAL,
                no_price REAL,
                
                -- Volume/Liquidity
                volume REAL,
                liquidity REAL,
                
                -- Dates
                end_date TEXT,
                created_at TEXT,
                
                -- UMA Resolution
                uma_resolution_status TEXT,       -- null, proposed, disputed, resolved
                uma_bond TEXT,
                uma_reward TEXT,
                
                -- Tracking
                first_seen_at TEXT NOT NULL,
                last_updated_at TEXT NOT NULL,
                raw_json TEXT                     -- Full API response for reference
            );
            
            -- Analysis results from LLM pipeline
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id TEXT NOT NULL,
                
                -- Dispute prediction
                dispute_probability REAL,         -- 0.0 to 1.0
                ambiguity_score REAL,             -- 0.0 to 1.0
                
                -- LLM outputs
                ambiguous_terms TEXT,             -- JSON array
                edge_cases TEXT,                  -- JSON array
                resolution_source_risk TEXT,      -- low, medium, high
                reasoning TEXT,
                
                -- Metadata
                model_used TEXT,                  -- Which LLM analyzed this
                analyzed_at TEXT NOT NULL,
                
                FOREIGN KEY (market_id) REFERENCES markets(id)
            );
            
            -- Indexes for common queries
            CREATE INDEX IF NOT EXISTS idx_markets_liquidity ON markets(liquidity);
            CREATE INDEX IF NOT EXISTS idx_markets_uma_status ON markets(uma_resolution_status);
            CREATE INDEX IF NOT EXISTS idx_markets_end_date ON markets(end_date);
            CREATE INDEX IF NOT EXISTS idx_analyses_market ON analyses(market_id);
            CREATE INDEX IF NOT EXISTS idx_analyses_dispute_prob ON analyses(dispute_probability);
        """)
        await self._connection.commit()
    
    # --- Market Operations ---
    
    async def upsert_market(self, market: Dict[str, Any]) -> None:
        """Insert or update a market from Polymarket API response."""
        now = datetime.now(timezone.utc).isoformat()
        
        await self._connection.execute("""
            INSERT INTO markets (
                id, question, description, resolution_source, slug,
                yes_price, no_price, volume, liquidity, end_date, created_at,
                uma_resolution_status, uma_bond, uma_reward,
                first_seen_at, last_updated_at, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                question = excluded.question,
                description = excluded.description,
                resolution_source = excluded.resolution_source,
                yes_price = excluded.yes_price,
                no_price = excluded.no_price,
                volume = excluded.volume,
                liquidity = excluded.liquidity,
                end_date = excluded.end_date,
                uma_resolution_status = excluded.uma_resolution_status,
                uma_bond = excluded.uma_bond,
                uma_reward = excluded.uma_reward,
                last_updated_at = excluded.last_updated_at,
                raw_json = excluded.raw_json
        """, (
            market.get("conditionId") or market.get("id"),
            market.get("question"),
            market.get("description"),
            market.get("resolutionSource"),
            market.get("slug"),
            self._parse_price(market.get("outcomePrices"), 0),
            self._parse_price(market.get("outcomePrices"), 1),
            float(market.get("volumeNum") or market.get("volume") or 0),
            float(market.get("liquidityNum") or market.get("liquidity") or 0),
            market.get("endDate"),
            market.get("createdAt"),
            market.get("umaResolutionStatus"),
            market.get("umaBond"),
            market.get("umaReward"),
            now,  # first_seen_at (ignored on conflict)
            now,  # last_updated_at
            json.dumps(market)
        ))
        await self._connection.commit()
    
    def _parse_price(self, outcome_prices: Any, index: int) -> Optional[float]:
        """Parse outcome prices from API response."""
        if not outcome_prices:
            return None
        try:
            if isinstance(outcome_prices, str):
                prices = json.loads(outcome_prices)
            else:
                prices = outcome_prices
            return float(prices[index]) if len(prices) > index else None
        except (json.JSONDecodeError, IndexError, TypeError):
            return None
    
    async def get_market(self, market_id: str) -> Optional[Dict[str, Any]]:
        """Get a single market by ID."""
        async with self._connection.execute(
            "SELECT * FROM markets WHERE id = ?", (market_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def get_unanalyzed_markets(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get markets that haven't been analyzed yet."""
        async with self._connection.execute("""
            SELECT m.* FROM markets m
            LEFT JOIN analyses a ON m.id = a.market_id
            WHERE a.id IS NULL
            ORDER BY m.liquidity DESC
            LIMIT ?
        """, (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_markets_by_liquidity(
        self,
        min_liquidity: float = 0,
        max_liquidity: float = float('inf'),
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get markets within a liquidity range."""
        async with self._connection.execute("""
            SELECT * FROM markets
            WHERE liquidity >= ? AND liquidity <= ?
            ORDER BY liquidity DESC
            LIMIT ?
        """, (min_liquidity, max_liquidity, limit)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    # --- Analysis Operations ---
    
    async def save_analysis(
        self,
        market_id: str,
        dispute_probability: float,
        ambiguity_score: float,
        ambiguous_terms: List[str],
        edge_cases: List[str],
        resolution_source_risk: str,
        reasoning: str,
        model_used: str
    ) -> int:
        """Save LLM analysis results for a market."""
        now = datetime.now(timezone.utc).isoformat()
        
        cursor = await self._connection.execute("""
            INSERT INTO analyses (
                market_id, dispute_probability, ambiguity_score,
                ambiguous_terms, edge_cases, resolution_source_risk,
                reasoning, model_used, analyzed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            market_id,
            dispute_probability,
            ambiguity_score,
            json.dumps(ambiguous_terms),
            json.dumps(edge_cases),
            resolution_source_risk,
            reasoning,
            model_used,
            now
        ))
        await self._connection.commit()
        return cursor.lastrowid
    
    async def get_analysis(self, market_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recent analysis for a market."""
        async with self._connection.execute("""
            SELECT * FROM analyses
            WHERE market_id = ?
            ORDER BY analyzed_at DESC
            LIMIT 1
        """, (market_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                result = dict(row)
                result["ambiguous_terms"] = json.loads(result.get("ambiguous_terms") or "[]")
                result["edge_cases"] = json.loads(result.get("edge_cases") or "[]")
                return result
            return None
    
    async def get_high_dispute_markets(
        self,
        min_probability: float = 0.5,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get markets with high dispute probability."""
        async with self._connection.execute("""
            SELECT m.*, a.dispute_probability, a.ambiguity_score, 
                   a.reasoning, a.analyzed_at
            FROM markets m
            JOIN analyses a ON m.id = a.market_id
            WHERE a.dispute_probability >= ?
            ORDER BY a.dispute_probability DESC
            LIMIT ?
        """, (min_probability, limit)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    # --- Stats ---
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        stats = {}
        
        async with self._connection.execute("SELECT COUNT(*) FROM markets") as cursor:
            stats["total_markets"] = (await cursor.fetchone())[0]
        
        async with self._connection.execute("SELECT COUNT(*) FROM analyses") as cursor:
            stats["total_analyses"] = (await cursor.fetchone())[0]
        
        async with self._connection.execute("""
            SELECT COUNT(*) FROM markets m
            LEFT JOIN analyses a ON m.id = a.market_id
            WHERE a.id IS NULL
        """) as cursor:
            stats["unanalyzed_markets"] = (await cursor.fetchone())[0]
        
        return stats
