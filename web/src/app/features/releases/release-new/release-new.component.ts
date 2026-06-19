import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterModule, ActivatedRoute } from '@angular/router';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { catchError, of } from 'rxjs';
import { AuthService } from '../../../core/services/auth.service';
import { TranslationService } from '../../../core/i18n/translation.service';
import { TranslatePipe } from '../../../core/i18n/translate.pipe';

interface Project {
  id: string;
  name: string;
}

@Component({
  selector: 'app-release-new',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule, TranslatePipe],
  template: `
    <div class="new-release-page">
      <div class="page-header">
        <div class="page-header-left">
          <a routerLink="/app/releases" class="back-link">{{ 'release_new.back_link' | t }}</a>
          <h1 class="page-title">{{ isEditMode() ? ('release_new.edit_title' | t) : ('release_new.title' | t) }}</h1>
        </div>
      </div>

      <div class="form-layout">
        <div class="card">
          <h2 class="card-title">{{ 'release_new.form_title' | t }}</h2>

          @if (loading()) {
            <div class="skeleton-list">
              <div class="skeleton sk-input"></div>
              <div class="skeleton sk-input"></div>
              <div class="skeleton sk-input"></div>
            </div>
          }

          @if (!loading()) {
            @if (!isEditMode() && projects().length === 0) {
              <div class="empty-notice">
                {{ 'release_new.no_projects' | t }}
                @if (isManager) {
                  {{ 'release_new.no_projects_manager' | t }}
                  <a routerLink="/app/projects/new" class="inline-link">{{ 'release_new.no_projects_link' | t }}</a>.
                }
              </div>
            }

            @if (isEditMode() || projects().length > 0) {
              <form [formGroup]="form" (ngSubmit)="submit()">
                @if (!isEditMode()) {
                  <div class="form-group">
                    <label for="project-id">{{ 'release_new.project_label' | t }}<span class="required-star" aria-hidden="true">*</span></label>
                    <select id="project-id" formControlName="project_id" aria-required="true">
                      <option value="">{{ 'release_new.project_placeholder' | t }}</option>
                      @for (p of projects(); track p.id) {
                        <option [value]="p.id">{{ p.name }}</option>
                      }
                    </select>
                    @if (form.get('project_id')?.hasError('required') && form.get('project_id')?.touched) {
                      <div class="field-error">{{ 'release_new.project_required' | t }}</div>
                    }
                  </div>
                }

                <div class="form-group">
                  <label for="name">{{ 'release_new.name_label' | t }}<span class="required-star" aria-hidden="true">*</span></label>
                  <input
                    id="name"
                    type="text"
                    formControlName="name"
                    aria-required="true"
                    [placeholder]="'release_new.name_placeholder' | t"
                    autocomplete="off"
                  />
                  @if (form.get('name')?.hasError('required') && form.get('name')?.touched) {
                    <div class="field-error">{{ 'release_new.name_required' | t }}</div>
                  }
                  @if (form.get('name')?.hasError('maxlength') && form.get('name')?.touched) {
                    <div class="field-error">{{ 'common.max_chars' | t : { max: 100 } }}</div>
                  }
                </div>

                <div class="form-group">
                  <label for="version">{{ 'release_new.version_label' | t }}<span class="required-star" aria-hidden="true">*</span></label>
                  <input
                    id="version"
                    type="text"
                    formControlName="version"
                    aria-required="true"
                    placeholder="1.4.2"
                    autocomplete="off"
                  />
                  @if (form.get('version')?.hasError('required') && form.get('version')?.touched) {
                    <div class="field-error">{{ 'release_new.version_required' | t }}</div>
                  }
                </div>

                <div class="form-group">
                  <label for="description">{{ 'release_new.description_label' | t }} <span class="optional">({{ 'common.optional' | t }})</span></label>
                  <textarea
                    id="description"
                    formControlName="description"
                    rows="3"
                    [placeholder]="'release_new.description_placeholder' | t"
                  ></textarea>
                  @if (form.get('description')?.hasError('maxlength') && form.get('description')?.touched) {
                    <div class="field-error">{{ 'common.max_chars' | t : { max: 1000 } }}</div>
                  }
                </div>

                @if (submitError()) {
                  <div class="alert-error">{{ submitError() }}</div>
                }

                <div class="form-footer">
                  <a routerLink="/app/releases" class="btn-secondary">{{ 'common.cancel' | t }}</a>
                  <button
                    type="submit"
                    class="btn-primary"
                    [disabled]="form.invalid || submitting()">
                    {{ submitting() ? (isEditMode() ? ('release_new.saving' | t) : ('release_new.submitting' | t)) : (isEditMode() ? ('release_new.save' | t) : ('release_new.submit' | t)) }}
                  </button>
                </div>
              </form>
            }
          }
        </div>
      </div>
    </div>
  `,
  styles: [`
    :host { display: block; }
    .new-release-page { padding: 0; }

    .page-header {
      display: flex;
      align-items: flex-start;
      margin-bottom: var(--spacing-lg);
    }

    .page-header-left {
      display: flex;
      flex-direction: column;
      gap: var(--spacing-xs);
    }

    .back-link {
      font-family: var(--font-sans);
      font-size: 0.8125rem;
      color: var(--muted);
      text-decoration: none;
      transition: color 0.12s ease;
    }

    .back-link:hover { color: var(--ink); }

    .page-title {
      font-family: var(--font-display);
      font-size: 2.25rem;
      font-weight: 400;
      line-height: 1.1;
      letter-spacing: -0.02em;
      margin: 0;
      color: var(--ink);
    }

    .form-layout {
      max-width: 40rem;
    }

    .card {
      background: var(--surface-raised);
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-lg);
      padding: var(--spacing-lg);
    }

    .card-title {
      font-family: var(--font-display);
      font-size: 1.5rem;
      font-weight: 400;
      line-height: 1.2;
      letter-spacing: -0.01em;
      margin: 0 0 var(--spacing-lg);
      color: var(--ink);
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

    .optional {
      font-weight: 400;
      text-transform: none;
      letter-spacing: 0;
      color: var(--muted);
      font-size: 0.75rem;
    }

    .required-star {
      color: var(--verdict-invalid);
      margin-left: 0.25rem;
      font-size: 0.75rem;
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
      min-height: 5rem;
      line-height: 1.65;
    }

    .form-group input:focus,
    .form-group select:focus,
    .form-group textarea:focus {
      border-color: var(--ink);
      background: var(--surface-raised);
      box-shadow: 0 0 0 0.1875rem rgba(232, 213, 163, 0.4);
    }

    .field-error {
      font-size: 0.75rem;
      color: var(--verdict-invalid);
      margin-top: var(--spacing-xs);
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

    .form-footer {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: var(--spacing-sm);
      padding-top: var(--spacing-md);
      border-top: 0.0625rem solid var(--border);
      margin-top: var(--spacing-md);
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
      transition: background-color 0.15s ease;
      text-decoration: none;
    }

    .btn-primary:hover:not(:disabled) { background: var(--ink-secondary); }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

    .btn-secondary {
      display: inline-flex;
      align-items: center;
      background: transparent;
      color: var(--ink);
      border: 0.0625rem solid var(--border-strong);
      border-radius: var(--rounded-md);
      padding: 0.5625rem 1.125rem;
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      cursor: pointer;
      transition: background-color 0.15s ease;
      text-decoration: none;
    }

    .btn-secondary:hover { background: var(--paper-secondary); }

    .skeleton-list {
      display: flex;
      flex-direction: column;
      gap: var(--spacing-md);
    }

    .skeleton {
      border-radius: var(--rounded-md);
      background: linear-gradient(90deg, var(--paper-secondary) 25%, #e5e2db 50%, var(--paper-secondary) 75%);
      background-size: 200% 100%;
      animation: shimmer 1.6s linear infinite;
    }

    .sk-input { height: 2.5rem; }

    @keyframes shimmer {
      0% { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }

    .empty-notice {
      font-size: 0.9375rem;
      color: var(--muted);
      line-height: 1.65;
      padding: var(--spacing-lg) 0;
    }

    .inline-link {
      color: var(--ink);
      font-weight: 500;
      text-decoration: underline;
    }

    @media (max-width: 48rem) {
      .page-title { font-size: 1.75rem; }

      .form-layout { max-width: 100%; }

      .form-footer {
        flex-direction: column-reverse;
        align-items: stretch;
      }

      .btn-primary,
      .btn-secondary {
        justify-content: center;
        width: 100%;
      }
    }
  `],
})
export class ReleaseNewComponent implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly fb = inject(FormBuilder);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly authService = inject(AuthService);
  private readonly ts = inject(TranslationService);

  readonly isManager = this.authService.getUserRole() === 'MANAGER';
  readonly isEditMode = signal(false);
  readonly loading = signal(true);
  readonly submitting = signal(false);
  readonly submitError = signal<string | null>(null);

  projects = signal<Project[]>([]);
  releaseId: string | null = null;

  form = this.fb.group({
    project_id: ['', [Validators.required]],
    name: ['', [Validators.required, Validators.maxLength(100)]],
    version: ['', [Validators.required]],
    description: ['', [Validators.maxLength(1000)]],
  });

  ngOnInit(): void {
    this.releaseId = this.route.snapshot.paramMap.get('id');

    if (this.releaseId) {
      this.isEditMode.set(true);
      this.loadRelease();
    } else {
      this.loadProjects();
    }
  }

  private loadRelease(): void {
    this.http.get<{ id: string; name: string; version: string; description: string; project_id?: string }>(
      `/api/v1/releases/${this.releaseId}`
    ).pipe(
      catchError(() => {
        this.router.navigate(['/app/releases']);
        return of(null);
      })
    ).subscribe(data => {
      if (data) {
        this.form.patchValue({
          name: data.name ?? '',
          version: data.version ?? '',
          description: data.description ?? '',
        });
        this.form.get('project_id')?.clearValidators();
        this.form.get('project_id')?.updateValueAndValidity();
      }
      this.loading.set(false);
    });
  }

  private loadProjects(): void {
    this.http.get<Project[]>('/api/v1/projects')
      .pipe(catchError(() => of([] as Project[])))
      .subscribe(data => {
        this.projects.set(data);
        this.loading.set(false);
      });
  }

  submit(): void {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.submitting.set(true);
    this.submitError.set(null);

    const { name, version, description } = this.form.value;
    const body: Record<string, unknown> = { name, version, description: description || '' };

    if (this.isEditMode() && this.releaseId) {
      this.http.patch<{ id: string }>(
        `/api/v1/releases/${this.releaseId}`, body
      ).pipe(
        catchError((err: HttpErrorResponse) => {
          this.submitError.set(err.error?.detail ?? this.ts.translateInstant('release_new.edit_error'));
          this.submitting.set(false);
          return of(null);
        })
      ).subscribe(res => {
        if (res) {
          this.router.navigate(['/app/releases', this.releaseId]);
        }
      });
    } else {
      const { project_id } = this.form.value;
      this.http.post<{ id: string; status: string }>(
        `/api/v1/projects/${project_id}/releases`, body
      ).pipe(
        catchError((err: HttpErrorResponse) => {
          this.submitError.set(err.error?.detail ?? this.ts.translateInstant('release_new.error'));
          this.submitting.set(false);
          return of(null);
        })
      ).subscribe(res => {
        if (res) {
          this.router.navigate(['/app/releases', res.id]);
        }
      });
    }
  }
}
