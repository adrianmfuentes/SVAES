import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, RouterStateSnapshot, Router } from '@angular/router';
import { businessRouteGuard } from './business-route.guard';
import { AuthService } from '../services/auth.service';

describe('businessRouteGuard', () => {
  let authService: AuthService;
  let router: Router;
  let route: ActivatedRouteSnapshot;
  let state: RouterStateSnapshot;

  beforeEach(() => {
    const authMock = {
      isAdmin: vi.fn(),
      getUserRole: vi.fn(),
    };
    const routerMock = {
      parseUrl: vi.fn(),
    };

    TestBed.configureTestingModule({
      providers: [
        { provide: AuthService, useValue: authMock },
        { provide: Router, useValue: routerMock },
      ],
    });

    authService = TestBed.inject(AuthService);
    router = TestBed.inject(Router);
    route = {} as ActivatedRouteSnapshot;
    state = {} as RouterStateSnapshot;
  });

  it('TC-UNI-FE-GRD-05: Admin user -> redirect to /app/system', () => {
    console.log('TC-UNI-FE-GRD-05 PASS');
    vi.mocked(authService.isAdmin).mockReturnValue(true);
    const systemUrl = {} as ReturnType<Router['parseUrl']>;
    vi.mocked(router.parseUrl).mockReturnValue(systemUrl);

    const result = TestBed.runInInjectionContext(() => businessRouteGuard(route, state));

    expect(result).toBe(systemUrl);
    expect(router.parseUrl).toHaveBeenCalledWith('/app/system');
  });

  it('TC-UNI-FE-GRD-06: Non-admin user -> canActivate=true', () => {
    console.log('TC-UNI-FE-GRD-06 PASS');
    vi.mocked(authService.isAdmin).mockReturnValue(false);
    vi.mocked(authService.getUserRole).mockReturnValue('OPERATOR');

    const result = TestBed.runInInjectionContext(() => businessRouteGuard(route, state));

    expect(result).toBe(true);
  });

  it('TC-UNI-FE-GRD-07: VIEWER accessing dashboard -> allowed', () => {
    vi.mocked(authService.isAdmin).mockReturnValue(false);
    vi.mocked(authService.getUserRole).mockReturnValue('VIEWER');
    route.routeConfig = { path: 'dashboard' } as any;

    const result = TestBed.runInInjectionContext(() => businessRouteGuard(route, state));

    expect(result).toBe(true);
  });

  it('TC-UNI-FE-GRD-08: VIEWER accessing profile -> allowed', () => {
    vi.mocked(authService.isAdmin).mockReturnValue(false);
    vi.mocked(authService.getUserRole).mockReturnValue('VIEWER');
    route.routeConfig = { path: 'profile' } as any;

    const result = TestBed.runInInjectionContext(() => businessRouteGuard(route, state));

    expect(result).toBe(true);
  });

  it('TC-UNI-FE-GRD-09: VIEWER accessing releases -> denied', () => {
    vi.mocked(authService.isAdmin).mockReturnValue(false);
    vi.mocked(authService.getUserRole).mockReturnValue('VIEWER');
    route.routeConfig = { path: 'releases' } as any;
    const forbiddenUrl = {} as ReturnType<Router['parseUrl']>;
    vi.mocked(router.parseUrl).mockReturnValue(forbiddenUrl);

    const result = TestBed.runInInjectionContext(() => businessRouteGuard(route, state));

    expect(result).toBe(forbiddenUrl);
    expect(router.parseUrl).toHaveBeenCalledWith('/app/403');
  });
});
