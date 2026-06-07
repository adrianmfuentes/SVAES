import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { AuthService } from '../../core/services/auth.service';
import { TranslationService } from '../../core/i18n/translation.service';
import { TranslatePipe } from '../../core/i18n/translate.pipe';
import { catchError, of } from 'rxjs';

interface Profile {
  id: string;
  name: string;
  description?: string;
  rules_count?: number;
  organization_id?: string;
  organization_name?: string;
  is_template?: boolean;
  is_default?: boolean;
  created_at?: string;
}

@Component({
  selector: 'app-profiles',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, TranslatePipe],
  template: `
    <div class="profiles-page">
      <div class="page-header">
        <div class="page-header-left">
          <h1 class="page-title">{{ 'profiles.title' | t }}</h1>
        </div>
        <button *ngIf="canManage" class="btn-primary" (click)="openCreate()">{{ 'profiles.create_button' | t }}</button>
      </div>

      <div *ngIf="loading()" class="skeleton-list">
        <div class="skeleton skeleton-row" *ngFor="let i of [1,2,3,4]"></div>
      </div>

      <div *ngIf="error() && !loading()" class="error-banner">{{ error() }}</div>

      <div *ngIf="!loading() && !error()">
        <!-- Org profiles -->
        <div class="section-label">{{ 'profiles.org_profiles' | t }}</div>
        <div class="data-table-wrap">
          <table class="data-table" *ngIf="orgProfiles().length > 0; else profilesEmpty">
            <thead>
              <tr>
                <th>{{ 'profiles.table_name' | t }}</th>
                <th>{{ 'common.description' | t }}</th>
                <th>{{ 'profiles.table_rules' | t }}</th>
                <th *ngIf="canManage"></th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let p of orgProfiles()">
                <td class="cell-primary">{{ p.name }}</td>
                <td class="cell-muted">{{ p.description ?? '—' }}</td>
                <td>{{ p.rules_count ?? '—' }}</td>
                <td *ngIf="canManage" class="cell-actions">
                  <button class="btn-ghost" (click)="openEdit(p)">{{ 'common.edit' | t }}</button>
                  <button
                    class="btn-ghost btn-danger-ghost"
                    [disabled]="deletingId() === p.id"
                    (click)="deleteProfile(p)"
                  >
                    {{ deletingId() === p.id ? ('profiles.deleting' | t) : ('common.delete' | t) }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
          <ng-template #profilesEmpty>
            <div class="empty-state">{{ 'profiles.no_profiles' | t }}</div>
          </ng-template>
        </div>
      </div>
    </div>

    <!-- MODAL: Create/Edit Template -->
    <div class="modal-overlay" *ngIf="showModal()" (click)="showModal.set(false)">
      <div class="modal-panel" (click)="$event.stopPropagation()">
        <div class="modal-header">
          <h3 class="modal-title">{{ editingProfile() ? ('profiles.edit_title' | t) : ('profiles.create_title' | t) }}</h3>
          <button class="modal-close" (click)="showModal.set(false)">&times;</button>
        </div>
        <form [formGroup]="profileForm" (ngSubmit)="submitProfile()">
          <div class="form-group">
            <label for="prof-name">{{ 'profiles.name_label' | t }}</label>
            <input id="prof-name" type="text" formControlName="name" [placeholder]="'profiles.template_placeholder' | t" />
          </div>
          <div class="form-group">
            <label for="prof-desc">{{ 'common.description' | t }}</label>
            <input id="prof-desc" type="text" formControlName="description" [placeholder]="'profiles.desc_placeholder' | t" />
          </div>
          <div *ngIf="modalError()" class="error-banner error-banner-sm">{{ modalError() }}</div>
          <div class="modal-footer">
            <button type="button" class="btn-secondary" (click)="showModal.set(false)">{{ 'common.cancel' | t }}</button>
            <button type="submit" class="btn-primary" [disabled]="saving()">
              {{ saving() ? ('profiles.saving' | t) : (editingProfile() ? ('profiles.save_changes' | t) : ('profiles.create_button' | t)) }}
            </button>
          </div>
        </form>
      </div>
    </div>
  `,
  styles: [`
    :host { display: block; }

    .profiles-page { padding: 0; }

    .page-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: var(--spacing-lg);
    }

    .page-header-left {
      display: flex;
      align-items: baseline;
      gap: var(--spacing-md);
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

    .global-badge {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--muted);
      background: var(--paper-secondary);
      border: 1px solid var(--border);
      border-radius: var(--rounded-sm);
      padding: 2px 8px;
    }

    .section-label {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--ink);
      margin-bottom: var(--spacing-sm);
    }

    .section-label-muted {
      color: var(--muted);
      margin-top: var(--spacing-md);
    }

    .data-table-wrap {
      background: var(--surface-raised);
      border: 1px solid var(--border);
      border-radius: var(--rounded-lg);
      overflow: hidden;
    }

    .data-table {
      width: 100%;
      border-collapse: collapse;
    }

    .data-table th {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
      padding: var(--spacing-sm) var(--spacing-md);
      text-align: left;
      border-bottom: 1px solid var(--border);
      background: var(--paper-secondary);
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
      display: flex;
      gap: var(--spacing-sm);
      justify-content: flex-end;
      align-items: center;
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
      transition: background-color 0.15s ease;
    }

    .btn-primary:hover:not(:disabled) { background: var(--ink-secondary); }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

    .btn-secondary {
      display: inline-flex;
      align-items: center;
      background: transparent;
      color: var(--ink);
      border: 1px solid var(--border-strong);
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

    .btn-secondary:hover { background: var(--paper-secondary); }

    .error-banner {
      background: var(--verdict-invalid-bg);
      color: var(--verdict-invalid);
      border: 1px solid var(--verdict-invalid-border);
      border-radius: var(--rounded-md);
      padding: var(--spacing-sm) var(--spacing-md);
      font-size: 0.8125rem;
      margin-bottom: var(--spacing-md);
    }

    .error-banner-sm { margin-bottom: 0; margin-top: var(--spacing-sm); }

    .skeleton-list { display: flex; flex-direction: column; gap: var(--spacing-sm); }

    .skeleton {
      border-radius: var(--rounded-md);
      background: linear-gradient(90deg, var(--paper-secondary) 25%, #e5e2db 50%, var(--paper-secondary) 75%);
      background-size: 200% 100%;
      animation: shimmer 1.6s linear infinite;
    }

    .skeleton-row { height: 44px; }

    @keyframes shimmer {
      0% { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }

    .empty-state {
      padding: var(--spacing-xl) var(--spacing-lg);
      text-align: center;
      font-size: 0.8125rem;
      color: var(--muted);
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

    .form-group {
      margin-bottom: var(--spacing-md);
    }

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

    .form-group input {
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

    .form-group input:focus {
      border-color: var(--ink);
      background: var(--surface-raised);
      box-shadow: 0 0 0 3px rgba(232, 213, 163, 0.4);
    }
  `],
})
export class ProfilesComponent implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly authService = inject(AuthService);
  private readonly fb = inject(FormBuilder);
  private readonly ts = inject(TranslationService);

  private orgId: string | null = null;
  readonly canManage = this.authService.getUserRole() === 'MANAGER';
  /** @deprecated keep for template compat — always false on this route */
  readonly isAdmin = false;

  allProfiles = signal<Profile[]>([]);
  templates = signal<Profile[]>([]);
  orgProfiles = signal<Profile[]>([]);
  loading = signal(true);
  error = signal<string | null>(null);

  showModal = signal(false);
  editingProfile = signal<Profile | null>(null);
  saving = signal(false);
  modalError = signal<string | null>(null);
  deletingId = signal<string | null>(null);

  profileForm = this.fb.group({
    name: ['', [Validators.required]],
    description: [''],
  });

  ngOnInit(): void {
    const user = this.authService.getUser();
    this.orgId = user?.organization_id ?? null;
    if (!this.orgId) {
      this.error.set(this.ts.translateInstant('profiles.loading_error'));
      this.loading.set(false);
      return;
    }
    this.http.get<Profile[]>(`/api/v1/organizations/${this.orgId}/profiles`)
      .pipe(catchError(() => { this.error.set(this.ts.translateInstant('profiles.loading_error')); return of([]); }))
      .subscribe(data => {
        this.allProfiles.set(data);
        this.templates.set([]);
        this.orgProfiles.set(data);
        this.loading.set(false);
      });
  }

  openCreate(): void {
    this.editingProfile.set(null);
    this.profileForm.reset({ name: '', description: '' });
    this.modalError.set(null);
    this.showModal.set(true);
  }

  openEdit(p: Profile): void {
    this.editingProfile.set(p);
    this.profileForm.patchValue({ name: p.name, description: p.description ?? '' });
    this.modalError.set(null);
    this.showModal.set(true);
  }

  submitProfile(): void {
    if (this.profileForm.invalid) { this.profileForm.markAllAsTouched(); return; }
    this.saving.set(true);
    this.modalError.set(null);
    const editing = this.editingProfile();
    const body = { ...this.profileForm.value, is_default: false };
    const req = editing
      ? this.http.patch<Profile>(`/api/v1/profiles/${editing.id}`, body)
      : this.http.post<Profile>(`/api/v1/organizations/${this.orgId}/profiles`, body);
    req.pipe(catchError((err: HttpErrorResponse) => {
      this.modalError.set(err.error?.detail ?? this.ts.translateInstant('profiles.saving_error'));
      this.saving.set(false);
      return of(null);
    })).subscribe(p => {
      if (p) {
        const formDesc = this.profileForm.value.description ?? '';
        if (editing) {
          this.orgProfiles.update(list => list.map(x =>
            x.id === p.id
              ? { ...x, name: p.name, description: formDesc, is_default: p.is_default }
              : x
          ));
        } else {
          this.orgProfiles.update(list => [...list, {
            id: p.id,
            name: p.name,
            description: formDesc,
            rules_count: 0,
            is_default: p.is_default,
            is_template: false,
          }]);
        }
        this.showModal.set(false);
      }
      this.saving.set(false);
    });
  }

  deleteProfile(p: Profile): void {
    this.deletingId.set(p.id);
    this.http.delete(`/api/v1/profiles/${p.id}`)
      .pipe(catchError(() => { this.deletingId.set(null); return of(null); }))
      .subscribe(() => {
        this.orgProfiles.update(list => list.filter(x => x.id !== p.id));
        this.deletingId.set(null);
      });
  }
}
