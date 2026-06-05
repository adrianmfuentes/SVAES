import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ActivatedRoute, provideRouter } from '@angular/router';
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
  let fixture: ComponentFixture<ReleaseDetailComponent>;
  let httpCtrl: HttpTestingController;

  beforeEach(() => {
    TestBed.resetTestingModule();
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

    fixture = TestBed.createComponent(ReleaseDetailComponent);
    component = fixture.componentInstance;
    httpCtrl = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpCtrl?.verify();
    TestBed.resetTestingModule();
  });

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

  describe('verdictBadgeClass', () => {
    it('should return verdict-badge-valid for VALID', () => {
      component.latestResult.set({ ...mockResult, verdict: 'VALID' });
      expect(component.verdictBadgeClass()['verdict-badge-valid']).toBe(true);
    });

    it('should return verdict-badge-warning for WITH_WARNINGS', () => {
      component.latestResult.set({ ...mockResult, verdict: 'WITH_WARNINGS' });
      expect(component.verdictBadgeClass()['verdict-badge-warning']).toBe(true);
    });

    it('should return verdict-badge-invalid for INVALID', () => {
      component.latestResult.set({ ...mockResult, verdict: 'INVALID' });
      expect(component.verdictBadgeClass()['verdict-badge-invalid']).toBe(true);
    });

    it('should return verdict-badge-unevaluated for null result', () => {
      component.latestResult.set(null);
      expect(component.verdictBadgeClass()['verdict-badge-unevaluated']).toBe(true);
    });
  });

  describe('verdictBadgeMap / verdictLabelMap', () => {
    it('verdictBadgeMap should delegate to ruleResultClass', () => {
      const cls = component.verdictBadgeMap('VALID');
      expect(cls['result-valid']).toBe(true);
    });

    it('verdictLabelMap should return VALID for VALID', () => {
      expect(component.verdictLabelMap('VALID')).toBe('VALID');
    });

    it('verdictLabelMap should return WITH_WARNINGS for VALID_WITH_WARNINGS', () => {
      expect(component.verdictLabelMap('VALID_WITH_WARNINGS')).toBe('WITH_WARNINGS');
    });

    it('verdictLabelMap should return NOT_EVALUATED for unknown', () => {
      expect(component.verdictLabelMap('')).toBe('NOT_EVALUATED');
    });
  });

  describe('launchVerification', () => {
    it('should POST verify and reload on success', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/releases/release-abc').flush(mockRelease);
      httpCtrl.expectOne('/api/v1/releases/release-abc/artifacts').flush([]);
      httpCtrl.expectOne('/api/v1/releases/release-abc/results').flush([mockResult]);

      component.launchVerification();
      expect(component.verifying()).toBe(true);
      httpCtrl.expectOne('/api/v1/releases/release-abc/verify').flush({ task_id: 't1', status: 'pending' });
      expect(component.verifying()).toBe(false);
      expect(component.loading()).toBe(true);

      httpCtrl.expectOne('/api/v1/releases/release-abc').flush(mockRelease);
      httpCtrl.expectOne('/api/v1/releases/release-abc/artifacts').flush([]);
      httpCtrl.expectOne('/api/v1/releases/release-abc/results').flush([mockResult]);
    });

    it('should set error and stop verifying on failure', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/releases/release-abc').flush(mockRelease);
      httpCtrl.expectOne('/api/v1/releases/release-abc/artifacts').flush([]);
      httpCtrl.expectOne('/api/v1/releases/release-abc/results').flush([]);

      component.launchVerification();
      httpCtrl.expectOne('/api/v1/releases/release-abc/verify').flush(
        { detail: 'Verification failed' },
        { status: 409, statusText: 'Conflict' }
      );
      expect(component.verifying()).toBe(false);
    });

    it('should not launch if already verifying', () => {
      component.verifying.set(true);
      component.launchVerification();
      httpCtrl.expectNone('/api/v1/releases/release-abc/verify');
    });
  });

  describe('loadResultDetail', () => {
    it('should fetch and set a specific result', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/releases/release-abc').flush(mockRelease);
      httpCtrl.expectOne('/api/v1/releases/release-abc/artifacts').flush([]);
      httpCtrl.expectOne('/api/v1/releases/release-abc/results').flush([mockResult]);

      const detailResult = { ...mockResult, id: 'res-2', verdict: 'INVALID' };
      component.loadResultDetail('res-2');
      httpCtrl.expectOne('/api/v1/releases/release-abc/results/res-2').flush(detailResult);
      expect(component.latestResult()?.id).toBe('res-2');
    });

    it('should not update on error', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/releases/release-abc').flush(mockRelease);
      httpCtrl.expectOne('/api/v1/releases/release-abc/artifacts').flush([]);
      httpCtrl.expectOne('/api/v1/releases/release-abc/results').flush([mockResult]);

      component.loadResultDetail('missing-res');
      httpCtrl.expectOne('/api/v1/releases/release-abc/results/missing-res').flush(
        {},
        { status: 404, statusText: 'Not Found' }
      );
      expect(component.latestResult()?.id).toBe('res-1');
    });
  });

  describe('ngOnInit with release load error', () => {
    it('should handle release error gracefully', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/releases/release-abc').flush(
        { detail: 'Not found' }, { status: 404, statusText: 'Not Found' }
      );
      httpCtrl.expectOne('/api/v1/releases/release-abc/artifacts').flush([]);
      httpCtrl.expectOne('/api/v1/releases/release-abc/results').flush([]);
      expect(component.release()).toBeNull();
      expect(component.loading()).toBe(false);
    });
  });

  describe('template rendering', () => {
    const mockRuleResult = { rule_id: 'r1', rule_name: 'Rule', verdict: 'VALID', evidence: '' as string, message: '', result: 'PASSED' };
    const fullResult = { ...mockResult, verdict: 'VALID', rule_results: [mockRuleResult], summary: { VALID: 1 } };
    const renderTemplate = () => {
      fixture.detectChanges();
      const requests = httpCtrl.match(() => true);
      if (requests.length > 0) {
        requests[0]?.flush(mockRelease);
        requests[1]?.flush([]);
        requests[2]?.flush([]);
      }
    };

    it('should render loading skeleton', () => {
      component.loading.set(true);
      renderTemplate();
    });

    it('should render error state', () => {
      component.loading.set(false);
      component.error.set('Release not found');
      renderTemplate();
    });

    it('should render loaded release with VALID result', () => {
      component.loading.set(false);
      component.release.set(mockRelease);
      component.latestResult.set(fullResult);
      component.artifacts.set([]);
      component.verificationHistory.set([fullResult]);
      component.verifying.set(false);
      renderTemplate();
    });

    it('should render loaded release with no result (unevaluated)', () => {
      component.loading.set(false);
      component.release.set(mockRelease);
      component.latestResult.set(null);
      component.artifacts.set([{ id: 'a1', connector_implementation: 'JIRA', artifact_type: 'TAREA', external_ref: 'REF-1', release_id: 'r1', connector_instance_id: 'ci1' }]);
      renderTemplate();
    });

    it('should render verifying state', () => {
      component.loading.set(false);
      component.release.set(mockRelease);
      component.latestResult.set(null);
      component.verifying.set(true);
      renderTemplate();
    });

    it('should render history with expanded rule', () => {
      component.loading.set(false);
      component.release.set(mockRelease);
      component.latestResult.set({ ...fullResult, verdict: 'INVALID' });
      component.expandedRule.set(0);
      renderTemplate();
    });

    it('should render WITH_WARNINGS verdict', () => {
      component.loading.set(false);
      component.release.set(mockRelease);
      component.latestResult.set({ ...fullResult, verdict: 'WITH_WARNINGS' });
      renderTemplate();
    });
  });
});

describe('ReleaseDetailComponent — no route id', () => {
  it('should set error and stop loading when no id param', () => {
    const routeNoId = { paramMap: of({ get: (_key: string) => null }) };
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TranslationService, useValue: tsMock },
        { provide: ActivatedRoute, useValue: routeNoId },
      ],
    });
    const fixture2 = TestBed.createComponent(ReleaseDetailComponent);
    const comp2 = fixture2.componentInstance;
    const httpCtrl2 = TestBed.inject(HttpTestingController);
    comp2.ngOnInit();
    expect(comp2.loading()).toBe(false);
    expect(comp2.error()).toBeTruthy();
    httpCtrl2.verify();
  });
});
