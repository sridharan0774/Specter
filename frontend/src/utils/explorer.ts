/**
 * Utility for constructing and normalizing verified blockchain explorer URLs across supported networks:
 * TRON (TronScan), BITCOIN (Mempool.space), ETHEREUM (Etherscan), BNB (BscScan), POLYGON (PolygonScan), SOLANA (Solscan).
 * Never invents placeholder transaction IDs or mock hashes.
 */

export function getExplorerName(chain: string = 'TRON'): string {
  const norm = (chain || 'TRON').toUpperCase();
  if (norm === 'BITCOIN' || norm === 'BTC') return 'Mempool.space';
  if (norm === 'ETHEREUM' || norm === 'ETH') return 'Etherscan';
  if (norm === 'BNB' || norm === 'BSC') return 'BscScan';
  if (norm === 'POLYGON' || norm === 'MATIC') return 'PolygonScan';
  if (norm === 'SOLANA' || norm === 'SOL') return 'Solscan';
  return 'TronScan';
}

export function buildExplorerUrl(txHash: string, chain: string = 'TRON', defaultUrl?: string): string {
  const cleanHash = txHash ? txHash.trim() : '';
  if (!cleanHash) return '#';

  const norm = (chain || 'TRON').toUpperCase();

  // If defaultUrl is valid and matches the target chain, use it
  if (defaultUrl && defaultUrl.startsWith('http')) {
    if (norm === 'BITCOIN' || norm === 'BTC') {
      if (defaultUrl.includes('mempool.space')) return defaultUrl;
    } else if (norm === 'TRON') {
      if (defaultUrl.includes('tronscan.org')) {
        return defaultUrl.includes('/transaction/') && !defaultUrl.includes('#/transaction/')
          ? defaultUrl.replace('/transaction/', '/#/transaction/')
          : defaultUrl;
      }
    } else if (norm === 'ETHEREUM' || norm === 'ETH') {
      if (defaultUrl.includes('etherscan.io')) return defaultUrl;
    } else if (norm === 'BNB' || norm === 'BSC') {
      if (defaultUrl.includes('bscscan.com')) return defaultUrl;
    } else if (norm === 'POLYGON' || norm === 'MATIC') {
      if (defaultUrl.includes('polygonscan.com')) return defaultUrl;
    } else if (norm === 'SOLANA' || norm === 'SOL') {
      if (defaultUrl.includes('solscan.io')) return defaultUrl;
    }
  }

  // Construct chain-aware URL
  if (norm === 'BITCOIN' || norm === 'BTC') {
    return `https://mempool.space/tx/${cleanHash}`;
  }
  if (norm === 'ETHEREUM' || norm === 'ETH') {
    return `https://etherscan.io/tx/${cleanHash}`;
  }
  if (norm === 'BNB' || norm === 'BSC') {
    return `https://bscscan.com/tx/${cleanHash}`;
  }
  if (norm === 'POLYGON' || norm === 'MATIC') {
    return `https://polygonscan.com/tx/${cleanHash}`;
  }
  if (norm === 'SOLANA' || norm === 'SOL') {
    return `https://solscan.io/tx/${cleanHash}`;
  }

  return `https://tronscan.org/#/transaction/${cleanHash}`;
}

export function buildAddressExplorerUrl(address: string, chain: string = 'TRON', defaultUrl?: string): string {
  const cleanAddr = address ? address.trim() : '';
  if (!cleanAddr) return '#';

  const norm = (chain || 'TRON').toUpperCase();

  if (defaultUrl && defaultUrl.startsWith('http')) {
    if (norm === 'BITCOIN' || norm === 'BTC') {
      if (defaultUrl.includes('mempool.space')) return defaultUrl;
    } else if (norm === 'TRON') {
      if (defaultUrl.includes('tronscan.org')) {
        return defaultUrl.includes('/address/') && !defaultUrl.includes('#/address/')
          ? defaultUrl.replace('/address/', '/#/address/')
          : defaultUrl;
      }
    } else if (norm === 'ETHEREUM' || norm === 'ETH') {
      if (defaultUrl.includes('etherscan.io')) return defaultUrl;
    } else if (norm === 'BNB' || norm === 'BSC') {
      if (defaultUrl.includes('bscscan.com')) return defaultUrl;
    } else if (norm === 'POLYGON' || norm === 'MATIC') {
      if (defaultUrl.includes('polygonscan.com')) return defaultUrl;
    } else if (norm === 'SOLANA' || norm === 'SOL') {
      if (defaultUrl.includes('solscan.io')) return defaultUrl;
    }
  }

  if (norm === 'BITCOIN' || norm === 'BTC') {
    return `https://mempool.space/address/${cleanAddr}`;
  }
  if (norm === 'ETHEREUM' || norm === 'ETH') {
    return `https://etherscan.io/address/${cleanAddr}`;
  }
  if (norm === 'BNB' || norm === 'BSC') {
    return `https://bscscan.com/address/${cleanAddr}`;
  }
  if (norm === 'POLYGON' || norm === 'MATIC') {
    return `https://polygonscan.com/address/${cleanAddr}`;
  }
  if (norm === 'SOLANA' || norm === 'SOL') {
    return `https://solscan.io/account/${cleanAddr}`;
  }

  return `https://tronscan.org/#/address/${cleanAddr}`;
}
