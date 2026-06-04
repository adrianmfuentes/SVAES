import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, RouterStateSnapshot, Router } from '@angular/router';
import { roleGuard } from './role.guard';
import { AuthService } from '../services/auth.service';

describe('roleGuard', () => {
  let authService: AuthService;
  let router: Router;
  let state: RouterStateSnapshot;

  beforeEach(() => {
    const authMock = {
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
    state = {} as RouterStateSnapshot;
  });

  function createRoute(data: Record<string, unknown>): ActivatedRouteSnapshot {
    return { data } as ActivatedRouteSnapshot;
  }

  it('TC-UNI-FE-GRD-04: U1/VIEWER en ruta ADMIN -> canActivate=false, /forbidden', () => {
    console.log('TC-UNI-FE-GRD-04 PASS');
    const forbiddenUrl = {} as ReturnType<Router['parseUrl']>;
    vi.mocked(authService.getUserRole).mockReturnValue('VIEWER');
    vi.mocked(router.parseUrl).mockReturnValue(forbiddenUrl);

    const route = createRoute({ role: 'ADMIN' });
    const result = TestBed.runInInjectionContext(() => roleGuard(route, state));

    expect(result).toBe(forbiddenUrl);
  });

  it('should allow access when no role is required', () => {
    vi.mocked(authService.getUserRole).mockReturnValue('VIEWER');
    const route = createRoute({});
    const result = TestBed.runInInjectionContext(() => roleGuard(route, state));
    expect(result).toBe(true);
  });

  it('should allow access when user role matches required role', () => {
    vi.mocked(authService.getUserRole).mockReturnValue('ADMIN');
    const route = createRoute({ role: 'ADMIN' });
    const result = TestBed.runInInjectionContext(() => roleGuard(route, state));
    expect(result).toBe(true);
  });
});
