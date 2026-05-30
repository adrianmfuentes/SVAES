import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { catchError, of } from 'rxjs';
import { AuthService } from '../../core/services/auth.service';

type AdminTab = 'organizations' | 'users';

interface Org {
  id: string;
  name: string;
  slug: string;
  plan?: string;
}

interface GlobalUser {
  id: string;
  email: string;
  display_name: string;
  role: string;
  is_active: boolean;
}


@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  template: `
    <div class="admin-page">
      <div class="page-header">
        <h1 class="page-title">Administraci&oacute;n</h1>
        <span class="page-badge">Global &middot; U3</span>
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
          <h2 class="tab-title">Organizaciones</h2>
          <button class="btn-primary" (click)="showCreateOrgModal.set(true)">Nueva organizaci&oacute;n</button>
        </div>

        <div *ngIf="orgsLoading()" class="skeleton-list">
          <div class="skeleton-row" *ngFor="let i of [1,2,3]"></div>
        </div>

        <div *ngIf="orgsError() && !orgsLoading()" class="error-banner">{{ orgsError() }}</div>

        <div *ngIf="!orgsLoading() && !orgsError()" class="data-table-wrap">
          <table class="data-table" *ngIf="orgs().length > 0; else orgsEmpty">
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Slug</th>
                <th>Plan</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let org of orgs()">
                <td class="cell-primary">{{ org.name }}</td>
                <td><code class="mono-cell">{{ org.slug }}</code></td>
                <td class="cell-muted">{{ org.plan ?? 'default' }}</td>
              </tr>
            </tbody>
          </table>
          <ng-template #orgsEmpty>
            <div class="empty-state">No hay organizaciones registradas.</div>
          </ng-template>
        </div>
      </div>

      <!-- USERS TAB -->
      <div *ngIf="activeTab() === 'users'" class="tab-content">
        <div class="tab-toolbar">
          <h2 class="tab-title">Usuarios globales</h2>
          <button class="btn-primary" (click)="showCreateUserModal.set(true)">Nuevo usuario</button>
        </div>

        <div *ngIf="usersLoading()" class="skeleton-list">
          <div class="skeleton-row" *ngFor="let i of [1,2,3,4]"></div>
        </div>

        <div *ngIf="usersError() && !usersLoading()" class="error-banner">{{ usersError() }}</div>

        <div *ngIf="!usersLoading() && !usersError()" class="data-table-wrap">
          <table class="data-table" *ngIf="users().length > 0; else usersEmpty">
            <thead>
              <tr>
                <th>Email</th>
                <th>Nombre</th>
                <th>Rol</th>
                <th>Estado</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let user of users()" [class.row-locked]="user.role === 'ADMIN'">
                <td><code class="mono-cell">{{ user.email }}</code></td>
                <td class="cell-primary">
                  {{ user.display_name }}
                  <span class="self-tag" *ngIf="user.id === currentUserId">Tú</span>
                </td>
                <td>
                  <span *ngIf="user.role === 'ADMIN'" class="role-fixed">Admin global</span>
                  <select
                    *ngIf="user.role !== 'ADMIN'"
                    class="role-select"
                    [value]="user.role"
                    (change)="changeUserRole(user, $any($event.target).value)"
                  >
                    <option value="VIEWER">Viewer</option>
                    <option value="OPERATOR">Operator</option>
                    <option value="MANAGER">Manager</option>
                  </select>
                </td>
                <td>
                  <span class="badge" [class.badge-active]="user.is_active" [class.badge-inactive]="!user.is_active">
                    {{ user.is_active ? 'Activo' : 'Inactivo' }}
                  </span>
                </td>
                <td class="cell-actions">
                  <button
                    class="btn-ghost"
                    [disabled]="user.role === 'ADMIN' || togglingUserId() === user.id"
                    (click)="user.role !== 'ADMIN' && toggleUser(user)"
                  >
                    {{ togglingUserId() === user.id ? '…' : (user.is_active ? 'Desactivar' : 'Activar') }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
          <ng-template #usersEmpty>
            <div class="empty-state">No hay usuarios registrados.</div>
          </ng-template>
        </div>
      </div>

    </div>

    <!-- MODAL: Create Organization -->
    <div class="modal-overlay" *ngIf="showCreateOrgModal()" (click)="showCreateOrgModal.set(false)">
      <div class="modal-panel" (click)="$event.stopPropagation()">
        <div class="modal-header">
          <h3 class="modal-title">Nueva organizaci&oacute;n</h3>
          <button class="modal-close" (click)="showCreateOrgModal.set(false)">&times;</button>
        </div>
        <form [formGroup]="createOrgForm" (ngSubmit)="submitCreateOrg()">
          <div class="form-group">
            <label for="org-name">Nombre</label>
            <input id="org-name" type="text" formControlName="name" placeholder="Acme Corp" />
          </div>
          <div class="form-group">
            <label for="org-slug">Slug</label>
            <input id="org-slug" type="text" formControlName="slug" placeholder="acme-corp" />
            <div class="field-hint">Solo min&uacute;sculas, n&uacute;meros y guiones.</div>
          </div>
          <div class="form-group">
            <label for="org-plan">Plan</label>
            <input id="org-plan" type="text" formControlName="plan" placeholder="default" />
          </div>
          <div *ngIf="createOrgError()" class="error-banner error-sm">{{ createOrgError() }}</div>
          <div class="modal-footer">
            <button type="button" class="btn-secondary" (click)="showCreateOrgModal.set(false)">Cancelar</button>
            <button type="submit" class="btn-primary" [disabled]="createOrgLoading()">
              {{ createOrgLoading() ? 'Creando…' : 'Crear organización' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- MODAL: Create User -->
    <div class="modal-overlay" *ngIf="showCreateUserModal()" (click)="showCreateUserModal.set(false)">
      <div class="modal-panel" (click)="$event.stopPropagation()">
        <div class="modal-header">
          <h3 class="modal-title">Nuevo usuario</h3>
          <button class="modal-close" (click)="showCreateUserModal.set(false)">&times;</button>
        </div>
        <form [formGroup]="createUserForm" (ngSubmit)="submitCreateUser()">
          <div class="form-group">
            <label for="user-email">Correo electr&oacute;nico</label>
            <input id="user-email" type="email" formControlName="email" placeholder="usuario@ejemplo.com" />
          </div>
          <div class="form-group">
            <label for="user-name">Nombre</label>
            <input id="user-name" type="text" formControlName="display_name" placeholder="Nombre completo" />
          </div>
          <div class="form-group">
            <label for="user-pw">Contrase&ntilde;a inicial</label>
            <input id="user-pw" type="password" formControlName="password" placeholder="M&iacute;nimo 8 caracteres" />
          </div>
          <div class="form-group">
            <label for="user-role">Rol</label>
            <select id="user-role" formControlName="role">
              <option value="VIEWER">Viewer</option>
              <option value="OPERATOR">Operator</option>
              <option value="MANAGER">Manager</option>
            </select>
          </div>
          <div *ngIf="createUserError()" class="error-banner error-sm">{{ createUserError() }}</div>
          <div class="modal-footer">
            <button type="button" class="btn-secondary" (click)="showCreateUserModal.set(false)">Cancelar</button>
            <button type="submit" class="btn-primary" [disabled]="createUserLoading()">
              {{ createUserLoading() ? 'Creando…' : 'Crear usuario' }}
            </button>
          </div>
        </form>
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
      border: 1px solid var(--verdict-warning-border);
      border-radius: var(--rounded-sm);
      padding: 2px 8px;
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
      font-family: var(--font-sans);
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
      padding: 2px 8px;
      border: 1px solid;
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
      border: 1px solid var(--border);
      border-radius: var(--rounded-sm);
      padding: 1px 6px;
    }

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
      font-family: var(--font-sans);
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
    .form-group select {
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
    .form-group select:focus {
      border-color: var(--ink);
      background: var(--surface-raised);
      box-shadow: 0 0 0 3px rgba(232, 213, 163, 0.4);
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
      border: 1px solid var(--border);
      border-radius: var(--rounded-sm);
      padding: 1px 5px;
      margin-left: var(--spacing-sm);
      vertical-align: middle;
    }

    .info-panel {
      display: flex;
      gap: var(--spacing-md);
      background: var(--surface-raised);
      border: 1px solid var(--border);
      border-radius: var(--rounded-lg);
      padding: var(--spacing-lg);
    }

    .info-icon {
      flex-shrink: 0;
      color: var(--muted);
      margin-top: 2px;
    }

    .info-body { flex: 1; }

    .info-title {
      font-family: var(--font-sans);
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
  `],
})
export class AdminComponent implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly fb = inject(FormBuilder);
  private readonly authService = inject(AuthService);

  readonly currentUserId = this.authService.getUser()?.id ?? '';

  readonly tabs: { id: AdminTab; label: string }[] = [
    { id: 'organizations', label: 'Organizaciones' },
    { id: 'users', label: 'Usuarios' },
  ];

  activeTab = signal<AdminTab>('organizations');

  // Organizations
  orgs = signal<Org[]>([]);
  orgsLoading = signal(true);
  orgsError = signal<string | null>(null);
  showCreateOrgModal = signal(false);
  createOrgLoading = signal(false);
  createOrgError = signal<string | null>(null);
  createOrgForm = this.fb.group({
    name: ['', [Validators.required, Validators.minLength(2)]],
    slug: ['', [Validators.required, Validators.pattern(/^[a-z0-9-]+$/)]],
    plan: ['default'],
  });

  // Users
  users = signal<GlobalUser[]>([]);
  usersLoading = signal(true);
  usersError = signal<string | null>(null);
  showCreateUserModal = signal(false);
  createUserLoading = signal(false);
  createUserError = signal<string | null>(null);
  togglingUserId = signal<string | null>(null);
  createUserForm = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
    display_name: ['', [Validators.required]],
    password: ['', [Validators.required, Validators.minLength(8)]],
    role: ['OPERATOR', [Validators.required]],
  });


  private loaded = new Set<AdminTab>();

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
    }
  }

  // ── Organizations ─────────────────────────────────────────────

  private loadOrgs(): void {
    this.orgsLoading.set(true);
    this.http.get<Org[]>('/api/v1/organizations')
      .pipe(catchError(() => { this.orgsError.set('Error al cargar organizaciones'); return of([]); }))
      .subscribe(data => { this.orgs.set(data); this.orgsLoading.set(false); });
  }

  submitCreateOrg(): void {
    if (this.createOrgForm.invalid) { this.createOrgForm.markAllAsTouched(); return; }
    this.createOrgLoading.set(true);
    this.createOrgError.set(null);
    this.http.post<Org>('/api/v1/organizations', this.createOrgForm.value)
      .pipe(catchError((err: HttpErrorResponse) => {
        this.createOrgError.set(err.error?.detail ?? 'Error al crear organización');
        this.createOrgLoading.set(false);
        return of(null);
      }))
      .subscribe(org => {
        if (org) {
          this.orgs.update(list => [...list, org]);
          this.showCreateOrgModal.set(false);
          this.createOrgForm.reset({ name: '', slug: '', plan: 'default' });
        }
        this.createOrgLoading.set(false);
      });
  }

  // ── Users ─────────────────────────────────────────────────────

  private loadUsers(): void {
    this.usersLoading.set(true);
    this.http.get<GlobalUser[]>('/api/v1/admin/users?limit=200')
      .pipe(catchError(() => { this.usersError.set('Error al cargar usuarios'); return of([]); }))
      .subscribe(data => { this.users.set(data); this.usersLoading.set(false); });
  }

  toggleUser(user: GlobalUser): void {
    this.togglingUserId.set(user.id);
    const endpoint = user.is_active
      ? `/api/v1/admin/users/${user.id}/deactivate`
      : `/api/v1/admin/users/${user.id}/activate`;
    this.http.patch<{ id: string; email: string; is_active: boolean }>(endpoint, {})
      .pipe(catchError(() => { this.togglingUserId.set(null); return of(null); }))
      .subscribe(updated => {
        if (updated) {
          this.users.update(list =>
            list.map(u => u.id === updated.id ? { ...u, is_active: updated.is_active } : u)
          );
        }
        this.togglingUserId.set(null);
      });
  }

  changeUserRole(user: GlobalUser, role: string): void {
    this.http.patch<{ id: string; email: string; role: string }>(
      `/api/v1/admin/users/${user.id}/role`,
      { role }
    )
      .pipe(catchError(() => of(null)))
      .subscribe(updated => {
        if (updated) {
          this.users.update(list =>
            list.map(u => u.id === updated.id ? { ...u, role: updated.role } : u)
          );
        }
      });
  }

  submitCreateUser(): void {
    if (this.createUserForm.invalid) { this.createUserForm.markAllAsTouched(); return; }
    this.createUserLoading.set(true);
    this.createUserError.set(null);
    this.http.post<GlobalUser>('/api/v1/admin/users', this.createUserForm.value)
      .pipe(catchError((err: HttpErrorResponse) => {
        this.createUserError.set(err.error?.detail ?? 'Error al crear usuario');
        this.createUserLoading.set(false);
        return of(null);
      }))
      .subscribe(user => {
        if (user) {
          this.users.update(list => [...list, { ...user, is_active: true }]);
          this.showCreateUserModal.set(false);
          this.createUserForm.reset({ email: '', display_name: '', password: '', role: 'OPERATOR' });
        }
        this.createUserLoading.set(false);
      });
  }

}
