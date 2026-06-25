import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
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
}

@Component({
  selector: 'app-org-settings',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslatePipe],
  template: `
    <div class="org-settings-page">
      <div class="page-header">
        <h1 class="page-title">{{ 'org_settings.title' | t }}</h1>
      </div>

      <div class="tab-content">
        <div class="tab-toolbar">
          <h2 class="tab-title">{{ 'org_settings.members_title' | t }}</h2>
          <button class="btn-primary" (click)="openInviteModal()">
            {{ 'org_settings.invite_btn' | t }}
          </button>
        </div>

        <div *ngIf="membersLoading()" class="skeleton-list">
          <div class="skeleton-row" *ngFor="let i of [1,2,3]"></div>
        </div>

        <div *ngIf="membersError() && !membersLoading()" class="error-banner">{{ membersError() }}</div>

        <div *ngIf="!membersLoading() && !membersError()" class="data-table-wrap">
          <table class="data-table" *ngIf="members().length > 0; else membersEmpty">
            <thead>
              <tr>
                <th scope="col">{{ 'common.name' | t }}</th>
                <th scope="col">{{ 'common.email' | t }}</th>
                <th scope="col">{{ 'common.role' | t }}</th>
                <th scope="col">{{ 'common.actions' | t }}</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let member of members()" [class.row-locked]="member.role === 'MANAGER'">
                <td class="cell-primary" [attr.data-label]="'common.name' | t">
                  {{ member.display_name }}
                  <span class="self-tag" *ngIf="member.id === currentUserId">{{ 'org_settings.self_tag' | t }}</span>
                </td>
                <td class="cell-muted" [attr.data-label]="'common.email' | t">{{ member.email }}</td>
                <td [attr.data-label]="'common.role' | t">
                  <span *ngIf="member.role === 'MANAGER'" class="role-owner">{{ 'org_settings.role_owner' | t }}</span>
                  <span *ngIf="member.role !== 'MANAGER'" class="role-text">{{ 'org_settings.role_' + member.role.toLowerCase() | t }}</span>
                </td>
                <td class="cell-actions" [attr.data-label]="'common.actions' | t">
                  <button
                    *ngIf="member.role === 'MANAGER' && members().length > 1"
                    class="btn-ghost btn-transfer"
                    (click)="openTransferModal()"
                  >{{ 'org_settings.transfer_btn' | t }}</button>
                  <button
                    *ngIf="member.id !== currentUserId && member.role !== 'MANAGER'"
                    class="btn-ghost btn-danger-ghost"
                    (click)="confirmRemoveMember(member)"
                  >{{ 'common.delete' | t }}</button>
                </td>
              </tr>
            </tbody>
          </table>
          <ng-template #membersEmpty>
            <div class="empty-state">{{ 'org_settings.no_members' | t }}</div>
          </ng-template>
        </div>
      </div>
    </div>

    <!-- INVITE MODAL -->
    <div *ngIf="showInviteModal()" class="modal-overlay" (click)="closeInviteModal()">
      <div class="modal-panel" (click)="$event.stopPropagation()">
        <div class="modal-header">
          <h3 class="modal-title">{{ 'org_settings.invite_title' | t }}</h3>
          <button class="modal-close" (click)="closeInviteModal()">×</button>
        </div>
        <div class="form-group">
          <label for="invite-email">{{ 'common.email' | t }}<span class="required-star" aria-hidden="true">*</span></label>
          <input
            id="invite-email"
            type="email"
            [(ngModel)]="inviteEmail"
            aria-required="true"
            [placeholder]="'login.email_placeholder' | t"
          />
        </div>
        <div class="form-group">
          <label for="invite-role">{{ 'common.role' | t }}<span class="required-star" aria-hidden="true">*</span></label>
          <select id="invite-role" [(ngModel)]="inviteRole" class="form-group select" aria-required="true">
            <option value="OPERATOR">{{ 'org_settings.role_operator' | t }}</option>
            <option value="MANAGER">{{ 'org_settings.role_manager' | t }}</option>
          </select>
        </div>
        <div *ngIf="inviteError()" class="error-banner error-sm">{{ inviteError() }}</div>
        <div *ngIf="inviteSuccess()" class="alert-success">{{ inviteSuccess() }}</div>
        <div class="modal-footer">
          <button class="btn-ghost" (click)="closeInviteModal()">{{ 'common.cancel' | t }}</button>
          <button class="btn-primary" (click)="sendInvite()" [disabled]="inviting()" [title]="inviting() ? ('common.disabled_tooltip.operation_in_progress' | t) : ''">
            {{ inviting() ? ('common.loading' | t) : ('org_settings.send_invite' | t) }}
          </button>
        </div>
      </div>
    </div>

    <!-- TRANSFER OWNERSHIP MODAL -->
    <div *ngIf="showTransferModal()" class="modal-overlay" (click)="closeTransferModal()">
      <div class="modal-panel" (click)="$event.stopPropagation()">
        <div class="modal-header">
          <h3 class="modal-title">{{ 'org_settings.transfer_title' | t }}</h3>
          <button class="modal-close" (click)="closeTransferModal()">×</button>
        </div>
        <p class="modal-body-text transfer-warning">{{ 'org_settings.transfer_warning' | t }}</p>
        <div class="form-group">
          <label for="transfer-target">{{ 'org_settings.transfer_select_label' | t }}<span class="required-star" aria-hidden="true">*</span></label>
          <select id="transfer-target" [(ngModel)]="transferTargetId" class="form-group select" aria-required="true">
            <option value="">{{ 'org_settings.transfer_select_placeholder' | t }}</option>
            <option *ngFor="let m of nonOwnerMembers()" [value]="m.id">
              {{ m.display_name }} ({{ 'org_settings.role_' + m.role.toLowerCase() | t }})
            </option>
          </select>
        </div>
        <div *ngIf="transferError()" class="error-banner error-sm">{{ transferError() }}</div>
        <div *ngIf="transferSuccess()" class="alert-success">{{ transferSuccess() }}</div>
        <div class="modal-footer">
          <button class="btn-ghost" (click)="closeTransferModal()" [disabled]="transferring()" [title]="transferring() ? ('common.disabled_tooltip.operation_in_progress' | t) : ''">{{ 'common.cancel' | t }}</button>
          <button class="btn-danger" (click)="confirmTransfer()" [disabled]="transferring() || !transferTargetId" [title]="!transferTargetId ? ('common.disabled_tooltip.no_target' | t) : ('common.disabled_tooltip.operation_in_progress' | t)">
            {{ transferring() ? ('common.loading' | t) : ('org_settings.transfer_confirm_btn' | t) }}
          </button>
        </div>
      </div>
    </div>

    <!-- CONFIRM REMOVE MODAL -->
    <div *ngIf="memberToRemove()" class="modal-overlay" (click)="cancelRemoveMember()">
      <div class="modal-panel" (click)="$event.stopPropagation()">
        <div class="modal-header">
          <h3 class="modal-title">{{ 'org_settings.remove_member_title' | t }}</h3>
          <button class="modal-close" (click)="cancelRemoveMember()">×</button>
        </div>
        <p class="modal-body-text">{{ 'org_settings.remove_member_confirm' | t: { name: memberToRemove()!.display_name } }}</p>
        <div class="modal-footer">
          <button class="btn-ghost" (click)="cancelRemoveMember()">{{ 'common.cancel' | t }}</button>
          <button class="btn-danger" (click)="removeMember()" [disabled]="removing()" [title]="removing() ? ('common.disabled_tooltip.operation_in_progress' | t) : ''">
            {{ removing() ? ('common.loading' | t) : ('common.delete' | t) }}
          </button>
        </div>
      </div>
    </div>

    
  `,
  styles: [`
    :host { display: block; }

    .org-settings-page { padding: 0; }

    .page-header {
      display: flex;
      align-items: baseline;
      gap: var(--spacing-md);
      margin-bottom: var(--spacing-lg);
    }

    .page-title {
      font-family: var(--font-display);
      font-size: 2.25rem;
      font-weight: 400;
      line-height: 1.1;
      letter-spacing: -0.02em;
      margin: 0;
      color: var(--ink);
    }

    .admin-tabs {
      display: flex;
      gap: 0.125rem;
      border-bottom: 0.0625rem solid var(--border);
      margin-bottom: var(--spacing-lg);
    }

    .admin-tab {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
      background: none;
      border: none;
      border-bottom: 0.125rem solid transparent;
      padding: var(--spacing-sm) var(--spacing-md);
      cursor: pointer;
      margin-bottom: -0.0625rem;
      transition: color 0.12s ease, border-color 0.12s ease;
    }

    .admin-tab:hover { color: var(--ink); }
    .admin-tab-active { color: var(--ink); border-bottom-color: var(--accent); }

    .tab-content { animation: fadeIn 0.12s ease; }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(0.25rem); }
      to   { opacity: 1; transform: translateY(0); }
    }

    .tab-toolbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: var(--spacing-md);
    }

    .tab-title {
      font-family: var(--font-display);
      font-size: 1.5rem;
      font-weight: 400;
      line-height: 1.2;
      letter-spacing: -0.01em;
      color: var(--ink);
      margin: 0;
    }

    .toolbar-actions {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);
    }

    .data-table-wrap {
      background: var(--surface-raised);
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-lg);
      overflow: hidden;
    }

    .data-table { width: 100%; border-collapse: collapse; }

    .data-table th {
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
      padding: var(--spacing-sm) var(--spacing-md);
      text-align: left;
      vertical-align: middle;
      border-bottom: 0.0625rem solid var(--border);
      background: var(--paper-secondary);
      height: 2.5rem;
    }

    .data-table th:last-child { text-align: center; }

    .data-table td {
      font-size: 0.8125rem;
      color: var(--ink);
      padding: var(--spacing-sm) var(--spacing-md);
      border-bottom: 0.0625rem solid var(--border);
      vertical-align: middle;
      height: 2.75rem;
    }

    .data-table tr:last-child td { border-bottom: none; }
    .data-table tr:hover td { background: var(--paper-secondary); }

    .cell-primary { font-weight: 500; }
    .cell-muted { color: var(--muted); }

    .cell-actions {
      white-space: nowrap;
      display: flex;
      gap: var(--spacing-sm);
      justify-content: center;
      align-items: center;
    }

    .btn-primary {
      display: inline-flex;
      align-items: center;
      background: var(--ink);
      color: var(--paper);
      border: 0.0625rem solid var(--ink);
      border-radius: var(--rounded-md);
      padding: 0.5625rem 1.125rem;
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      cursor: pointer;
      text-decoration: none;
      transition: background-color 0.15s ease;
    }

    .btn-primary:hover:not(:disabled) { background: var(--ink-secondary); }
    .btn-primary:disabled { opacity: 0.45; cursor: not-allowed; }

    .btn-danger {
      display: inline-flex;
      align-items: center;
      background: var(--verdict-invalid);
      color: var(--paper);
      border: 0.0625rem solid var(--verdict-invalid);
      border-radius: var(--rounded-md);
      padding: 0.5625rem 1.125rem;
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      cursor: pointer;
      transition: background-color 0.15s ease;
    }

    .btn-danger:hover:not(:disabled) { background: var(--verdict-invalid-bg); color: var(--verdict-invalid); }
    .btn-danger:disabled { opacity: 0.45; cursor: not-allowed; }

    .btn-ghost {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--muted);
      background: none;
      border: 0.0625rem solid transparent;
      border-radius: var(--rounded-md);
      padding: 0.25rem 0.625rem;
      cursor: pointer;
      transition: color 0.12s ease, background-color 0.12s ease, border-color 0.12s ease;
    }

    .btn-ghost:hover:not(:disabled) { color: var(--ink); background: var(--paper-secondary); border-color: var(--border); }
    .btn-ghost:disabled { opacity: 0.45; cursor: not-allowed; }

    .btn-danger-ghost { color: var(--verdict-invalid); }
    .btn-danger-ghost:hover:not(:disabled) { background: var(--verdict-invalid-bg); border-color: var(--verdict-invalid-border); }

    .btn-transfer { color: var(--verdict-warning); }
    .btn-transfer:hover:not(:disabled) { background: rgba(232, 213, 163, 0.15); border-color: var(--verdict-warning); }

    .transfer-warning { color: var(--verdict-warning); }

    .role-text {
      font-family: var(--font-sans);
      font-size: 0.8125rem;
      color: var(--ink);
      font-weight: 500;
    }

    .role-owner {
      font-family: var(--font-sans);
      font-size: 0.8125rem;
      font-weight: 600;
      color: var(--verdict-warning);
    }

    .self-tag {
      display: inline-flex;
      align-items: center;
      font-family: var(--font-mono);
      font-size: 0.625rem;
      font-weight: 600;
      letter-spacing: 0.04em;
      color: var(--muted);
      background: var(--paper-secondary);
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-sm);
      padding: 0.0625rem 0.3125rem;
      margin-left: var(--spacing-sm);
      vertical-align: middle;
    }

    .status-badge {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      border-radius: var(--rounded-sm);
      padding: 0.125rem 0.5rem;
      background: var(--verdict-valid-bg);
      color: var(--verdict-valid);
      border: 0.0625rem solid var(--verdict-valid-border);
    }

    .status-badge.status-archived {
      background: var(--verdict-unevaluated-bg);
      color: var(--verdict-unevaluated);
      border-color: var(--verdict-unevaluated-border);
    }

    .empty-state {
      padding: var(--spacing-xl) var(--spacing-lg);
      text-align: center;
      font-size: 0.8125rem;
      color: var(--muted);
    }

    .skeleton-list { display: flex; flex-direction: column; gap: var(--spacing-sm); }

    .skeleton-row {
      height: 2.75rem;
      border-radius: var(--rounded-md);
      background: linear-gradient(90deg, var(--paper-secondary) 25%, #e5e2db 50%, var(--paper-secondary) 75%);
      background-size: 200% 100%;
      animation: shimmer 1.6s linear infinite;
    }

    @keyframes shimmer {
      0%   { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }

    .error-banner {
      background: var(--verdict-invalid-bg);
      color: var(--verdict-invalid);
      border: 0.0625rem solid var(--verdict-invalid-border);
      border-radius: var(--rounded-md);
      padding: var(--spacing-sm) var(--spacing-md);
      font-size: 0.8125rem;
      margin-bottom: var(--spacing-md);
    }

    .error-sm { margin-bottom: 0; margin-top: var(--spacing-sm);     }

    .modal-overlay {
      position: fixed;
      inset: 0;
      background: var(--overlay);
      z-index: 100;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .modal-panel {
      background: var(--surface-raised);
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-lg);
      padding: var(--spacing-lg);
      width: 30rem;
      max-width: calc(100vw - 3rem);
      max-height: calc(100vh - 5rem);
      overflow-y: auto;
    }

    .modal-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: var(--spacing-lg);
    }

    .modal-title {
      font-size: 1rem;
      font-weight: 600;
      line-height: 1.4;
      margin: 0;
    }

    .modal-close {
      font-size: 1.25rem;
      color: var(--muted);
      background: none;
      border: none;
      cursor: pointer;
      padding: 0 0.25rem;
      line-height: 1;
      transition: color 0.12s ease;
    }

    .modal-close:hover { color: var(--ink); }

    .modal-footer {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: var(--spacing-sm);
      margin-top: var(--spacing-lg);
      padding-top: var(--spacing-md);
      border-top: 0.0625rem solid var(--border);
    }

    .modal-body-text {
      font-family: var(--font-sans);
      font-size: 0.875rem;
      color: var(--ink);
      line-height: 1.65;
      margin: 0 0 var(--spacing-md);
    }

    .form-group { margin-bottom: var(--spacing-md); }

    .form-group label {
      display: block;
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--ink);
      margin-bottom: var(--spacing-xs);
    }

    .required-star {
      color: var(--verdict-invalid);
      margin-left: 0.25rem;
      font-size: 0.75rem;
    }

    .form-group input[type=text],
    .form-group input[type=email],
    .form-group select,
    .form-group textarea {
      width: 100%;
      background: var(--paper);
      color: var(--ink);
      border: 0.0625rem solid var(--border-strong);
      border-radius: var(--rounded-md);
      padding: 0.5625rem 0.75rem;
      font-family: var(--font-sans);
      font-size: 0.9375rem;
      outline: none;
      transition: border-color 0.15s ease, background-color 0.15s ease, box-shadow 0.15s ease;
    }

    .form-group input:focus,
    .form-group select:focus,
    .form-group textarea:focus {
      border-color: var(--ink);
      background: var(--surface-raised);
      box-shadow: 0 0 0 0.1875rem rgba(232, 213, 163, 0.4);
    }

    .row-locked td {
      background: rgba(232, 213, 163, 0.05);
    }

    .select {
      width: 100%;
      background: var(--paper);
      color: var(--ink);
      border: 0.0625rem solid var(--border-strong);
      border-radius: var(--rounded-md);
      padding: 0.5625rem 0.75rem;
      font-family: var(--font-sans);
      font-size: 0.9375rem;
      outline: none;
      cursor: pointer;
    }

    @media (max-width: 48rem) {
      .page-title { font-size: 1.75rem; }

      .data-table-wrap { overflow-x: visible; }

      .data-table,
      .data-table tbody,
      .data-table tr,
      .data-table td {
        display: block;
      }

      .data-table thead {
        display: none;
      }

      .data-table tr {
        margin-bottom: var(--spacing-sm);
        border: 0.0625rem solid var(--border);
        border-radius: var(--rounded-md);
        background: var(--surface-raised);
      }

      .data-table tr:last-child {
        margin-bottom: 0;
      }

      .data-table td {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: var(--spacing-sm) var(--spacing-md);
        border-bottom: 0.0625rem solid var(--border);
        height: auto;
        min-height: 2.5rem;
        text-align: right;
      }

      .data-table td:last-child {
        border-bottom: none;
      }

      .data-table tr:hover td {
        background: transparent;
      }

      .data-table td::before {
        content: attr(data-label);
        font-family: var(--font-sans);
        font-size: 0.6875rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--muted);
        margin-right: var(--spacing-md);
        flex-shrink: 0;
        text-align: left;
        white-space: nowrap;
      }

      .row-locked {
        border-color: var(--verdict-warning-border, var(--verdict-warning));
      }

      .row-locked td {
        background: rgba(232, 213, 163, 0.05);
      }

      .admin-tabs { overflow-x: auto; white-space: nowrap; }

      .tab-toolbar {
        flex-direction: column;
        align-items: flex-start;
        gap: var(--spacing-sm);
      }

      .tab-toolbar .btn-primary { width: 100%; }

      .modal-panel {
        width: calc(100vw - 1.5rem);
        max-width: none;
        padding: var(--spacing-md);
        max-height: calc(100vh - 3rem);
      }

      .modal-header { margin-bottom: var(--spacing-md); }
      .modal-title { font-size: 0.9375rem; }

      .modal-footer {
        flex-direction: column-reverse;
        gap: var(--spacing-xs);
        margin-top: var(--spacing-md);
        padding-top: var(--spacing-sm);
      }

      .modal-footer .btn-primary,
      .modal-footer .btn-danger,
      .modal-footer .btn-ghost {
        width: 100%;
        justify-content: center;
        padding: 0.625rem 1rem;
        min-height: 2.75rem;
      }

      .form-group input[type=text],
      .form-group input[type=email],
      .form-group select,
      .form-group textarea {
        padding: 0.625rem 0.75rem;
        min-height: 2.75rem;
        font-size: 0.875rem;
      }

      .form-group label { font-size: 0.625rem; }

      .modal-body-text { font-size: 0.8125rem; }

      .tab-title { font-size: 1.25rem; }
    }
  `],
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
    this.memberToRemove.set(member);
  }

  cancelRemoveMember(): void {
    this.memberToRemove.set(null);
  }

  removeMember(): void {
    const member = this.memberToRemove();
    if (!member) return;
    this.removing.set(true);

    this.http.delete(`/api/v1/organizations/${this.orgId}/users/${member.id}`)
      .pipe(catchError(() => {
        this.removing.set(false);
        return of(null);
      }))
      .subscribe(() => {
        this.removing.set(false);
        this.members.update(members => members.filter(m => m.id !== member.id));
        this.memberToRemove.set(null);
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