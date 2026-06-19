import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { catchError, of } from 'rxjs';
import { AuthService } from '../../../core/services/auth.service';
import { TranslationService } from '../../../core/i18n/translation.service';
import { TranslatePipe } from '../../../core/i18n/translate.pipe';

interface Profile {
  id: string;
  name: string;
  is_system?: boolean;
  is_default?: boolean;
}

@Component({
  selector: 'app-project-new',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule, TranslatePipe],
  template: `
    <div class="new-project-page">
      <div class="page-header">
        <div class="page-header-left">
          <a routerLink="/app/projects" class="back-link">{{ 'project_new.back_link' | t }}</a>
          <h1 class="page-title">{{ 'project_new.title' | t }}</h1>
        </div>
      </div>

      <div class="form-layout">
        <div class="card">
          <h2 class="card-title">{{ 'project_new.form_title' | t }}</h2>

          @if (profilesLoading()) {
            <div class="skeleton-list">
              <div class="skeleton sk-input"></div>
              <div class="skeleton sk-input"></div>
              <div class="skeleton sk-input"></div>
            </div>
          }

          @if (!profilesLoading()) {
            <form [formGroup]="form" (ngSubmit)="submit()">
              <div class="form-group">
                <label for="proj-name">{{ 'project_new.name_label' | t }}<span class="required-star" aria-hidden="true">*</span></label>
                <input
                  id="proj-name"
                  type="text"
                  formControlName="name"
                  aria-required="true"
                  [placeholder]="'project_new.name_placeholder' | t"
                  autocomplete="off"
                />
                @if (form.get('name')?.hasError('required') && form.get('name')?.touched) {
                  <div class="field-error">{{ 'project_new.name_required' | t }}</div>
                }
                @if (form.get('name')?.hasError('maxlength') && form.get('name')?.touched) {
                  <div class="field-error">{{ 'common.max_chars' | t : { max: 100 } }}</div>
                }
              </div>

              <div class="form-group">
                <label for="proj-description">
                  {{ 'project_new.description_label' | t }}
                  <span class="optional">({{ 'common.optional' | t }})</span>
                </label>
                <textarea
                  id="proj-description"
                  formControlName="description"
                  rows="3"
                  [placeholder]="'project_new.description_placeholder' | t"
                ></textarea>
                @if (form.get('description')?.hasError('maxlength') && form.get('description')?.touched) {
                  <div class="field-error">{{ 'common.max_chars' | t : { max: 500 } }}</div>
                }
              </div>

              <div class="form-group">
                <label for="proj-profile">{{ 'project_new.profile_label' | t }}<span class="required-star" aria-hidden="true">*</span></label>
                <select id="proj-profile" formControlName="profile_id" aria-required="true">
                  @for (p of profiles(); track p.id) {
                    <option [value]="p.id">
                      {{ p.name }}{{ p.is_system ? (' — ' + ('project_new.profile_system_tag' | t)) : '' }}
                    </option>
                  }
                </select>
                @if (customProfiles().length === 0) {
                  <div class="field-hint">{{ 'project_new.profile_default_hint' | t }}</div>
                }
                @if (form.get('profile_id')?.hasError('required') && form.get('profile_id')?.touched) {
                  <div class="field-error">{{ 'project_new.profile_required' | t }}</div>
                }
              </div>

              @if (submitError()) {
                <div class="alert-error">{{ submitError() }}</div>
              }

              <div class="form-footer">
                <a routerLink="/app/projects" class="btn-secondary">{{ 'common.cancel' | t }}</a>
                <button
                  type="submit"
                  class="btn-primary"
                  [disabled]="form.invalid || submitting()">
                  {{ submitting() ? ('project_new.submitting' | t) : ('project_new.submit' | t) }}
                </button>
              </div>
            </form>
          }
        </div>
      </div>
    </div>
  `,
  styles: [`
    :host { display: block; }
    .new-project-page { padding: 0; }

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

    .form-layout { max-width: 40rem; }

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

    .field-hint {
      font-size: 0.75rem;
      color: var(--muted);
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
export class ProjectNewComponent implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly fb = inject(FormBuilder);
  private readonly router = inject(Router);
  private readonly authService = inject(AuthService);
  private readonly ts = inject(TranslationService);

  profiles = signal<Profile[]>([]);
  profilesLoading = signal(true);
  submitting = signal(false);
  submitError = signal<string | null>(null);

  customProfiles = computed(() => this.profiles().filter(p => !p.is_system));

  form = this.fb.group({
    name: ['', [Validators.required, Validators.maxLength(100)]],
    description: ['', [Validators.maxLength(500)]],
    profile_id: ['', [Validators.required]],
  });

  ngOnInit(): void {
    const orgId = this.authService.getUser()?.organization_id;
    if (!orgId) {
      this.profilesLoading.set(false);
      return;
    }
    this.http.get<Profile[]>(`/api/v1/organizations/${orgId}/profiles`)
      .pipe(catchError(() => of([] as Profile[])))
      .subscribe(data => {
        this.profiles.set(data);
        const systemProfile = data.find(p => p.is_system);
        const defaultCustom = data.find(p => !p.is_system && p.is_default);
        const autoSelect = defaultCustom ?? systemProfile;
        if (autoSelect) {
          this.form.patchValue({ profile_id: autoSelect.id });
        }
        this.profilesLoading.set(false);
      });
  }

  submit(): void {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    const orgId = this.authService.getUser()?.organization_id;
    if (!orgId) return;

    this.submitting.set(true);
    this.submitError.set(null);

    const { name, description, profile_id } = this.form.value;
    const body = { name, description: description || '', profile_id };

    this.http.post<{ id: string }>(`/api/v1/organizations/${orgId}/projects`, body)
      .pipe(
        catchError((err: HttpErrorResponse) => {
          this.submitError.set(err.error?.detail ?? this.ts.translateInstant('project_new.error'));
          this.submitting.set(false);
          return of(null);
        })
      )
      .subscribe(res => {
        if (res) {
          this.router.navigate(['/app/projects']);
        }
      });
  }
}
