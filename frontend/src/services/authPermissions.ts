export type Permission = 'STR' | 'CTR' | 'RCOA' | 'ROCA';

const TOKEN_STORAGE_KEY = 'token';
const PERMISSIONS_STORAGE_KEY = 'permissions';

export const getStoredPermissions = (): Permission[] => {
  const rawPermissions = localStorage.getItem(PERMISSIONS_STORAGE_KEY);

  if (!rawPermissions) {
    console.log(`Could not find permissions`)
    return [];
  }

  try {
    const parsed = JSON.parse(rawPermissions) as unknown;
    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed.filter(
      (permission): permission is Permission =>
        permission === 'STR' || permission === 'CTR' || permission === 'RCOA' || permission === 'ROCA',
    );
  } catch {
    return [];
  }
};

export const isAuthenticated = () => Boolean(localStorage.getItem(TOKEN_STORAGE_KEY));

export const getDefaultRouteForPermissions = (permissions: Permission[]) => {
  if (permissions.includes('RCOA') || permissions.includes('ROCA')) {
    return '/rcoa';
  }

  if (permissions.includes('STR')) {
    return '/xml-generator';
  }

  if (permissions.includes('CTR')) {
    return '/ctr-generator';
  }

  return '/home';
};

export const setAuthSession = (token: string, permissions: Permission[]) => {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
  localStorage.setItem(PERMISSIONS_STORAGE_KEY, JSON.stringify(permissions));
};

export const clearAuthSession = () => {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
  localStorage.removeItem(PERMISSIONS_STORAGE_KEY);
};

export const hasPermission = (permission: Permission) => {
  const permissions = getStoredPermissions();
  if (permission === 'RCOA') {
    return permissions.includes('RCOA') || permissions.includes('ROCA');
  }
  return permissions.includes(permission);
};
