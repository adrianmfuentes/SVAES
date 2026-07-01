import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { AuthService } from '../../core/services/auth.service';
import { TranslationService } from '../../core/i18n/translation.service';
import { TranslatePipe } from '../../core/i18n/translate.pipe';
import { catchError, of } from 'rxjs';

interface Project {
  id: string;
  name: string;
  description: string;
  profile_id: string | null;
  is_archived: boolean;
  created_at: string | null;
}

interface Profile {
  id: string;
  name: string;
  is_system?: boolean;
}

@Component({
  selector: 'app-projects',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule, TranslatePipe],
  template: `
    <div class="projects-page">
      <div class="page-header">
        <h1 class="page-title">{{ 'projects.title' | t }}</h1>
        <a *ngIf="isManager" routerLink="/app/projects/new" class="btn-primary">
          {{ 'projects.new_btn' | t }}
        </a>
      </div>

      <div *ngIf="loading()" class="skeleton-list">
        <div class="skeleton skeleton-row" *ngFor="let i of [1,2,3,4]"></div>
      </div>

      <div *ngIf="error() && !loading()" class="error-banner">{{ error() }}</div>

      <div *ngIf="!loading() && !error()">
        <div class="data-table-wrap" *ngIf="projects().length > 0; else emptyState">
          <table class="data-table">
            <thead>
              <tr>
                <th scope="col">{{ 'projects.col_name' | t }}</th>
                <th scope="col">{{ 'projects.col_description' | t }}</th>
                <th scope="col">{{ 'projects.col_status' | t }}</th>
                <th scope="col">{{ 'projects.col_created' | t }}</th>
                <th scope="col" *ngIf="isManager" class="cell-actions-header">{{ 'common.actions' | t }}</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let p of projects()">
                <td class="cell-primary" [attr.data-label]="'projects.col_name' | t">{{ p.name }}</td>
                <td class="cell-muted" [attr.data-label]="'projects.col_description' | t">{{ p.description || '—' }}</td>
                <td [attr.data-label]="'projects.col_status' | t">
                  <span class="status-badge" [class.status-archived]="p.is_archived">
                    {{ (p.is_archived ? 'projects.status_archived' : 'projects.status_active') | t }}
                  </span>
                </td>
                <td class="cell-muted" [attr.data-label]="'projects.col_created' | t">{{ p.created_at | date:'dd MMM yyyy' }}</td>
                <td *ngIf="isManager" class="cell-actions" [attr.data-label]="'common.actions' | t">
                  <button
                    class="btn-ghost"
                    (click)="openEdit(p)"
                  >{{ 'projects.edit_btn' | t }}</button>
                  <button
                    *ngIf="!p.is_archived"
                    class="btn-ghost"
                    (click)="confirmArchive(p)"
                  >{{ 'org_settings.archive_btn' | t }}</button>
                  <button
                    *ngIf="p.is_archived"
                    class="btn-ghost"
                    (click)="unarchive(p)"
                  >{{ 'projects.unarchive_btn' | t }}</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <ng-template #emptyState>
          <div class="empty-state">
            <p class="empty-text">{{ 'projects.empty_text' | t }}</p>
            <a *ngIf="isManager" routerLink="/app/projects/new" class="btn-primary">
              {{ 'projects.empty_cta' | t }}
            </a>
          </div>
        </ng-template>
      </div>
    </div>

    <!-- CONFIRM ARCHIVE MODAL -->
    <div *ngIf="projectToArchive()" class="modal-overlay" (click)="cancelArchive()">
      <div class="modal-panel" (click)="$event.stopPropagation()">
        <div class="modal-header">
          <h3 class="modal-title">{{ 'org_settings.archive_project_title' | t }}</h3>
          <button class="modal-close" (click)="cancelArchive()">×</button>
        </div>
        <p class="modal-body-text">{{ 'org_settings.archive_project_confirm' | t: { name: projectToArchive()!.name } }}</p>
        <div class="modal-footer">
          <button class="btn-ghost" (click)="cancelArchive()">{{ 'common.cancel' | t }}</button>
          <button class="btn-primary" (click)="archive()" [disabled]="archiving()" [title]="archiving() ? ('common.disabled_tooltip.operation_in_progress' | t) : ''">
            {{ archiving() ? ('common.loading' | t) : ('org_settings.archive_btn' | t) }}
          </button>
        </div>
      </div>
    </div>

    <!-- EDIT PROJECT MODAL -->
    <div *ngIf="editingProject()" class="modal-overlay" (click)="cancelEdit()">
      <div class="modal-panel" (click)="$event.stopPropagation()">
        <div class="modal-header">
          <h3 class="modal-title">{{ 'projects.edit_title' | t }}</h3>
          <button class="modal-close" (click)="cancelEdit()">×</button>
        </div>

        <div class="form-group">
          <label for="edit-proj-name">{{ 'project_new.name_label' | t }}</label>
          <input
            id="edit-proj-name"
            type="text"
            [ngModel]="editName()"
            (ngModelChange)="editName.set($event)"
            maxlength="100"
            autocomplete="off"
          />
        </div>

        <div class="form-group">
          <label for="edit-proj-description">{{ 'project_new.description_label' | t }}</label>
          <textarea
            id="edit-proj-description"
            [ngModel]="editDescription()"
            (ngModelChange)="editDescription.set($event)"
            rows="3"
            maxlength="500"
          ></textarea>
        </div>

        <div class="form-group">
          <label for="edit-proj-profile">{{ 'project_new.profile_label' | t }}</label>
          <select id="edit-proj-profile" [ngModel]="editProfileId()" (ngModelChange)="editProfileId.set($event)">
            @for (p of editProfiles(); track p.id) {
              <option [value]="p.id">
                {{ p.name }}{{ p.is_system ? (' — ' + ('project_new.profile_system_tag' | t)) : '' }}
              </option>
            }
          </select>
        </div>

        <div *ngIf="editError()" class="alert-error">{{ editError() }}</div>

        <div class="modal-footer">
          <button class="btn-ghost" (click)="cancelEdit()">{{ 'common.cancel' | t }}</button>
          <button
            class="btn-primary"
            (click)="saveEdit()"
            [disabled]="editSubmitting() || !editName().trim()"
            [title]="editSubmitting() ? ('common.disabled_tooltip.operation_in_progress' | t) : ''">
            {{ editSubmitting() ? ('common.loading' | t) : ('projects.edit_submit' | t) }}
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    :host { display: block; }
    .projects-page { padding: 0; }

    .page-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
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

    .btn-primary:hover { background: var(--ink-secondary); }

    .data-table-wrap {
      background: var(--surface-raised);
      border: 0.0625rem solid var(--border);
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
      border-bottom: 0.0625rem solid var(--border);
      background: var(--paper-secondary);
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

    .cell-primary { font-weight: 500; }
    .cell-muted { color: var(--muted); }
    .data-table th.cell-actions-header, .data-table td.cell-actions { text-align: right !important; }
    .data-table th.cell-actions-header { text-align: center !important; }
    .cell-actions { padding-right: var(--spacing-md); }

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

    .error-banner {
      background: var(--verdict-invalid-bg);
      color: var(--verdict-invalid);
      border: 0.0625rem solid var(--verdict-invalid-border);
      border-radius: var(--rounded-md);
      padding: var(--spacing-sm) var(--spacing-md);
      font-size: 0.8125rem;
    }

    .skeleton-list { display: flex; flex-direction: column; gap: var(--spacing-sm); }

    .skeleton {
      border-radius: var(--rounded-md);
      background: linear-gradient(90deg, var(--paper-secondary) 25%, #e5e2db 50%, var(--paper-secondary) 75%);
      background-size: 200% 100%;
      animation: shimmer 1.6s linear infinite;
    }

    .skeleton-row { height: 2.75rem; }

    @keyframes shimmer {
      0% { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: var(--spacing-md);
      padding: var(--spacing-xl) var(--spacing-lg);
      text-align: center;
    }

    .empty-text {
      font-size: 0.9375rem;
      color: var(--muted);
      margin: 0;
    }

    .cell-actions {
      white-space: nowrap;
      display: flex;
      gap: var(--spacing-sm);
      justify-content: center;
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
      border: 0.0625rem solid transparent;
      border-radius: var(--rounded-md);
      padding: 0.25rem 0.625rem;
      cursor: pointer;
      transition: color 0.12s ease, background-color 0.12s ease, border-color 0.12s ease;
    }

    .btn-ghost:hover:not(:disabled) { color: var(--ink); background: var(--paper-secondary); border-color: var(--border); }
    .btn-ghost:disabled { opacity: 0.45; cursor: not-allowed; }

    .modal-overlay {
      position: fixed;
      top: 0;
      right: 0;
      bottom: 0;
      left: 0;
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

    .form-group input,
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
      box-sizing: border-box;
    }

    .form-group textarea {
      resize: vertical;
      min-height: 4rem;
      line-height: 1.65;
    }

    .form-group input:focus,
    .form-group select:focus,
    .form-group textarea:focus {
      border-color: var(--ink);
      background: var(--surface-raised);
      box-shadow: 0 0 0 0.1875rem rgba(232, 213, 163, 0.4);
    }

    .alert-error {
      background: var(--verdict-invalid-bg);
      color: var(--verdict-invalid);
      border: 0.0625rem solid var(--verdict-invalid-border);
      border-radius: var(--rounded-md);
      padding: var(--spacing-sm) var(--spacing-md);
      font-size: 0.8125rem;
      margin-bottom: var(--spacing-md);
    }

    @media (max-width: 48rem) {
      .page-header { flex-wrap: wrap; }

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
    }
  `],
})
export class ProjectsComponent implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly authService = inject(AuthService);
  private readonly ts = inject(TranslationService);

  readonly isManager = this.authService.getUserRole() === 'MANAGER';
  readonly orgId = this.authService.getUser()?.organization_id ?? '';

  projects = signal<Project[]>([]);
  loading = signal(true);
  error = signal<string | null>(null);
  projectToArchive = signal<Project | null>(null);
  archiving = signal(false);

  editingProject = signal<Project | null>(null);
  editProfiles = signal<Profile[]>([]);
  editName = signal('');
  editDescription = signal('');
  editProfileId = signal('');
  editSubmitting = signal(false);
  editError = signal<string | null>(null);

  ngOnInit(): void {
    this.http.get<Project[]>(`/api/v1/organizations/${this.orgId}/projects`)
      .pipe(catchError(() => {
        this.error.set(this.ts.translateInstant('projects.load_error'));
        return of([] as Project[]);
      }))
      .subscribe(data => {
        this.projects.set(data);
        this.loading.set(false);
      });
  }

  confirmArchive(project: Project): void {
    this.projectToArchive.set(project);
  }

  cancelArchive(): void {
    this.projectToArchive.set(null);
  }

  archive(): void {
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

  unarchive(project: Project): void {
    this.http.post(`/api/v1/organizations/${this.orgId}/projects/${project.id}/unarchive`, {})
      .pipe(catchError(() => of(null)))
      .subscribe(res => {
        if (res === null) return;
        this.projects.update(projects => projects.map(p =>
          p.id === project.id ? { ...p, is_archived: false } : p
        ));
      });
  }

  openEdit(project: Project): void {
    this.editingProject.set(project);
    this.editName.set(project.name);
    this.editDescription.set(project.description ?? '');
    this.editProfileId.set(project.profile_id ?? '');
    this.editError.set(null);

    this.http.get<Profile[]>(`/api/v1/organizations/${this.orgId}/profiles`)
      .pipe(catchError(() => of([] as Profile[])))
      .subscribe(data => this.editProfiles.set(data));
  }

  cancelEdit(): void {
    this.editingProject.set(null);
  }

  saveEdit(): void {
    const project = this.editingProject();
    if (!project || !this.editName().trim()) return;

    this.editSubmitting.set(true);
    this.editError.set(null);

    const body = {
      name: this.editName().trim(),
      description: this.editDescription(),
      profile_id: this.editProfileId() || null,
    };

    this.http.patch<Project>(`/api/v1/projects/${project.id}`, body)
      .pipe(catchError((err: HttpErrorResponse) => {
        this.editError.set(err.error?.detail ?? this.ts.translateInstant('projects.edit_error'));
        this.editSubmitting.set(false);
        return of(null);
      }))
      .subscribe(updated => {
        this.editSubmitting.set(false);
        if (!updated) return;
        this.projects.update(projects => projects.map(p =>
          p.id === project.id ? { ...p, name: updated.name, description: updated.description, profile_id: updated.profile_id } : p
        ));
        this.editingProject.set(null);
      });
  }
}
