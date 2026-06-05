import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { of } from 'rxjs';
import { SystemComponent } from './system.component';
import { TranslationService } from '../../core/i18n/translation.service';
import { provideRouter } from '@angular/router';

const tsMock = {
  translateInstant: vi.fn((key: string) => key),
  currentLang: 'es',
  lang$: of('es'),
};

const healthOk = { version: '1.2.3', service: 'SVAES API' };
const mockOrg = { id: 'org-1', name: 'Test Org' };
const mockUser = { id: 'u1', role: 'OPERATOR', is_active: true };
const mockConnType = { type: 'REPO_CODIGO' };

describe('SystemComponent', () => {
  let component: SystemComponent;
  let httpCtrl: HttpTestingController;

  const flushAll = () => {
    httpCtrl.expectOne('/health').flush(healthOk);
    httpCtrl.expectOne('/api/v1/organizations').flush([mockOrg]);
    httpCtrl.expectOne('/api/v1/admin/users?limit=200').flush([mockUser]);
    httpCtrl.expectOne('/api/v1/connectors/types').flush([mockConnType]);
  };

  beforeEach(() => {
    vi.clearAllMocks();
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TranslationService, useValue: tsMock },
      ],
    });

    const fixture = TestBed.createComponent(SystemComponent);
    component = fixture.componentInstance;
    httpCtrl = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    component.ngOnDestroy();
    httpCtrl.verify();
  });

  describe('loadAll', () => {
    it('should load all system data', () => {
      component.loadAll();
      flushAll();
      expect(component.apiVersion()).toBe('1.2.3');
      expect(component.orgs()).toHaveLength(1);
      expect(component.users()).toHaveLength(1);
      expect(component.loading()).toBe(false);
      expect(component.services()).toHaveLength(4);
    });

    it('should still load when health endpoint fails', () => {
      component.loadAll();
      httpCtrl.expectOne('/health').flush('', { status: 503, statusText: 'Error' });
      httpCtrl.expectOne('/api/v1/organizations').flush([mockOrg]);
      httpCtrl.expectOne('/api/v1/admin/users?limit=200').flush([mockUser]);
      httpCtrl.expectOne('/api/v1/connectors/types').flush('', { status: 503, statusText: 'Error' });
      expect(component.loading()).toBe(false);
      expect(component.apiVersion()).toBeNull();
    });

    it('should reset secondsSince on load', () => {
      component.secondsSince.set(99);
      component.loadAll();
      expect(component.secondsSince()).toBe(0);
      flushAll();
    });
  });

  describe('executeReload', () => {
    beforeEach(() => {
      component.loadAll();
      flushAll();
    });

    it('should POST and set reloadResult on success', () => {
      component.executeReload();
      const req = httpCtrl.expectOne('/api/v1/admin/rules/reload');
      expect(req.request.method).toBe('POST');
      req.flush({ rules_loaded: 10, rules_failed: 0 });
      expect(component.reloadResult()).toMatchObject({ rules_loaded: 10 });
      expect(component.reloading()).toBe(false);
    });

    it('should set reloadError on failure', () => {
      component.executeReload();
      httpCtrl.expectOne('/api/v1/admin/rules/reload').flush(
        { detail: 'Engine unavailable' },
        { status: 503, statusText: 'Error' }
      );
      expect(component.reloadError()).toBe('Engine unavailable');
      expect(component.reloading()).toBe(false);
    });
  });

  describe('statusLabel', () => {
    it('should call translateInstant for up', () => {
      component.statusLabel('up');
      expect(tsMock.translateInstant).toHaveBeenCalledWith('system.status_healthy');
    });

    it('should call translateInstant for down', () => {
      component.statusLabel('down');
      expect(tsMock.translateInstant).toHaveBeenCalledWith('system.status_unhealthy');
    });

    it('should call translateInstant for unknown', () => {
      component.statusLabel('unknown');
      expect(tsMock.translateInstant).toHaveBeenCalledWith('system.status_unknown');
    });
  });

  describe('maskId', () => {
    it('should return placeholder for short ids', () => {
      expect(component.maskId('')).toBe('••••••••');
      expect(component.maskId('abc')).toBe('••••••••');
    });

    it('should mask middle of regular id', () => {
      const result = component.maskId('abcdef1234567890');
      expect(result).toContain('••••');
      expect(result.startsWith('abcdef')).toBe(true);
    });

    it('should preserve first 6 and last 4 chars', () => {
      const result = component.maskId('abcdefXXXX7890');
      expect(result).toBe('abcdef••••7890');
    });
  });

  describe('activeUserCount', () => {
    it('should count active users', () => {
      component.loadAll();
      httpCtrl.expectOne('/health').flush(healthOk);
      httpCtrl.expectOne('/api/v1/organizations').flush([]);
      httpCtrl.expectOne('/api/v1/admin/users?limit=200').flush([
        { id: 'u1', role: 'OPERATOR', is_active: true },
        { id: 'u2', role: 'VIEWER', is_active: false },
        { id: 'u3', role: 'MANAGER', is_active: true },
      ]);
      httpCtrl.expectOne('/api/v1/connectors/types').flush([]);
      expect(component.activeUserCount()).toBe(2);
    });
  });

  describe('ngOnInit', () => {
    it('should call loadAll and set up timer subscription', () => {
      const loadSpy = vi.spyOn(component, 'loadAll');
      component.ngOnInit();
      flushAll();
      expect(loadSpy).toHaveBeenCalled();
    });

    it('ngOnDestroy should unsubscribe timer', () => {
      component.ngOnInit();
      flushAll();
      expect(() => component.ngOnDestroy()).not.toThrow();
    });
  });

  describe('buildServiceCards edge cases', () => {
    it('should set api as down when all endpoints fail', () => {
      component.loadAll();
      httpCtrl.expectOne('/health').flush('', { status: 503, statusText: 'Error' });
      httpCtrl.expectOne('/api/v1/organizations').flush('', { status: 503, statusText: 'Error' });
      httpCtrl.expectOne('/api/v1/admin/users?limit=200').flush('', { status: 503, statusText: 'Error' });
      httpCtrl.expectOne('/api/v1/connectors/types').flush('', { status: 503, statusText: 'Error' });
      const services = component.services();
      const apiSvc = services.find(s => s.name === 'system.service_api');
      expect(apiSvc?.status).toBe('down');
    });

    it('should mark db as unknown when health ok but db fails', () => {
      component.loadAll();
      httpCtrl.expectOne('/health').flush(healthOk);
      httpCtrl.expectOne('/api/v1/organizations').flush('', { status: 503, statusText: 'Error' });
      httpCtrl.expectOne('/api/v1/admin/users?limit=200').flush('', { status: 503, statusText: 'Error' });
      httpCtrl.expectOne('/api/v1/connectors/types').flush([mockConnType]);
      const services = component.services();
      const dbSvc = services.find(s => s.name === 'system.service_db');
      expect(dbSvc?.status).toBe('unknown');
    });

    it('should mark engine as unknown when api up but connTypes fail', () => {
      component.loadAll();
      httpCtrl.expectOne('/health').flush(healthOk);
      httpCtrl.expectOne('/api/v1/organizations').flush([mockOrg]);
      httpCtrl.expectOne('/api/v1/admin/users?limit=200').flush([mockUser]);
      httpCtrl.expectOne('/api/v1/connectors/types').flush('', { status: 503, statusText: 'Error' });
      const services = component.services();
      const engSvc = services.find(s => s.name === 'system.service_engine');
      expect(engSvc?.status).toBe('unknown');
    });
  });

  describe('confirmingReload', () => {
    it('should be set to false after executeReload completes', () => {
      component.loadAll();
      flushAll();
      component.confirmingReload.set(true);
      component.executeReload();
      httpCtrl.expectOne('/api/v1/admin/rules/reload').flush({ success: true, rules_loaded: 5, message: 'ok' });
      expect(component.confirmingReload()).toBe(false);
    });
  });
});
