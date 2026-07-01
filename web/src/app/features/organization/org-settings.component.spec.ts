import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { of } from 'rxjs';
import { OrgSettingsComponent } from './org-settings.component';
import { AuthService } from '../../core/services/auth.service';
import { TranslationService } from '../../core/i18n/translation.service';

const tsMock = {
  translateInstant: vi.fn((key: string) => key),
  currentLang: 'es',
  lang$: of('es'),
};

interface MockUser {
  id: string;
  email: string;
  display_name: string;
  role: 'OPERATOR' | 'ADMIN' | 'MANAGER';
  organization_id?: string;
  is_active: boolean;
}

const createMockAuthService = (user: MockUser | null) => {
  return {
    getUser: vi.fn(() => user),
    getUserRole: vi.fn(() => user?.role ?? ''),
    logout: vi.fn(),
  };
};

const mockMembers: MockUser[] = [
  { id: 'user-1', email: 'admin@test.com', display_name: 'Admin User', role: 'MANAGER', is_active: true },
  { id: 'user-2', email: 'op@test.com', display_name: 'Operator User', role: 'OPERATOR', is_active: true },
  { id: 'user-3', email: 'op2@test.com', display_name: 'Operator User 2', role: 'OPERATOR', is_active: true },
  { id: 'user-4', email: 'orgadmin@test.com', display_name: 'Org Admin', role: 'ADMIN', is_active: true },
];

