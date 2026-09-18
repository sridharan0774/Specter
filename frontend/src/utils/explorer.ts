/**
 * Utility for constructing and normalizing verified blockchain explorer URLs.
 * Never invents placeholder transaction IDs or mock hashes.
 */
export function buildExplorerUrl(txHash: string, chain: string = 'TRON', defaultUrl?: string): string {
  if (defaultUrl && defaultUrl.startsWith('http')) {
    // Standardize TronScan web hash link format to include #/transaction/ if needed
    if (defaultUrl.includes('tronscan.org') && defaultUrl.includes('/transaction/') && !defaultUrl.includes('#/transaction/')) {
      return defaultUrl.replace('/transaction/', '/#/transaction/');
    }
    return defaultUrl;
  }

  const cleanHash = txHash ? txHash.trim() : '';
  if (!cleanHash) return '#';

  const normalizedChain = (chain || 'TRON').toUpperCase();

  if (normalizedChain === 'TRON') {
    return `https://tronscan.org/#/transaction/${cleanHash}`;
  }

  // Default to TronScan for TRON assets
  return `https://tronscan.org/#/transaction/${cleanHash}`;
}

export function buildAddressExplorerUrl(address: string, chain: string = 'TRON', defaultUrl?: string): string {
  if (defaultUrl && defaultUrl.startsWith('http')) {
    if (defaultUrl.includes('tronscan.org') && defaultUrl.includes('/address/') && !defaultUrl.includes('#/address/')) {
      return defaultUrl.replace('/address/', '/#/address/');
    }
    return defaultUrl;
  }

  const cleanAddr = address ? address.trim() : '';
  if (!cleanAddr) return '#';

  const normalizedChain = (chain || 'TRON').toUpperCase();

  if (normalizedChain === 'TRON') {
    return `https://tronscan.org/#/address/${cleanAddr}`;
  }

  return `https://tronscan.org/#/address/${cleanAddr}`;
}


