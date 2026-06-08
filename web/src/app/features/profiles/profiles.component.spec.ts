import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { of } from 'rxjs';
import { ProfilesComponent } from './profiles.component';
import { AuthService } from '../../core/services/auth.service';
import { TranslationService } from '../../core/i18n/translation.service';
import { provideRouter } from '@angular/router';

const tsMock = {
  translateInstant: vi.fn((key: string) => key),
  currentLang: 'es',
  lang$: of('es'),
};

const authMock = {
  isAdmin: vi.fn().mockReturnValue(false),
  getUserRole: vi.fn().mockReturnValue('MANAGER'),
  getUser: vi.fn().mockReturnValue({ id: 'u1', organization_id: 'org-abc' }),
};

const mockProfile = { id: 'p1', name: 'Profile A', description: 'Desc', rules_count: 3, is_template: false };

describe('ProfilesComponent', () => {
  let component: ProfilesComponent;
  let fixture: ComponentFixture<ProfilesComponent>;
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

    fixture = TestBed.createComponent(ProfilesComponent);
    component = fixture.componentInstance;
    httpCtrl = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpCtrl?.verify();
    TestBed.resetTestingModule();
  });

  describe('ngOnInit', () => {
    it('should load profiles on init', () => {
      component.ngOnInit();
      const req = httpCtrl.expectOne('/api/v1/organizations/org-abc/profiles');
      req.flush([mockProfile]);
      expect(component.allProfiles()).toHaveLength(1);
      expect(component.orgProfiles()).toHaveLength(1);
      expect(component.loading()).toBe(false);
    });

    it('should set error when no orgId', () => {
      authMock.getUser.mockReturnValue(null);
      component.ngOnInit();
      httpCtrl.expectNone('/api/v1/organizations/org-abc/profiles');
      expect(component.error()).toBe('profiles.loading_error');
      authMock.getUser.mockReturnValue({ id: 'u1', organization_id: 'org-abc' });
    });

    it('should set error on HTTP failure', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations/org-abc/profiles').flush('', { status: 500, statusText: 'Error' });
      expect(component.error()).toBe('profiles.loading_error');
    });
  });

  describe('openCreate / openEdit', () => {
    it('openCreate should reset form and show modal', () => {
      component.openCreate();
      expect(component.showModal()).toBe(true);
      expect(component.editingProfile()).toBeNull();
      expect(component.modalError()).toBeNull();
    });

    it('openEdit should populate form and show modal', () => {
      component.openEdit(mockProfile);
      expect(component.showModal()).toBe(true);
      expect(component.editingProfile()).toEqual(mockProfile);
      expect(component.profileForm.value.name).toBe('Profile A');
    });
  });

  describe('submitProfile', () => {
    beforeEach(() => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations/org-abc/profiles').flush([]);
    });

    it('should POST new profile and close modal', () => {
      component.openCreate();
      component.profileForm.setValue({ name: 'New', description: 'Desc' });
      component.submitProfile();
      const req = httpCtrl.expectOne('/api/v1/organizations/org-abc/profiles');
      expect(req.request.method).toBe('POST');
      req.flush({ ...mockProfile, id: 'p2', name: 'New' });
      expect(component.showModal()).toBe(false);
      expect(component.orgProfiles()).toHaveLength(1);
    });

    it('should PATCH existing profile', () => {
      component.templates.set([mockProfile]);
      component.openEdit(mockProfile);
      component.profileForm.setValue({ name: 'Updated', description: 'Desc' });
      component.submitProfile();
      const req = httpCtrl.expectOne(`/api/v1/profiles/${mockProfile.id}`);
      expect(req.request.method).toBe('PATCH');
      req.flush({ ...mockProfile, name: 'Updated' });
      expect(component.showModal()).toBe(false);
    });

    it('should set modalError on failure', () => {
      component.openCreate();
      component.profileForm.setValue({ name: 'X', description: '' });
      component.submitProfile();
      httpCtrl.expectOne('/api/v1/organizations/org-abc/profiles').flush(
        { detail: 'Already exists' },
        { status: 409, statusText: 'Conflict' }
      );
      expect(component.modalError()).toBe('Already exists');
    });
  });

  describe('deleteProfile', () => {
    beforeEach(() => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations/org-abc/profiles').flush([mockProfile]);
    });

    it('should remove profile from orgProfiles on success', () => {
      component.deleteProfile(mockProfile);
      httpCtrl.expectOne(`/api/v1/profiles/${mockProfile.id}`).flush({});
      expect(component.orgProfiles()).toHaveLength(0);
      expect(component.deletingId()).toBeNull();
    });
  });

  describe('template rendering', () => {
    const renderTemplate = () => {
      fixture.detectChanges();
      httpCtrl.expectOne('/api/v1/organizations/org-abc/profiles').flush([]);
    };

    it('should render loading skeleton', () => {
      component.loading.set(true);
      renderTemplate();
    });

    it('should render error state', () => {
      component.loading.set(false);
      component.error.set('profiles.loading_error');
      renderTemplate();
    });

    it('should render profiles list', () => {
      component.loading.set(false);
      component.orgProfiles.set([mockProfile]);
      component.templates.set([{ ...mockProfile, id: 'tmpl-1', is_template: true }]);
      renderTemplate();
    });

    it('should render empty state', () => {
      component.loading.set(false);
      component.orgProfiles.set([]);
      component.templates.set([]);
      renderTemplate();
    });

    it('should render create modal', () => {
      component.loading.set(false);
      component.showModal.set(true);
      component.editingProfile.set(null);
      renderTemplate();
    });

    it('should render edit modal with error', () => {
      component.loading.set(false);
      component.showModal.set(true);
      component.editingProfile.set(mockProfile);
      component.modalError.set('Already exists');
      renderTemplate();
    });
  });
});
