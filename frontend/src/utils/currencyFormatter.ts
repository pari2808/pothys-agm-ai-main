export function formatIndianCurrency(value: number | string | undefined | null): string {
  if (value === undefined || value === null) return '₹0';
  
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return '₹0';

  const absNum = Math.abs(num);
  const sign = num < 0 ? '-' : '';

  if (absNum < 100000) {
    // Less than 1 Lakh
    return `${sign}₹${absNum.toLocaleString('en-IN')}`;
  } else if (absNum < 10000000) {
    // 1 Lakh to 99.99 Lakhs
    const lakhs = absNum / 100000;
    return `${sign}₹${lakhs.toFixed(2)}L`;
  } else {
    // 1 Crore and above
    const crores = absNum / 10000000;
    return `${sign}₹${crores.toFixed(2)}Cr`;
  }
}

export function formatFullIndianCurrency(value: number | string | undefined | null): string {
  if (value === undefined || value === null) return '₹0';
  
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return '₹0';

  const absNum = Math.round(Math.abs(num));
  const sign = num < 0 ? '-' : '';

  return `${sign}₹${absNum.toLocaleString('en-IN')}`;
}

