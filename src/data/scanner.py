"""
PR3DICT: Polymarket Scanner

Fetches markets from Polymarket Gamma API and stores them in SQLite.
Designed to run periodically (every 6 hours) to discover new markets.
"""
import asyncio
import httpx
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from .database import MarketDatabase

logger = logging.getLogger(__name__)

GAMMA_API_URL = "https://gamma-api.polymarket.com"


class MarketScanner:
    """
    Scans Polymarket for markets in target liquidity range.
    
    No authentication required for read-only access to Gamma API.
    """
    
    def __init__(
        self,
        db: MarketDatabase,
        min_liquidity: float = 5000,    # $5k minimum
        max_liquidity: float = 500000,  # $500k maximum
        batch_size: int = 100
    ):
        self.db = db
        self.min_liquidity = min_liquidity
        self.max_liquidity = max_liquidity
        self.batch_size = batch_size
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "PR3DICT/1.0",
                "Accept": "application/json"
            }
        )
        await self.db.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
        await self.db.close()
    
    async def fetch_markets(
        self,
        closed: bool = False,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Fetch markets from Gamma API with liquidity filters.
        
        No authentication needed - this is public read-only data.
        """
        params = {
            "liquidity_num_min": self.min_liquidity,
            "liquidity_num_max": self.max_liquidity,
            "closed": str(closed).lower(),
            "limit": self.batch_size,
            "offset": offset,
            "order": "liquidityNum",
            "ascending": "false"  # Highest liquidity first
        }
        
        try:
            response = await self._client.get(
                f"{GAMMA_API_URL}/markets",
                params=params
            )
            response.raise_for_status()
            markets = response.json()
            logger.info(f"Fetched {len(markets)} markets (offset={offset})")
            return markets
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch markets: {e}")
            return []
    
    async def fetch_all_markets(self, closed: bool = False) -> List[Dict[str, Any]]:
        """Fetch all markets with pagination."""
        all_markets = []
        offset = 0
        
        while True:
            batch = await self.fetch_markets(closed=closed, offset=offset)
            if not batch:
                break
            
            all_markets.extend(batch)
            
            # Check if we got fewer than batch_size (last page)
            if len(batch) < self.batch_size:
                break
            
            offset += self.batch_size
            
            # Rate limiting - be nice to the API
            await asyncio.sleep(0.5)
        
        return all_markets
    
    async def scan_and_store(self) -> Dict[str, Any]:
        """
        Main scanning routine: fetch markets and store in database.
        
        Returns statistics about the scan.
        """
        start_time = datetime.now(timezone.utc)
        logger.info(f"Starting market scan at {start_time.isoformat()}")
        logger.info(f"Liquidity range: ${self.min_liquidity:,.0f} - ${self.max_liquidity:,.0f}")
        
        # Fetch active markets
        markets = await self.fetch_all_markets(closed=False)
        
        # Store each market
        new_count = 0
        updated_count = 0
        
        for market in markets:
            market_id = market.get("conditionId") or market.get("id")
            
            # Check if this is a new market
            existing = await self.db.get_market(market_id)
            if existing is None:
                new_count += 1
            else:
                updated_count += 1
            
            await self.db.upsert_market(market)
        
        # Get final stats
        stats = await self.db.get_stats()
        
        result = {
            "scan_time": start_time.isoformat(),
            "markets_fetched": len(markets),
            "new_markets": new_count,
            "updated_markets": updated_count,
            "total_in_db": stats["total_markets"],
            "unanalyzed": stats["unanalyzed_markets"]
        }
        
        logger.info(f"Scan complete: {result}")
        return result
    
    async def get_markets_for_analysis(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get unanalyzed markets ready for LLM analysis.
        
        Returns markets with all relevant fields for dispute prediction.
        """
        markets = await self.db.get_unanalyzed_markets(limit=limit)
        
        # Format for analysis
        formatted = []
        for m in markets:
            formatted.append({
                "id": m["id"],
                "question": m["question"],
                "description": m["description"],
                "resolution_source": m["resolution_source"],
                "liquidity": m["liquidity"],
                "volume": m["volume"],
                "end_date": m["end_date"],
                "uma_status": m["uma_resolution_status"],
                "slug": m["slug"]  # For building Polymarket URL
            })
        
        return formatted


async def run_scanner(
    min_liquidity: float = 5000,
    max_liquidity: float = 500000
) -> Dict[str, Any]:
    """
    Convenience function to run a single scan.
    
    Usage:
        python -c "import asyncio; from src.data.scanner import run_scanner; print(asyncio.run(run_scanner()))"
    """
    db = MarketDatabase()
    scanner = MarketScanner(
        db=db,
        min_liquidity=min_liquidity,
        max_liquidity=max_liquidity
    )
    
    async with scanner:
        return await scanner.scan_and_store()


# CLI entry point
if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    parser = argparse.ArgumentParser(description="Scan Polymarket for markets")
    parser.add_argument("--min-liquidity", type=float, default=5000,
                        help="Minimum liquidity in USD (default: 5000)")
    parser.add_argument("--max-liquidity", type=float, default=500000,
                        help="Maximum liquidity in USD (default: 500000)")
    parser.add_argument("--show-unanalyzed", action="store_true",
                        help="Show unanalyzed markets after scan")
    
    args = parser.parse_args()
    
    async def main():
        result = await run_scanner(
            min_liquidity=args.min_liquidity,
            max_liquidity=args.max_liquidity
        )
        
        print("\n=== Scan Results ===")
        print(f"Markets fetched: {result['markets_fetched']}")
        print(f"New markets: {result['new_markets']}")
        print(f"Updated markets: {result['updated_markets']}")
        print(f"Total in database: {result['total_in_db']}")
        print(f"Awaiting analysis: {result['unanalyzed']}")
        
        if args.show_unanalyzed:
            db = MarketDatabase()
            await db.connect()
            
            unanalyzed = await db.get_unanalyzed_markets(limit=10)
            if unanalyzed:
                print("\n=== Top Unanalyzed Markets ===")
                for m in unanalyzed:
                    print(f"\n[{m['id'][:8]}...] ${m['liquidity']:,.0f} liquidity")
                    print(f"  Q: {m['question'][:80]}...")
                    print(f"  URL: https://polymarket.com/event/{m['slug']}")
            
            await db.close()
    
    asyncio.run(main())
