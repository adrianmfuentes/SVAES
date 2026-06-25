import { Component, inject, OnInit, ChangeDetectorRef } from '@angular/core';
import {
  FormBuilder,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../../core/services/auth.service';

import { TranslatePipe } from '../../../core/i18n/translate.pipe';
import { LangToggleComponent } from '../../../core/components/lang-toggle/lang-toggle.component';
import { catchError, finalize, of } from 'rxjs';


const STATUS_ERROR_MAP: Record<number, string> = {
  400: 'login.error.invalid_data',
  401: 'login.error.wrong_credentials',
  403: 'login.error.pending_activation',
  404: 'login.error.auth_unavailable',
  429: 'login.error.too_many',
  502: 'login.error.server_unreachable',
  503: 'login.error.server_unreachable',
  504: 'login.error.server_unreachable',
};

function extractDetail(err: HttpErrorResponse): string | null {
  const detail = err.error?.detail ?? err.error?.message ?? '';
  if (typeof detail === 'string' && detail.length > 0 && detail.length < 200) {
    return detail;
  }
  return null;
}

function parseLoginErrorKey(err: HttpErrorResponse): string {
  if (err.status === 0 || !err.status) {
    return 'login.error.no_connection';
  }

  if (err.status >= 500) {
    return 'login.error.internal';
  }

  const mapped = STATUS_ERROR_MAP[err.status];
  if (mapped) {
    return extractDetail(err) ?? mapped;
  }

  return extractDetail(err) ?? 'login.error.unexpected';
}

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule, TranslatePipe, LangToggleComponent],
  template: `
    <div class="login-page">
      <a routerLink="/" class="login-back">
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true" focusable="false">
          <path d="M7.5 2.5L4 6l3.5 3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        {{ 'login.back_home' | t }}
      </a>

      <main class="login-main">
        <div class="login-panel">
          <div class="login-context">
            <div class="context-brand">
              SVAES
              <span class="brand-badge">{{ 'common.beta' | t }}</span>
            </div>
            <h1 class="context-title">
              {{ 'login.context_title_line1' | t }}<br />{{ 'login.context_title_line2' | t }}<br />{{ 'login.context_title_line3' | t }}
            </h1>
            <p class="context-desc">
              {{ 'login.context_desc' | t }}
            </p>
            <div class="context-features">
              <div class="context-feature">
                <span class="feature-num">10</span>
                <span class="feature-label">{{ 'login.feature_rules' | t }}</span>
              </div>
              <div class="context-feature">
                <span class="feature-num">5+</span>
                <span class="feature-label">{{ 'login.feature_connectors' | t }}</span>
              </div>
            </div>
          </div>

          <!-- Step 1: email + password -->
          <div class="login-form" *ngIf="!totpRequired && !forgotMode">
            <form [formGroup]="loginForm" (ngSubmit)="onSubmit()" novalidate>
              <h2 class="form-title">{{ 'login.title' | t }}</h2>

              <div class="alert-error" *ngIf="errorKey" role="alert">
                <svg class="alert-error-icon" width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true" focusable="false">
                  <circle cx="7" cy="7" r="6" stroke="currentColor" stroke-width="1.2"/>
                  <path d="M7 4v3.5M7 10v.5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
                </svg>
                <span>{{ errorKey | t }}</span>
              </div>

              <div class="form-group">
                <label for="email">{{ 'login.email_label' | t }}<span class="required-star" aria-hidden="true">*</span></label>
                <input
                  id="email"
                  type="email"
                  formControlName="email"
                  autocomplete="email"
                  aria-required="true"
                  [placeholder]="'login.email_placeholder' | t"
                  [class.input-error]="fieldHasError('email')"
                />
                <div class="field-error" *ngIf="loginForm.get('email')?.hasError('required') && loginForm.get('email')?.touched">
                  {{ 'login.email_required' | t }}
                </div>
                <div class="field-error" *ngIf="loginForm.get('email')?.hasError('email') && loginForm.get('email')?.touched">
                  {{ 'login.email_invalid' | t }}
                </div>
              </div>

              <div class="form-group">
                <label for="password">{{ 'login.password_label' | t }}<span class="required-star" aria-hidden="true">*</span></label>
                <input
                  id="password"
                  type="password"
                  formControlName="password"
                  autocomplete="current-password"
                  aria-required="true"
                  [placeholder]="'login.password_placeholder' | t"
                  [class.input-error]="fieldHasError('password')"
                />
                <div class="field-error" *ngIf="loginForm.get('password')?.hasError('required') && loginForm.get('password')?.touched">
                  {{ 'login.password_required' | t }}
                </div>
              </div>

              <button
                type="submit"
                class="btn-primary full-width btn-submit"
                [disabled]="loginForm.invalid || loading"
                [title]="loginForm.invalid ? ('common.disabled_tooltip.form_invalid' | t) : ('common.disabled_tooltip.operation_in_progress' | t)"
                [class.btn-loading]="loading"
              >
                <span *ngIf="!loading">{{ 'login.submit' | t }}</span>
                <span *ngIf="loading">{{ 'login.verifying' | t }}</span>
              </button>
            </form>
            <p class="form-footer-link">
              {{ 'login.no_account' | t }}
              <a routerLink="/request-access">{{ 'login.request_access' | t }}</a>
            </p>
            <p class="form-footer-link" style="margin-top:0.5rem;">
              <button type="button" class="btn-link" (click)="goToForgot()">
                {{ 'login.forgot_password' | t }}
              </button>
            </p>
          </div>

          <!-- Step 2: TOTP code -->
          <div class="login-form" *ngIf="totpRequired && !forgotMode">
            <form [formGroup]="totpForm" (ngSubmit)="onSubmitTotp()" novalidate>
              <h2 class="form-title">{{ 'login.2fa_title' | t }}</h2>
              <p class="totp-hint">{{ 'login.2fa_hint' | t }}</p>

              <div class="alert-error" *ngIf="errorKey" role="alert">
                <svg class="alert-error-icon" width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true" focusable="false">
                  <circle cx="7" cy="7" r="6" stroke="currentColor" stroke-width="1.2"/>
                  <path d="M7 4v3.5M7 10v.5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
                </svg>
                <span>{{ errorKey | t }}</span>
              </div>

              <div class="form-group">
                <label for="totp-code">{{ 'login.2fa_code_label' | t }}<span class="required-star" aria-hidden="true">*</span></label>
                <input
                  id="totp-code"
                  type="text"
                  inputmode="numeric"
                  formControlName="code"
                  autocomplete="one-time-code"
                  aria-required="true"
                  [placeholder]="'login.2fa_code_placeholder' | t"
                  [class.input-error]="totpForm.get('code')?.invalid && totpForm.get('code')?.touched"
                  maxlength="6"
                />
                <div class="field-error" *ngIf="totpForm.get('code')?.hasError('required') && totpForm.get('code')?.touched">
                  {{ 'login.2fa_code_required' | t }}
                </div>
                <div class="field-error" *ngIf="totpForm.get('code')?.hasError('pattern') && totpForm.get('code')?.touched">
                  {{ 'login.2fa_code_invalid' | t }}
                </div>
              </div>

              <button
                type="submit"
                class="btn-primary full-width btn-submit"
                [disabled]="totpForm.invalid || loading"
                [title]="totpForm.invalid ? ('common.disabled_tooltip.form_invalid' | t) : ('common.disabled_tooltip.operation_in_progress' | t)"
                [class.btn-loading]="loading"
              >
                <span *ngIf="!loading">{{ 'login.2fa_verify' | t }}</span>
                <span *ngIf="loading">{{ 'login.verifying' | t }}</span>
              </button>
            </form>
            <p class="form-footer-link">
              <button type="button" class="btn-link" (click)="backToLogin()">
                {{ 'login.2fa_back' | t }}
              </button>
            </p>
          </div>

          <!-- Step: Forgot password -->
          <div class="login-form" *ngIf="forgotMode && !forgotSent">
            <h2 class="form-title">{{ 'forgot_password.title' | t }}</h2>
            <p class="totp-hint">{{ 'forgot_password.desc' | t }}</p>

            <form [formGroup]="forgotForm" (ngSubmit)="onSubmitForgot()" novalidate>
              <div class="form-group">
                <label for="forgot-email">{{ 'forgot_password.email_label' | t }}<span class="required-star" aria-hidden="true">*</span></label>
                <input
                  id="forgot-email"
                  type="email"
                  formControlName="email"
                  autocomplete="email"
                  aria-required="true"
                  [placeholder]="'login.email_placeholder' | t"
                  [class.input-error]="forgotForm.get('email')?.invalid && forgotForm.get('email')?.touched"
                />
                <div class="field-error" *ngIf="forgotForm.get('email')?.hasError('required') && forgotForm.get('email')?.touched">
                  {{ 'forgot_password.email_required' | t }}
                </div>
                <div class="field-error" *ngIf="forgotForm.get('email')?.hasError('email') && forgotForm.get('email')?.touched">
                  {{ 'forgot_password.email_invalid' | t }}
                </div>
              </div>

              <button
                type="submit"
                class="btn-primary full-width btn-submit"
                [disabled]="forgotForm.invalid || loading"
                [title]="forgotForm.invalid ? ('common.disabled_tooltip.form_invalid' | t) : ('common.disabled_tooltip.operation_in_progress' | t)"
                [class.btn-loading]="loading"
              >
                <span *ngIf="!loading">{{ 'forgot_password.submit' | t }}</span>
                <span *ngIf="loading">{{ 'forgot_password.sending' | t }}</span>
              </button>
            </form>
            <p class="form-footer-link">
              <button type="button" class="btn-link" (click)="backFromForgot()">
                {{ 'forgot_password.back' | t }}
              </button>
            </p>
          </div>

          <!-- Step: Forgot password — sent -->
          <div class="login-form" *ngIf="forgotMode && forgotSent">
            <h2 class="form-title">{{ 'forgot_password.sent_title' | t }}</h2>
            <p class="totp-hint">{{ 'forgot_password.sent_desc' | t }}</p>
            <p class="form-footer-link">
              <button type="button" class="btn-link" (click)="backFromForgot()">
                {{ 'forgot_password.back' | t }}
              </button>
            </p>
          </div>
        </div>
      </main>

      <footer class="login-footer">
        <span>&copy; 2026 SVAES</span>
        <nav class="footer-links">
          <app-lang-toggle theme="light" />
          <span aria-hidden="true">&middot;</span>
          <a routerLink="/legal/privacidad">{{ 'login.footer_privacy' | t }}</a>
          <span aria-hidden="true">&middot;</span>
          <a routerLink="/legal/aviso-legal">{{ 'login.footer_legal' | t }}</a>
        </nav>
      </footer>
    </div>
  `,
  styles: [
    `
      :host {
        display: block;
      }

      .login-page {
        min-height: 100vh;
        display: flex;
        flex-direction: column;
        background: var(--paper);
      }

      .login-back {
        position: absolute;
        top: var(--spacing-lg);
        left: var(--spacing-lg);
        display: inline-flex;
        align-items: center;
        gap: 0.375rem;
        font-family: var(--font-sans);
        font-size: 0.8125rem;
        font-weight: 500;
        color: var(--muted);
        transition: color 0.15s ease;
        text-decoration: none;
        z-index: 5;
      }

      .login-back:hover {
        color: var(--ink);
      }

      .login-back svg {
        flex-shrink: 0;
      }

      .login-main {
        flex: 1;
        display: flex;
        align-items: stretch;
      }

      .login-panel {
        flex: 1;
        display: flex;
        align-items: stretch;
        min-height: 0;
      }

      .login-context {
        flex: 0 0 26.25rem;
        background: var(--ink);
        color: var(--paper);
        display: flex;
        flex-direction: column;
        justify-content: center;
        padding: var(--spacing-xxl);
        position: relative;
      }

      .context-brand {
        font-family: var(--font-display);
        font-size: 1.25rem;
        letter-spacing: 0.04em;
        display: flex;
        align-items: center;
        gap: var(--spacing-sm);
        margin-bottom: var(--spacing-xl);
      }

      .brand-badge {
        font-family: var(--font-sans);
        font-size: 0.625rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--muted);
        background: rgba(246, 244, 240, 0.12);
        border: 0.0625rem solid rgba(246, 244, 240, 0.15);
        border-radius: var(--rounded-sm);
        padding: 0.0625rem 0.375rem;
      }

      .context-title {
        font-family: var(--font-display);
        font-size: 2.5rem;
        font-weight: 400;
        line-height: 1.08;
        letter-spacing: -0.025em;
        color: var(--paper);
        margin: 0 0 var(--spacing-lg);
      }

      .context-desc {
        font-family: var(--font-sans);
        font-size: 0.875rem;
        line-height: 1.7;
        color: rgba(246, 244, 240, 0.6);
        margin: 0 0 var(--spacing-xl);
        max-width: 20rem;
      }

      .context-features {
        display: flex;
        gap: var(--spacing-xl);
      }

      .context-feature {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
      }

      .feature-num {
        font-family: var(--font-display);
        font-size: 1.75rem;
        line-height: 1;
        letter-spacing: -0.02em;
        color: var(--accent);
      }

      .feature-label {
        font-family: var(--font-sans);
        font-size: 0.6875rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: rgba(246, 244, 240, 0.45);
      }

      .login-form {
        flex: 1;
        display: flex;
        flex-direction: column;
        justify-content: center;
        padding: var(--spacing-xxl);
        max-width: 30rem;
        margin: 0 auto;
        width: 100%;
      }

      .form-title {
        font-family: var(--font-display);
        font-size: 1.5rem;
        font-weight: 400;
        line-height: 1.2;
        letter-spacing: -0.01em;
        color: var(--ink);
        margin: 0 0 var(--spacing-lg);
      }

      .totp-hint {
        font-family: var(--font-sans);
        font-size: 0.875rem;
        color: var(--muted);
        margin: 0 0 var(--spacing-lg);
        line-height: 1.5;
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

      .required-star {
        color: var(--verdict-invalid);
        margin-left: 0.25rem;
        font-size: 0.75rem;
      }

      .form-group input {
        width: 100%;
        background: var(--paper);
        color: var(--ink);
        border: 0.0625rem solid var(--border-strong);
        border-radius: var(--rounded-md);
        padding: 0.5625rem 0.75rem;
        font-family: var(--font-sans);
        font-size: 0.9375rem;
        line-height: 1.5;
        outline: none;
        transition: border-color 0.15s ease, background-color 0.15s ease, box-shadow 0.15s ease;
      }

      .form-group input:focus {
        border-color: var(--ink);
        background: var(--surface-raised);
        box-shadow: 0 0 0 0.1875rem rgba(232, 213, 163, 0.4);
      }

      .form-group input.input-error {
        border-color: var(--verdict-invalid-border);
        background: var(--verdict-invalid-bg);
      }

      .form-group input::placeholder {
        color: var(--muted);
        opacity: 0.6;
      }

      .field-error {
        font-family: var(--font-sans);
        font-size: 0.75rem;
        color: var(--verdict-invalid);
        margin-top: var(--spacing-xs);
      }

      .btn-submit {
        margin-top: var(--spacing-sm);
        width: 100%;
        height: 2.5rem;
        transition: opacity 0.2s ease;
      }

      .btn-submit.btn-loading {
        opacity: 0.7;
        cursor: wait;
      }

      .form-footer-link {
        font-family: var(--font-sans);
        font-size: 0.8125rem;
        color: var(--muted);
        text-align: center;
        margin: var(--spacing-md) 0 0;
      }

      .form-footer-link a {
        font-weight: 500;
        color: var(--ink);
        transition: color 0.15s ease;
      }

      .form-footer-link a:hover {
        color: var(--accent-dark);
      }

      .btn-link {
        background: none;
        border: none;
        padding: 0;
        font-family: var(--font-sans);
        font-size: 0.8125rem;
        font-weight: 500;
        color: var(--ink);
        cursor: pointer;
        transition: color 0.15s ease;
      }

      .btn-link:hover {
        color: var(--accent-dark);
      }

      .login-footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: var(--spacing-md) var(--spacing-lg);
        border-top: 0.0625rem solid var(--border);
        background: var(--paper);
        font-size: 0.75rem;
        color: var(--muted);
      }

      .footer-links {
        display: flex;
        align-items: center;
        gap: var(--spacing-md);
      }

      .footer-links a {
        color: var(--muted);
        transition: color 0.15s ease;
      }

      .footer-links a:hover {
        color: var(--ink);
      }

      @media (max-width: 48rem) {
        .login-panel {
          flex-direction: column;
        }

        .login-context {
          flex: none;
          padding: var(--spacing-xl) var(--spacing-lg);
        }

        .context-title {
          font-size: 1.75rem;
        }

        .context-desc {
          display: none;
        }

        .context-features {
          display: none;
        }

        .login-form {
          padding: var(--spacing-xl) var(--spacing-lg);
          max-width: none;
        }

        .login-back {
          top: var(--spacing-md);
          left: var(--spacing-md);
        }

        .form-group input {
          padding: 0.625rem 0.75rem;
          min-height: 2.75rem;
          font-size: 0.875rem;
        }

        .form-group label { font-size: 0.625rem; }

        .btn-submit {
          min-height: 2.75rem;
          padding: 0.625rem 1rem;
        }

        .login-footer {
          flex-direction: column;
          gap: var(--spacing-sm);
          text-align: center;
          padding: var(--spacing-sm) var(--spacing-md);
        }

        .footer-links { gap: var(--spacing-sm); flex-wrap: wrap; justify-content: center; }
      }
    `,
  ],
})
export class LoginComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly router = inject(Router);
  private readonly authService = inject(AuthService);
  private readonly cdr = inject(ChangeDetectorRef);
  private readonly http = inject(HttpClient);

  readonly loginForm = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required]],
  });

  readonly totpForm = this.fb.group({
    code: ['', [Validators.required, Validators.pattern(/^\d{6}$/)]],
  });

  readonly forgotForm = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
  });

  loading = false;
  errorKey: string | null = null;
  totpRequired = false;
  forgotMode = false;
  forgotSent = false;
  private pendingTotpToken: string | null = null;
  private pendingEmail = '';

  ngOnInit(): void {
    if (this.authService.isAuthenticated()) {
      this.router.navigate(['/app/dashboard']);
    }
  }

  fieldHasError(name: string): boolean {
    const ctrl = this.loginForm.get(name);
    return !!(ctrl?.invalid && ctrl?.touched);
  }

  onSubmit(): void {
    if (this.loginForm.invalid || this.loading) {
      this.loginForm.markAllAsTouched();
      return;
    }

    this.loading = true;
    this.errorKey = null;

    const { email, password } = this.loginForm.value;
    this.pendingEmail = email!;

    this.authService
      .login(email as string, password as string)
      .pipe(
        finalize(() => {
          this.loading = false;
          this.cdr.detectChanges();
        }),
        catchError((err: HttpErrorResponse) => {
          this.errorKey = parseLoginErrorKey(err);
          return of(null);
        }),
      )
      .subscribe({
        next: (response) => {
          if (!response) {
            return;
          }

          if (response.requires_2fa) {
            this.pendingTotpToken = response.totp_token ?? null;
            this.totpRequired = true;
            this.cdr.detectChanges();
            return;
          }

          if (!response.access_token) {
            this.errorKey = 'login.error.unexpected_response';
            this.cdr.detectChanges();
            return;
          }

          this.authService.storeTokens(response, this.pendingEmail);
          const destination = this.authService.isAdmin() ? '/app/system' : '/app/dashboard';
          this.router.navigate([destination]);
        },
      });
  }

  onSubmitTotp(): void {
    if (this.totpForm.invalid || this.loading || !this.pendingTotpToken) {
      this.totpForm.markAllAsTouched();
      return;
    }

    this.loading = true;
    this.errorKey = null;

    const { code } = this.totpForm.value;

    this.authService
      .verify2fa(this.pendingTotpToken, code as string)
      .pipe(
        finalize(() => {
          this.loading = false;
          this.cdr.detectChanges();
        }),
        catchError((err: HttpErrorResponse) => {
          this.errorKey = parseLoginErrorKey(err);
          return of(null);
        }),
      )
      .subscribe({
        next: (response) => {
          if (!response?.access_token) {
            this.errorKey = 'login.error.unexpected_response';
            this.cdr.detectChanges();
            return;
          }
          this.authService.storeTokens(response, this.pendingEmail);
          const destination = this.authService.isAdmin() ? '/app/system' : '/app/dashboard';
          this.router.navigate([destination]);
        },
      });
  }

  backToLogin(): void {
    this.totpRequired = false;
    this.pendingTotpToken = null;
    this.errorKey = null;
    this.totpForm.reset();
  }

  goToForgot(): void {
    this.forgotMode = true;
    this.forgotSent = false;
    this.errorKey = null;
    this.forgotForm.reset();
    this.cdr.detectChanges();
  }

  backFromForgot(): void {
    this.forgotMode = false;
    this.forgotSent = false;
    this.errorKey = null;
    this.forgotForm.reset();
    this.cdr.detectChanges();
  }

  onSubmitForgot(): void {
    if (this.forgotForm.invalid || this.loading) {
      this.forgotForm.markAllAsTouched();
      return;
    }

    this.loading = true;
    this.errorKey = null;

    const { email } = this.forgotForm.value;

    this.http
      .post('/api/v1/auth/forgot-password', { email })
      .pipe(
        finalize(() => {
          this.loading = false;
          this.cdr.detectChanges();
        }),
      )
      .subscribe({
        next: () => {
          this.forgotSent = true;
          this.cdr.detectChanges();
        },
        error: () => {
          // Always show success to prevent enumeration
          this.forgotSent = true;
          this.cdr.detectChanges();
        },
      });
  }
}
