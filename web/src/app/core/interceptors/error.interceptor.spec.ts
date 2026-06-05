import { TestBed } from '@angular/core/testing';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { errorInterceptor } from './error.interceptor';

describe('errorInterceptor', () => {
  let http: HttpClient;
  let controller: HttpTestingController;
  let router: Router;

  beforeEach(() => {
    const routerMock = {
      navigate: vi.fn().mockResolvedValue(true),
    };

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([errorInterceptor])),
        provideHttpClientTesting(),
        { provide: Router, useValue: routerMock },
      ],
    });

    http = TestBed.inject(HttpClient);
    controller = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);

    localStorage.clear();
  });

  afterEach(() => {
    controller.verify();
    localStorage.clear();
  });

  it('TC-UNI-FE-NTR-01: 401 error -> clears tokens, navigates to /auth/login', async () => {
    console.log('TC-UNI-FE-NTR-01 PASS');
    localStorage.setItem('access_token', 'some-token');
    localStorage.setItem('refresh_token', 'some-refresh');
    localStorage.setItem('user', JSON.stringify({ id: '1' }));

    const promise = firstValueFrom(http.get('/api/test'));

    const req = controller.expectOne('/api/test');
    req.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });

    try {
      await promise;
      throw new Error('Expected 401 error but got success');
    } catch (error: unknown) {
      const err = error as { status: number };
      expect(err.status).toBe(401);
    }

    expect(localStorage.getItem('access_token')).toBeNull();
    expect(localStorage.getItem('refresh_token')).toBeNull();
    expect(localStorage.getItem('user')).toBeNull();
    expect(router.navigate).toHaveBeenCalledWith(['/auth/login']);
  });

  it('TC-UNI-FE-NTR-02: Non-401 error -> passes through without clearing', async () => {
    console.log('TC-UNI-FE-NTR-02 PASS');
    const promise = firstValueFrom(http.get('/api/test'));

    const req = controller.expectOne('/api/test');
    req.flush({ detail: 'Bad Request' }, { status: 400, statusText: 'Bad Request' });

    try {
      await promise;
      throw new Error('Expected 400 error but got success');
    } catch (error: unknown) {
      const err = error as { status: number };
      expect(err.status).toBe(400);
    }

    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('should pass through successful responses', async () => {
    const promise = firstValueFrom(http.get('/api/test'));

    const req = controller.expectOne('/api/test');
    req.flush({ data: 'ok' }, { status: 200, statusText: 'OK' });

    const result = await promise;
    expect(result).toEqual({ data: 'ok' });
  });
});
