import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { catchError, of } from 'rxjs';
import { AuthService } from '../../core/services/auth.service';
import { TranslationService } from '../../core/i18n/translation.service';
import { TranslatePipe } from '../../core/i18n/translate.pipe';

type OrgSettingsTab = 'members' | 'projects';

interface OrgUser {
  id: string;
  email: string;
  display_name: string;
  role: 'VIEWER' | 'OPERATOR' | 'ADMIN' | 'MANAGER';
}

interface Project {
  id: string;
  name: string;
  description: string;
  is_archived: boolean;
  created_at: string | null;
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

      <nav class="admin-tabs">
        <button
          *ngFor="let tab of tabs"
          class="admin-tab"
          [class.admin-tab-active]="activeTab() === tab.id"
          (click)="setTab(tab.id)"
        >{{ tab.label }}</button>
      </nav>

      <!-- MEMBERS TAB -->
      <div *ngIf="activeTab() === 'members'" class="tab-content">
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
                <th>{{ 'common.name' | t }}</th>
                <th>{{ 'common.email' | t }}</th>
                <th>{{ 'common.role' | t }}</th>
                <th>{{ 'common.actions' | t }}</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let member of members()" [class.row-locked]="member.role === 'OWNER'">
                <td class="cell-primary">
                  {{ member.display_name }}
                  <span class="self-tag" *ngIf="member.id === currentUserId">{{ 'org_settings.self_tag' | t }}</span>
                </td>
                <td class="cell-muted">{{ member.email }}</td>
                <td>
                  <select
                    *ngIf="member.role !== 'OWNER' && member.id !== currentUserId"
                    class="role-select"
                    [value]="member.role"
                    (change)="onRoleChange(member, $event)"
                  >
                    <option value="VIEWER">{{ 'org_settings.role_viewer' | t }}</option>
                    <option value="OPERATOR">{{ 'org_settings.role_operator' | t }}</option>
                    <option value="MANAGER">{{ 'org_settings.role_manager' | t }}</option>
                  </select>
                  <span *ngIf="member.role === 'OWNER'" class="role-owner">{{ 'org_settings.role_owner' | t }}</span>
                  <span *ngIf="member.id === currentUserId && member.role !== 'OWNER'" class="role-text">{{ 'org_settings.role_' + member.role.toLowerCase() | t }}</span>
                </td>
                <td class="cell-actions">
                  <button
                    *ngIf="member.id !== currentUserId && member.role !== 'OWNER'"
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

      <!-- PROJECTS TAB -->
      <div *ngIf="activeTab() === 'projects'" class="tab-content">
        <div class="tab-toolbar">
          <h2 class="tab-title">{{ 'org_settings.projects_title' | t }}</h2>
        </div>

        <div *ngIf="projectsLoading()" class="skeleton-list">
          <div class="skeleton-row" *ngFor="let i of [1,2,3]"></div>
        </div>

        <div *ngIf="projectsError() && !projectsLoading()" class="error-banner">{{ projectsError() }}</div>

        <div *ngIf="!projectsLoading() && !projectsError()" class="data-table-wrap">
          <table class="data-table" *ngIf="projects().length > 0; else projectsEmpty">
            <thead>
              <tr>
                <th>{{ 'common.name' | t }}</th>
                <th>{{ 'common.description' | t }}</th>
                <th>{{ 'common.status' | t }}</th>
                <th>{{ 'common.actions' | t }}</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let project of projects()">
                <td class="cell-primary">{{ project.name }}</td>
                <td class="cell-muted">{{ project.description || '—' }}</td>
                <td>
                  <span class="status-badge" [class.status-archived]="project.is_archived">
                    {{ (project.is_archived ? 'projects.status_archived' : 'projects.status_active') | t }}
                  </span>
                </td>
                <td class="cell-actions">
                  <button
                    *ngIf="!project.is_archived"
                    class="btn-ghost"
                    (click)="confirmArchiveProject(project)"
                  >{{ 'org_settings.archive_btn' | t }}</button>
                </td>
              </tr>
            </tbody>
          </table>
          <ng-template #projectsEmpty>
            <div class="empty-state">{{ 'org_settings.no_projects' | t }}</div>
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
          <label for="invite-email">{{ 'common.email' | t }}</label>
          <input
            id="invite-email"
            type="email"
            [(ngModel)]="inviteEmail"
            [placeholder]="'login.email_placeholder' | t"
          />
        </div>
        <div class="form-group">
          <label for="invite-role">{{ 'common.role' | t }}</label>
          <select id="invite-role" [(ngModel)]="inviteRole" class="form-group select">
            <option value="VIEWER">{{ 'org_settings.role_viewer' | t }}</option>
            <option value="OPERATOR">{{ 'org_settings.role_operator' | t }}</option>
            <option value="MANAGER">{{ 'org_settings.role_manager' | t }}</option>
          </select>
        </div>
        <div *ngIf="inviteError()" class="error-banner error-sm">{{ inviteError() }}</div>
        <div *ngIf="inviteSuccess()" class="success-banner">{{ inviteSuccess() }}</div>
        <div class="modal-footer">
          <button class="btn-ghost" (click)="closeInviteModal()">{{ 'common.cancel' | t }}</button>
          <button class="btn-primary" (click)="sendInvite()" [disabled]="inviting()">
            {{ inviting() ? ('common.loading' | t) : ('org_settings.send_invite' | t) }}
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
          <button class="btn-danger" (click)="removeMember()" [disabled]="removing()">
            {{ removing() ? ('common.loading' | t) : ('common.delete' | t) }}
          </button>
        </div>
      </div>
    </div>

