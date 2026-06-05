import { TestBed } from '@angular/core/testing';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { firstValueFrom } from 'rxjs';
import { jwtInterceptor } from './jwt.interceptor';
import { AuthService } from '../services/auth.service';

describe('jwtInterceptor', () => {
  let http: HttpClient;
  let controller: HttpTestingController;
  let authService: AuthService;

  beforeEach(() => {
    const authMock = {
      getToken: vi.fn(),
    };

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([jwtInterceptor])),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: authMock },
      ],
    });

    http = TestBed.inject(HttpClient);
    controller = TestBed.inject(HttpTestingController);
    authService = TestBed.inject(AuthService);
  });

  afterEach(() => {
    controller.verify();
  });

  it('TC-UNI-FE-NTR-03: Token presente -> adds Authorization Bearer header', async () => {
    console.log('TC-UNI-FE-NTR-03 PASS');
    vi.mocked(authService.getToken).mockReturnValue('my-jwt-token');

    const promise = firstValueFrom(http.get('/api/test'));

    const req = controller.expectOne('/api/test');
    expect(req.request.headers.get('Authorization')).toBe('Bearer my-jwt-token');
    req.flush({ ok: true });

    const result = await promise;
    expect(result).toEqual({ ok: true });
  });

  it('TC-UNI-FE-NTR-04: Token ausente -> no Authorization header', async () => {
    console.log('TC-UNI-FE-NTR-04 PASS');
    vi.mocked(authService.getToken).mockReturnValue(null);

    const promise = firstValueFrom(http.get('/api/test'));

    const req = controller.expectOne('/api/test');
    expect(req.request.headers.has('Authorization')).toBe(false);
    req.flush({ ok: true });

    const result = await promise;
    expect(result).toEqual({ ok: true });
  });
});
