import { formatIndianCurrency } from './currencyFormatter';

/**
 * Formats weight in grams (g) with space before unit.
 * Example: 1480 -> "1480 g"
 */
export function formatGrams(value: number | string | undefined | null): string {
  if (value === undefined || value === null) return '0 g';
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num) || num === 0) return '0 g';
  const formatted = num % 1 === 0 ? num.toString() : num.toFixed(1);
  return `${formatted} g`;
}

/**
 * Formats weight in carats (ct) with space before unit.
 * Example: 105 -> "105 ct"
 */
export function formatCarats(value: number | string | undefined | null): string {
  if (value === undefined || value === null) return '0 ct';
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num) || num === 0) return '0 ct';
  const formatted = num % 1 === 0 ? num.toString() : num.toFixed(1);
  return `${formatted} ct`;
}

/**
 * Formats monetary value in Indian currency (₹).
 * Example: 510000 -> "₹5.10L"
 */
export function formatSilverMRP(value: number | string | undefined | null): string {
  if (value === undefined || value === null) return '₹0';
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num) || num === 0) return '₹0';
  return formatIndianCurrency(num);
}