    <!-- CONFIRM ARCHIVE MODAL -->
    <div *ngIf="projectToArchive()" class="modal-overlay" (click)="cancelArchiveProject()">
      <div class="modal-panel" (click)="$event.stopPropagation()">
        <div class="modal-header">
          <h3 class="modal-title">{{ 'org_settings.archive_project_title' | t }}</h3>
          <button class="modal-close" (click)="cancelArchiveProject()">×</button>
        </div>
        <p class="modal-body-text">{{ 'org_settings.archive_project_confirm' | t: { name: projectToArchive()!.name } }}</p>
        <div class="modal-footer">
          <button class="btn-ghost" (click)="cancelArchiveProject()">{{ 'common.cancel' | t }}</button>
          <button class="btn-primary" (click)="archiveProject()" [disabled]="archiving()">
            {{ archiving() ? ('common.loading' | t) : ('org_settings.archive_btn' | t) }}
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
      gap: 2px;
      border-bottom: 1px solid var(--border);
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
      border-bottom: 2px solid transparent;
      padding: var(--spacing-sm) var(--spacing-md);
      cursor: pointer;
      margin-bottom: -1px;
      transition: color 0.12s ease, border-color 0.12s ease;
    }

    .admin-tab:hover { color: var(--ink); }
    .admin-tab-active { color: var(--ink); border-bottom-color: var(--accent); }

    .tab-content { animation: fadeIn 0.12s ease; }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(4px); }
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

    .data-table-wrap {
      background: var(--surface-raised);
      border: 1px solid var(--border);
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
      border-bottom: 1px solid var(--border);
      background: var(--paper-secondary);
      height: 40px;
    }

    .data-table td {
      font-size: 0.8125rem;
      color: var(--ink);
      padding: var(--spacing-sm) var(--spacing-md);
      border-bottom: 1px solid var(--border);
      vertical-align: middle;
      height: 44px;
    }

    .data-table tr:last-child td { border-bottom: none; }
    .data-table tr:hover td { background: var(--paper-secondary); }

    .cell-primary { font-weight: 500; }
    .cell-muted { color: var(--muted); }

    .cell-actions {
      text-align: right;
      white-space: nowrap;
      display: flex;
      gap: var(--spacing-sm);
      justify-content: flex-end;
      align-items: center;
    }

    .btn-primary {
      display: inline-flex;
      align-items: center;
      background: var(--ink);
      color: var(--paper);
      border: 1px solid var(--ink);
      border-radius: var(--rounded-md);
      padding: 9px 18px;
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
      border: 1px solid var(--verdict-invalid);
      border-radius: var(--rounded-md);
      padding: 9px 18px;
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
      border: 1px solid transparent;
      border-radius: var(--rounded-md);
      padding: 4px 10px;
      cursor: pointer;
      transition: color 0.12s ease, background-color 0.12s ease, border-color 0.12s ease;
    }

    .btn-ghost:hover:not(:disabled) { color: var(--ink); background: var(--paper-secondary); border-color: var(--border); }
    .btn-ghost:disabled { opacity: 0.45; cursor: not-allowed; }

    .btn-danger-ghost { color: var(--verdict-invalid); }
    .btn-danger-ghost:hover:not(:disabled) { background: var(--verdict-invalid-bg); border-color: var(--verdict-invalid-border); }

    .role-select {
      font-family: var(--font-sans);
      font-size: 0.8125rem;
      color: var(--ink);
      background: var(--paper);
      border: 1px solid var(--border-strong);
      border-radius: var(--rounded-md);
      padding: 3px 6px;
      outline: none;
      cursor: pointer;
    }

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
      border: 1px solid var(--border);
      border-radius: var(--rounded-sm);
      padding: 1px 5px;
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
      padding: 2px 8px;
      background: var(--verdict-valid-bg);
      color: var(--verdict-valid);
      border: 1px solid var(--verdict-valid-border);
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
      height: 44px;
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
      border: 1px solid var(--verdict-invalid-border);
      border-radius: var(--rounded-md);
      padding: var(--spacing-sm) var(--spacing-md);
      font-size: 0.8125rem;
      margin-bottom: var(--spacing-md);
    }

    .error-sm { margin-bottom: 0; margin-top: var(--spacing-sm); }

    .success-banner {
      background: var(--verdict-valid-bg);
      color: var(--verdict-valid);
      border: 1px solid var(--verdict-valid-border);
      border-radius: var(--rounded-md);
      padding: var(--spacing-sm) var(--spacing-md);
      font-size: 0.8125rem;
      margin-bottom: var(--spacing-md);
    }

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
      border: 1px solid var(--border);
      border-radius: var(--rounded-lg);
      padding: var(--spacing-lg);
      width: 480px;
      max-width: calc(100vw - 48px);
      max-height: calc(100vh - 80px);
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
      padding: 0 4px;
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
      border-top: 1px solid var(--border);
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

    .form-group input[type=text],
    .form-group input[type=email],
    .form-group select,
    .form-group textarea {
      width: 100%;
      background: var(--paper);
      color: var(--ink);
      border: 1px solid var(--border-strong);
      border-radius: var(--rounded-md);
      padding: 9px 12px;
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
      box-shadow: 0 0 0 3px rgba(232, 213, 163, 0.4);
    }

    .row-locked td {
      background: rgba(232, 213, 163, 0.05);
    }

    .select {
      width: 100%;
      background: var(--paper);
      color: var(--ink);
      border: 1px solid var(--border-strong);
      border-radius: var(--rounded-md);
      padding: 9px 12px;
      font-family: var(--font-sans);
      font-size: 0.9375rem;
      outline: none;
      cursor: pointer;
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

  get tabs(): { id: OrgSettingsTab; label: string }[] {
    return [
      { id: 'members', label: this.ts.translateInstant('org_settings.tab_members') },
      { id: 'projects', label: this.ts.translateInstant('org_settings.tab_projects') },
    ];
  }

  activeTab = signal<OrgSettingsTab>('members');

  // Members
  members = signal<OrgUser[]>([]);
  membersLoading = signal(true);
  membersError = signal<string | null>(null);

  // Projects
  projects = signal<Project[]>([]);
  projectsLoading = signal(true);
  projectsError = signal<string | null>(null);

  // Invite modal
  showInviteModal = signal(false);
  inviteEmail = '';
  inviteRole: 'VIEWER' | 'OPERATOR' | 'MANAGER' = 'VIEWER';
  inviteError = signal<string | null>(null);
  inviteSuccess = signal<string | null>(null);
  inviting = signal(false);

  // Remove member modal
  memberToRemove = signal<OrgUser | null>(null);
  removing = signal(false);

  // Archive project modal
  projectToArchive = signal<Project | null>(null);
  archiving = signal(false);

  private readonly loaded = new Set<OrgSettingsTab>();

  ngOnInit(): void {
    if (!this.orgId) {
      this.membersError.set('No organization found for current user');
      this.membersLoading.set(false);
      return;
    }
    this.loadTab('members');
  }

  setTab(tab: OrgSettingsTab): void {
    this.activeTab.set(tab);
    this.loadTab(tab);
  }

  private loadTab(tab: OrgSettingsTab): void {
    if (this.loaded.has(tab)) return;
    this.loaded.add(tab);
    switch (tab) {
      case 'members': this.loadMembers(); break;
      case 'projects': this.loadProjects(); break;
    }
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

  private loadProjects(): void {
    this.projectsLoading.set(true);
    this.http.get<Project[]>(`/api/v1/organizations/${this.orgId}/projects`)
      .pipe(catchError(() => {
        this.projectsError.set(this.ts.translateInstant('org_settings.loading_projects_error'));
        return of([] as Project[]);
      }))
      .subscribe(data => {
        this.projects.set(data);
        this.projectsLoading.set(false);
      });
  }

  openInviteModal(): void {
    this.inviteEmail = '';
    this.inviteRole = 'VIEWER';
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

  onRoleChange(member: OrgUser, event: Event): void {
    const select = event.target as HTMLSelectElement;
    const newRole = select.value as OrgUser['role'];
    this.http.patch(`/api/v1/organizations/${this.orgId}/users/${member.id}/role`, { role: newRole })
      .pipe(catchError(() => {
        select.value = member.role;
        return of(null);
      }))
      .subscribe(() => {
        this.members.update(members => members.map(m =>
          m.id === member.id ? { ...m, role: newRole } : m
        ));
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

  confirmArchiveProject(project: Project): void {
    this.projectToArchive.set(project);
  }

  cancelArchiveProject(): void {
    this.projectToArchive.set(null);
  }

  archiveProject(): void {
    const project = this.projectToArchive();
    if (!project) return;
    this.archiving.set(true);

    this.http.post(`/api/v1/organizations/${this.orgId}/projects/${project.id}/archive`, {})
      .pipe(catchError(() => {
        this.archiving.set(false);
        return of(null);
      }))
      .subscribe(() => {
        this.archiving.set(false);
        this.projects.update(projects => projects.map(p =>
          p.id === project.id ? { ...p, is_archived: true } : p
        ));
        this.projectToArchive.set(null);
      });
  }
}