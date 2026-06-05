import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ActivatedRoute } from '@angular/router';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { ReleaseDetailComponent } from './release-detail.component';
import { TranslationService } from '../../../core/i18n/translation.service';

const tsMock = {
  translateInstant: vi.fn((key: string) => key),
  currentLang: 'es',
  lang$: of('es'),
};

const routeMock = {
  paramMap: of({ get: (key: string) => key === 'id' ? 'release-abc' : null }),
};

const mockRelease = {
  id: 'release-abc', name: 'v1.0.0', version: '1.0.0', description: '', status: 'valida',
  project_id: 'proj-1', profile_id: 'prof-1', created_by: 'u1', created_at: '2025-01-01T00:00:00Z', updated_at: '2025-01-01T00:00:00Z',
};
const mockResult = {
  id: 'res-1', release_id: 'release-abc', verdict: 'VALID',
  rule_results: [], summary: { VALID: 5, INVALID: 1 }, duration_ms: 100, executed_at: '2025-01-01T00:00:00Z',
};

describe('ReleaseDetailComponent', () => {
  let component: ReleaseDetailComponent;
  let httpCtrl: HttpTestingController;

  beforeEach(() => {
    vi.clearAllMocks();
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TranslationService, useValue: tsMock },
        { provide: ActivatedRoute, useValue: routeMock },
      ],
    });

    const fixture = TestBed.createComponent(ReleaseDetailComponent);
    component = fixture.componentInstance;
    httpCtrl = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpCtrl.verify());

  describe('ngOnInit', () => {
    it('should load release, artifacts, and results', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/releases/release-abc').flush(mockRelease);
      httpCtrl.expectOne('/api/v1/releases/release-abc/artifacts').flush([]);
      httpCtrl.expectOne('/api/v1/releases/release-abc/results').flush([mockResult]);
      expect(component.release()).toEqual(mockRelease);
      expect(component.latestResult()).toEqual(mockResult);
      expect(component.loading()).toBe(false);
    });

    it('should handle results load gracefully on error', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/releases/release-abc').flush(mockRelease);
      httpCtrl.expectOne('/api/v1/releases/release-abc/artifacts').flush([]);
      httpCtrl.expectOne('/api/v1/releases/release-abc/results').flush('', { status: 500, statusText: 'Error' });
      expect(component.verificationHistory()).toEqual([]);
    });
  });

  describe('toggleEvidence', () => {
    it('should set expandedRule to index', () => {
      component.toggleEvidence(2);
      expect(component.expandedRule()).toBe(2);
    });

    it('should collapse if same index clicked again', () => {
      component.toggleEvidence(2);
      component.toggleEvidence(2);
      expect(component.expandedRule()).toBeNull();
    });

    it('should switch to different index', () => {
      component.toggleEvidence(0);
      component.toggleEvidence(1);
      expect(component.expandedRule()).toBe(1);
    });
  });

  describe('verdictBannerClass', () => {
    it('should return valid banner for VALID verdict', () => {
      component.latestResult.set({ ...mockResult, verdict: 'VALID' });
      const cls = component.verdictBannerClass();
      expect(cls['verdict-banner-valid']).toBe(true);
      expect(cls['verdict-banner-invalid']).toBe(false);
    });

    it('should return warning for WITH_WARNINGS', () => {
      component.latestResult.set({ ...mockResult, verdict: 'WITH_WARNINGS' });
      expect(component.verdictBannerClass()['verdict-banner-warning']).toBe(true);
    });

    it('should return invalid for INVALID', () => {
      component.latestResult.set({ ...mockResult, verdict: 'INVALID' });
      expect(component.verdictBannerClass()['verdict-banner-invalid']).toBe(true);
    });

    it('should return unevaluated when no result', () => {
      component.latestResult.set(null);
      expect(component.verdictBannerClass()['verdict-banner-unevaluated']).toBe(true);
    });
  });

  describe('verdictIcon', () => {
    it('should return checkmark for VALID', () => {
      component.latestResult.set({ ...mockResult, verdict: 'VALID' });
      expect(component.verdictIcon()).toBe('✓');
    });

    it('should return warning for WITH_WARNINGS', () => {
      component.latestResult.set({ ...mockResult, verdict: 'WITH_WARNINGS' });
      expect(component.verdictIcon()).toBe('⚠');
    });

    it('should return X for INVALID', () => {
      component.latestResult.set({ ...mockResult, verdict: 'INVALID' });
      expect(component.verdictIcon()).toBe('✕');
    });

    it('should return dash for null verdict', () => {
      component.latestResult.set(null);
      expect(component.verdictIcon()).toBe('—');
    });
  });

  describe('verdictLabel', () => {
    it('should return VALID for VALID', () => {
      component.latestResult.set({ ...mockResult, verdict: 'VALID' });
      expect(component.verdictLabel()).toBe('VALID');
    });

    it('should return NOT_EVALUATED for null', () => {
      component.latestResult.set(null);
      expect(component.verdictLabel()).toBe('NOT_EVALUATED');
    });
  });

  describe('ruleResultClass', () => {
    it('should return result-valid for VALID', () => {
      expect(component.ruleResultClass('VALID')['result-valid']).toBe(true);
    });

    it('should return result-valid for PASSED', () => {
      expect(component.ruleResultClass('PASSED')['result-valid']).toBe(true);
    });

    it('should return result-invalid for FAILED', () => {
      expect(component.ruleResultClass('FAILED')['result-invalid']).toBe(true);
    });

    it('should return result-warning for WITH_WARNINGS', () => {
      expect(component.ruleResultClass('WITH_WARNINGS')['result-warning']).toBe(true);
    });

    it('should return result-unevaluated for empty string', () => {
      expect(component.ruleResultClass('')['result-unevaluated']).toBe(true);
    });
  });

  describe('summaryItems', () => {
    it('should sort entries by count descending', () => {
      const summary = { VALID: 5, INVALID: 1, WARNING: 3 };
      const result = component.summaryItems(summary);
      expect(result[0][0]).toBe('VALID');
      expect(result[0][1]).toBe(5);
      expect(result[1][0]).toBe('WARNING');
      expect(result[2][0]).toBe('INVALID');
    });

    it('should return empty array for empty summary', () => {
      expect(component.summaryItems({})).toEqual([]);
    });
  });

  describe('statusBadgeClass', () => {
    it('should return status-valida for valida', () => {
      component.release.set({ ...mockRelease, status: 'valida' });
      expect(component.statusBadgeClass()['status-valida']).toBe(true);
    });

    it('should return status-borrador for borrador', () => {
      component.release.set({ ...mockRelease, status: 'borrador' });
      expect(component.statusBadgeClass()['status-borrador']).toBe(true);
    });
  });
});
