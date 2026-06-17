import { Component, inject, OnDestroy, OnInit, signal } from '@angular/core';
import {
  AbstractControl,
  FormBuilder,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { setAccessToken } from '../../../core/services/auth.service';
import { finalize, Subscription } from 'rxjs';
import { TranslatePipe } from '../../../core/i18n/translate.pipe';
import { TranslationService } from '../../../core/i18n/translation.service';

interface ActivateResponse {
  access_token: string;
}

interface PasswordChecks {
  minLength: boolean;
  uppercase: boolean;
  number: boolean;
  specialChar: boolean;
}

function passwordMatchValidator(control: AbstractControl): ValidationErrors | null {
  const password = control.get('password');
  const confirm = control.get('password_confirm');
  if (!password || !confirm) return null;
  return password.value === confirm.value ? null : { mismatch: true };
}

function passwordStrengthValidator(control: AbstractControl): ValidationErrors | null {
  const value: string = control.value || '';
  const valid =
    value.length >= 8 &&
    /[A-Z]/.test(value) &&
    /\d/.test(value) &&
    /[^a-zA-Z0-9]/.test(value);
  return valid ? null : { passwordStrength: true };
}

@Component({
  selector: 'app-activate-account',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, TranslatePipe],
  template: `
    <div class="activate-page">
      <header class="activate-header">
        <span class="activate-logo">SVAES</span>
      </header>

      <main class="activate-main">
        <div class="activate-card">

          <!-- ── Token expired / invalid ─────────────── -->
          <div *ngIf="tokenExpired" class="state-card">
            <div class="state-icon state-icon--error">✕</div>
            <h1 class="state-title">{{ 'activate.error.invalid_code' | t }}</h1>
            <p class="state-desc">{{ 'activate.error.generic' | t }}</p>
          </div>

          <!-- ── Success ─────────────────────────────── -->
          <div *ngIf="activationSuccess" class="state-card">
            <div class="state-icon state-icon--success">✓</div>
            <h1 class="state-title">{{ 'activate.success_title' | t }}</h1>
            <p class="state-desc">{{ 'activate.success_desc' | t }}</p>
          </div>

          <!-- ── Step form ───────────────────────────── -->
          <ng-container *ngIf="!tokenExpired && !activationSuccess">

            <!-- Step indicator -->
            <div class="stepper">
              <div class="step" [class.step--active]="step() === 1" [class.step--done]="step() > 1">
                <div class="step-circle">
                  <span *ngIf="step() <= 1">1</span>
                  <span *ngIf="step() > 1">✓</span>
                </div>
                <span class="step-label">{{ 'activate.step1_title' | t }}</span>
              </div>
              <div class="step-line" [class.step-line--done]="step() > 1"></div>
              <div class="step" [class.step--active]="step() === 2">
                <div class="step-circle">2</div>
                <span class="step-label">{{ 'activate.step2_title' | t }}</span>
              </div>
            </div>

            <form [formGroup]="activateForm" (ngSubmit)="onSubmit()" novalidate>

              <!-- ── Step 1: activation code ─────────── -->
              <div *ngIf="step() === 1" class="step-body">
                <h1 class="step-title">{{ 'activate.step1_title' | t }}</h1>
                <p class="step-desc">{{ 'activate.step1_desc' | t }}</p>

                <div class="form-group">
                  <label for="activationCode">{{ 'activate.code_label' | t }}</label>
                  <input
                    id="activationCode"
                    type="text"
                    formControlName="activation_code"
                    [placeholder]="'activate.code_placeholder' | t"
                    autocomplete="off"
                    spellcheck="false"
                    class="input-mono"
                  />
                  <div
                    *ngIf="activateForm.get('activation_code')?.invalid && activateForm.get('activation_code')?.touched"
                    class="field-error"
                  >
                    {{ 'activate.code_required' | t }}
                  </div>
                </div>

                <div class="step-footer">
                  <button
                    type="button"
                    class="btn-primary btn-full"
                    [disabled]="activateForm.get('activation_code')?.invalid"
                    (click)="nextStep()"
                  >
                    {{ 'common.continue' | t }}
                  </button>
                </div>
              </div>

              <!-- ── Step 2: password ────────────────── -->
              <div *ngIf="step() === 2" class="step-body">
                <h1 class="step-title">{{ 'activate.step2_title' | t }}</h1>
                <p class="step-desc">{{ 'activate.step2_desc' | t }}</p>

                <div class="form-group">
                  <label for="password">{{ 'activate.password_label' | t }}</label>
                  <div class="input-wrap">
                    <input
                      id="password"
                      [type]="showPassword() ? 'text' : 'password'"
                      formControlName="password"
                      autocomplete="new-password"
                    />
                    <button
                      type="button"
                      class="btn-reveal"
                      (click)="showPassword.set(!showPassword())"
                      [attr.aria-label]="showPassword() ? 'Ocultar' : 'Mostrar'"
                    >
                      {{ showPassword() ? '🙈' : '👁' }}
                    </button>
                  </div>
                </div>

                <div class="password-checklist">
                  <div class="checklist-item" [class.checklist-item--met]="passwordChecks.minLength">
                    <span class="checklist-icon">{{ passwordChecks.minLength ? '✓' : '○' }}</span>
                    <span>{{ 'activate.password_min_length' | t }}</span>
                  </div>
                  <div class="checklist-item" [class.checklist-item--met]="passwordChecks.uppercase">
                    <span class="checklist-icon">{{ passwordChecks.uppercase ? '✓' : '○' }}</span>
                    <span>{{ 'activate.password_strength_good' | t }}</span>
                  </div>
                  <div class="checklist-item" [class.checklist-item--met]="passwordChecks.number">
                    <span class="checklist-icon">{{ passwordChecks.number ? '✓' : '○' }}</span>
                    <span>{{ 'activate.password_strength_fair' | t }}</span>
                  </div>
                  <div class="checklist-item" [class.checklist-item--met]="passwordChecks.specialChar">
                    <span class="checklist-icon">{{ passwordChecks.specialChar ? '✓' : '○' }}</span>
                    <span>{{ 'activate.password_strength_strong' | t }}</span>
                  </div>
                </div>

                <div class="form-group">
                  <label for="passwordConfirm">{{ 'activate.confirm_label' | t }}</label>
                  <div class="input-wrap">
                    <input
                      id="passwordConfirm"
                      [type]="showConfirm() ? 'text' : 'password'"
                      formControlName="password_confirm"
                      autocomplete="new-password"
                    />
                    <button
                      type="button"
                      class="btn-reveal"
                      (click)="showConfirm.set(!showConfirm())"
                      [attr.aria-label]="showConfirm() ? 'Ocultar' : 'Mostrar'"
                    >
                      {{ showConfirm() ? '🙈' : '👁' }}
                    </button>
                  </div>
                  <div
                    *ngIf="activateForm.hasError('mismatch') && activateForm.get('password_confirm')?.touched"
                    class="field-error"
                  >
                    {{ 'activate.confirm_mismatch' | t }}
                  </div>
                </div>

                <div *ngIf="submitError" class="alert-error" role="alert">{{ submitError }}</div>

                <div class="step-footer step-footer--two">
                  <button type="button" class="btn-secondary" (click)="prevStep()">
                    {{ 'activate.back_login' | t }}
                  </button>
                  <button
                    type="submit"
                    class="btn-primary"
                    [disabled]="activateForm.get('password')?.invalid ||
                                activateForm.get('password_confirm')?.invalid ||
                                activateForm.hasError('mismatch') ||
                                loading"
                  >
                    <span *ngIf="loading" class="spinner"></span>
                    <span *ngIf="!loading">{{ 'activate.step2_button' | t }}</span>
                  </button>
                </div>
              </div>

            </form>
          </ng-container>

        </div>
      </main>

      <footer class="activate-footer">
        <span>&copy; 2026 SVAES</span>
      </footer>
    </div>
  `,
  styles: [`
    :host { display: block; }

    /* ── Page shell ─────────────────────────────────── */

    .activate-page {
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      background: var(--paper);
    }

    .activate-header {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: var(--spacing-lg) var(--spacing-xxl);
      border-bottom: 0.0625rem solid var(--border);
    }

    .activate-logo {
      font-family: var(--font-display);
      font-size: 1.25rem;
      letter-spacing: 0.04em;
      color: var(--ink);
    }

    .activate-main {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: var(--spacing-xl) var(--spacing-lg);
    }

    .activate-card {
      width: 100%;
      max-width: 35rem;
      background: var(--surface-raised);
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-lg);
      padding: var(--spacing-xl);
    }

    .activate-footer {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: var(--spacing-md);
      border-top: 0.0625rem solid var(--border);
      font-family: var(--font-sans);
      font-size: 0.75rem;
      color: var(--muted);
    }

    /* ── Stepper ─────────────────────────────────────── */

    .stepper {
      display: flex;
      align-items: center;
      margin-bottom: var(--spacing-xl);
    }

    .step {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: var(--spacing-xs);
    }

    .step-circle {
      width: 1.75rem;
      height: 1.75rem;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: var(--font-sans);
      font-size: 0.75rem;
      font-weight: 600;
      border: 0.0625rem solid var(--border-strong);
      color: var(--muted);
      background: transparent;
      transition: background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease;
    }

    .step--active .step-circle {
      background: var(--ink);
      color: var(--paper);
      border-color: var(--ink);
    }

    .step--done .step-circle {
      background: var(--accent);
      color: var(--ink);
      border-color: var(--accent-dark);
    }

    .step-label {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--muted);
      transition: color 0.2s ease;
    }

    .step--active .step-label,
    .step--done .step-label {
      color: var(--ink);
    }

    .step-line {
      flex: 1;
      height: 0.0625rem;
      background: var(--border);
      margin: 0 var(--spacing-sm);
      margin-bottom: 1.25rem;
      transition: background-color 0.2s ease;
    }

    .step-line--done {
      background: var(--accent-dark);
    }

    /* ── Step body ───────────────────────────────────── */

    .step-body {
      display: flex;
      flex-direction: column;
      gap: var(--spacing-md);
    }

    .step-title {
      font-family: var(--font-display);
      font-size: 1.5rem;
      font-weight: 400;
      line-height: 1.2;
      letter-spacing: -0.01em;
      color: var(--ink);
      margin: 0;
    }

    .step-desc {
      font-family: var(--font-sans);
      font-size: 0.8125rem;
      line-height: 1.55;
      color: var(--muted);
      margin: 0;
    }

    /* ── Form elements ───────────────────────────────── */

    .form-group {
      display: flex;
      flex-direction: column;
      gap: var(--spacing-xs);
    }

    .form-group label {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--ink);
    }

    .input-wrap {
      position: relative;
      display: flex;
    }

    .input-wrap input {
      flex: 1;
      padding-right: 2.5rem;
    }

    .form-group input {
      font-family: var(--font-sans);
      font-size: 0.9375rem;
      background: var(--paper);
      color: var(--ink);
      border: 0.0625rem solid var(--border-strong);
      border-radius: var(--rounded-md);
      padding: 0.5625rem 0.75rem;
      outline: none;
      width: 100%;
      box-sizing: border-box;
      transition: border-color 0.15s ease, background-color 0.15s ease;
    }

    .input-mono {
      font-family: var(--font-mono) !important;
      font-size: 0.8125rem !important;
      letter-spacing: 0.02em;
    }

    .form-group input:focus {
      border-color: var(--ink);
      background: var(--surface-raised);
      outline: 0.1875rem solid rgba(232, 213, 163, 0.4);
    }

    .btn-reveal {
      position: absolute;
      right: 0;
      top: 0;
      bottom: 0;
      width: 2.5rem;
      display: flex;
      align-items: center;
      justify-content: center;
      background: none;
      border: none;
      cursor: pointer;
      font-size: 1rem;
      color: var(--muted);
      border-radius: 0 var(--rounded-md) var(--rounded-md) 0;
      transition: color 0.12s ease;
    }

    .btn-reveal:hover { color: var(--ink); }

    .field-error {
      font-family: var(--font-sans);
      font-size: 0.75rem;
      color: var(--verdict-invalid);
    }

    /* ── Password checklist ──────────────────────────── */

    .password-checklist {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.25rem 0;
      background: var(--paper-secondary);
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-md);
      padding: var(--spacing-md);
    }

    .checklist-item {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);
      font-family: var(--font-sans);
      font-size: 0.8125rem;
      color: var(--muted);
      transition: color 0.15s ease;
    }

    .checklist-item--met { color: var(--verdict-valid); }

    .checklist-icon {
      width: 1rem;
      text-align: center;
      font-size: 0.75rem;
      font-weight: 600;
      flex-shrink: 0;
    }

    /* ── Buttons ─────────────────────────────────────── */

    .step-footer {
      display: flex;
      justify-content: flex-end;
      padding-top: var(--spacing-sm);
      border-top: 0.0625rem solid var(--border);
      margin-top: var(--spacing-xs);
    }

    .step-footer--two {
      justify-content: space-between;
    }

    .btn-full { width: 100%; }

    .btn-primary {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: var(--spacing-sm);
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
    }

    .btn-primary:hover:not(:disabled) { background: var(--ink-secondary); }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

    .btn-secondary {
      display: inline-flex;
      align-items: center;
      gap: var(--spacing-xs);
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
    }

    .btn-secondary:hover { background: var(--paper-secondary); }

    /* ── Spinner ─────────────────────────────────────── */

    .spinner {
      display: inline-block;
      width: 0.875rem;
      height: 0.875rem;
      border: 0.125rem solid var(--paper);
      border-top-color: transparent;
      border-radius: 50%;
      animation: spin 0.6s linear infinite;
    }

    @keyframes spin { to { transform: rotate(360deg); } }

    /* ── Error / success states ──────────────────────── */

    .alert-error {
      font-family: var(--font-sans);
      font-size: 0.8125rem;
      color: var(--verdict-invalid);
      background: var(--verdict-invalid-bg);
      border: 0.0625rem solid var(--verdict-invalid-border);
      border-radius: var(--rounded-sm);
      padding: var(--spacing-sm) var(--spacing-md);
    }

    .state-card {
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      padding: var(--spacing-lg) 0;
      gap: var(--spacing-md);
    }

    .state-icon {
      width: 3rem;
      height: 3rem;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.25rem;
      font-weight: 600;
    }

    .state-icon--success {
      background: var(--verdict-valid-bg);
      color: var(--verdict-valid);
      border: 0.0625rem solid var(--verdict-valid-border);
    }

    .state-icon--error {
      background: var(--verdict-invalid-bg);
      color: var(--verdict-invalid);
      border: 0.0625rem solid var(--verdict-invalid-border);
    }

    .state-title {
      font-family: var(--font-display);
      font-size: 1.5rem;
      font-weight: 400;
      color: var(--ink);
      margin: 0;
    }

    .state-desc {
      font-family: var(--font-sans);
      font-size: 0.9375rem;
      line-height: 1.65;
      color: var(--muted);
      margin: 0;
    }
  `],
})
export class ActivateAccountComponent implements OnInit, OnDestroy {
  private readonly fb = inject(FormBuilder);
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly ts = inject(TranslationService);

