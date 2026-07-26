/**
 * Helper utility to extract the short branch name by removing
 * the suffix "Swarna Mahal" and trimming any trailing/leading spaces.
 */
export function getShortBranchName(fullName: string | undefined | null): string {
  if (!fullName) return '';
  return fullName.replace(/Swarna\s+Mahal/i, '').trim();
}
