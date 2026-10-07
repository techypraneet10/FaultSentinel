/**
 * Formatting helpers for FaultSentinel Command Center.
 */

export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

export function formatConfidence(score: number): string {
  return `${(score * 100).toFixed(1)}%`;
}

export function truncateString(str: string, maxLen: number): string {
  if (!str || str.length <= maxLen) return str;
  return `${str.slice(0, maxLen)}...`;
}

export function normalizeDatasetName(name: string): string {
  return name.toUpperCase();
}
