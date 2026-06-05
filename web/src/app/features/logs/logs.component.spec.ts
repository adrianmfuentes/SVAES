import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { of } from 'rxjs';
import { LogsComponent } from './logs.component';
import { TranslationService } from '../../core/i18n/translation.service';

const tsMock = {
  translateInstant: vi.fn((key: string) => key),
  currentLang: 'es',
  lang$: of('es'),
};

const makeLogs = (n: number) =>
  Array.from({ length: n }, (_, i) => ({
    id: `log${i}`,
    timestamp: '2025-01-01T00:00:00Z',
    action: 'LOGIN',
    category: 'auth',
    actor_id: `user-id-${i}`,
    actor_role: 'OPERATOR',
    result: 'success' as const,
    ip_address: `192.168.1.${i}`,
  }));

describe('LogsComponent', () => {
  let component: LogsComponent;
  let httpCtrl: HttpTestingController;

  beforeEach(() => {
    vi.clearAllMocks();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TranslationService, useValue: tsMock },
      ],
    });

    const fixture = TestBed.createComponent(LogsComponent);
    component = fixture.componentInstance;
    httpCtrl = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpCtrl.verify());

  describe('ngOnInit / HTTP', () => {
    it('should load logs on init', () => {
      const logs = makeLogs(5);
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/audit/logs?limit=500').flush({ total: 5, logs });
      expect(component.allLogs()).toHaveLength(5);
      expect(component.filtered()).toHaveLength(5);
      expect(component.loading()).toBe(false);
      expect(component.notAvailable()).toBe(false);
    });

    it('should set notAvailable on HTTP error', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/audit/logs?limit=500').flush('', { status: 403, statusText: 'Forbidden' });
      expect(component.notAvailable()).toBe(true);
      expect(component.loading()).toBe(false);
    });
  });

  describe('applyFilters', () => {
    beforeEach(() => {
      const logs = [
        ...makeLogs(2).map(l => ({ ...l, category: 'auth', result: 'success' as const })),
        ...makeLogs(2).map(l => ({ ...l, id: `admin-${l.id}`, category: 'admin', result: 'failure' as const })),
      ];
      component.allLogs.set(logs);
      component.filtered.set(logs);
    });

    it('should filter by category', () => {
      component.filterCategory = 'admin';
      component.applyFilters();
      expect(component.filtered().every(l => l.category === 'admin')).toBe(true);
    });

    it('should filter by result', () => {
      component.filterResult = 'failure';
      component.applyFilters();
      expect(component.filtered().every(l => l.result === 'failure')).toBe(true);
    });

    it('should combine category and result filters', () => {
      component.filterCategory = 'auth';
      component.filterResult = 'failure';
      component.applyFilters();
      expect(component.filtered()).toHaveLength(0);
    });

    it('should reset page to 0 on filter', () => {
      component.page.set(5);
      component.applyFilters();
      expect(component.page()).toBe(0);
    });
  });

  describe('resetFilters', () => {
    it('should clear filterCategory and filterResult', () => {
      const logs = makeLogs(3);
      component.allLogs.set(logs);
      component.filtered.set(logs);
      component.filterCategory = 'admin';
      component.filterResult = 'failure';
      component.resetFilters();
      expect(component.filterCategory).toBe('');
      expect(component.filterResult).toBe('');
      expect(component.filtered()).toHaveLength(3);
    });
  });

  describe('pagination', () => {
    it('should paginate filtered results', () => {
      const logs = makeLogs(60);
      component.filtered.set(logs);
      expect(component.paginated()).toHaveLength(25);
      expect(component.totalPages()).toBe(3);
    });

    it('nextPage/prevPage should clamp', () => {
      component.filtered.set(makeLogs(50));
      expect(component.page()).toBe(0);
      component.prevPage();
      expect(component.page()).toBe(0);
      component.nextPage();
      expect(component.page()).toBe(1);
    });
  });

  describe('maskId', () => {
    it('should return placeholder for short ids', () => {
      expect(component.maskId('')).toBe('••••••••');
      expect(component.maskId('abc')).toBe('••••••••');
    });

    it('should truncate sha256 hashes', () => {
      const result = component.maskId('sha256:abcdefghijklmnopqrstuvwx');
      expect(result).toContain('sha256:');
      expect(result.endsWith('…')).toBe(true);
    });

    it('should mask middle of regular id', () => {
      const result = component.maskId('abcdef1234567890');
      expect(result).toContain('••••');
    });
  });

  describe('maskIp', () => {
    it('should mask last octets of IPv4', () => {
      expect(component.maskIp('192.168.1.100')).toBe('192.168.•••.•••'); // NOSONAR: intentional test data for IP masking logic
    });

    it('should truncate sha256 ips', () => {
      const result = component.maskIp('sha256:abcdefghijklmnopqr');
      expect(result.endsWith('…')).toBe(true);
    });

    it('should handle non-IPv4 format', () => {
      const result = component.maskIp('abcdef');
      expect(result).toBeTruthy();
    });
  });

  describe('resultLabel', () => {
    it('should call translateInstant for known results', () => {
      component.resultLabel('success');
      expect(tsMock.translateInstant).toHaveBeenCalledWith('logs.result_success');
      component.resultLabel('failure');
      expect(tsMock.translateInstant).toHaveBeenCalledWith('logs.result_failure');
      component.resultLabel('denied');
      expect(tsMock.translateInstant).toHaveBeenCalledWith('logs.result_denied');
    });

    it('should return unknown result as-is', () => {
      const result = component.resultLabel('other');
      expect(result).toBe('other');
    });
  });
});
