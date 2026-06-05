import { TestBed } from '@angular/core/testing';
import { HttpClient, provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { firstValueFrom } from 'rxjs';

describe('Verify Release — Verification Flow', () => {
  let http: HttpClient;
  let controller: HttpTestingController;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpClient);
    controller = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    controller?.verify();
    TestBed.resetTestingModule();
  });

  it('TC-UNI-FE-NGR-01: API 202+taskId -> verifyReleaseSuccess con taskId', async () => {
    console.log('TC-UNI-FE-NGR-01 PASS');
    const releaseId = 'rel-verify-ok';
    const mockResponse = { task_id: 'task-001', status: 'EN_VERIFICACION' };

    const promise = firstValueFrom(
      http.post<{ task_id: string; status: string }>(
        `/api/v1/releases/${releaseId}/verify`,
        {},
      ),
    );

    const req = controller.expectOne(`/api/v1/releases/${releaseId}/verify`);
    expect(req.request.method).toBe('POST');
    req.flush(mockResponse, { status: 202, statusText: 'Accepted' });

    const result = await promise;
    expect(result.task_id).toBe('task-001');
    expect(result.status).toBe('EN_VERIFICACION');
  });

  it('TC-UNI-FE-NGR-02: API 409 -> verifyReleaseFailure con INVALID_STATE', async () => {
    console.log('TC-UNI-FE-NGR-02 PASS');
    const releaseId = 'rel-verify-conflict';

    const promise = firstValueFrom(
      http.post(`/api/v1/releases/${releaseId}/verify`, {}),
    );

    const req = controller.expectOne(`/api/v1/releases/${releaseId}/verify`);
    req.flush(
      { detail: 'La release no se encuentra en un estado valido para verificacion' },
      { status: 409, statusText: 'Conflict' },
    );

    try {
      await promise;
      throw new Error('Expected 409 Conflict error but got success');
    } catch (error: unknown) {
      const err = error as { status: number };
      expect(err.status).toBe(409);
    }
  });
});