  readonly activateForm = this.fb.group(
    {
      activation_code: ['', [Validators.required]],
      password: ['', [Validators.required, passwordStrengthValidator]],
      password_confirm: ['', [Validators.required]],
    },
    { validators: passwordMatchValidator },
  );

  step = signal<1 | 2>(1);
  showPassword = signal(false);
  showConfirm = signal(false);

  activationSuccess = false;
  tokenExpired = false;
  loading = false;
  submitError: string | null = null;

  passwordChecks: PasswordChecks = {
    minLength: false,
    uppercase: false,
    number: false,
    specialChar: false,
  };

  private readonly passwordSub: Subscription;

  constructor() {
    this.passwordSub = this.activateForm
      .get('password')!
      .valueChanges.subscribe((value) => {
        this.updatePasswordChecks(value ?? '');
      });
  }

  ngOnInit(): void {
    const token = this.route.snapshot.queryParamMap.get('token');
    if (token) {
      this.activateForm.patchValue({ activation_code: token });
      this.step.set(2);
    }
  }

  ngOnDestroy(): void {
    this.passwordSub.unsubscribe();
  }

  nextStep(): void {
    this.activateForm.get('activation_code')?.markAsTouched();
    if (this.activateForm.get('activation_code')?.invalid) return;
    this.step.set(2);
  }

  prevStep(): void {
    this.step.set(1);
    this.submitError = null;
  }

  onSubmit(): void {
    if (this.activateForm.invalid || this.loading) return;

    this.loading = true;
    this.submitError = null;

    const { activation_code, password, password_confirm } = this.activateForm.value;

    this.http
      .post<ActivateResponse>('/api/v1/auth/activate', {
        activation_token: activation_code,
        password,
        password_confirm,
      })
      .pipe(finalize(() => { this.loading = false; }))
      .subscribe({
        next: (response) => {
          this.activationSuccess = true;
          setAccessToken(response.access_token);
          setTimeout(() => this.router.navigate(['/app/dashboard']), 300);
        },
        error: (err: HttpErrorResponse) => {
          if (err.status === 400 || err.status === 410) {
            this.tokenExpired = true;
          } else {
            this.submitError = this.ts.translateInstant('activate.error.generic');
          }
        },
      });
  }

  private updatePasswordChecks(value: string): void {
    this.passwordChecks.minLength = value.length >= 8;
    this.passwordChecks.uppercase = /[A-Z]/.test(value);
    this.passwordChecks.number = /\d/.test(value);
    this.passwordChecks.specialChar = /[^a-zA-Z0-9]/.test(value);
  }
}
