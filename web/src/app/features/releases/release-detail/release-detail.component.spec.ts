import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { ReleaseDetailComponent } from './release-detail.component';
import { TranslationService } from '../../../core/i18n/translation.service';
import { ToastService } from '../../../core/services/toast.service';

const tsMock = {
  translateInstant: vi.fn((key: string) => {
    const translations: Record<string, string> = {
      'verdict.VALID': 'VALID',
      'verdict.VALID_WITH_WARNINGS': 'WITH_WARNINGS',
      'verdict.INVALID': 'INVALID',
      'verdict.NOT_EVALUATED': 'NOT_EVALUATED',
      'verdict.WITH_WARNINGS': 'WITH_WARNINGS',
      'verdict.WARNING': 'WARNING',
      'verdict.FAILED': 'FAILED',
      'verdict.PASSED': 'PASSED',
      'verdict.ERROR': 'ERROR',
      'verdict.SKIPPED': 'SKIPPED',
      'rule_result.VALID': 'PASSED',
      'rule_result.WITH_WARNINGS': 'WITH_WARNINGS',
      'rule_result.INVALID': 'FAILED',
      'rule_result.NOT_EVALUATED': 'NOT_EVALUATED',
      'rule_result.WARNING': 'WARNING',
      'rule_result.FAILED': 'FAILED',
      'rule_result.PASSED': 'PASSED',
      'rule_result.ERROR': 'ERROR',
      'rule_result.SKIPPED': 'SKIPPED',
      'admin.error_loading_access_requests': 'Error loading access requests',
    };
    return translations[key] ?? key;
  }),
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

  describe('summaryTotal', () => {
    it('should return total value from summary object', () => {
      expect(component.summaryTotal({ TOTAL: 5, OK: 3 })).toBe(5);
    });

    it('should return null for string summary', () => {
      expect(component.summaryTotal('not an object')).toBeNull();
    });

    it('should return null when TOTAL key is missing', () => {
      expect(component.summaryTotal({ OK: 3 })).toBeNull();
    });
  });

  describe('summaryStatusItems', () => {
    it('should filter out TOTAL key and sort by count', () => {
      const summary = { TOTAL: 5, OK: 3, ERROR: 1, WARNING: 2 };
      const result = component.summaryStatusItems(summary);
      expect(result).toEqual([['OK', 3], ['WARNING', 2], ['ERROR', 1]]);
    });

    it('should return empty array for string summary', () => {
      expect(component.summaryStatusItems('not an object')).toEqual([]);
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
    afterEach(() => {
      vi.useRealTimers();
      vi.restoreAllMocks();
    });

    it('should POST verify and reload on success', () => {
      vi.useFakeTimers();

      const mockNotification = { permission: 'default', requestPermission: vi.fn().mockResolvedValue('granted') };
      vi.stubGlobal('Notification', mockNotification);

      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/releases/release-abc').flush(mockRelease);
      httpCtrl.expectOne('/api/v1/releases/release-abc/artifacts').flush([]);
      httpCtrl.expectOne('/api/v1/releases/release-abc/results').flush([mockResult]);

      component.launchVerification();
      expect(component.verifying()).toBe(true);

      httpCtrl.expectOne('/api/v1/releases/release-abc/verify').flush({ task_id: 't1', status: 'pending' });
      httpCtrl.expectOne('/api/v1/tasks/t1').flush({});
      httpCtrl.expectOne('/api/v1/releases/release-abc').flush({ ...mockRelease, status: 'valida' });

      httpCtrl.expectOne('/api/v1/releases/release-abc/artifacts').flush([]);
      httpCtrl.expectOne('/api/v1/releases/release-abc/results').flush([mockResult]);
      httpCtrl.expectOne('/api/v1/releases/release-abc').flush(mockRelease);

      expect(component.verifying()).toBe(false);

      vi.useRealTimers();
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

  describe('deleteArtifact', () => {
    it('should set artifactToDelete signal', () => {
      component.deleteArtifact('art-1');
      expect(component.artifactToDelete()).toBe('art-1');
    });
  });

  describe('confirmDeleteArtifact (no artifactId)', () => {
    it('should return early when no artifactId', () => {
      component.artifactToDelete.set(null);
      component.confirmDeleteArtifact();
      expect(component.artifactToDelete()).toBeNull();
      httpCtrl.expectNone('/api/v1/releases/release-abc/artifacts/');
    });
  });

  describe('openImportModal', () => {
    it('should reset all import-related signals', () => {
      component.importConnector.set({ id: 'c1', name: 'JIRA', connector_type: 'GESTOR_TAREAS', connector_implementation: 'JIRA', status: 'active', created_at: '' });
      component.importArtifactType.set('CODIGO');
      component.importExternalRef.set('REF-1');
      component.importDescription.set('desc');
      component.importError.set('err');
      component.browseItems.set([{ ref: 'R1', title: 'T1', subtitle: '' }]);
      component.browseError.set('browse err');
      component.browseSearch.set('query');
      component.browseManual.set(true);
      component.showImportModal.set(false);

      component.openImportModal();

      expect(component.importConnector()).toBeNull();
      expect(component.importArtifactType()).toBe('TAREA');
      expect(component.importExternalRef()).toBe('');
      expect(component.importDescription()).toBe('');
      expect(component.importError()).toBeNull();
      expect(component.browseItems()).toEqual([]);
      expect(component.browseError()).toBeNull();
      expect(component.browseSearch()).toBe('');
      expect(component.browseManual()).toBe(false);
      expect(component.showImportModal()).toBe(true);
    });
  });

  describe('closeImportModal', () => {
    it('should set showImportModal false', () => {
      component.showImportModal.set(true);
      component.closeImportModal();
      expect(component.showImportModal()).toBe(false);
    });
  });

  describe('dismissVerifyNotice', () => {
    it('should set showVerifyNotice false', () => {
      component.showVerifyNotice.set(true);
      component.dismissVerifyNotice();
      expect(component.showVerifyNotice()).toBe(false);
    });
  });

  describe('onConnectorSelect', () => {
    const connJira = { id: 'c1', name: 'JIRA', connector_type: 'GESTOR_TAREAS', connector_implementation: 'JIRA', status: 'active', created_at: '2025-01-01' };
    const connGitHub = { id: 'c2', name: 'GitHub', connector_type: 'REPO_CODIGO', connector_implementation: 'GITHUB', status: 'active', created_at: '2025-01-01' };
    const connDoc = { id: 'c3', name: 'SharePoint', connector_type: 'SISTEMA_DOCUMENTAL', connector_implementation: 'SP', status: 'active', created_at: '2025-01-01' };
    const connUnknown = { id: 'c4', name: 'Custom', connector_type: 'UNKNOWN_TYPE', connector_implementation: 'CUSTOM', status: 'active', created_at: '2025-01-01' };

    beforeEach(() => {
      (component as any).orgId = 'org-1';
      component.orgConnectors.set([connJira, connGitHub, connDoc, connUnknown]);
    });

    it('should set importConnector and auto-set artifactType from CONNECTOR_TYPE_TO_ARTIFACT', () => {
      component.onConnectorSelect('c3');
      httpCtrl.expectOne('/api/v1/organizations/org-1/connectors/c3/browse').flush([]);
      expect(component.importConnector()?.id).toBe('c3');
      expect(component.importArtifactType()).toBe('DOCUMENTO');
      expect(component.importExternalRef()).toBe('');
      expect(component.importDescription()).toBe('');
    });

    it('should set type to TAREA for GESTOR_TAREAS connector', () => {
      component.onConnectorSelect('c1');
      httpCtrl.expectOne('/api/v1/organizations/org-1/connectors/c1/browse').flush([]);
      expect(component.importConnector()?.id).toBe('c1');
      expect(component.importArtifactType()).toBe('TAREA');
    });

    it('should set type to CODIGO for REPO_CODIGO connector', () => {
      component.onConnectorSelect('c2');
      httpCtrl.expectOne('/api/v1/organizations/org-1/connectors/c2/browse').flush([]);
      expect(component.importConnector()?.id).toBe('c2');
      expect(component.importArtifactType()).toBe('CODIGO');
    });

    it('should default to TAREA for unknown connector type', () => {
      component.onConnectorSelect('c4');
      httpCtrl.expectOne('/api/v1/organizations/org-1/connectors/c4/browse').flush([]);
      expect(component.importConnector()?.id).toBe('c4');
      expect(component.importArtifactType()).toBe('TAREA');
    });

    it('should set importConnector to null for non-existent connector ID', () => {
      component.importConnector.set(connJira);
      component.onConnectorSelect('non-existent');
      expect(component.importConnector()).toBeNull();
      expect(component.importExternalRef()).toBe('');
      expect(component.importDescription()).toBe('');
    });
  });

  describe('selectBrowseItem', () => {
    it('should set importExternalRef and importDescription', () => {
      const item = { ref: 'REF-123', title: 'Test Item', subtitle: 'SUB' };
      component.selectBrowseItem(item);
      expect(component.importExternalRef()).toBe('REF-123');
      expect(component.importDescription()).toBe('Test Item');
    });
  });

  describe('clearBrowseSelection', () => {
    it('should clear ref and description', () => {
      component.importExternalRef.set('REF-1');
      component.importDescription.set('desc');
      component.clearBrowseSelection();
      expect(component.importExternalRef()).toBe('');
      expect(component.importDescription()).toBe('');
    });
  });

  describe('isSummaryString', () => {
    it('should return true for string', () => {
      expect(component.isSummaryString('hello')).toBe(true);
    });

    it('should return false for object', () => {
      expect(component.isSummaryString({ VALID: 1 })).toBe(false);
    });
  });

  describe('translateVerdict', () => {
    it('should call translateInstant with verdict. prefix', () => {
      expect(component.translateVerdict('VALID')).toBe('VALID');
      expect(component.translateVerdict('INVALID')).toBe('INVALID');
    });
  });

  describe('translateRuleResult', () => {
    it('should call translateInstant with rule_result. prefix', () => {
      expect(component.translateRuleResult('PASSED')).toBe('PASSED');
      expect(component.translateRuleResult('FAILED')).toBe('FAILED');
    });
  });

  describe('verdictLabelMap', () => {
    it('should return WARNING for WARNING verdict', () => {
      expect(component.verdictLabelMap('WARNING')).toBe('WARNING');
    });

    it('should return FAILED for FAILED verdict', () => {
      expect(component.verdictLabelMap('FAILED')).toBe('FAILED');
    });
  });

  describe('ruleResultClass', () => {
    it('should return result-valid for SUCCESS', () => {
      expect(component.ruleResultClass('SUCCESS')['result-valid']).toBe(true);
    });

    it('should return result-valid for OK', () => {
      expect(component.ruleResultClass('OK')['result-valid']).toBe(true);
    });

    it('should return result-warning for WARNING', () => {
      expect(component.ruleResultClass('WARNING')['result-warning']).toBe(true);
    });

    it('should return result-invalid for ERROR', () => {
      expect(component.ruleResultClass('ERROR')['result-invalid']).toBe(true);
    });

    it('should return result-unevaluated for SKIPPED', () => {
      expect(component.ruleResultClass('SKIPPED')['result-unevaluated']).toBe(true);
    });

    it('should return result-unevaluated for NOT_EVALUATED', () => {
      expect(component.ruleResultClass('NOT_EVALUATED')['result-unevaluated']).toBe(true);
    });
  });

  describe('statusBadgeClass', () => {
    it('should return status-pendiente for pendiente', () => {
      component.release.set({ ...mockRelease, status: 'pendiente' });
      expect(component.statusBadgeClass()['status-pendiente']).toBe(true);
    });

    it('should return status-en_verificacion for en_verificacion', () => {
      component.release.set({ ...mockRelease, status: 'en_verificacion' });
      expect(component.statusBadgeClass()['status-en_verificacion']).toBe(true);
    });

    it('should return status-con_advertencias for con_advertencias', () => {
      component.release.set({ ...mockRelease, status: 'con_advertencias' });
      expect(component.statusBadgeClass()['status-con_advertencias']).toBe(true);
    });

    it('should return status-no_valida for no_valida', () => {
      component.release.set({ ...mockRelease, status: 'no_valida' });
      expect(component.statusBadgeClass()['status-no_valida']).toBe(true);
    });

    it('should return status-archivada for archivada', () => {
      component.release.set({ ...mockRelease, status: 'archivada' });
      expect(component.statusBadgeClass()['status-archivada']).toBe(true);
    });
  });

  describe('expandedEvidence', () => {
    it('should return null when no result', () => {
      component.latestResult.set(null);
      component.expandedRule.set(0);
      expect(component.expandedEvidence()).toBeNull();
    });

    it('should return evidence text when expanded', () => {
      component.latestResult.set({
        ...mockResult,
        rule_results: [{ rule_id: 'r1', evidence: 'some evidence' }],
      });
      component.expandedRule.set(0);
      expect(component.expandedEvidence()).toBe('some evidence');
    });

    it('should return message when no evidence', () => {
      component.latestResult.set({
        ...mockResult,
        rule_results: [{ rule_id: 'r1', message: 'only message', evidence: undefined }],
      });
      component.expandedRule.set(0);
      expect(component.expandedEvidence()).toBe('only message');
    });

    it('should return null when index out of bounds', () => {
      component.latestResult.set({
        ...mockResult,
        rule_results: [{ rule_id: 'r1', evidence: 'ev' }],
      });
      component.expandedRule.set(5);
      expect(component.expandedEvidence()).toBeNull();
    });
  });

  describe('summaryItems', () => {
    it('should return empty array for string summary', () => {
      expect(component.summaryItems('not an object')).toEqual([]);
    });

    it('should return empty array for null', () => {
      expect(component.summaryItems(null as any)).toEqual([]);
    });
  });

  describe('onBrowseSearchInput', () => {
    it('should set browseSearch and call subject.next', () => {
      component.browseSearch.set('');
      component.onBrowseSearchInput('test query');
      expect(component.browseSearch()).toBe('test query');
    });
  });

  describe('filteredBrowseItems', () => {
    const items = [
      { ref: 'R1', title: 'Alpha', subtitle: '' },
      { ref: 'R2', title: 'Beta', subtitle: '' },
      { ref: 'R3', title: 'Alpha Beta', subtitle: '' },
    ];

    it('should filter items by search query', () => {
      component.browseItems.set(items);
      component.browseSearch.set('alpha');
      const result = component.filteredBrowseItems();
      expect(result.length).toBe(2);
      expect(result[0].ref).toBe('R1');
      expect(result[1].ref).toBe('R3');
    });

    it('should return all items when query empty', () => {
      component.browseItems.set(items);
      component.browseSearch.set('');
      const result = component.filteredBrowseItems();
      expect(result.length).toBe(3);
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

describe('ReleaseDetailComponent — with ToastService', () => {
  let component: ReleaseDetailComponent;
  let fixture: ComponentFixture<ReleaseDetailComponent>;
  let httpCtrl: HttpTestingController;

  const toastMock = { error: vi.fn(), info: vi.fn(), success: vi.fn() };

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
        { provide: ToastService, useValue: toastMock },
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

  describe('cancelVerification', () => {
    afterEach(() => {
      vi.useRealTimers();
      vi.restoreAllMocks();
    });

    it('should POST cancel, call stopPolling, and set verifying to false on success', () => {
      vi.useFakeTimers();

      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/releases/release-abc').flush(mockRelease);
      httpCtrl.expectOne('/api/v1/releases/release-abc/artifacts').flush([]);
      httpCtrl.expectOne('/api/v1/releases/release-abc/results').flush([]);

      component.verifying.set(true);
      component.showVerifyNotice.set(true);

      const stopPollingSpy = vi.spyOn(component as any, 'stopPolling');
      const reloadDataSpy = vi.spyOn(component as any, 'reloadData').mockImplementation(() => {});

      component.cancelVerification();
      httpCtrl.expectOne('/api/v1/releases/release-abc/cancel').flush({ cancelled: true });

      expect(stopPollingSpy).toHaveBeenCalled();
      expect(component.verifying()).toBe(false);
      expect(component.showVerifyNotice()).toBe(false);
      expect(toastMock.info).toHaveBeenCalled();

      vi.useRealTimers();
    });

    it('should call toast.error on cancel error', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/releases/release-abc').flush(mockRelease);
      httpCtrl.expectOne('/api/v1/releases/release-abc/artifacts').flush([]);
      httpCtrl.expectOne('/api/v1/releases/release-abc/results').flush([]);

      component.cancelVerification();
      httpCtrl.expectOne('/api/v1/releases/release-abc/cancel').flush(
        { detail: 'Error' },
        { status: 500, statusText: 'Server Error' }
      );

      expect(toastMock.error).toHaveBeenCalled();
    });
  });

  describe('confirmDeleteArtifact', () => {
    it('should DELETE artifact and update artifacts list on success', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/releases/release-abc').flush(mockRelease);
      httpCtrl.expectOne('/api/v1/releases/release-abc/artifacts').flush([]);
      httpCtrl.expectOne('/api/v1/releases/release-abc/results').flush([]);

      const art1 = { id: 'art-1', release_id: 'release-abc', connector_instance_id: 'ci1', connector_implementation: 'JIRA', artifact_type: 'TAREA', external_ref: 'REF-1' };
      const art2 = { id: 'art-2', release_id: 'release-abc', connector_instance_id: 'ci2', connector_implementation: 'GIT', artifact_type: 'CODIGO', external_ref: 'REF-2' };
      component.artifacts.set([art1, art2]);
      component.artifactToDelete.set('art-1');

      component.confirmDeleteArtifact();
      httpCtrl.expectOne('/api/v1/releases/release-abc/artifacts/art-1').flush({});

      expect(component.artifacts().length).toBe(1);
      expect(component.artifacts()[0].id).toBe('art-2');
      expect(component.artifactToDelete()).toBeNull();
      expect(toastMock.success).toHaveBeenCalled();
    });

    it('should call toast.error on delete error', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/releases/release-abc').flush(mockRelease);
      httpCtrl.expectOne('/api/v1/releases/release-abc/artifacts').flush([]);
      httpCtrl.expectOne('/api/v1/releases/release-abc/results').flush([]);

      const art1 = { id: 'art-1', release_id: 'release-abc', connector_instance_id: 'ci1', connector_implementation: 'JIRA', artifact_type: 'TAREA', external_ref: 'REF-1' };
      component.artifacts.set([art1]);
      component.artifactToDelete.set('art-1');

      component.confirmDeleteArtifact();
      httpCtrl.expectOne('/api/v1/releases/release-abc/artifacts/art-1').flush(
        { detail: 'Not found' },
        { status: 404, statusText: 'Not Found' }
      );

      expect(component.artifacts().length).toBe(1);
      expect(toastMock.error).toHaveBeenCalled();
    });
  });
});
