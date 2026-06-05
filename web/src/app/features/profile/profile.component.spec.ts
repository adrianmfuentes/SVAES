import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { of } from 'rxjs';
import { ProfileComponent } from './profile.component';
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
  getUser: vi.fn().mockReturnValue({ id: 'u1', organization_id: 'org-1' }),
  logout: vi.fn(),
  setup2fa: vi.fn(),
  enable2fa: vi.fn(),
  disable2fa: vi.fn(),
};

const mockUser = { id: 'u1', display_name: 'Test User', email: 'test@example.com', role: 'MANAGER', totp_enabled: false };

describe('ProfileComponent', () => {
  let component: ProfileComponent;
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

    const fixture = TestBed.createComponent(ProfileComponent);
    component = fixture.componentInstance;
    httpCtrl = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpCtrl.verify());

  describe('ngOnInit', () => {
    it('should load profile and API keys', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/users/me').flush(mockUser);
      httpCtrl.expectOne('/api/v1/users/u1/api-keys').flush([]);
      expect(component.profile()).toEqual(mockUser);
      expect(component.loading()).toBe(false);
      expect(component.keysLoading()).toBe(false);
    });

    it('should handle profile load error gracefully', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/users/me').flush('', { status: 500, statusText: 'Error' });
      httpCtrl.expectOne('/api/v1/users/u1/api-keys').flush([]);
      expect(component.profile()).toBeNull();
      expect(component.loading()).toBe(false);
    });
  });

  describe('saveName', () => {
    beforeEach(() => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/users/me').flush(mockUser);
      httpCtrl.expectOne('/api/v1/users/u1/api-keys').flush([]);
    });

    it('should PATCH and set nameSaved on success', () => {
      component.nameForm.setValue({ display_name: 'New Name' });
      component.saveName();
      const req = httpCtrl.expectOne('/api/v1/users/me');
      expect(req.request.method).toBe('PATCH');
      req.flush({ ...mockUser, display_name: 'New Name' });
      expect(component.nameSaved()).toBe(true);
    });

    it('should set nameSaveError on failure', () => {
      component.nameForm.setValue({ display_name: 'X' });
      component.saveName();
      httpCtrl.expectOne('/api/v1/users/me').flush({ detail: 'Error' }, { status: 500, statusText: 'Error' });
      expect(component.nameSaveError()).toBe('Error');
    });

    it('should not submit if form is invalid', () => {
      component.nameForm.setValue({ display_name: '' });
      component.saveName();
      httpCtrl.expectNone('/api/v1/users/me');
    });
  });

  describe('savePassword', () => {
    beforeEach(() => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/users/me').flush(mockUser);
      httpCtrl.expectOne('/api/v1/users/u1/api-keys').flush([]);
    });

    it('should POST and set pwSaved on success', () => {
      component.pwForm.setValue({ current_password: 'old123', new_password: 'NewPass1!', confirm_password: 'NewPass1!' });
      component.savePassword();
      const req = httpCtrl.expectOne('/api/v1/users/me/password');
      expect(req.request.method).toBe('POST');
      req.flush({});
      expect(component.pwSaved()).toBe(true);
    });

    it('should set pwSaveError on failure', () => {
      component.pwForm.setValue({ current_password: 'wrong', new_password: 'NewPass1!', confirm_password: 'NewPass1!' });
      component.savePassword();
      httpCtrl.expectOne('/api/v1/users/me/password').flush({ detail: 'Wrong password' }, { status: 400, statusText: 'Bad Request' });
      expect(component.pwSaveError()).toBe('Wrong password');
    });
  });

  describe('autoSlug', () => {
    it('should generate slug from org name', () => {
      component.orgForm.patchValue({ name: 'My Company Ltd', slug: '' });
      component.autoSlug();
      expect(component.orgForm.value.slug).toBe('my-company-ltd');
    });

    it('should remove special characters', () => {
      component.orgForm.patchValue({ name: 'Company & Co.', slug: '' });
      component.autoSlug();
      expect(component.orgForm.value.slug).toBe('company-co');
    });
  });

  describe('createOrg', () => {
    beforeEach(() => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/users/me').flush(mockUser);
      httpCtrl.expectOne('/api/v1/users/u1/api-keys').flush([]);
    });

    it('should POST and set orgCreated on success', () => {
      component.orgForm.setValue({ name: 'New Org', slug: 'new-org' });
      component.createOrg();
      httpCtrl.expectOne('/api/v1/organizations').flush({ id: 'org-new', name: 'New Org', slug: 'new-org' });
      expect(component.orgCreated()).toBe(true);
    });
  });

  describe('roleLabel', () => {
    it('should call translateInstant for known roles', () => {
      component.roleLabel('ADMIN');
      expect(tsMock.translateInstant).toHaveBeenCalledWith('profile_page.role_admin');
      component.roleLabel('MANAGER');
      expect(tsMock.translateInstant).toHaveBeenCalledWith('profile_page.role_manager');
      component.roleLabel('OPERATOR');
      expect(tsMock.translateInstant).toHaveBeenCalledWith('profile_page.role_operator');
    });

    it('should return role as-is for unknown', () => {
      expect(component.roleLabel('CUSTOM')).toBe('CUSTOM');
    });
  });

  describe('createKey / revokeKey', () => {
    beforeEach(() => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/users/me').flush(mockUser);
      httpCtrl.expectOne('/api/v1/users/u1/api-keys').flush([]);
    });

    it('createKey should POST and reveal the key value', () => {
      component.keyForm.setValue({ name: 'My Key', expires_in_days: null });
      component.createKey();
      httpCtrl.expectOne('/api/v1/users/u1/api-keys').flush({ id: 'k1', name: 'My Key', key: 'secret-key-value' });
      expect(component.newKeyValue()).toBe('secret-key-value');
      expect(component.apiKeys()).toHaveLength(1);
    });

    it('revokeKey should DELETE and remove from list', () => {
      component.apiKeys.set([{ id: 'k1', name: 'Key1', prefix: 'abc', is_active: true, expires_at: null, created_at: '2025-01-01T00:00:00Z', last_used_at: null }]);
      component.revokeKey('k1');
      httpCtrl.expectOne('/api/v1/users/u1/api-keys/k1').flush({});
      expect(component.apiKeys()).toHaveLength(0);
    });
  });

  describe('relogin', () => {
    it('should call authService.logout()', () => {
      component.relogin();
      expect(authMock.logout).toHaveBeenCalled();
    });
  });
});
