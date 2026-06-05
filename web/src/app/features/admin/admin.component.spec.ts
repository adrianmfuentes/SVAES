import { ComponentFixture, TestBed } from '@angular/core/testing';
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
  let fixture: ComponentFixture<AdminComponent>;
  let httpCtrl: HttpTestingController;

  beforeEach(() => {
    vi.clearAllMocks();
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: authMock },
        { provide: TranslationService, useValue: tsMock },
      ],
    });

    fixture = TestBed.createComponent(AdminComponent);
    component = fixture.componentInstance;
    httpCtrl = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpCtrl?.verify();
    TestBed.resetTestingModule();
  });

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

    it('should return formatted date string for >30 days', () => {
      const old = new Date(Date.now() - 60 * 86400000).toISOString();
      const result = component.relativeDate(old);
      expect(typeof result).toBe('string');
      expect(result.length).toBeGreaterThan(0);
    });
  });

  describe('loadUsers', () => {
    it('should load users and anonymize them', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations').flush([]);
      component.setTab('users');
      const req = httpCtrl.expectOne('/api/v1/admin/users?limit=200');
      req.flush([{ id: 'user-abc', email: 'real@example.com', display_name: 'Real Name', role: 'OPERATOR', is_active: true }]);
      expect(component.users()).toHaveLength(1);
      expect(component.users()[0].email).toContain('anonymous.local');
      expect(component.usersLoading()).toBe(false);
    });

    it('should set usersError on failure', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations').flush([]);
      component.setTab('users');
      httpCtrl.expectOne('/api/v1/admin/users?limit=200').flush('', { status: 500, statusText: 'Error' });
      expect(component.usersError()).toBe('admin.loading_users_error');
      expect(component.usersLoading()).toBe(false);
    });
  });

  describe('loadOrgs anonymization', () => {
    it('should anonymize org names', () => {
      component.ngOnInit();
      const req = httpCtrl.expectOne('/api/v1/organizations');
      req.flush([{ id: 'org-aaa', name: 'Real Org Name', slug: 'real-org' }]);
      expect(component.orgs()[0].name).toMatch(/^Organization /);
    });
  });

  describe('setArStatus reload', () => {
    it('should reload access requests on status change', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations').flush([]);
      component.setTab('access-requests');
      httpCtrl.expectOne('/api/v1/access-requests?status=PENDING').flush([]);
      component.setArStatus('REJECTED');
      const req = httpCtrl.expectOne('/api/v1/access-requests?status=REJECTED');
      req.flush([]);
      expect(component.arStatus()).toBe('REJECTED');
      expect(component.arLoading()).toBe(false);
    });
  });

  describe('loadAccessRequests error', () => {
    it('should set arError when access requests fail to load', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations').flush([]);
      component.setTab('access-requests');
      httpCtrl.expectOne('/api/v1/access-requests?status=PENDING').flush(
        '',
        { status: 500, statusText: 'Error' }
      );
      expect(component.arError()).toBe('Error loading access requests');
      expect(component.arLoading()).toBe(false);
    });
  });

  describe('template rendering', () => {
    const mockOrgs = [{ id: 'org-1', name: 'Org A', slug: 'org-a' }];
    const mockUsers = [{ id: 'u1', email: 'a@b.com', display_name: 'User', role: 'OPERATOR', is_active: true }];
    const mockAR = [{ id: 'ar-1', requester_name: 'Jane', requester_email: 'j@example.com', organization_name: 'Org', status: 'PENDING' as const, created_at: new Date().toISOString() }];

    const renderTemplate = (flushOrgLoad = true) => {
      fixture.detectChanges();
      if (flushOrgLoad) {
        httpCtrl.expectOne('/api/v1/organizations').flush(mockOrgs);
      }
    };

    it('should render organizations tab (default)', () => {
      component.orgsLoading.set(false);
      component.orgs.set(mockOrgs);
      renderTemplate();
    });

    it('should render organizations tab loading state', () => {
      component.orgsLoading.set(true);
      renderTemplate();
    });

    it('should render organizations tab error state', () => {
      component.orgsLoading.set(false);
      component.orgsError.set('Failed to load');
      renderTemplate();
    });

    it('should render users tab', () => {
      component.activeTab.set('users');
      component.usersLoading.set(false);
      component.users.set(mockUsers);
      renderTemplate();
    });

    it('should render users tab error', () => {
      component.activeTab.set('users');
      component.usersLoading.set(false);
      component.usersError.set('Error');
      renderTemplate();
    });

    it('should render access-requests tab with data', () => {
      component.activeTab.set('access-requests');
      component.arLoading.set(false);
      component.accessRequests.set(mockAR);
      renderTemplate();
    });

    it('should render access-requests tab error and success', () => {
      component.activeTab.set('access-requests');
      component.arLoading.set(false);
      component.arError.set('Load failed');
      component.arSuccess.set('Done');
      renderTemplate();
    });

    it('should render empty states', () => {
      component.orgsLoading.set(false);
      component.orgs.set([]);
      renderTemplate();
      component.activeTab.set('users');
      component.usersLoading.set(false);
      component.users.set([]);
      renderTemplate(false);
      component.activeTab.set('access-requests');
      component.arLoading.set(false);
      component.accessRequests.set([]);
      renderTemplate(false);
    });
  });
});
