import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { catchError, of } from 'rxjs';
import { AuthService } from '../../core/services/auth.service';
import { TranslationService } from '../../core/i18n/translation.service';
import { TranslatePipe } from '../../core/i18n/translate.pipe';

type AdminTab = 'organizations' | 'users' | 'access-requests';
type AccessRequestStatus = 'PENDING' | 'APPROVED' | 'REJECTED';

interface Org {
  id: string;
  name: string;
  slug: string;
}

interface GlobalUser {
  id: string;
  email: string;
  display_name: string;
  role: string;
  is_active: boolean;
}

interface AccessRequest {
  id: string;
  requester_name: string;
  requester_email: string;
  organization_name: string;
  organization_description?: string;
  slug_preview?: string;
  status: AccessRequestStatus;
  created_at?: string;
  rejection_reason?: string;
}


@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule, TranslatePipe],
  template: `
    <div class="admin-page">
      <div class="page-header">
        <h1 class="page-title">{{ 'admin.title' | t }}</h1>
        <span class="page-badge">{{ 'admin.global_badge' | t }}</span>
      </div>

      <div class="info-panel" style="margin-bottom: var(--spacing-lg)">
        <span class="info-icon">
          <svg width="18" height="18" viewBox="0 0 16 16" fill="none">
            <circle cx="8" cy="8" r="6.5" stroke="currentColor" stroke-width="1.2"/>
            <path d="M8 5V4.5M8 7v4" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
          </svg>
        </span>
        <div class="info-body">
          <div class="info-title">{{ 'admin.anonymized_title' | t }}</div>
          <p class="info-desc">{{ 'admin.anonymized_desc' | t }}</p>
        </div>
      </div>

      <nav class="admin-tabs">
        <button
          *ngFor="let tab of tabs"
          class="admin-tab"
          [class.admin-tab-active]="activeTab() === tab.id"
          (click)="setTab(tab.id)"
        >{{ tab.label }}</button>
      </nav>

      <!-- ORGANIZATIONS TAB -->
      <div *ngIf="activeTab() === 'organizations'" class="tab-content">
        <div class="tab-toolbar">
          <h2 class="tab-title">{{ 'admin.orgs_title' | t }}</h2>
          <span class="tab-meta">{{ 'admin.read_only_badge' | t }}</span>
        </div>

        <div *ngIf="orgsLoading()" class="skeleton-list">
          <div class="skeleton-row" *ngFor="let i of [1,2,3]"></div>
        </div>

        <div *ngIf="orgsError() && !orgsLoading()" class="error-banner">{{ orgsError() }}</div>

        <div *ngIf="!orgsLoading() && !orgsError()" class="data-table-wrap">
          <table class="data-table" *ngIf="orgs().length > 0; else orgsEmpty">
            <thead>
              <tr>
                <th scope="col">{{ 'admin.org_id_col' | t }}</th>
                <th scope="col">{{ 'admin.org_anon_name' | t }}</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let org of orgs()">
                <td><code class="mono-cell">{{ org.id }}</code></td>
                <td class="cell-primary">{{ org.name }}</td>
              </tr>
            </tbody>
          </table>
          <ng-template #orgsEmpty>
            <div class="empty-state">{{ 'admin.no_organizations' | t }}</div>
          </ng-template>
        </div>
      </div>

      <!-- USERS TAB -->
      <div *ngIf="activeTab() === 'users'" class="tab-content">
        <div class="tab-toolbar">
          <h2 class="tab-title">{{ 'admin.global_users_title' | t }}</h2>
          <span class="tab-meta">{{ 'admin.read_only_badge' | t }}</span>
        </div>

        <div *ngIf="usersLoading()" class="skeleton-list">
          <div class="skeleton-row" *ngFor="let i of [1,2,3,4]"></div>
        </div>

        <div *ngIf="usersError() && !usersLoading()" class="error-banner">{{ usersError() }}</div>

        <div *ngIf="!usersLoading() && !usersError()" class="data-table-wrap">
          <table class="data-table" *ngIf="users().length > 0; else usersEmpty">
            <thead>
              <tr>
                <th scope="col">{{ 'admin.org_id_col' | t }}</th>
                <th scope="col">{{ 'admin.org_anon_name' | t }}</th>
                <th scope="col">{{ 'common.role' | t }}</th>
                <th scope="col">{{ 'admin.user_status_col' | t }}</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let user of users()" [class.row-locked]="user.role === 'ADMIN'">
                <td><code class="mono-cell">{{ user.id }}</code></td>
                <td class="cell-primary">
                  {{ user.display_name }}
                  <span class="self-tag" *ngIf="user.id === currentUserId">{{ 'admin.self_tag' | t }}</span>
                </td>
                <td>
                  <span *ngIf="user.role === 'ADMIN'" class="role-fixed">{{ 'admin.global_admin_role' | t }}</span>
                  <span *ngIf="user.role !== 'ADMIN'" class="role-text">{{ user.role }}</span>
                </td>
                <td>
                  <span class="badge" [class.badge-active]="user.is_active" [class.badge-inactive]="!user.is_active">
                    {{ user.is_active ? ('admin.active_badge' | t) : ('admin.inactive_badge' | t) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
          <ng-template #usersEmpty>
            <div class="empty-state">{{ 'admin.no_users' | t }}</div>
          </ng-template>
        </div>
      </div>

      <!-- ACCESS REQUESTS TAB -->
      <div *ngIf="activeTab() === 'access-requests'" class="tab-content">
        <div class="tab-toolbar">
          <h2 class="tab-title">{{ 'admin.access_requests_title' | t }}</h2>
          <span class="tab-meta">{{ 'admin.read_only_badge' | t }}</span>
        </div>

        <div class="ar-status-tabs">
          <button
            *ngFor="let st of accessRequestStatuses"
            class="ar-status-tab"
            [class.ar-status-tab-active]="arStatus() === st.value"
            (click)="setArStatus(st.value)"
          >{{ st.label }}</button>
        </div>

        <div *ngIf="arLoading()" class="skeleton-list">
          <div class="skeleton-row" *ngFor="let i of [1,2,3,4]"></div>
        </div>

        <div *ngIf="arError() && !arLoading()" class="error-banner">{{ arError() }}</div>

        <div *ngIf="arSuccess()" class="success-banner">{{ arSuccess() }}</div>

        <div *ngIf="!arLoading() && !arError()" class="data-table-wrap">
          <table class="data-table" *ngIf="accessRequests().length > 0; else arEmpty">
            <thead>
              <tr>
                <th scope="col">{{ 'admin.access_requester' | t }}</th>
                <th scope="col">{{ 'admin.access_org' | t }}</th>
                <th scope="col">{{ 'admin.access_created' | t }}</th>
                <th scope="col">{{ 'common.status' | t }}</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let ar of accessRequests()">
                <td>
                  <div class="cell-primary">{{ ar.requester_name }}</div>
                  <div class="cell-muted">{{ ar.requester_email }}</div>
                </td>
                <td>
                  <div class="cell-primary">{{ ar.organization_name }}</div>
                </td>
                <td class="cell-muted">{{ relativeDate(ar.created_at) }}</td>
                <td>
                  <span class="badge" [class.badge-pending]="ar.status === 'PENDING'" [class.badge-approved]="ar.status === 'APPROVED'" [class.badge-rejected]="ar.status === 'REJECTED'">
                    {{ ar.status === 'PENDING' ? 'Pending' : ar.status === 'APPROVED' ? 'Approved' : 'Rejected' }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
          <ng-template #arEmpty>
            <div class="empty-state">{{ 'admin.no_ar' | t }}</div>
          </ng-template>
        </div>
      </div>

    </div>

  `,
  styles: [`
    :host { display: block; }

    .admin-page { padding: 0; }

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

    .page-badge {
      font-family: var(--font-mono);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.04em;
      color: var(--verdict-warning);
      background: var(--verdict-warning-bg);
      border: 0.0625rem solid var(--verdict-warning-border);
      border-radius: var(--rounded-sm);
      padding: 0.125rem 0.5rem;
    }

    .admin-tabs {
      display: flex;
      gap: 0.125rem;
      border-bottom: 0.0625rem solid var(--border);
      margin-bottom: var(--spacing-lg);
    }

    .admin-tab,
    .ar-status-tab {
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

    .admin-tab:hover,
    .ar-status-tab:hover { color: var(--ink); }

    .admin-tab-active,
    .ar-status-tab-active { color: var(--ink); border-bottom-color: var(--accent); }

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
      text-align: right;
      white-space: nowrap;
      display: flex;
      gap: var(--spacing-sm);
      justify-content: flex-end;
      align-items: center;
    }

    .mono-cell {
      font-family: var(--font-mono);
      font-size: 0.75rem;
      color: var(--muted);
    }

    .badge {
      display: inline-flex;
      align-items: center;
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      border-radius: var(--rounded-sm);
      padding: 0.125rem 0.5rem;
      border: 0.0625rem solid;
    }

    .badge-active {
      color: var(--verdict-valid);
      background: var(--verdict-valid-bg);
      border-color: var(--verdict-valid-border);
    }

    .badge-inactive {
      color: var(--verdict-unevaluated);
      background: var(--verdict-unevaluated-bg);
      border-color: var(--verdict-unevaluated-border);
    }

    .type-chip {
      font-family: var(--font-mono);
      font-size: 0.75rem;
      color: var(--muted);
      background: var(--paper-secondary);
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-sm);
      padding: 0.0625rem 0.375rem;
    }

    .role-select {
      font-family: var(--font-sans);
      font-size: 0.8125rem;
      color: var(--ink);
      background: var(--paper);
      border: 0.0625rem solid var(--border-strong);
      border-radius: var(--rounded-md);
      padding: 0.1875rem 0.375rem;
      outline: none;
      cursor: pointer;
    }

    .role-text {
      font-family: var(--font-sans);
      font-size: 0.8125rem;
      color: var(--ink);
      font-weight: 500;
    }

    .tab-meta {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 500;
      letter-spacing: 0.04em;
      color: var(--verdict-unevaluated);
      background: var(--verdict-unevaluated-bg);
      border: 0.0625rem solid var(--verdict-unevaluated-border);
      border-radius: var(--rounded-sm);
      padding: 0.125rem 0.5rem;
      text-transform: uppercase;
    }

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

    .error-sm { margin-bottom: 0; margin-top: var(--spacing-sm); }

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
    .form-group input[type=password],
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

    .field-hint {
      font-size: 0.75rem;
      color: var(--muted);
      margin-top: var(--spacing-xs);
    }

    .row-locked td {
      background: rgba(232, 213, 163, 0.05);
    }

    .role-fixed {
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

    .info-panel {
      display: flex;
      gap: var(--spacing-md);
      background: var(--surface-raised);
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-lg);
      padding: var(--spacing-lg);
    }

    .info-icon {
      flex-shrink: 0;
      color: var(--muted);
      margin-top: 0.125rem;
    }

    .info-body { flex: 1; }

    .info-title {
      font-size: 1rem;
      font-weight: 600;
      color: var(--ink);
      margin-bottom: var(--spacing-sm);
    }

    .info-desc {
      font-size: 0.8125rem;
      color: var(--muted);
      line-height: 1.65;
      margin: 0 0 var(--spacing-sm);
    }

    .success-banner {
      background: var(--verdict-valid-bg);
      color: var(--verdict-valid);
      border: 0.0625rem solid var(--verdict-valid-border);
      border-radius: var(--rounded-md);
      padding: var(--spacing-sm) var(--spacing-md);
      font-size: 0.8125rem;
      margin-bottom: var(--spacing-md);
    }

    .ar-status-tabs {
      display: flex;
      gap: 0.125rem;
      border-bottom: 0.0625rem solid var(--border);
      margin-bottom: var(--spacing-md);
    }

    .badge-pending {
      color: var(--verdict-warning);
      background: var(--verdict-warning-bg);
      border-color: var(--verdict-warning-border);
    }

    .badge-approved {
      color: var(--verdict-valid);
      background: var(--verdict-valid-bg);
      border-color: var(--verdict-valid-border);
    }

    .badge-rejected {
      color: var(--verdict-invalid);
      background: var(--verdict-invalid-bg);
      border-color: var(--verdict-invalid-border);
    }

    .btn-approve-ghost { color: var(--verdict-valid); }
    .btn-approve-ghost:hover:not(:disabled) { background: var(--verdict-valid-bg); border-color: var(--verdict-valid-border); }

    .modal-body-text {
      font-family: var(--font-sans);
      font-size: 0.875rem;
      color: var(--ink);
      line-height: 1.65;
      margin: 0 0 var(--spacing-md);
    }

    .modal-body-text strong {
      font-weight: 600;
    }

    .form-group textarea {
      line-height: 1.5;
      resize: vertical;
      min-height: 4.5rem;
    }

    @media (max-width: 48rem) {
      .page-header { flex-wrap: wrap; }

      .page-title { font-size: 1.75rem; }

      .admin-tabs { overflow-x: auto; }

      .data-table-wrap { overflow-x: auto; }

      .modal-panel { width: calc(100vw - 2rem); }
    }
  `],
})
export class AdminComponent implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly authService = inject(AuthService);
  private readonly ts = inject(TranslationService);

  readonly currentUserId = this.authService.getUser()?.id ?? '';

  get tabs(): { id: AdminTab; label: string }[] {
    return [
      { id: 'organizations', label: this.ts.translateInstant('admin.tab_organizations') },
      { id: 'users', label: this.ts.translateInstant('admin.tab_users') },
      { id: 'access-requests', label: this.ts.translateInstant('admin.access_requests_title') },
    ];
  }

  activeTab = signal<AdminTab>('organizations');

  // Organizations
  orgs = signal<Org[]>([]);
  orgsLoading = signal(true);
  orgsError = signal<string | null>(null);

  // Users
  users = signal<GlobalUser[]>([]);
  usersLoading = signal(true);
  usersError = signal<string | null>(null);

  // Access Requests
  accessRequests = signal<AccessRequest[]>([]);
  arLoading = signal(true);
  arError = signal<string | null>(null);
  arSuccess = signal<string | null>(null);
  arStatus = signal<AccessRequestStatus>('PENDING');
  get accessRequestStatuses(): { value: AccessRequestStatus; label: string }[] {
    return [
      { value: 'PENDING', label: this.ts.translateInstant('admin.tab_pending') },
      { value: 'APPROVED', label: this.ts.translateInstant('admin.tab_approved') },
      { value: 'REJECTED', label: this.ts.translateInstant('admin.tab_rejected') },
    ];
  }

  private simpleHash(input: string): string {
    let hash = 0;
    for (let i = 0; i < input.length; i++) {
      const char = input.codePointAt(i)!;
      hash = ((hash << 5) - hash) + char;
      hash = Math.trunc(hash);
    }
    return Math.abs(hash).toString(16).slice(0, 8).padStart(8, '0');
  }

  relativeDate(iso: string | undefined): string {
    if (!iso) return '';
    const d = new Date(iso);
    const now = Date.now();
    const diff = now - d.getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return this.ts.translateInstant('releases.relative_just_now');
    if (mins < 60) return this.ts.translateInstant('releases.relative_minutes', { n: mins });
    const hours = Math.floor(mins / 60);
    if (hours < 24) return this.ts.translateInstant('releases.relative_hours', { n: hours });
    const days = Math.floor(hours / 24);
    if (days < 30) return this.ts.translateInstant('releases.relative_days', { n: days });
    return d.toLocaleDateString(this.ts.currentLang === 'en' ? 'en-GB' : 'es-ES', { month: 'short', day: 'numeric' });
  }


  private readonly loaded = new Set<AdminTab>();

  ngOnInit(): void {
    this.loadTab('organizations');
  }

  setTab(tab: AdminTab): void {
    this.activeTab.set(tab);
    this.loadTab(tab);
  }

  private loadTab(tab: AdminTab): void {
    if (this.loaded.has(tab)) return;
    this.loaded.add(tab);
    switch (tab) {
      case 'organizations': this.loadOrgs(); break;
      case 'users': this.loadUsers(); break;
      case 'access-requests': this.loadAccessRequests(); break;
    }
  }

  // ── Organizations ─────────────────────────────────────────────

  private loadOrgs(): void {
    this.orgsLoading.set(true);
    this.http.get<Org[]>('/api/v1/organizations')
      .pipe(catchError(() => { this.orgsError.set(this.ts.translateInstant('admin.loading_orgs_error')); return of([]); }))
      .subscribe(data => {
        const anonymized = data.map(org => ({
          ...org,
          name: `Organization ${this.simpleHash(org.id)}`,
        }));
        this.orgs.set(anonymized);
        this.orgsLoading.set(false);
      });
  }

  // ── Users ─────────────────────────────────────────────────────

  private loadUsers(): void {
    this.usersLoading.set(true);
    this.http.get<GlobalUser[]>('/api/v1/admin/users?limit=200')
      .pipe(catchError(() => { this.usersError.set(this.ts.translateInstant('admin.loading_users_error')); return of([]); }))
      .subscribe(data => {
        const anonymized = data.map(user => ({
          ...user,
          email: `user-${this.simpleHash(user.id)}@anonymous.local`,
          display_name: `User ${this.simpleHash(user.id).slice(0, 6)}`,
        }));
        this.users.set(anonymized);
        this.usersLoading.set(false);
      });
  }

  // ── Access Requests ───────────────────────────────────────────

  setArStatus(status: AccessRequestStatus): void {
    this.arStatus.set(status);
    this.arLoading.set(true);
    this.arError.set(null);
    this.arSuccess.set(null);
    this.loadAccessRequests();
  }

  private loadAccessRequests(): void {
    this.arLoading.set(true);
    this.http
      .get<AccessRequest[]>(`/api/v1/access-requests?status=${this.arStatus()}`)
      .pipe(
        catchError(() => {
          this.arError.set('Error loading access requests');
          return of([]);
        }),
      )
      .subscribe((data) => {
        const anonymized = data.map(ar => ({
          ...ar,
          requester_name: `Requester ${this.simpleHash(ar.id).slice(0, 6)}`,
          requester_email: `req-${this.simpleHash(ar.id)}@anonymous.local`,
          organization_name: `Org ${this.simpleHash(ar.id).slice(0, 6)}`,
          slug_preview: undefined,
          organization_description: undefined,
        }));
        this.accessRequests.set(anonymized);
        this.arLoading.set(false);
      });
  }
}
