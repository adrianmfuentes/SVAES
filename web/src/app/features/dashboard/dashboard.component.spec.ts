import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { NO_ERRORS_SCHEMA } from '@angular/core';
import { provideRouter } from '@angular/router';
import { DashboardComponent } from './dashboard.component';
import { DashboardService, DashboardMetrics, RecentRelease } from './services/dashboard.service';
import { TranslationService } from '../../core/i18n/translation.service';

const tsMock = {
  translateInstant: vi.fn((key: string) => key),
  currentLang: 'es',
  lang$: of('es'),
};

const mockMetrics: DashboardMetrics = {
  total_releases: 10,
  valid_releases: 8,
  invalid_releases: 1,
  pending_releases: 1,
  total_verifications: 20,
  pass_rate: 80,
  temporal_data: [],
  top_failed_rules: [],
};

const mockReleases: RecentRelease[] = [
  { id: 'r1', created_at: '2025-01-01T00:00:00Z', verdict: 'VALID' },
];

describe('DashboardComponent', () => {
  let component: DashboardComponent;
  let svcMock: { getMetrics: ReturnType<typeof vi.fn>; getRecentReleases: ReturnType<typeof vi.fn> };

  beforeEach(() => {
    svcMock = {
      getMetrics: vi.fn().mockReturnValue(of(mockMetrics)),
      getRecentReleases: vi.fn().mockReturnValue(of(mockReleases)),
    };

    TestBed.configureTestingModule({
      schemas: [NO_ERRORS_SCHEMA],
      providers: [
        provideRouter([]),
        { provide: DashboardService, useValue: svcMock },
        { provide: TranslationService, useValue: tsMock },
      ],
    });

    const fixture = TestBed.createComponent(DashboardComponent);
    component = fixture.componentInstance;
  });

  describe('passRateClass', () => {
    it('should return rate--valid for >= 80', () => {
      expect(component.passRateClass(80)).toBe('rate--valid');
      expect(component.passRateClass(100)).toBe('rate--valid');
    });

    it('should return rate--warning for 50-79', () => {
      expect(component.passRateClass(50)).toBe('rate--warning');
      expect(component.passRateClass(79)).toBe('rate--warning');
    });

    it('should return rate--invalid for < 50', () => {
      expect(component.passRateClass(49)).toBe('rate--invalid');
      expect(component.passRateClass(0)).toBe('rate--invalid');
    });
  });

  describe('ngOnInit', () => {
    it('should load metrics and set data', () => {
      component.ngOnInit();
      expect(svcMock.getMetrics).toHaveBeenCalled();
      expect(component.metrics()).toEqual(mockMetrics);
      expect(component.metricsLoading()).toBe(false);
    });

    it('should load recent releases', () => {
      component.ngOnInit();
      expect(svcMock.getRecentReleases).toHaveBeenCalled();
      expect(component.recentReleases()).toEqual(mockReleases);
      expect(component.releasesLoading()).toBe(false);
    });

    it('should set metrics error on failure', () => {
      svcMock.getMetrics.mockReturnValue(throwError(() => new Error('fail')));
      component.ngOnInit();
      expect(component.metricsError()).toBe('system.error.loading_metrics');
    });

    it('should set releases error on failure', () => {
      svcMock.getRecentReleases.mockReturnValue(throwError(() => new Error('fail')));
      component.ngOnInit();
      expect(component.releasesError()).toBe('releases.loading_error');
    });
  });
});
