import { type ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { getDefaultRouteForPermissions, getStoredPermissions, hasPermission, isAuthenticated, type Permission } from '../../services/authPermissions';

type PermissionRouteProps = {
  permission: Permission;
  children: ReactNode;
};

const PermissionRoute = ({ permission, children }: PermissionRouteProps) => {
  const permissions = getStoredPermissions();

  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }

  if (!hasPermission(permission)) {
    return <Navigate to={getDefaultRouteForPermissions(permissions)} replace />;
  }

  return <>{children}</>;
};

export default PermissionRoute;
