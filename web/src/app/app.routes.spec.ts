import { Routes } from '@angular/router';
import { routes } from './app.routes';

describe('app.routes', () => {
  it('should have routes defined', () => {
    expect(routes).toBeDefined();
    expect(routes.length).toBeGreaterThan(0);
  });

  describe('route paths', () => {
    it('should have empty path route', () => {
      const emptyRoute = routes.find((r: Routes[number]) => r.path === '');
      expect(emptyRoute).toBeDefined();
      expect(emptyRoute?.loadComponent).toBeDefined();
    });

    it('should have auth path with children', () => {
      const authRoute = routes.find((r: Routes[number]) => r.path === 'auth');
      expect(authRoute).toBeDefined();
      expect(authRoute?.children).toBeDefined();

      const authChildren = authRoute?.children ?? [];

      const loginRoute = authChildren.find((c: Routes[number]) => c.path === 'login');
      expect(loginRoute).toBeDefined();
      expect(loginRoute?.loadComponent).toBeDefined();

      const activateRoute = authChildren.find((c: Routes[number]) => c.path === 'activate');
      expect(activateRoute).toBeDefined();
      expect(activateRoute?.loadComponent).toBeDefined();

      const redirectRoute = authChildren.find(
        (c: Routes[number]) => c.path === '' && c.redirectTo !== undefined,
      );
      expect(redirectRoute).toBeDefined();
      expect(redirectRoute?.redirectTo).toBe('login');
    });

    it('should have app path with authGuard and children', () => {
      const appRoute = routes.find((r: Routes[number]) => r.path === 'app');
      expect(appRoute).toBeDefined();
      expect(appRoute?.canActivate).toBeDefined();
      expect(appRoute?.children).toBeDefined();

      const children = appRoute?.children ?? [];

      const dashboardRoute = children.find((c: Routes[number]) => c.path === 'dashboard');
      expect(dashboardRoute).toBeDefined();
      expect(dashboardRoute?.canActivate).toBeDefined();

      const systemRoute = children.find((c: Routes[number]) => c.path === 'system');
      expect(systemRoute).toBeDefined();
      expect(systemRoute?.canActivate).toBeDefined();
      expect((systemRoute as { data?: Record<string, unknown> }).data).toEqual({ role: 'ADMIN' });

      const adminRoute = children.find((c: Routes[number]) => c.path === 'admin');
      expect(adminRoute).toBeDefined();
      expect(adminRoute?.canActivate).toBeDefined();
      expect((adminRoute as { data?: Record<string, unknown> }).data).toEqual({ role: 'ADMIN' });

      const redirectRoute = children.find(
        (c: Routes[number]) => c.path === '' && c.pathMatch === 'full' && c.redirectTo !== undefined,
      );
      expect(redirectRoute).toBeDefined();
      expect(redirectRoute?.redirectTo).toBe('dashboard');
    });

    it('should have request-access path route', () => {
      const reqRoute = routes.find((r: Routes[number]) => r.path === 'request-access');
      expect(reqRoute).toBeDefined();
      expect(reqRoute?.loadComponent).toBeDefined();
    });

    it('should have catch-all wildcard route', () => {
      const catchAll = routes.find((r: Routes[number]) => r.path === '**');
      expect(catchAll).toBeDefined();
      expect(catchAll?.loadComponent).toBeDefined();
    });
  });
});
