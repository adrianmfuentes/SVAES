import { Component, inject, OnInit, ChangeDetectorRef } from '@angular/core';
import {
  AbstractControl,
  FormBuilder,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { finalize } from 'rxjs';
import { TranslatePipe } from '../../../core/i18n/translate.pipe';

function passwordMatchValidator(control: AbstractControl): ValidationErrors | null {
  const password = control.get('password');
  const confirm = control.get('password_confirm');
  if (!password || !confirm) return null;
  return password.value === confirm.value ? null : { mismatch: true };
}

function passwordStrengthValidator(control: AbstractControl): ValidationErrors | null {
  const v: string = control.value || '';
  const valid =
    v.length >= 8 &&
    /[A-Z]/.test(v) &&
    /[a-z]/.test(v) &&
    /\d/.test(v) &&
    /[^a-zA-Z0-9]/.test(v);
  return valid ? null : { passwordStrength: true };
}

@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule, TranslatePipe],
  template: `
    <div class="reset-page">
      <header class="reset-header">
        <span class="reset-logo">SVAES</span>
      </header>

      <main class="reset-main">
        <div class="reset-card">

          <!-- Invalid / missing token -->
          <ng-container *ngIf="!token">
            <h1 class="card-title">{{ 'reset_password.error.invalid_token' | t }}</h1>
            <p class="card-desc">{{ 'reset_password.error.invalid_token' | t }}</p>
            <a routerLink="/auth/login" class="btn-primary">{{ 'reset_password.go_login' | t }}</a>
          </ng-container>

          <!-- Success -->
          <ng-container *ngIf="token && done">
            <div class="success-icon" aria-hidden="true">
              <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
                <circle cx="20" cy="20" r="19" stroke="currentColor" stroke-width="1.5"/>
                <path d="M12 20.5l6 6 10-12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
            <h1 class="card-title">{{ 'reset_password.success_title' | t }}</h1>
            <p class="card-desc">{{ 'reset_password.success_desc' | t }}</p>
            <a routerLink="/auth/login" class="btn-primary">{{ 'reset_password.go_login' | t }}</a>
          </ng-container>

          <!-- Form -->
          <ng-container *ngIf="token && !done">
            <h1 class="card-title">{{ 'reset_password.title' | t }}</h1>
            <p class="card-desc">{{ 'reset_password.desc' | t }}</p>

            <div class="alert-error" *ngIf="errorKey" role="alert">
              <svg class="alert-icon" width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                <circle cx="7" cy="7" r="6" stroke="currentColor" stroke-width="1.2"/>
                <path d="M7 4v3.5M7 10v.5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
              </svg>
              <span>{{ errorKey | t }}</span>
            </div>

            <form [formGroup]="form" (ngSubmit)="onSubmit()" novalidate>
              <div class="form-group">
                <label for="password">{{ 'reset_password.password_label' | t }}<span class="required-star" aria-hidden="true">*</span></label>
                <input
                  id="password"
                  type="password"
                  formControlName="password"
                  autocomplete="new-password"
                  aria-required="true"
                  [placeholder]="'reset_password.password_placeholder' | t"
                  [class.input-error]="form.get('password')?.invalid && form.get('password')?.touched"
                />
                <div class="field-error" *ngIf="form.get('password')?.hasError('required') && form.get('password')?.touched">
                  {{ 'reset_password.password_required' | t }}
                </div>
                <div class="field-error" *ngIf="form.get('password')?.hasError('passwordStrength') && form.get('password')?.touched">
                  {{ 'reset_password.password_complexity' | t }}
                </div>
              </div>

              <div class="form-group">
                <label for="password_confirm">{{ 'reset_password.confirm_label' | t }}<span class="required-star" aria-hidden="true">*</span></label>
                <input
                  id="password_confirm"
                  type="password"
                  formControlName="password_confirm"
                  autocomplete="new-password"
                  aria-required="true"
                  [placeholder]="'reset_password.confirm_placeholder' | t"
                  [class.input-error]="form.get('password_confirm')?.invalid && form.get('password_confirm')?.touched || form.hasError('mismatch') && form.get('password_confirm')?.touched"
                />
                <div class="field-error" *ngIf="form.get('password_confirm')?.hasError('required') && form.get('password_confirm')?.touched">
                  {{ 'reset_password.confirm_required' | t }}
                </div>
                <div class="field-error" *ngIf="form.hasError('mismatch') && form.get('password_confirm')?.touched">
                  {{ 'reset_password.password_mismatch' | t }}
                </div>
              </div>

              <button
                type="submit"
                class="btn-primary full-width"
                [disabled]="form.invalid || loading"
                [title]="form.invalid ? ('common.disabled_tooltip.form_invalid' | t) : ('common.disabled_tooltip.operation_in_progress' | t)"
                [class.btn-loading]="loading"
              >
                <span *ngIf="!loading">{{ 'reset_password.submit' | t }}</span>
                <span *ngIf="loading">{{ 'reset_password.saving' | t }}</span>
              </button>
            </form>
          </ng-container>

        </div>
      </main>
    </div>
  `,
  styles: [`
    :host { display: block; }

    .reset-page {
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      background: var(--paper);
    }

    .reset-header {
      padding: var(--spacing-lg) var(--spacing-xl);
      border-bottom: 1px solid var(--border);
    }

    .reset-logo {
      font-family: var(--font-sans);
      font-size: 0.75rem;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--ink);
    }

    .reset-main {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: var(--spacing-xl) var(--spacing-md);
    }

    .reset-card {
      width: 100%;
      max-width: 400px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 2rem;
    }

    .card-title {
      font-family: var(--font-serif);
      font-size: 1.5rem;
      font-weight: 400;
      color: var(--ink);
      margin: 0 0 0.5rem;
    }

    .card-desc {
      font-size: 0.9rem;
      color: var(--muted);
      line-height: 1.6;
      margin: 0 0 1.5rem;
    }

    .success-icon {
      color: #2D7A4F;
      margin-bottom: 1rem;
    }

    .form-group {
      margin-bottom: 1rem;
    }

    label {
      display: block;
      font-size: 0.8125rem;
      font-weight: 500;
      color: var(--ink);
      margin-bottom: 0.375rem;
    }

    .required-star {
      color: var(--danger, #C0392B);
      margin-left: 2px;
    }

    input {
      width: 100%;
      padding: 0.5rem 0.75rem;
      font-size: 0.9375rem;
      font-family: var(--font-sans);
      color: var(--ink);
      background: var(--paper);
      border: 1px solid var(--border);
      border-radius: 4px;
      box-sizing: border-box;
      transition: border-color 0.15s;
      outline: none;
    }

    input:focus {
      border-color: var(--ink);
    }

    input.input-error {
      border-color: var(--danger, #C0392B);
    }

    .field-error {
      font-size: 0.75rem;
      color: var(--danger, #C0392B);
      margin-top: 0.25rem;
    }

    .alert-error {
      display: flex;
      align-items: flex-start;
      gap: 0.5rem;
      padding: 0.625rem 0.875rem;
      background: #FDECEA;
      border: 1px solid #F5C6C2;
      border-radius: 4px;
      font-size: 0.8125rem;
      color: #8B1A10;
      margin-bottom: 1rem;
    }

    .alert-icon {
      flex-shrink: 0;
      margin-top: 1px;
    }

    .btn-primary {
      display: inline-block;
      padding: 0.5625rem 1.125rem;
      background: var(--ink);
      color: var(--paper);
      border: none;
      border-radius: 4px;
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      text-decoration: none;
      cursor: pointer;
      transition: opacity 0.15s;
    }

    .btn-primary:hover:not(:disabled) {
      opacity: 0.85;
    }

    .btn-primary:disabled {
      opacity: 0.45;
      cursor: not-allowed;
    }

    .btn-primary.full-width {
      width: 100%;
      text-align: center;
      margin-top: 0.5rem;
    }

    .btn-primary.btn-loading {
      opacity: 0.65;
      cursor: not-allowed;
    }

    /* ── Responsive ──────────────────────────────────── */

    @media (max-width: 48rem) {
      .reset-header { padding: var(--spacing-md) var(--spacing-lg); }
      .reset-main { padding: var(--spacing-md); }
      .reset-card {
        max-width: 100%;
        padding: 1.5rem;
      }
      .card-title { font-size: 1.25rem; }
      .card-desc { font-size: 0.8125rem; }

      label { font-size: 0.6875rem; }
      input {
        padding: 0.625rem 0.75rem;
        min-height: 2.75rem;
        font-size: 0.875rem;
      }

      .btn-primary.full-width {
        min-height: 2.75rem;
        padding: 0.625rem 1rem;
      }

      .alert-error { font-size: 0.75rem; }
    }

    @media (max-width: 22.5rem) {
      .reset-card { padding: 1rem; }
    }
  `],
})
export class ResetPasswordComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly http = inject(HttpClient);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly cdr = inject(ChangeDetectorRef);

  token: string | null = null;
  loading = false;
  done = false;
  errorKey: string | null = null;

  readonly form = this.fb.group(
    {
      password: ['', [Validators.required, passwordStrengthValidator]],
      password_confirm: ['', [Validators.required]],
    },
    { validators: passwordMatchValidator },
  );

  ngOnInit(): void {
    this.token = this.route.snapshot.queryParamMap.get('token');
  }

  onSubmit(): void {
    if (this.form.invalid || this.loading || !this.token) {
      this.form.markAllAsTouched();
      return;
    }

    this.loading = true;
    this.errorKey = null;

    const { password, password_confirm } = this.form.value;

    this.http
      .post('/api/v1/auth/reset-password', {
        token: this.token,
        password,
        password_confirm,
      })
      .pipe(finalize(() => { this.loading = false; this.cdr.detectChanges(); }))
      .subscribe({
        next: () => {
          this.done = true;
          this.cdr.detectChanges();
        },
        error: (err: HttpErrorResponse) => {
          if (err.status === 410) {
            this.errorKey = 'reset_password.error.expired_token';
          } else if (err.status === 400) {
            this.errorKey = 'reset_password.error.invalid_token';
          } else {
            this.errorKey = 'reset_password.error.internal';
          }
          this.cdr.detectChanges();
        },
      });
  }
}
