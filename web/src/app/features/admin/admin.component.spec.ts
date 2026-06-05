import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { of } from 'rxjs';
import { AdminComponent } from './admin.component';
import { AuthService } from '../../core/services/auth.service';
import { TranslationService } from '../../core/i18n/translation.service';
import { provideRouter } from '@angular/router';

const tsMock = {
  translateInstant: vi.fn((key: string) => key),
  currentLang: 'es',
  lang$: of('es'),
};

const authMock = {
  isAdmin: vi.fn().mockReturnValue(true),
  getUserRole: vi.fn().mockReturnValue('MANAGER'),
  getUser: vi.fn().mockReturnValue({ id: 'user-123', organization_id: 'org-1' }),
};

describe('AdminComponent', () => {
  let component: AdminComponent;
  let httpCtrl: HttpTestingController;

  beforeEach(() => {
    vi.clearAllMocks();
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: authMock },
        { provide: TranslationService, useValue: tsMock },
      ],
    });

    const fixture = TestBed.createComponent(AdminComponent);
    component = fixture.componentInstance;
    httpCtrl = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpCtrl.verify());

  describe('ngOnInit', () => {
    it('should load organizations on init', () => {
      component.ngOnInit();
      const req = httpCtrl.expectOne('/api/v1/organizations');
      req.flush([{ id: 'org-aaa', name: 'Org A', created_at: '2025-01-01T00:00:00Z' }]);
      expect(component.orgs()).toHaveLength(1);
      expect(component.orgsLoading()).toBe(false);
    });

    it('should set orgsError on HTTP failure', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations').flush('', { status: 500, statusText: 'Error' });
      expect(component.orgsError()).toBe('admin.loading_orgs_error');
      expect(component.orgsLoading()).toBe(false);
    });
  });

  describe('setTab', () => {
    it('should switch active tab', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations').flush([]);
      component.setTab('users');
      httpCtrl.expectOne('/api/v1/admin/users?limit=200').flush([]);
      expect(component.activeTab()).toBe('users');
    });

    it('should not reload an already-loaded tab', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations').flush([]);
      component.setTab('organizations');
      httpCtrl.expectNone('/api/v1/organizations');
    });

    it('should load access requests when switching to that tab', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations').flush([]);
      component.setTab('access-requests');
      httpCtrl.expectOne('/api/v1/access-requests?status=PENDING').flush([]);
      expect(component.activeTab()).toBe('access-requests');
    });
  });

  describe('setArStatus', () => {
    beforeEach(() => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations').flush([]);
      component.setTab('access-requests');
      httpCtrl.expectOne('/api/v1/access-requests?status=PENDING').flush([]);
    });

    it('should update arStatus and reload', () => {
      component.setArStatus('APPROVED');
      httpCtrl.expectOne('/api/v1/access-requests?status=APPROVED').flush([]);
      expect(component.arStatus()).toBe('APPROVED');
    });
  });

  describe('relativeDate', () => {
    it('should return empty string for undefined', () => {
      expect(component.relativeDate(undefined)).toBe('');
    });

    it('should return just_now for very recent', () => {
      const recent = new Date(Date.now() - 30000).toISOString();
      component.relativeDate(recent);
      expect(tsMock.translateInstant).toHaveBeenCalledWith('releases.relative_just_now');
    });

    it('should return minutes for <60 min', () => {
      const ago = new Date(Date.now() - 10 * 60000).toISOString();
      component.relativeDate(ago);
      expect(tsMock.translateInstant).toHaveBeenCalledWith('releases.relative_minutes', { n: 10 });
    });

    it('should return hours for <24h', () => {
      const ago = new Date(Date.now() - 3 * 3600000).toISOString();
      component.relativeDate(ago);
      expect(tsMock.translateInstant).toHaveBeenCalledWith('releases.relative_hours', { n: 3 });
    });

    it('should return days for <30 days', () => {
      const ago = new Date(Date.now() - 5 * 86400000).toISOString();
      component.relativeDate(ago);
      expect(tsMock.translateInstant).toHaveBeenCalledWith('releases.relative_days', { n: 5 });
    });
  });
});
