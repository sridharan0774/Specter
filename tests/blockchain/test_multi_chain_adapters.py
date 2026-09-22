import pytest
from datetime import datetime, timezone
from app.blockchain.registry import ChainRegistry, get_adapter
from app.blockchain.adapters.base import BlockchainAdapter
from app.blockchain.adapters.tron import TronAdapter
from app.blockchain.adapters.ethereum import EthereumAdapter
from app.blockchain.adapters.bnb import BnbAdapter
from app.blockchain.adapters.polygon import PolygonAdapter
from app.blockchain.adapters.bitcoin import BitcoinAdapter
from app.blockchain.adapters.solana import SolanaAdapter
from app.schemas.transaction import NormalizedTransactionBase
from app.models.vasp import VASPRecord, VASPCluster


def test_chain_registry_supported_chains():
    chains = ["TRON", "ETHEREUM", "ETH", "BNB", "BSC", "POLYGON", "MATIC", "BITCOIN", "BTC", "SOLANA", "SOL"]
    for c in chains:
        adapter = ChainRegistry.get_adapter(c)
        assert isinstance(adapter, BlockchainAdapter)

    all_chains_info = ChainRegistry.list_supported_chains()
    assert len(all_chains_info) == 6
    tron_info = next(item for item in all_chains_info if item["chain"] == "TRON")
    assert tron_info["status"] == "OPERATIONAL"


def test_chain_registry_unknown_chain():
    with pytest.raises(ValueError, match="Unsupported or unknown blockchain network"):
        ChainRegistry.get_adapter("CARDANO_DOGE_INVALID")


def test_tron_adapter_validation_and_normalization():
    adapter = TronAdapter()
    assert adapter.chain_name == "TRON"
    assert adapter.status_state == "OPERATIONAL"
    assert adapter.validate_address("TEZFaYL8TEwpCEe9kWScBrUe65GmMDTbQL") is True
    assert adapter.validate_address("0x1234567890123456789012345678901234567890") is False

    raw_tx = {
        "transaction_id": "3941029cbb1eaa874af11696225965d991701b7f247314ab1036ae2049e34227",
        "block_timestamp": 1700000000000,
        "from": "TEZFaYL8TEwpCEe9kWScBrUe65GmMDTbQL",
        "to": "TBpr1tQ5kvo79GmMDTbQL",
        "value": "10000000",
        "token_info": {"symbol": "USDT", "decimals": 6, "address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"},
    }
    norm = adapter.normalize_transaction(raw_tx)
    assert norm.chain == "TRON"
    assert norm.asset == "USDT"
    assert norm.amount == 10.0
    assert norm.transaction_type == "TRC20_TRANSFER"


def test_ethereum_adapter_validation_and_normalization():
    adapter = EthereumAdapter()
    assert adapter.chain_name == "ETHEREUM"
    assert adapter.validate_address("0x1111111111111111111111111111111111111111") is True
    assert adapter.validate_address("TEZFaYL8TEwpCEe9kWScBrUe65GmMDTbQL") is False

    raw_tx = {
        "hash": "0xabc123456789",
        "timeStamp": "1700000000",
        "from": "0x1111111111111111111111111111111111111111",
        "to": "0x2222222222222222222222222222222222222222",
        "value": "5000000000000000000",
        "tokenSymbol": "ETH",
        "tokenDecimal": "18",
    }
    norm = adapter.normalize_transaction(raw_tx)
    assert norm.chain == "ETHEREUM"
    assert norm.asset == "ETH"
    assert norm.amount == 5.0


def test_bnb_adapter_validation_and_normalization():
    adapter = BnbAdapter()
    assert adapter.chain_name == "BNB"
    assert adapter.validate_address("0x8888888888888888888888888888888888888888") is True

    raw_tx = {
        "hash": "0xbnb123456",
        "timeStamp": "1700000000",
        "from": "0x8888888888888888888888888888888888888888",
        "to": "0x9999999999999999999999999999999999999999",
        "value": "2000000000000000000",
        "tokenSymbol": "BNB",
        "tokenDecimal": "18",
    }
    norm = adapter.normalize_transaction(raw_tx)
    assert norm.chain == "BNB"
    assert norm.amount == 2.0


