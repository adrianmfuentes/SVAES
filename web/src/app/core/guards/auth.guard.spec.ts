import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, RouterStateSnapshot, Router } from '@angular/router';
import { authGuard } from './auth.guard';
import { AuthService } from '../services/auth.service';

describe('authGuard', () => {
  let authService: AuthService;
  let router: Router;
  let route: ActivatedRouteSnapshot;
  let state: RouterStateSnapshot;

  beforeEach(() => {
    const authMock = {
      isAuthenticated: vi.fn(),
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

  it('TC-UNI-FE-GRD-01: Token valido, U2/OPERATOR, ruta permitida -> canActivate=true', () => {
    console.log('TC-UNI-FE-GRD-01 PASS');
    vi.mocked(authService.isAuthenticated).mockReturnValue(true);
    const result = TestBed.runInInjectionContext(() => authGuard(route, state));
    expect(result).toBe(true);
  });

  it('TC-UNI-FE-GRD-02: Token caducado -> canActivate=false, redirige /login', () => {
    console.log('TC-UNI-FE-GRD-02 PASS');
    vi.mocked(authService.isAuthenticated).mockReturnValue(false);
    const loginUrl = {} as ReturnType<Router['parseUrl']>;
    vi.mocked(router.parseUrl).mockReturnValue(loginUrl);
    const result = TestBed.runInInjectionContext(() => authGuard(route, state));
    expect(result).toBe(loginUrl);
  });

  it('TC-UNI-FE-GRD-03: Token ausente -> canActivate=false, redirige /login', () => {
    console.log('TC-UNI-FE-GRD-03 PASS');
    vi.mocked(authService.isAuthenticated).mockReturnValue(false);
    const loginUrl = {} as ReturnType<Router['parseUrl']>;
    vi.mocked(router.parseUrl).mockReturnValue(loginUrl);
    const result = TestBed.runInInjectionContext(() => authGuard(route, state));
    expect(result).toBe(loginUrl);
  });
});
