import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { of, throwError } from 'rxjs';
import { OrgSettingsComponent } from './org-settings.component';
import { AuthService } from '../../core/services/auth.service';
import { TranslationService } from '../../core/i18n/translation.service';

const tsMock = {
  translateInstant: vi.fn((key: string) => key),
};

interface MockUser {
  id: string;
  email: string;
  display_name: string;
  role: 'VIEWER' | 'OPERATOR' | 'ADMIN' | 'MANAGER';
  organization_id?: string;
}

const createMockAuthService = (user: MockUser | null) => {
  return {
    getUser: vi.fn(() => user),
    getUserRole: vi.fn(() => user?.role ?? ''),
    logout: vi.fn(),
  };
};

const mockMembers: MockUser[] = [
  { id: 'user-1', email: 'admin@test.com', display_name: 'Admin User', role: 'MANAGER' },
  { id: 'user-2', email: 'op@test.com', display_name: 'Operator User', role: 'OPERATOR' },
  { id: 'user-3', email: 'viewer@test.com', display_name: 'Viewer User', role: 'VIEWER' },
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
      component.ngOnInit();
      const req = httpCtrl.expectOne('/api/v1/organizations/org-1/users');
      expect(req.request.method).toBe('GET');
      req.flush(mockMembers);
      fixture.detectChanges();

      expect(component.members()).toEqual(mockMembers);
      expect(component.membersLoading()).toBe(false);
      expect(component.membersError()).toBeNull();
    });

    it('should set error when orgId is missing', () => {
      authService.getUser.mockReturnValueOnce({ ...userWithOrg, organization_id: '' });
      component.ngOnInit();
      fixture.detectChanges();

      expect(component.membersError()).toBe('org_settings.no_organization');
      expect(component.membersLoading()).toBe(false);
      httpCtrl.expectNone('/api/v1/organizations//users');
    });

    it('should set error on HTTP failure', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations/org-1/users').flush('', { status: 500, statusText: 'Error' });
      fixture.detectChanges();

      expect(component.membersError()).toBe('org_settings.loading_members_error');
      expect(component.membersLoading()).toBe(false);
    });

    it('should show skeleton while loading', () => {
      component.ngOnInit();
      fixture.detectChanges();

      expect(component.membersLoading()).toBe(true);
      const skeletonRows = fixture.nativeElement.querySelectorAll('.skeleton-row');
      expect(skeletonRows.length).toBe(3);
    });

    it('should show error banner when error occurs', () => {
      component.ngOnInit();
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
      expect(component.inviteRole).toBe('VIEWER');
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

  describe('role change', () => {
    it('should update member role on role change', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations/org-1/users').flush(mockMembers);
      fixture.detectChanges();

      const member = mockMembers[1];
      const event = { target: { value: 'ADMIN' } } as unknown as Event;
      component.onRoleChange(member, event);

      const req = httpCtrl.expectOne(`/api/v1/organizations/org-1/users/${member.id}/role`);
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual({ role: 'ADMIN' });
      req.flush({});

      expect(component.members()[1].role).toBe('ADMIN');
    });

    it('should revert role on error', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations/org-1/users').flush(mockMembers);
      fixture.detectChanges();

      const member = mockMembers[1];
      const event = { target: { value: 'ADMIN' } } as unknown as Event;
      component.onRoleChange(member, event);

      httpCtrl.expectOne(`/api/v1/organizations/org-1/users/${member.id}/role`).flush('', { status: 500, statusText: 'Error' });
      fixture.detectChanges();

      expect(component.members()[1].role).toBe('OPERATOR');
    });
  });

  describe('remove member', () => {
    it('should open confirm remove modal', () => {
      const member = mockMembers[1];
      component.confirmRemoveMember(member);
      expect(component.memberToRemove()).toBe(member);
    });

    it('should cancel remove member', () => {
      component.memberToRemove.set(mockMembers[1]);
      component.cancelRemoveMember();
      expect(component.memberToRemove()).toBeNull();
    });

    it('should remove member successfully', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations/org-1/users').flush(mockMembers);
      fixture.detectChanges();

      component.confirmRemoveMember(mockMembers[1]);
      component.removeMember();

      const req = httpCtrl.expectOne(`/api/v1/organizations/org-1/users/${mockMembers[1].id}`);
      expect(req.request.method).toBe('DELETE');
      req.flush({});
      fixture.detectChanges();

      expect(component.removing()).toBe(false);
      expect(component.members()).toHaveLength(2);
      expect(component.memberToRemove()).toBeNull();
    });

    it('should handle remove error', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations/org-1/users').flush(mockMembers);
      fixture.detectChanges();

      component.confirmRemoveMember(mockMembers[1]);
      component.removeMember();

      httpCtrl.expectOne(`/api/v1/organizations/org-1/users/${mockMembers[1].id}`).flush('', { status: 500, statusText: 'Error' });
      fixture.detectChanges();

      expect(component.removing()).toBe(false);
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
      component.transferTargetId = 'user-2';
      component.confirmTransfer();

      const req = httpCtrl.expectOne('/api/v1/organizations/org-1/transfer-ownership');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ new_owner_id: 'user-2' });
      req.flush({});
      fixture.detectChanges();

      expect(component.transferSuccess()).toBe('org_settings.transfer_success');
      expect(authService.logout).toHaveBeenCalled();
    });

    it('should handle transfer error', () => {
      component.transferTargetId = 'user-2';
      component.confirmTransfer();

      httpCtrl.expectOne('/api/v1/organizations/org-1/transfer-ownership').flush(
        { detail: 'Transfer failed' },
        { status: 400, statusText: 'Bad Request' }
      );
      fixture.detectChanges();

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
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations/org-1/users').flush(mockMembers);
      fixture.detectChanges();

      const nonOwners = component.nonOwnerMembers();
      expect(nonOwners).toHaveLength(2);
      expect(nonOwners.every(m => m.role !== 'MANAGER')).toBe(true);
    });
  });
});
