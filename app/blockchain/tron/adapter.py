"""
TRON Adapter module re-exporting TronAdapter from app.blockchain.adapters.tron
for backward compatibility across existing import paths.
"""
from app.blockchain.adapters.tron import TronAdapter, TRON_USDT_CONTRACT

__all__ = ["TronAdapter", "TRON_USDT_CONTRACT"]
