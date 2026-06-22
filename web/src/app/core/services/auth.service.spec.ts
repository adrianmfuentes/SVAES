import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import {
  AuthService,
  getAccessToken,
  clearAccessToken,
  setAccessToken,
  LoginStep1Response,
  TotpSetupResponse,
  Organization,
  UserInfo,
} from './auth.service';

function createJwt(payload: object): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const body = btoa(JSON.stringify(payload));
  return `${header}.${body}.signature`;
}

describe('AuthService', () => {
  let service: AuthService;
  let controller: HttpTestingController;
  let router: Router;

  beforeEach(() => {
    TestBed.resetTestingModule();
    clearAccessToken();
    localStorage.clear();

    const routerMock = {
      navigate: vi.fn(),
    };

    TestBed.configureTestingModule({
      providers: [
        AuthService,
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: routerMock },
      ],
    });

    service = TestBed.inject(AuthService);
    controller = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
  });

  afterEach(() => {
    controller?.verify();
    localStorage.clear();
    TestBed.resetTestingModule();
  });

  describe('decodeToken', () => {
    it('should decode a valid JWT payload', () => {
      const payload = { sub: 'user-1', role: 'OPERATOR', exp: 9999999999 };
      const token = createJwt(payload);
      const result = service.decodeToken(token);
      expect(result).toBeTruthy();
      expect(result!.sub).toBe('user-1');
      expect(result!.role).toBe('OPERATOR');
    });

    it('should return null for an invalid token', () => {
      const result = service.decodeToken('not.a.jwt');
      expect(result).toBeNull();
    });

    it('should return null for empty string', () => {
      const result = service.decodeToken('');
      expect(result).toBeNull();
    });
  });

  describe('isAdmin', () => {
    it('should return true when role is ADMIN', () => {
      const token = createJwt({ sub: '1', role: 'ADMIN' });
      setAccessToken(token);
      localStorage.setItem('access_token', token);
      expect(service.isAdmin()).toBe(true);
    });

    it('should return false when role is not ADMIN', () => {
      const token = createJwt({ sub: '1', role: 'OPERATOR' });
      setAccessToken(token);
      localStorage.setItem('access_token', token);
      expect(service.isAdmin()).toBe(false);
    });

    it('should return false when no token exists', () => {
      expect(service.isAdmin()).toBe(false);
    });
  });

  describe('login', () => {
    it('should POST /api/v1/auth/login and store tokens when login succeeds without 2FA', async () => {
      const response: LoginStep1Response = {
        requires_2fa: false,
        access_token: createJwt({ sub: 'u1', role: 'OPERATOR' }),
        refresh_token: 'refresh-abc',
        user_id: 'u1',
        role: 'OPERATOR',
      };

      const promise = firstValueFrom(service.login('test@test.com', 'password'));

      const req = controller.expectOne('/api/v1/auth/login');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ email: 'test@test.com', password: 'password' });
      req.flush(response);

      const result = await promise;
      expect(result.requires_2fa).toBe(false);
      expect(result.access_token).toBe(response.access_token);
      expect(getAccessToken()).toBe(response.access_token);
      expect(localStorage.getItem('access_token')).toBe(response.access_token);
      expect(localStorage.getItem('refresh_token')).toBe('refresh-abc');

      const storedUser = JSON.parse(localStorage.getItem('user')!);
      expect(storedUser.email).toBe('test@test.com');
      expect(storedUser.role).toBe('OPERATOR');
    });

    it('should not store tokens when login requires 2FA', async () => {
      const response: LoginStep1Response = {
        requires_2fa: true,
        totp_token: 'totp-token-xyz',
      };

      const promise = firstValueFrom(service.login('test@test.com', 'password'));

      const req = controller.expectOne('/api/v1/auth/login');
      req.flush(response);

      const result = await promise;
      expect(result.requires_2fa).toBe(true);
      expect(getAccessToken()).toBeNull();
      expect(localStorage.getItem('access_token')).toBeNull();
    });
  });

  describe('storeTokens', () => {
    it('should store access_token, refresh_token, and user info', () => {
      const token = createJwt({ sub: 'usr-1', email: 'u@test.com', role: 'ADMIN', organization_id: 'org-1' });
      const response: LoginStep1Response = {
        requires_2fa: false,
        access_token: token,
        refresh_token: 'rf-1',
        user_id: 'usr-1',
        role: 'ADMIN',
      };
      service.storeTokens(response, 'u@test.com');
      expect(getAccessToken()).toBe(token);
      expect(localStorage.getItem('access_token')).toBe(token);
      expect(localStorage.getItem('refresh_token')).toBe('rf-1');
      const user: UserInfo = JSON.parse(localStorage.getItem('user')!);
      expect(user.id).toBe('usr-1');
      expect(user.email).toBe('u@test.com');
      expect(user.role).toBe('ADMIN');
      expect(user.organization_id).toBe('org-1');
    });

    it('should not store anything if no access_token', () => {
      const response: LoginStep1Response = { requires_2fa: true };
      service.storeTokens(response, 'email@x.com');
      expect(getAccessToken()).toBeNull();
      expect(localStorage.getItem('access_token')).toBeNull();
    });
  });

  describe('verify2fa', () => {
    it('should POST /api/v1/auth/2fa/verify', async () => {
      const response: LoginStep1Response = {
        requires_2fa: false,
        access_token: 'at-2fa',
        refresh_token: 'rf-2fa',
      };

      const promise = firstValueFrom(service.verify2fa('totp-tk', '123456'));

      const req = controller.expectOne('/api/v1/auth/2fa/verify');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ totp_token: 'totp-tk', code: '123456' });
      req.flush(response);

      const result = await promise;
      expect(result.access_token).toBe('at-2fa');
    });
  });

  describe('setup2fa', () => {
    it('should GET /api/v1/auth/2fa/setup', async () => {
      const response: TotpSetupResponse = {
        totp_uri: 'otpauth://totp/SVAES:user?secret=ABC',
        secret: 'ABC',
        qr_data_url: 'data:image/png;base64,....',
      };

      const promise = firstValueFrom(service.setup2fa());

      const req = controller.expectOne('/api/v1/auth/2fa/setup');
      expect(req.request.method).toBe('GET');
      req.flush(response);

      const result = await promise;
      expect(result.secret).toBe('ABC');
      expect(result.totp_uri).toBe(response.totp_uri);
    });
  });

  describe('enable2fa', () => {
    it('should POST /api/v1/auth/2fa/enable', async () => {
      const promise = firstValueFrom(service.enable2fa('654321'));

      const req = controller.expectOne('/api/v1/auth/2fa/enable');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ code: '654321' });
      req.flush({ message: '2FA enabled' });

      const result = await promise;
      expect(result.message).toBe('2FA enabled');
    });
  });

  describe('disable2fa', () => {
    it('should POST /api/v1/auth/2fa/disable', async () => {
      const promise = firstValueFrom(service.disable2fa('111111'));

      const req = controller.expectOne('/api/v1/auth/2fa/disable');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ code: '111111' });
      req.flush({ message: '2FA disabled' });

      const result = await promise;
      expect(result.message).toBe('2FA disabled');
    });
  });

  describe('logout', () => {
    it('should clear tokens and navigate to /', () => {
      setAccessToken('some-token');
      localStorage.setItem('access_token', 'some-token');
      localStorage.setItem('refresh_token', 'rf');
      localStorage.setItem('user', JSON.stringify({ id: '1' }));

      service.logout();

      expect(getAccessToken()).toBeNull();
      expect(localStorage.getItem('access_token')).toBeNull();
      expect(localStorage.getItem('refresh_token')).toBeNull();
      expect(localStorage.getItem('user')).toBeNull();
      expect(router.navigate).toHaveBeenCalledWith(['/']);
    });
  });

  describe('isAuthenticated', () => {
    it('should return true when access token is in memory', () => {
      setAccessToken('mem-token');
      expect(service.isAuthenticated()).toBe(true);
    });

    it('should return true when access token is in localStorage', () => {
      localStorage.setItem('access_token', 'ls-token');
      expect(service.isAuthenticated()).toBe(true);
    });

    it('should return false when no token exists anywhere', () => {
      expect(service.isAuthenticated()).toBe(false);
    });
  });

  describe('getToken', () => {
    it('should return in-memory token first', () => {
      setAccessToken('mem-tk');
      localStorage.setItem('access_token', 'ls-tk');
      expect(service.getToken()).toBe('mem-tk');
    });

    it('should fallback to localStorage token', () => {
      localStorage.setItem('access_token', 'ls-tk');
      expect(service.getToken()).toBe('ls-tk');
    });

    it('should return null when no token exists', () => {
      expect(service.getToken()).toBeNull();
    });
  });

  describe('getUser', () => {
    it('should return parsed user from localStorage', () => {
      const user: UserInfo = { id: '1', email: 'x@y', display_name: 'X', role: 'OPERATOR' };
      localStorage.setItem('user', JSON.stringify(user));
      expect(service.getUser()).toEqual(user);
    });

    it('should return null when user is not stored', () => {
      expect(service.getUser()).toBeNull();
    });

    it('should return null for invalid JSON', () => {
      localStorage.setItem('user', 'not-json');
      expect(service.getUser()).toBeNull();
    });
  });

  describe('getUserRole', () => {
    it('should return role from token payload', () => {
      const token = createJwt({ sub: '1', role: 'ADMIN' });
      setAccessToken(token);
      localStorage.setItem('access_token', token);
      expect(service.getUserRole()).toBe('ADMIN');
    });

    it('should fallback to stored user role when token has no role', () => {
      const token = createJwt({ sub: '1' });
      setAccessToken(token);
      localStorage.setItem('access_token', token);
      localStorage.setItem('user', JSON.stringify({ id: '1', role: 'OPERATOR' }));
      expect(service.getUserRole()).toBe('OPERATOR');
    });

    it('should return empty string when no role found', () => {
      const token = createJwt({ sub: '1' });
      setAccessToken(token);
      localStorage.setItem('access_token', token);
      expect(service.getUserRole()).toBe('');
    });
  });

  describe('getOrganizations', () => {
    it('should GET /api/v1/organizations', async () => {
      const orgs: Organization[] = [
        { id: 'org-1', name: 'Org One', slug: 'org-one' },
        { id: 'org-2', name: 'Org Two', slug: 'org-two' },
      ];

      const promise = firstValueFrom(service.getOrganizations());

      const req = controller.expectOne('/api/v1/organizations');
      expect(req.request.method).toBe('GET');
      req.flush(orgs);

      const result = await promise;
      expect(result).toHaveLength(2);
      expect(result[0].slug).toBe('org-one');
    });
  });
});
