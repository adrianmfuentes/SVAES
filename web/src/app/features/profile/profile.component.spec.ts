import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { of, throwError } from 'rxjs';
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
  let fixture: ComponentFixture<ProfileComponent>;
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

    fixture = TestBed.createComponent(ProfileComponent);
    component = fixture.componentInstance;
    httpCtrl = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpCtrl?.verify();
    TestBed.resetTestingModule();
  });

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

  describe('setupTotp', () => {
    it('should call setup2fa and set totpSetupData on success', () => {
      const setupData = { secret: 'TOTP_SECRET', qr_data_url: 'data:image/png;base64,abc' };
      authMock.setup2fa.mockReturnValue(of(setupData));
      component.setupTotp();
      expect(authMock.setup2fa).toHaveBeenCalled();
      expect(component.totpSetupData()).toEqual(setupData);
      expect(component.totpLoading()).toBe(false);
    });

    it('should set totpError on failure', () => {
      authMock.setup2fa.mockReturnValue(throwError(() => ({ error: { detail: '2FA setup failed' }, status: 500 })));
      component.setupTotp();
      expect(component.totpError()).toBe('2FA setup failed');
      expect(component.totpLoading()).toBe(false);
    });
  });

  describe('enableTotp', () => {
    it('should mark form touched if invalid', () => {
      const spy = vi.spyOn(component.totpEnableForm, 'markAllAsTouched');
      component.enableTotp();
      expect(spy).toHaveBeenCalled();
      expect(authMock.enable2fa).not.toHaveBeenCalled();
    });

    it('should call enable2fa and update profile on success', () => {
      authMock.enable2fa.mockReturnValue(of({ success: true }));
      component.profile.set({ id: 'u1', email: 'test@example.com', display_name: 'Test', role: 'MANAGER', totp_enabled: false });
      component.totpEnableForm.setValue({ code: '123456' });
      component.enableTotp();
      expect(authMock.enable2fa).toHaveBeenCalledWith('123456');
      expect(component.profile()?.totp_enabled).toBe(true);
      expect(component.totpLoading()).toBe(false);
    });

    it('should set totpError on failure', () => {
      authMock.enable2fa.mockReturnValue(throwError(() => ({ error: { detail: 'Invalid code' }, status: 422 })));
      component.totpEnableForm.setValue({ code: '999999' });
      component.enableTotp();
      expect(component.totpError()).toBe('Invalid code');
    });
  });

  describe('disableTotp', () => {
    it('should mark form touched if invalid', () => {
      const spy = vi.spyOn(component.totpDisableForm, 'markAllAsTouched');
      component.disableTotp();
      expect(spy).toHaveBeenCalled();
      expect(authMock.disable2fa).not.toHaveBeenCalled();
    });

    it('should call disable2fa and update profile on success', () => {
      authMock.disable2fa.mockReturnValue(of({ success: true }));
      component.profile.set({ id: 'u1', email: 'test@example.com', display_name: 'Test', role: 'MANAGER', totp_enabled: true });
      component.totpDisableForm.setValue({ code: '654321' });
      component.disableTotp();
      expect(authMock.disable2fa).toHaveBeenCalledWith('654321');
      expect(component.profile()?.totp_enabled).toBe(false);
      expect(component.totpLoading()).toBe(false);
    });

    it('should set totpError on failure', () => {
      authMock.disable2fa.mockReturnValue(throwError(() => ({ error: { detail: 'Code mismatch' }, status: 422 })));
      component.totpDisableForm.setValue({ code: '111111' });
      component.disableTotp();
      expect(component.totpError()).toBe('Code mismatch');
    });
  });

  describe('createKey error path', () => {
    beforeEach(() => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/users/me').flush(mockUser);
      httpCtrl.expectOne('/api/v1/users/u1/api-keys').flush([]);
    });

    it('should set keyCreateError on failure', () => {
      component.keyForm.setValue({ name: 'Bad Key', expires_in_days: null });
      component.createKey();
      httpCtrl.expectOne('/api/v1/users/u1/api-keys').flush(
        { detail: 'Key limit exceeded' },
        { status: 422, statusText: 'Unprocessable' }
      );
      expect(component.keyCreateError()).toBe('Key limit exceeded');
      expect(component.keyCreating()).toBe(false);
    });
  });

  describe('createOrg error path', () => {
    beforeEach(() => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/users/me').flush(mockUser);
      httpCtrl.expectOne('/api/v1/users/u1/api-keys').flush([]);
    });

    it('should set orgError on conflict', () => {
      component.orgForm.setValue({ name: 'Existing Org', slug: 'existing-org' });
      component.createOrg();
      httpCtrl.expectOne('/api/v1/organizations').flush(
        { detail: 'Slug already taken' },
        { status: 409, statusText: 'Conflict' }
      );
      expect(component.orgError()).toBe('Slug already taken');
      expect(component.orgCreating()).toBe(false);
    });

    it('should not submit if orgForm is invalid', () => {
      component.orgForm.setValue({ name: '', slug: '' });
      component.createOrg();
      httpCtrl.expectNone('/api/v1/organizations');
    });
  });

  describe('ngOnInit without userId', () => {
    it('should set keysLoading false when no userId', () => {
      authMock.getUser.mockReturnValue(null);
      const fixture2 = TestBed.createComponent(ProfileComponent);
      const comp2 = fixture2.componentInstance;
      comp2.ngOnInit();
      httpCtrl.expectOne('/api/v1/users/me').flush(mockUser);
      expect(comp2.keysLoading()).toBe(false);
      authMock.getUser.mockReturnValue({ id: 'u1', organization_id: 'org-1' });
    });

    it('should handle api-keys load error gracefully', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/users/me').flush(mockUser);
      httpCtrl.expectOne('/api/v1/users/u1/api-keys').flush(
        '',
        { status: 500, statusText: 'Error' }
      );
      expect(component.apiKeys()).toEqual([]);
      expect(component.keysLoading()).toBe(false);
    });
  });

  describe('savePassword invalid form', () => {
    beforeEach(() => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/users/me').flush(mockUser);
      httpCtrl.expectOne('/api/v1/users/u1/api-keys').flush([]);
    });

    it('should not submit if pwForm is invalid', () => {
      component.savePassword();
      httpCtrl.expectNone('/api/v1/users/me/password');
    });
  });

  describe('createKey edge cases', () => {
    beforeEach(() => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/users/me').flush(mockUser);
      httpCtrl.expectOne('/api/v1/users/u1/api-keys').flush([]);
    });

    it('should not submit if keyForm is invalid', () => {
      component.keyForm.setValue({ name: '', expires_in_days: null });
      component.createKey();
      httpCtrl.expectNone('/api/v1/users/u1/api-keys');
    });

    it('should include expires_in_days in body when set', () => {
      component.keyForm.setValue({ name: 'Expiring Key', expires_in_days: 30 });
      component.createKey();
      const req = httpCtrl.expectOne('/api/v1/users/u1/api-keys');
      expect(req.request.body).toMatchObject({ name: 'Expiring Key', expires_in_days: 30 });
      req.flush({ id: 'k2', name: 'Expiring Key', key: 'new-secret' });
      expect(component.newKeyValue()).toBe('new-secret');
    });

    it('should do nothing when no userId on createKey', () => {
      authMock.getUser.mockReturnValue(null);
      component.keyForm.setValue({ name: 'Key', expires_in_days: null });
      component.createKey();
      httpCtrl.expectNone('/api/v1/users/u1/api-keys');
      authMock.getUser.mockReturnValue({ id: 'u1', organization_id: 'org-1' });
    });
  });

  describe('revokeKey edge cases', () => {
    beforeEach(() => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/users/me').flush(mockUser);
      httpCtrl.expectOne('/api/v1/users/u1/api-keys').flush([]);
    });

    it('should clear newKeyValue when revoking', () => {
      component.apiKeys.set([{ id: 'k1', name: 'Key1', prefix: 'abc', is_active: true, expires_at: null, created_at: '2025-01-01T00:00:00Z', last_used_at: null }]);
      component.newKeyValue.set('some-raw-key');
      component.revokeKey('k1');
      httpCtrl.expectOne('/api/v1/users/u1/api-keys/k1').flush({});
      expect(component.newKeyValue()).toBeNull();
    });

    it('should do nothing when no userId on revokeKey', () => {
      authMock.getUser.mockReturnValue(null);
      component.revokeKey('k1');
      httpCtrl.expectNone('/api/v1/users/u1/api-keys/k1');
      authMock.getUser.mockReturnValue({ id: 'u1', organization_id: 'org-1' });
    });
  });

  describe('copyKey', () => {
    afterEach(() => vi.unstubAllGlobals());

    it('should do nothing when no key present', () => {
      const writeText = vi.fn();
      vi.stubGlobal('navigator', { clipboard: { writeText } });
      component.newKeyValue.set(null);
      component.copyKey();
      expect(writeText).not.toHaveBeenCalled();
    });

    it('should copy key to clipboard and set keyCopied', async () => {
      const writeText = vi.fn().mockResolvedValue(undefined);
      vi.stubGlobal('navigator', { clipboard: { writeText } });
      component.newKeyValue.set('the-raw-api-key');
      component.copyKey();
      expect(writeText).toHaveBeenCalledWith('the-raw-api-key');
      await writeText.mock.results[0].value;
      expect(component.keyCopied()).toBe(true);
    });
  });

  describe('saveName fallback error message', () => {
    beforeEach(() => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/users/me').flush(mockUser);
      httpCtrl.expectOne('/api/v1/users/u1/api-keys').flush([]);
    });

    it('should use fallback message when error has no detail', () => {
      component.nameForm.setValue({ display_name: 'X' });
      component.saveName();
      httpCtrl.expectOne('/api/v1/users/me').flush({}, { status: 500, statusText: 'Error' });
      expect(component.nameSaveError()).toBe('common.error_saving');
    });
  });

  describe('delete account', () => {
    beforeEach(() => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/users/me').flush(mockUser);
      httpCtrl.expectOne('/api/v1/users/u1/api-keys').flush([]);
    });

    describe('openDeleteModal', () => {
      it('should open modal and not fetch org when user has no org', () => {
        authMock.getUser.mockReturnValue({ id: 'u1' });
        component.openDeleteModal();
        expect(component.showDeleteModal()).toBe(true);
        expect(component.deleteAccountChecking()).toBe(false);
        expect(component.deleteOrgWarning()).toBe(false);
        httpCtrl.expectNone('/api/v1/organizations/org-1');
        authMock.getUser.mockReturnValue({ id: 'u1', organization_id: 'org-1' });
      });

      it('should set org deletion warning when user is sole org owner', () => {
        component.openDeleteModal();
        httpCtrl.expectOne('/api/v1/organizations/org-1').flush({ owner_id: 'u1' });
        httpCtrl.expectOne('/api/v1/organizations/org-1/users').flush([{ id: 'u1' }]);
        expect(component.deleteOrgWarning()).toBe(true);
        expect(component.deleteAccountChecking()).toBe(false);
      });

      it('should NOT set org deletion warning when org has other members', () => {
        component.openDeleteModal();
        httpCtrl.expectOne('/api/v1/organizations/org-1').flush({ owner_id: 'u1' });
        httpCtrl.expectOne('/api/v1/organizations/org-1/users').flush([{ id: 'u1' }, { id: 'u2' }]);
        expect(component.deleteOrgWarning()).toBe(false);
        expect(component.deleteAccountChecking()).toBe(false);
      });

      it('should NOT set warning when user is not the org owner', () => {
        component.openDeleteModal();
        httpCtrl.expectOne('/api/v1/organizations/org-1').flush({ owner_id: 'u2' });
        expect(component.deleteOrgWarning()).toBe(false);
        expect(component.deleteAccountChecking()).toBe(false);
      });

      it('should handle org fetch error gracefully', () => {
        component.openDeleteModal();
        httpCtrl.expectOne('/api/v1/organizations/org-1').flush('', { status: 500, statusText: 'Error' });
        expect(component.deleteAccountChecking()).toBe(false);
      });

      it('should handle members fetch error gracefully', () => {
        component.openDeleteModal();
        httpCtrl.expectOne('/api/v1/organizations/org-1').flush({ owner_id: 'u1' });
        httpCtrl.expectOne('/api/v1/organizations/org-1/users').flush('', { status: 500, statusText: 'Error' });
        expect(component.deleteAccountChecking()).toBe(false);
      });
    });

    describe('closeDeleteModal', () => {
      it('should close modal when not deleting', () => {
        component.showDeleteModal.set(true);
        component.deleteAccountDeleting.set(false);
        component.closeDeleteModal();
        expect(component.showDeleteModal()).toBe(false);
      });

      it('should not close modal when deleting', () => {
        component.showDeleteModal.set(true);
        component.deleteAccountDeleting.set(true);
        component.closeDeleteModal();
        expect(component.showDeleteModal()).toBe(true);
      });
    });

    describe('confirmDeleteAccount', () => {
      it('should not submit if form is invalid', () => {
        component.deleteAccountForm.setValue({ password: '' });
        component.confirmDeleteAccount();
        httpCtrl.expectNone('/api/v1/users/me/account');
      });

      it('should send DELETE and logout on success', () => {
        component.deleteAccountForm.setValue({ password: 'mypassword' });
        component.confirmDeleteAccount();
        httpCtrl.expectOne('/api/v1/users/me/account').flush({});
        expect(component.deleteAccountSuccess()).toBe(true);
      });

      it('should show wrong password error on 400', () => {
        component.deleteAccountForm.setValue({ password: 'wrong' });
        component.confirmDeleteAccount();
        httpCtrl.expectOne('/api/v1/users/me/account').flush(
          { detail: 'bad' },
          { status: 400, statusText: 'Bad Request' }
        );
        expect(component.deleteAccountError()).toBe('profile_page.delete_account_wrong_password');
        expect(component.deleteAccountDeleting()).toBe(false);
      });

      it('should show wrong password error on 401', () => {
        component.deleteAccountForm.setValue({ password: 'wrong' });
        component.confirmDeleteAccount();
        httpCtrl.expectOne('/api/v1/users/me/account').flush(
          {},
          { status: 401, statusText: 'Unauthorized' }
        );
        expect(component.deleteAccountError()).toBe('profile_page.delete_account_wrong_password');
        expect(component.deleteAccountDeleting()).toBe(false);
      });

      it('should show detail message on 403', () => {
        component.deleteAccountForm.setValue({ password: 'pwd' });
        component.confirmDeleteAccount();
        httpCtrl.expectOne('/api/v1/users/me/account').flush(
          { detail: 'Blocked by policy' },
          { status: 403, statusText: 'Forbidden' }
        );
        expect(component.deleteAccountError()).toBe('Blocked by policy');
        expect(component.deleteAccountDeleting()).toBe(false);
      });

      it('should show generic error on 403 without detail', () => {
        component.deleteAccountForm.setValue({ password: 'pwd' });
        component.confirmDeleteAccount();
        httpCtrl.expectOne('/api/v1/users/me/account').flush(
          {},
          { status: 403, statusText: 'Forbidden' }
        );
        expect(component.deleteAccountError()).toBe('profile_page.delete_account_error');
        expect(component.deleteAccountDeleting()).toBe(false);
      });

      it('should show generic error on 500', () => {
        component.deleteAccountForm.setValue({ password: 'pwd' });
        component.confirmDeleteAccount();
        httpCtrl.expectOne('/api/v1/users/me/account').flush(
          '',
          { status: 500, statusText: 'Error' }
        );
        expect(component.deleteAccountError()).toBe('profile_page.delete_account_error');
        expect(component.deleteAccountDeleting()).toBe(false);
      });
    });
  });

  describe('template rendering', () => {
    const renderTemplate = (flushInitRequests = true) => {
      fixture.detectChanges();
      if (flushInitRequests) {
        httpCtrl.expectOne('/api/v1/users/me').flush(mockUser);
        httpCtrl.expectOne('/api/v1/users/u1/api-keys').flush([]);
      }
    };

    it('should render loading skeleton', () => {
      component.loading.set(true);
      renderTemplate();
    });

    it('should render profile with org (hasOrg=true, isAdmin=false)', () => {
      component.loading.set(false);
      component.profile.set(mockUser);
      component.hasOrg.set(true);
      component.isAdmin.set(false);
      component.apiKeys.set([]);
      component.keysLoading.set(false);
      renderTemplate();
    });

    it('should render org creation form (hasOrg=false, isAdmin=false)', () => {
      component.loading.set(false);
      component.profile.set(mockUser);
      component.hasOrg.set(false);
      component.isAdmin.set(false);
      component.orgCreated.set(false);
      component.apiKeys.set([]);
      component.keysLoading.set(false);
      renderTemplate();
    });

    it('should render org created success state', () => {
      component.loading.set(false);
      component.profile.set(mockUser);
      component.hasOrg.set(false);
      component.isAdmin.set(false);
      component.orgCreated.set(true);
      component.apiKeys.set([]);
      component.keysLoading.set(false);
      renderTemplate();
    });

    it('should render API keys table and new-key banner', () => {
      const key = { id: 'k1', name: 'Key', prefix: 'abc', is_active: true, expires_at: '2026-01-01T00:00:00Z', created_at: '2025-01-01T00:00:00Z', last_used_at: null };
      component.loading.set(false);
      component.profile.set(mockUser);
      component.hasOrg.set(true);
      component.isAdmin.set(true);
      component.apiKeys.set([key]);
      component.keysLoading.set(false);
      component.newKeyValue.set('raw-key-value');
      renderTemplate();
    });

    it('should render keys skeleton and empty state', () => {
      component.loading.set(false);
      component.profile.set(mockUser);
      component.hasOrg.set(true);
      component.isAdmin.set(false);
      component.apiKeys.set([]);
      component.keysLoading.set(true);
      renderTemplate();
      component.keysLoading.set(false);
      renderTemplate(false);
    });

    it('should render TOTP setup panel', () => {
      component.loading.set(false);
      component.profile.set({ ...mockUser, totp_enabled: false });
      component.hasOrg.set(true);
      component.isAdmin.set(true);
      component.apiKeys.set([]);
      component.keysLoading.set(false);
      component.totpSetupData.set({ secret: 'ABCD1234', qr_data_url: 'data:image/png;base64,abc', totp_uri: 'otpauth://totp/Example:alice@example.com?secret=ABCD1234&issuer=Example' });
      renderTemplate();
    });

    it('should render TOTP enabled (disable form)', () => {
      component.loading.set(false);
      component.profile.set({ ...mockUser, totp_enabled: true });
      component.hasOrg.set(true);
      component.isAdmin.set(true);
      component.apiKeys.set([]);
      component.keysLoading.set(false);
      renderTemplate();
    });

    it('should render name save and pw save confirmation states', () => {
      component.loading.set(false);
      component.profile.set(mockUser);
      component.hasOrg.set(true);
      component.isAdmin.set(true);
      component.apiKeys.set([]);
      component.keysLoading.set(false);
      component.nameSaved.set(true);
      component.pwSaved.set(true);
      component.nameSaveError.set('some error');
      component.pwSaveError.set('pw error');
      component.orgError.set('org error');
      component.keyCreateError.set('key error');
      component.totpError.set('totp error');
      component.totpSuccess.set(true);
      renderTemplate();
    });

    it('should NOT render delete account card for admin', () => {
      component.loading.set(false);
      component.profile.set(mockUser);
      component.isAdmin.set(true);
      component.hasOrg.set(true);
      component.apiKeys.set([]);
      component.keysLoading.set(false);
      renderTemplate();
      const deleteCard = fixture.nativeElement.querySelector('.delete-account-card');
      expect(deleteCard).toBeNull();
    });

    it('should render delete account card for non-admin', () => {
      component.loading.set(false);
      component.profile.set(mockUser);
      component.isAdmin.set(false);
      component.hasOrg.set(true);
      component.apiKeys.set([]);
      component.keysLoading.set(false);
      renderTemplate();
      const deleteCard = fixture.nativeElement.querySelector('.delete-account-card');
      expect(deleteCard).not.toBeNull();
    });

    it('should render delete account modal with org deletion warning', () => {
      component.loading.set(false);
      component.profile.set(mockUser);
      component.isAdmin.set(false);
      component.hasOrg.set(true);
      component.apiKeys.set([]);
      component.keysLoading.set(false);
      component.showDeleteModal.set(true);
      component.deleteOrgWarning.set(true);
      renderTemplate();
      const warning = fixture.nativeElement.querySelector('.transfer-warning');
      expect(warning).not.toBeNull();
    });

    it('should render delete account modal with standard confirm', () => {
      component.loading.set(false);
      component.profile.set(mockUser);
      component.isAdmin.set(false);
      component.hasOrg.set(true);
      component.apiKeys.set([]);
      component.keysLoading.set(false);
      component.showDeleteModal.set(true);
      component.deleteOrgWarning.set(false);
      renderTemplate();
      const warning = fixture.nativeElement.querySelector('.transfer-warning');
      expect(warning).toBeNull();
    });

    it('should render delete account error in modal', () => {
      component.loading.set(false);
      component.profile.set(mockUser);
      component.isAdmin.set(false);
      component.hasOrg.set(true);
      component.apiKeys.set([]);
      component.keysLoading.set(false);
      component.showDeleteModal.set(true);
      component.deleteAccountError.set('wrong password');
      renderTemplate();
      const error = fixture.nativeElement.querySelector('.modal-error');
      expect(error).not.toBeNull();
    });

    it('should render delete account success in modal', () => {
      component.loading.set(false);
      component.profile.set(mockUser);
      component.isAdmin.set(false);
      component.hasOrg.set(true);
      component.apiKeys.set([]);
      component.keysLoading.set(false);
      component.showDeleteModal.set(true);
      component.deleteAccountSuccess.set(true);
      renderTemplate();
      const success = fixture.nativeElement.querySelector('.alert-success');
      expect(success).not.toBeNull();
    });
  });
});
