"""
Base module re-exporting BlockchainAdapter from app.blockchain.adapters.base
for backward compatibility across existing import paths.
"""
from app.blockchain.adapters.base import BlockchainAdapter

__all__ = ["BlockchainAdapter"]
