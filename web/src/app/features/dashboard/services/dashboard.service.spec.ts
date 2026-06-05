import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { DashboardService, DashboardMetrics, Project, RecentRelease } from './dashboard.service';
import { firstValueFrom } from 'rxjs';

describe('DashboardService', () => {
  let service: DashboardService;
  let controller: HttpTestingController;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), DashboardService],
    });
    service = TestBed.inject(DashboardService);
    controller = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    controller?.verify();
    TestBed.resetTestingModule();
  });

  describe('getMetrics', () => {
    it('should fetch dashboard metrics', async () => {
      const mockMetrics: DashboardMetrics = {
        total_releases: 100,
        valid_releases: 80,
        invalid_releases: 10,
        pending_releases: 10,
        total_verifications: 200,
        pass_rate: 80,
      };

      const promise = firstValueFrom(service.getMetrics());

      const req = controller.expectOne('/api/v1/dashboard/metrics');
      expect(req.request.method).toBe('GET');
      req.flush(mockMetrics);

      const result = await promise;
      expect(result.total_releases).toBe(100);
      expect(result.valid_releases).toBe(80);
      expect(result.pass_rate).toBe(80);
    });

    it('should propagate HTTP errors', async () => {
      const promise = firstValueFrom(service.getMetrics());

      const req = controller.expectOne('/api/v1/dashboard/metrics');
      req.flush(null, { status: 500, statusText: 'Internal Server Error' });

      try {
        await promise;
        throw new Error('Expected error');
      } catch (error: unknown) {
        const err = error as { status: number };
        expect(err.status).toBe(500);
      }
    });
  });

  describe('getProjects', () => {
    it('should fetch projects list', async () => {
      const mockProjects: Project[] = [
        { id: 'proj-1', name: 'Project Alpha' },
        { id: 'proj-2', name: 'Project Beta' },
      ];

      const promise = firstValueFrom(service.getProjects());

      const req = controller.expectOne('/api/v1/projects');
      expect(req.request.method).toBe('GET');
      req.flush(mockProjects);

      const result = await promise;
      expect(result.length).toBe(2);
      expect(result[0].name).toBe('Project Alpha');
    });

    it('should cache projects with shareReplay', async () => {
      const mockProjects: Project[] = [
        { id: 'proj-1', name: 'Project Alpha' },
      ];

      const promise1 = firstValueFrom(service.getProjects());

      const req = controller.expectOne('/api/v1/projects');
      req.flush(mockProjects);

      const result1 = await promise1;
      expect(result1.length).toBe(1);

      // Second call should use cached value, no new HTTP request
      const promise2 = firstValueFrom(service.getProjects());
      const result2 = await promise2;
      expect(result2).toEqual(result1);

      // No pending requests expected
      controller.expectNone('/api/v1/projects');
    });

    it('should handle projects error by returning empty array', async () => {
      const promise = firstValueFrom(service.getProjects());

      const req = controller.expectOne('/api/v1/projects');
      req.flush(null, { status: 500, statusText: 'Error' });

      const result = await promise;
      expect(result).toEqual([]);
    });
  });

  describe('getRecentReleases', () => {
    it('should fetch releases per project, flatten and sort by date descending', async () => {
      const mockProjects: Project[] = [
        { id: 'p1', name: 'Alpha' },
        { id: 'p2', name: 'Beta' },
      ];

      const alphaReleases: RecentRelease[] = [
        {
          id: 'r1',
          name: 'R1',
          version: '1.0.0',
          verdict: 'VALID',
          created_at: '2025-01-10T00:00:00Z',
        },
      ];

      const betaReleases: RecentRelease[] = [
        {
          id: 'r2',
          name: 'R2',
          version: '2.0.0',
          verdict: 'VALID',
          created_at: '2025-01-15T00:00:00Z',
        },
        {
          id: 'r3',
          name: 'R3',
          version: '2.1.0',
          verdict: 'INVALID',
          created_at: '2025-01-05T00:00:00Z',
        },
      ];

      const promise = firstValueFrom(service.getRecentReleases());

      // First: projects request
      const projectsReq = controller.expectOne('/api/v1/projects');
      projectsReq.flush(mockProjects);

      // Then: release requests per project (max 5)
      const alphaReq = controller.expectOne('/api/v1/projects/p1/releases');
      alphaReq.flush(alphaReleases);

      const betaReq = controller.expectOne('/api/v1/projects/p2/releases');
      betaReq.flush(betaReleases);

      const result = await promise;

      expect(result.length).toBe(3);
      // Should be sorted by date descending: 2025-01-15 first, then 2025-01-10, then 2025-01-05
      expect(result[0].id).toBe('r2');
      expect(result[1].id).toBe('r1');
      expect(result[2].id).toBe('r3');
      // Project names should be attached
      expect(result[0].project_name).toBe('Beta');
      expect(result[1].project_name).toBe('Alpha');
      expect(result[2].project_name).toBe('Beta');
    });

    it('should slice to top 10 results', async () => {
      const mockProjects: Project[] = [
        { id: 'p1', name: 'Alpha' },
      ];

      const manyReleases: RecentRelease[] = Array.from({ length: 15 }, (_, i) => ({
        id: `r${i}`,
        name: `Release ${i}`,
        version: `${i}.0.0`,
        verdict: 'VALID',
        created_at: new Date(2025, 0, 15 - i).toISOString(),
      }));

      const promise = firstValueFrom(service.getRecentReleases());

      const projectsReq = controller.expectOne('/api/v1/projects');
      projectsReq.flush(mockProjects);

      const alphaReq = controller.expectOne('/api/v1/projects/p1/releases');
      alphaReq.flush(manyReleases);

      const result = await promise;
      expect(result.length).toBe(10);
    });

    it('should return empty array when no projects exist', async () => {
      const promise = firstValueFrom(service.getRecentReleases());

      const projectsReq = controller.expectOne('/api/v1/projects');
      projectsReq.flush([]);

      const result = await promise;
      expect(result).toEqual([]);
    });

    it('should limit to first 5 projects', async () => {
      const mockProjects: Project[] = [
        { id: 'p1', name: 'A' },
        { id: 'p2', name: 'B' },
        { id: 'p3', name: 'C' },
        { id: 'p4', name: 'D' },
        { id: 'p5', name: 'E' },
        { id: 'p6', name: 'F' },
        { id: 'p7', name: 'G' },
      ];

      const promise = firstValueFrom(service.getRecentReleases());

      const projectsReq = controller.expectOne('/api/v1/projects');
      projectsReq.flush(mockProjects);

      // Should only make 5 release requests (for p1-p5)
      for (let i = 1; i <= 5; i++) {
        const req = controller.expectOne(`/api/v1/projects/p${i}/releases`);
        req.flush([]);
      }

      await promise;

      // No more requests expected
      controller.expectNone('/api/v1/projects/p6/releases');
    });

    it('should handle individual project release request errors gracefully', async () => {
      const mockProjects: Project[] = [
        { id: 'p1', name: 'Alpha' },
        { id: 'p2', name: 'Beta' },
      ];

      const alphaReleases: RecentRelease[] = [
        {
          id: 'r1',
          name: 'R1',
          version: '1.0.0',
          verdict: 'VALID',
          created_at: '2025-01-10T00:00:00Z',
        },
      ];

      const promise = firstValueFrom(service.getRecentReleases());

      const projectsReq = controller.expectOne('/api/v1/projects');
      projectsReq.flush(mockProjects);

      const alphaReq = controller.expectOne('/api/v1/projects/p1/releases');
      alphaReq.flush(alphaReleases);

      // Beta's releases fail
      const betaReq = controller.expectOne('/api/v1/projects/p2/releases');
      betaReq.flush(null, { status: 500, statusText: 'Error' });

      const result = await promise;
      // Should still get the successful project's releases
      expect(result.length).toBe(1);
      expect(result[0].id).toBe('r1');
    });
  });
});