describe('OrgSettingsComponent', () => {
  let component: OrgSettingsComponent;
  let fixture: ComponentFixture<OrgSettingsComponent>;
  let httpCtrl: HttpTestingController;
  let authService: ReturnType<typeof createMockAuthService>;

  const userWithOrg: MockUser = {
    id: 'user-1',
    email: 'admin@test.com',
    display_name: 'Admin User',
    role: 'MANAGER',
    organization_id: 'org-1',
    is_active: true,
  };

  beforeEach(() => {
    authService = createMockAuthService(userWithOrg);

    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: authService },
        { provide: TranslationService, useValue: tsMock },
      ],
    });

    fixture = TestBed.createComponent(OrgSettingsComponent);
    component = fixture.componentInstance;
    httpCtrl = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpCtrl?.verify();
    TestBed.resetTestingModule();
  });

  describe('ngOnInit', () => {
    it('should load members on init', () => {
      fixture.detectChanges();
      const req = httpCtrl.expectOne('/api/v1/organizations/org-1/users');
      expect(req.request.method).toBe('GET');
      req.flush(mockMembers);
      fixture.detectChanges();

      expect(component.members()).toEqual(mockMembers);
      expect(component.membersLoading()).toBe(false);
      expect(component.membersError()).toBeNull();
    });

    it('should set error when orgId is missing', () => {
      const noOrgAuth = createMockAuthService({ ...userWithOrg, organization_id: '' });
      TestBed.resetTestingModule();
      TestBed.configureTestingModule({
        providers: [
          provideHttpClient(),
          provideHttpClientTesting(),
          { provide: AuthService, useValue: noOrgAuth },
          { provide: TranslationService, useValue: tsMock },
        ],
      });
      const localFixture = TestBed.createComponent(OrgSettingsComponent);
      const localComponent = localFixture.componentInstance;
      const localCtrl = TestBed.inject(HttpTestingController);
      localFixture.detectChanges();

      expect(localComponent.membersError()).toBe('org_settings.no_organization');
      expect(localComponent.membersLoading()).toBe(false);
      localCtrl.expectNone('/api/v1/organizations//users');
    });

    it('should set error on HTTP failure', () => {
      fixture.detectChanges();
      httpCtrl.expectOne('/api/v1/organizations/org-1/users').flush('', { status: 500, statusText: 'Error' });

      expect(component.membersError()).toBe('org_settings.loading_members_error');
      expect(component.membersLoading()).toBe(false);
    });

    it('should show skeleton while loading', () => {
      fixture.detectChanges();

      expect(component.membersLoading()).toBe(true);
      const skeletonRows = fixture.nativeElement.querySelectorAll('.skeleton-row');
      expect(skeletonRows.length).toBe(3);
      httpCtrl.expectOne('/api/v1/organizations/org-1/users').flush([]);
    });

    it('should show error banner when error occurs', () => {
      fixture.detectChanges();
      httpCtrl.expectOne('/api/v1/organizations/org-1/users').flush('', { status: 500, statusText: 'Error' });
      fixture.detectChanges();

      const errorBanner = fixture.nativeElement.querySelector('.error-banner');
      expect(errorBanner).toBeTruthy();
    });
  });

  describe('invite modal', () => {
    it('should open invite modal and reset fields', () => {
      component.inviteEmail = 'old@test.com';
      component.inviteRole = 'OPERATOR';
      component.inviteError.set('previous error');

      component.openInviteModal();

      expect(component.inviteEmail).toBe('');
      expect(component.inviteRole).toBe('OPERATOR');
      expect(component.inviteError()).toBeNull();
      expect(component.inviteSuccess()).toBeNull();
      expect(component.showInviteModal()).toBe(true);
    });

    it('should close invite modal', () => {
      component.showInviteModal.set(true);
      component.closeInviteModal();
      expect(component.showInviteModal()).toBe(false);
    });

    it('should not send invite if email is empty', () => {
      component.inviteEmail = '';
      component.sendInvite();
      httpCtrl.expectNone('/api/v1/organizations/org-1/users/invite');
    });

    it('should send invite and show success', () => {
      fixture.detectChanges();
      httpCtrl.expectOne('/api/v1/organizations/org-1/users').flush([]);

      component.inviteEmail = 'new@test.com';
      component.inviteRole = 'OPERATOR';
      component.sendInvite();

      const req = httpCtrl.expectOne('/api/v1/organizations/org-1/users/invite');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ email: 'new@test.com', role: 'OPERATOR' });
      req.flush({});
      fixture.detectChanges();

      expect(component.inviting()).toBe(false);
      expect(component.inviteSuccess()).toBe('org_settings.invite_success');
    });

    it('should handle invite error', () => {
      fixture.detectChanges();
      httpCtrl.expectOne('/api/v1/organizations/org-1/users').flush([]);

      component.inviteEmail = 'bad@test.com';
      component.sendInvite();

      httpCtrl.expectOne('/api/v1/organizations/org-1/users/invite').flush(
        { detail: 'Invite failed' },
        { status: 400, statusText: 'Bad Request' }
      );
      fixture.detectChanges();

      expect(component.inviteError()).toBe('Invite failed');
      expect(component.inviting()).toBe(false);
    });

    it('should close modal after successful invite with timeout', () => {
      vi.useFakeTimers();
      fixture.detectChanges();
      httpCtrl.expectOne('/api/v1/organizations/org-1/users').flush([]);

      component.inviteEmail = 'new@test.com';
      component.sendInvite();

      httpCtrl.expectOne('/api/v1/organizations/org-1/users/invite').flush({});
      fixture.detectChanges();

      expect(component.inviteSuccess()).toBe('org_settings.invite_success');
      vi.advanceTimersByTime(1500);
      expect(component.showInviteModal()).toBe(false);

      vi.useRealTimers();
    });
  });

  describe('remove member', () => {
    beforeEach(() => {
      fixture.detectChanges();
      httpCtrl.expectOne('/api/v1/organizations/org-1/users').flush(mockMembers);
    });

    it('should open confirm remove modal and clear error', () => {
      component.removeError.set('previous error');
      const member = mockMembers[1];
      component.confirmRemoveMember(member);
      expect(component.memberToRemove()).toBe(member);
      expect(component.removeError()).toBeNull();
    });

    it('should cancel remove member and clear error', () => {
      component.removeError.set('previous error');
      component.memberToRemove.set(mockMembers[1]);
      component.cancelRemoveMember();
      expect(component.memberToRemove()).toBeNull();
      expect(component.removeError()).toBeNull();
    });

    it('should remove OPERATOR member successfully (200)', () => {
      const operator = mockMembers[1];
      component.confirmRemoveMember(operator);
      component.removeMember();

      const req = httpCtrl.expectOne(`/api/v1/organizations/org-1/users/${operator.id}`);
      expect(req.request.method).toBe('DELETE');
      req.flush({});
      fixture.detectChanges();

      expect(component.removing()).toBe(false);
      expect(component.removeError()).toBeNull();
      expect(component.members()).toHaveLength(3);
      expect(component.memberToRemove()).toBeNull();
    });

    it('should handle 403 when removing ADMIN member (forbidden)', () => {
      const orgAdmin = mockMembers[3];
      component.confirmRemoveMember(orgAdmin);
      component.removeMember();

      httpCtrl.expectOne(`/api/v1/organizations/org-1/users/${orgAdmin.id}`).flush(
        { detail: 'Cannot remove admin' },
        { status: 403, statusText: 'Forbidden' }
      );
      fixture.detectChanges();

      expect(component.removing()).toBe(false);
      expect(component.removeError()).toBe('org_settings.remove_member_forbidden');
      expect(component.memberToRemove()).not.toBeNull();
      expect(component.members()).toHaveLength(4);
    });

    it('should handle 404 when member not found', () => {
      const operator = mockMembers[1];
      component.confirmRemoveMember(operator);
      component.removeMember();

      httpCtrl.expectOne(`/api/v1/organizations/org-1/users/${operator.id}`).flush(
        '',
        { status: 404, statusText: 'Not Found' }
      );
      fixture.detectChanges();

      expect(component.removing()).toBe(false);
      expect(component.removeError()).toBe('org_settings.remove_member_not_found');
      expect(component.memberToRemove()).not.toBeNull();
    });

    it('should handle generic error on 500', () => {
      const operator = mockMembers[1];
      component.confirmRemoveMember(operator);
      component.removeMember();

      httpCtrl.expectOne(`/api/v1/organizations/org-1/users/${operator.id}`).flush('', { status: 500, statusText: 'Error' });
      fixture.detectChanges();

      expect(component.removing()).toBe(false);
      expect(component.removeError()).toBe('org_settings.remove_member_error');
    });

    it('should not remove if no member selected', () => {
      component.memberToRemove.set(null);
      component.removeMember();
      httpCtrl.expectNone('/api/v1/organizations/org-1/users//');
    });
  });

  describe('transfer ownership', () => {
    it('should open transfer modal', () => {
      component.openTransferModal();
      expect(component.transferTargetId).toBe('');
      expect(component.transferError()).toBeNull();
      expect(component.transferSuccess()).toBeNull();
      expect(component.showTransferModal()).toBe(true);
    });

    it('should close transfer modal when not transferring', () => {
      component.showTransferModal.set(true);
      component.closeTransferModal();
      expect(component.showTransferModal()).toBe(false);
    });

    it('should not close transfer modal when transferring', () => {
      component.showTransferModal.set(true);
      component.transferring.set(true);
      component.closeTransferModal();
      expect(component.showTransferModal()).toBe(true);
    });

    it('should not transfer if no target selected', () => {
      component.transferTargetId = '';
      component.confirmTransfer();
      httpCtrl.expectNone('/api/v1/organizations/org-1/transfer-ownership');
    });

    it('should transfer ownership and logout on success', () => {
      vi.useFakeTimers();
      fixture.detectChanges();
      httpCtrl.expectOne('/api/v1/organizations/org-1/users').flush([]);

      component.transferTargetId = 'user-2';
      component.confirmTransfer();

      const req = httpCtrl.expectOne('/api/v1/organizations/org-1/transfer-ownership');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ new_owner_id: 'user-2' });
      req.flush({});

      expect(component.transferSuccess()).toBe('org_settings.transfer_success');
      vi.advanceTimersByTime(2000);
      expect(authService.logout).toHaveBeenCalled();
      vi.useRealTimers();
    });

    it('should handle transfer error', () => {
      fixture.detectChanges();
      httpCtrl.expectOne('/api/v1/organizations/org-1/users').flush([]);

      component.transferTargetId = 'user-2';
      component.confirmTransfer();

      httpCtrl.expectOne('/api/v1/organizations/org-1/transfer-ownership').flush(
        { detail: 'Transfer failed' },
        { status: 400, statusText: 'Bad Request' }
      );

      expect(component.transferError()).toBe('Transfer failed');
      expect(component.transferring()).toBe(false);
    });

    it('should not transfer if transferring', () => {
      component.transferTargetId = 'user-2';
      component.transferring.set(true);
      component.confirmTransfer();
      httpCtrl.expectNone('/api/v1/organizations/org-1/transfer-ownership');
    });
  });

  describe('nonOwnerMembers', () => {
    it('should return only non-owner members', () => {
      fixture.detectChanges();
      httpCtrl.expectOne('/api/v1/organizations/org-1/users').flush(mockMembers);

      const nonOwners = component.nonOwnerMembers();
      expect(nonOwners).toHaveLength(3);
      expect(nonOwners.every(m => m.role !== 'MANAGER')).toBe(true);
    });
  });
});
