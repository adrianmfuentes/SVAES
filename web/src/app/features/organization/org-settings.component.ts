import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { catchError, of } from 'rxjs';
import { AuthService } from '../../core/services/auth.service';
import { TranslationService } from '../../core/i18n/translation.service';
import { TranslatePipe } from '../../core/i18n/translate.pipe';



interface OrgUser {
  id: string;
  email: string;
  display_name: string;
  role: 'OPERATOR' | 'ADMIN' | 'MANAGER';
  is_active: boolean;
}

@Component({
  selector: 'app-org-settings',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslatePipe],
  templateUrl: './org-settings.component.html',
  styleUrls: ['./org-settings.component.scss'],
})
export class OrgSettingsComponent implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly authService = inject(AuthService);
  private readonly ts = inject(TranslationService);

  readonly currentUserId = this.authService.getUser()?.id ?? '';
  readonly currentUserRole = this.authService.getUserRole();
  readonly orgId = this.authService.getUser()?.organization_id ?? '';

  // Members
  members = signal<OrgUser[]>([]);
  membersLoading = signal(true);
  membersError = signal<string | null>(null);

  // Invite modal
  showInviteModal = signal(false);
  inviteEmail = '';
  inviteRole: 'OPERATOR' | 'MANAGER' = 'OPERATOR';
  inviteError = signal<string | null>(null);
  inviteSuccess = signal<string | null>(null);
  inviting = signal(false);

  // Remove member modal
  memberToRemove = signal<OrgUser | null>(null);
  removing = signal(false);
  removeError = signal<string | null>(null);

  // Transfer ownership modal
  showTransferModal = signal(false);
  transferTargetId = '';
  transferring = signal(false);
  transferError = signal<string | null>(null);
  transferSuccess = signal<string | null>(null);

  nonOwnerMembers(): OrgUser[] {
    return this.members().filter(m => m.role !== 'MANAGER');
  }

  ngOnInit(): void {
    if (!this.orgId) {
      this.membersError.set(this.ts.translateInstant('org_settings.no_organization'));
      this.membersLoading.set(false);
      return;
    }
    this.loadMembers();
  }

  private loadMembers(): void {
    this.membersLoading.set(true);
    this.http.get<OrgUser[]>(`/api/v1/organizations/${this.orgId}/users`)
      .pipe(catchError(() => {
        this.membersError.set(this.ts.translateInstant('org_settings.loading_members_error'));
        return of([] as OrgUser[]);
      }))
      .subscribe(data => {
        this.members.set(data);
        this.membersLoading.set(false);
      });
  }

  openInviteModal(): void {
    this.inviteEmail = '';
    this.inviteRole = 'OPERATOR';
    this.inviteError.set(null);
    this.inviteSuccess.set(null);
    this.showInviteModal.set(true);
  }

  closeInviteModal(): void {
    this.showInviteModal.set(false);
  }

  sendInvite(): void {
    if (!this.inviteEmail) return;
    this.inviting.set(true);
    this.inviteError.set(null);
    this.inviteSuccess.set(null);

    this.http.post(`/api/v1/organizations/${this.orgId}/users/invite`, {
      email: this.inviteEmail,
      role: this.inviteRole,
    }).pipe(
      catchError(err => {
        const msg = err.error?.detail || this.ts.translateInstant('org_settings.invite_error');
        this.inviteError.set(msg);
        return of(null);
      })
    ).subscribe(res => {
      this.inviting.set(false);
      if (res) {
        this.inviteSuccess.set(this.ts.translateInstant('org_settings.invite_success'));
        setTimeout(() => this.closeInviteModal(), 1500);
      }
    });
  }

  confirmRemoveMember(member: OrgUser): void {
    this.removeError.set(null);
    this.memberToRemove.set(member);
  }

  cancelRemoveMember(): void {
    this.removeError.set(null);
    this.memberToRemove.set(null);
  }

  removeMember(): void {
    const member = this.memberToRemove();
    if (!member) return;
    this.removing.set(true);
    this.removeError.set(null);

    this.http.delete(`/api/v1/organizations/${this.orgId}/users/${member.id}`).subscribe({
      next: () => {
        this.removing.set(false);
        this.members.update(members => members.filter(m => m.id !== member.id));
        this.memberToRemove.set(null);
      },
      error: (err: HttpErrorResponse) => {
        this.removing.set(false);
        if (err.status === 403) {
          this.removeError.set(this.ts.translateInstant('org_settings.remove_member_forbidden'));
        } else if (err.status === 404) {
          this.removeError.set(this.ts.translateInstant('org_settings.remove_member_not_found'));
        } else {
          this.removeError.set(this.ts.translateInstant('org_settings.remove_member_error'));
        }
      },
    });
  }

  openTransferModal(): void {
    this.transferTargetId = '';
    this.transferError.set(null);
    this.transferSuccess.set(null);
    this.showTransferModal.set(true);
  }

  closeTransferModal(): void {
    if (!this.transferring()) {
      this.showTransferModal.set(false);
    }
  }

  confirmTransfer(): void {
    if (!this.transferTargetId || this.transferring()) return;
    this.transferring.set(true);
    this.transferError.set(null);

    this.http.post(`/api/v1/organizations/${this.orgId}/transfer-ownership`, {
      new_owner_id: this.transferTargetId,
    }).pipe(
      catchError(err => {
        const msg = err.error?.detail || this.ts.translateInstant('org_settings.transfer_error');
        this.transferError.set(msg);
        this.transferring.set(false);
        return of(null);
      })
    ).subscribe(res => {
      if (res !== null) {
        this.transferSuccess.set(this.ts.translateInstant('org_settings.transfer_success'));
        setTimeout(() => {
          this.authService.logout();
        }, 2000);
      }
    });
  }
}