def test_polygon_adapter_validation_and_normalization():
    adapter = PolygonAdapter()
    assert adapter.chain_name == "POLYGON"
    assert adapter.validate_address("0x7777777777777777777777777777777777777777") is True

    raw_tx = {
        "hash": "0xpoly123456",
        "timeStamp": "1700000000",
        "from": "0x7777777777777777777777777777777777777777",
        "to": "0x6666666666666666666666666666666666666666",
        "value": "100000000",
        "tokenSymbol": "USDT",
        "tokenDecimal": "6",
        "contractAddress": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
    }
    norm = adapter.normalize_transaction(raw_tx)
    assert norm.chain == "POLYGON"
    assert norm.asset == "USDT"
    assert norm.amount == 100.0


def test_bitcoin_adapter_validation_and_utxo_normalization():
    adapter = BitcoinAdapter()
    assert adapter.chain_name == "BITCOIN"
    assert adapter.validate_address("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa") is True  # Genesis address
    assert adapter.validate_address("3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy") is True  # P2SH address
    assert adapter.validate_address("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq") is True  # Native SegWit

    raw_utxo_tx = {
        "txid": "f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16",
        "status": {"confirmed": True, "block_height": 700000, "block_time": 1700000000},
        "vin": [
            {
                "txid": "prev123",
                "vout": 0,
                "prevout": {"scriptpubkey_address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "value": 250000000},
            }
        ],
        "vout": [
            {"scriptpubkey_address": "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy", "value": 150000000},
            {"scriptpubkey_address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "value": 100000000},
        ],
    }
    norm = adapter.normalize_transaction(raw_utxo_tx)
    assert norm.chain == "BITCOIN"
    assert norm.asset == "BTC"
    assert norm.amount == 1.5  # 150,000,000 Satoshis = 1.5 BTC
    assert norm.from_address == "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
    assert norm.to_address == "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy"

    # Test full multi-vout UTXO normalization
    multi_norms = adapter.normalize_utxo_outputs(raw_utxo_tx)
    assert len(multi_norms) == 2
    assert multi_norms[0].amount == 1.5
    assert multi_norms[1].amount == 1.0


def test_solana_adapter_validation_and_normalization():
    adapter = SolanaAdapter()
    assert adapter.chain_name == "SOLANA"
    assert adapter.validate_address("7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU") is True

    raw_tx = {
        "txHash": "5KjW...signature",
        "blockTime": 1700000000,
        "src": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
        "dst": "9wFFyRfZBsuAha4YcuxcPPHS6frtzZM2kGUt5aK9b1sZ",
        "amount": "1000000000",
        "symbol": "SOL",
        "decimals": 9,
    }
    norm = adapter.normalize_transaction(raw_tx)
    assert norm.chain == "SOLANA"
    assert norm.asset == "SOL"
    assert norm.amount == 1.0


def test_vasp_cluster_model():
    cluster = VASPCluster(
        cluster_id="cluster-binance-tron-01",
        vasp_name="Binance",
        chain="TRON",
        cluster_type="EXCHANGE_CLUSTER",
        primary_wallet="TMuA6YqfCeX8EhbfYEg5y7S4DqzSJireY9",
        member_wallets=[
            {"address": "TMuA6YqfCeX8EhbfYEg5y7S4DqzSJireY9", "entity_role": "COLD_WALLET"},
            {"address": "TWd4WrZ9wn84f5x1hZhL4DHvk738ns5jwb", "entity_role": "COLD_WALLET"},
        ],
        provenance="Binance Official Transparency Report",
    )
    assert cluster.cluster_id == "cluster-binance-tron-01"
    assert cluster.vasp_name == "Binance"
    assert len(cluster.member_wallets) == 2
