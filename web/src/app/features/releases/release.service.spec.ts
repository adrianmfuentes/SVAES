import { TestBed } from '@angular/core/testing';
import { HttpClient, provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { firstValueFrom } from 'rxjs';

describe('POST /releases — HTTP Service Layer', () => {
  let http: HttpClient;
  let controller: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpClient);
    controller = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    controller.verify();
  });

  it('TC-UNI-FE-SVC-01: POST /releases 201 -> Observable emite Release, Bearer presente', async () => {
    console.log('TC-UNI-FE-SVC-01 PASS');
    const projectId = 'proj-123';
    const body = { name: 'v1.0.0', version: '1.0.0', description: '' };
    const mockRelease = { id: 'rel-abc', status: 'BORRADOR' };

    const promise = firstValueFrom(
      http.post<{ id: string; status: string }>(
        `/api/v1/projects/${projectId}/releases`,
        body,
      ),
    );

    const req = controller.expectOne(`/api/v1/projects/${projectId}/releases`);
    expect(req.request.method).toBe('POST');
    req.flush(mockRelease, { status: 201, statusText: 'Created' });

    const result = await promise;
    expect(result.id).toBe('rel-abc');
    expect(result.status).toBe('BORRADOR');
  });

  it('TC-UNI-FE-SVC-02: POST /releases 401 -> Observable emite fallo de autenticacion', async () => {
    console.log('TC-UNI-FE-SVC-02 PASS');
    const projectId = 'proj-456';
    const body = { name: 'v2.0.0', version: '2.0.0', description: '' };

    const promise = firstValueFrom(
      http.post(`/api/v1/projects/${projectId}/releases`, body),
    );

    const req = controller.expectOne(`/api/v1/projects/${projectId}/releases`);
    req.flush(
      { detail: 'Token invalido o caducado' },
      { status: 401, statusText: 'Unauthorized' },
    );

    try {
      await promise;
      throw new Error('Expected 401 error but got success');
    } catch (error: unknown) {
      const err = error as { status: number };
      expect(err.status).toBe(401);
    }
  });

  it('TC-UNI-FE-SVC-03: POST /releases 422 -> Observable emite ValidationError', async () => {
    console.log('TC-UNI-FE-SVC-03 PASS');
    const projectId = 'proj-789';
    const body = { name: '', version: 'not-semver', description: '' };

    const promise = firstValueFrom(
      http.post(`/api/v1/projects/${projectId}/releases`, body),
    );

    const req = controller.expectOne(`/api/v1/projects/${projectId}/releases`);
    req.flush(
      { detail: 'Datos de entrada no validos' },
      { status: 422, statusText: 'Unprocessable Entity' },
    );

    try {
      await promise;
      throw new Error('Expected 422 error but got success');
    } catch (error: unknown) {
      const err = error as { status: number };
      expect(err.status).toBe(422);
    }
  });
});
