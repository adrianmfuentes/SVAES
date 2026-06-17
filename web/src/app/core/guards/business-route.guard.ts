import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

const VIEWER_ALLOWED_ROUTES = ['dashboard', 'profile'];

export const businessRouteGuard: CanActivateFn = (route) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (authService.isAdmin()) {
    return router.parseUrl('/app/system');
  }

  const userRole = authService.getUserRole();
  const path = route.routeConfig?.path ?? '';

  if (userRole === 'VIEWER' && !VIEWER_ALLOWED_ROUTES.includes(path)) {
    return router.parseUrl('/app/403');
  }

  return true;
};
