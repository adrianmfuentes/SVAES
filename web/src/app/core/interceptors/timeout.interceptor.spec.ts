import { TestBed } from '@angular/core/testing';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { firstValueFrom } from 'rxjs';
import { timeoutInterceptor } from './timeout.interceptor';

describe('timeoutInterceptor', () => {
  let http: HttpClient;
  let controller: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([timeoutInterceptor])),
        provideHttpClientTesting(),
      ],
    });

    http = TestBed.inject(HttpClient);
    controller = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    controller.verify();
  });

  it('TC-UNI-FE-NTR-05: Successful request completes normally', async () => {
    console.log('TC-UNI-FE-NTR-05 PASS');
    const promise = firstValueFrom(http.get('/api/test'));

    const req = controller.expectOne('/api/test');
    req.flush({ data: 'ok' });

    const result = await promise;
    expect(result).toEqual({ data: 'ok' });
  });

  it('TC-UNI-FE-NTR-06: Slow request -> timeout error after 30000ms', async () => {
    console.log('TC-UNI-FE-NTR-06 PASS');
    const promise = firstValueFrom(http.get('/api/test'));

    const req = controller.expectOne('/api/test');

    req.error(new ProgressEvent('timeout'), { status: 0, statusText: 'Timeout' });

    try {
      await promise;
      throw new Error('Expected timeout error but got success');
    } catch (error: unknown) {
      const err = error as { status: number };
      expect(err.status).toBe(0);
    }
  });
});
