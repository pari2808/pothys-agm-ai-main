export const BRANCH_IMAGES: Record<string, any> = {
  'Chromepet': require('../../assets/branch_chromepet.png'),
  'Coimbatore': require('../../assets/branch_coimbatore.png'),
  'Padi': require('../../assets/branch_padi.png'),
  'Poonamallee': require('../../assets/branch_poonamallee.png'),
  'Salem': require('../../assets/branch_salem.png'),
  'Tirunelveli': require('../../assets/branch_tirunelveli.png'),
  'Trichy': require('../../assets/branch_trichy.png'),
  'Trivandrum': require('../../assets/branch_trivandrum.png'),
};

export const getBranchImage = (branchName: string) => {
  if (!branchName) return BRANCH_IMAGES['Chromepet'];
  const name = branchName.replace(/Swarna Mahal/gi, '').replace(/Pothys/gi, '').trim();
  return BRANCH_IMAGES[name] || BRANCH_IMAGES['Chromepet'];
};
