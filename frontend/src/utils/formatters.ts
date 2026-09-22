/**
 * Utility functions for formatting numbers, currency, crypto amounts,
 * and time intervals cleanly across the SPECTER frontend.
 */

export function parseNumberSafely(val: number | string | undefined | null): number {
  if (val === undefined || val === null || val === '') return 0;
  if (typeof val === 'number') {
    return isNaN(val) ? 0 : val;
  }
  const parsed = parseFloat(val);
  return isNaN(parsed) ? 0 : parsed;
}

/**
 * Abbreviates large numeric values into human-readable strings (K, M, B, T, Q).
 * Example: 115792089237316200000000000 -> "115.79Q" or "115.79T+"
 */
export function formatLargeNumber(val: number | string | undefined | null): string {
  const num = parseNumberSafely(val);
  const absNum = Math.abs(num);

  if (absNum >= 1e18) {
    return `${(num / 1e18).toFixed(2)}E`; // Exa
  }
  if (absNum >= 1e15) {
    return `${(num / 1e15).toFixed(2)}Q`; // Quadrillion
  }
  if (absNum >= 1e12) {
    return `${(num / 1e12).toFixed(2)}T`; // Trillion
  }
  if (absNum >= 1e9) {
    return `${(num / 1e9).toFixed(2)}B`; // Billion
  }
  if (absNum >= 1e6) {
    return `${(num / 1e6).toFixed(2)}M`; // Million
  }
  if (absNum >= 1e3) {
    return `${(num / 1e3).toFixed(1)}K`;
  }
  return num.toLocaleString('en-US', { maximumFractionDigits: 2 });
}

/**
 * Formats a currency value with intelligent abbreviation.
 * Example: 115792089237316200000000000 -> "$115.79E"
 * Example: 50000 -> "$50,000" or "$50K"
 */
export function formatCurrency(val: number | string | undefined | null, abbreviate = true): string {
  const num = parseNumberSafely(val);
  if (abbreviate && Math.abs(num) >= 100000) {
    return `$${formatLargeNumber(num)}`;
  }
  return `$${num.toLocaleString('en-US', { maximumFractionDigits: 2 })}`;
}

/**
 * Formats crypto transfer amounts cleanly without trailing zero noise.
 */
export function formatCryptoAmount(val: number | string | undefined | null, asset = 'USDT'): string {
  const num = parseNumberSafely(val);
  if (Math.abs(num) >= 1000000) {
    return `${formatLargeNumber(num)} ${asset}`;
  }
  return `${num.toLocaleString('en-US', { maximumFractionDigits: 2 })} ${asset}`;
}

/**
 * Formats seconds into human-readable transfer gaps.
 * Example: 8 -> "8s", 125 -> "2m 5s", 4200 -> "1.2h"
 */
export function formatTimeInterval(seconds: number | string | undefined | null): string {
  if (seconds === undefined || seconds === null || seconds === '') return 'N/A';
  const secs = parseNumberSafely(seconds);
  if (secs <= 0) return '0s';
  if (secs < 60) return `${Math.round(secs)}s`;
  if (secs < 3600) {
    const mins = Math.floor(secs / 60);
    const remainder = Math.round(secs % 60);
    return remainder > 0 ? `${mins}m ${remainder}s` : `${mins}m`;
  }
  const hours = (secs / 3600).toFixed(1);
  return `${hours.endsWith('.0') ? hours.slice(0, -2) : hours}h`;
}

/**
 * Formats exact numbers for tooltips and detailed views.
 */
export function formatExactNumber(val: number | string | undefined | null): string {
  if (val === undefined || val === null) return '0';
  if (typeof val === 'string') return val;
  return val.toLocaleString('en-US', { maximumFractionDigits: 4 });
}
