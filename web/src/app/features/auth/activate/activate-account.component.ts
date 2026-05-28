import { Component, inject, OnDestroy, OnInit } from '@angular/core';
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
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { setAccessToken } from '../../../core/services/auth.service';
import { Subscription } from 'rxjs';

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
  if (!password || !confirm) {
    return null;
  }
  return password.value === confirm.value ? null : { mismatch: true };
}

function passwordStrengthValidator(control: AbstractControl): ValidationErrors | null {
  const value: string = control.value || '';
  const valid =
    value.length >= 12 &&
    /[A-Z]/.test(value) &&
    /\d/.test(value) &&
    /[^a-zA-Z0-9]/.test(value);
  return valid ? null : { passwordStrength: true };
}

@Component({
  selector: 'app-activate-account',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatProgressSpinnerModule,
  ],
  template: `
    <div class="activate-view">
      <div *ngIf="tokenMissing" class="activate-error-page">
        <p class="activate-error-title">
          Enlace de activación inválido o expirado
        </p>
        <p class="activate-error-sub">
          <a href="mailto:soporte@svaes.local">Contacta con soporte</a>
        </p>
      </div>

      <mat-card *ngIf="tokenExpired" class="activate-card">
        <mat-card-content>
          <p class="activate-expired-message">
            Este enlace ya fue utilizado o ha expirado. Contacta con tu
            administrador.
          </p>
        </mat-card-content>
      </mat-card>

      <mat-card
        *ngIf="!tokenMissing && !tokenExpired"
        class="activate-card"
      >
        <mat-card-header>
          <mat-card-title>Activar cuenta</mat-card-title>
        </mat-card-header>

        <mat-card-content>
          <form
            [formGroup]="activateForm"
            (ngSubmit)="onSubmit()"
            novalidate
            class="activate-form"
          >
            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Nueva contraseña</mat-label>
              <input
                matInput
                type="password"
                formControlName="password"
                autocomplete="new-password"
              />
            </mat-form-field>

            <div class="password-checklist">
              <div
                class="checklist-item"
                [class.checklist-item--met]="passwordChecks.minLength"
              >
                <span class="checklist-icon">{{
                  passwordChecks.minLength ? '\u2713' : '\u2717'
                }}</span>
                <span>Mínimo 12 caracteres</span>
              </div>
              <div
                class="checklist-item"
                [class.checklist-item--met]="passwordChecks.uppercase"
              >
                <span class="checklist-icon">{{
                  passwordChecks.uppercase ? '\u2713' : '\u2717'
                }}</span>
                <span>Al menos una mayúscula</span>
              </div>
              <div
                class="checklist-item"
                [class.checklist-item--met]="passwordChecks.number"
              >
                <span class="checklist-icon">{{
                  passwordChecks.number ? '\u2713' : '\u2717'
                }}</span>
                <span>Al menos un número</span>
              </div>
              <div
                class="checklist-item"
                [class.checklist-item--met]="passwordChecks.specialChar"
              >
                <span class="checklist-icon">{{
                  passwordChecks.specialChar ? '\u2713' : '\u2717'
                }}</span>
                <span>Al menos un carácter especial</span>
              </div>
            </div>

            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Confirmar contraseña</mat-label>
              <input
                matInput
                type="password"
                formControlName="password_confirm"
                autocomplete="new-password"
              />
              <mat-error
                *ngIf="
                  activateForm.hasError('mismatch') &&
                  activateForm.get('password_confirm')?.touched
                "
              >
                Las contraseñas no coinciden
              </mat-error>
            </mat-form-field>

            <div class="activate-error" *ngIf="submitError">
              {{ submitError }}
            </div>

            <button
              mat-flat-button
              type="submit"
              class="full-width activate-submit"
              [disabled]="activateForm.invalid || loading"
            >
              <mat-spinner
                *ngIf="loading"
                diameter="20"
                class="button-spinner"
              ></mat-spinner>
              <span *ngIf="!loading">Activar cuenta</span>
            </button>
          </form>
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: [
    `
      :host {
        display: block;
      }

      .activate-view {
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--paper);
        padding: var(--spacing-lg);
      }

      .activate-card {
        width: 100%;
        max-width: 420px;
        background: var(--surface-raised);
        border: 1px solid var(--border);
        border-radius: var(--rounded-lg);
      }

      mat-card-header {
        justify-content: center;
        padding-bottom: var(--spacing-md);
      }

      mat-card-title {
        font-family: var(--font-display);
        font-size: 1.5rem;
        letter-spacing: 0.04em;
        color: var(--ink);
      }

      mat-card-content {
        padding: 0 var(--spacing-lg) var(--spacing-lg);
      }

      .activate-form {
        display: flex;
        flex-direction: column;
      }

      .full-width {
        width: 100%;
      }

      .password-checklist {
        margin: 0 0 var(--spacing-md) 0;
      }

      .checklist-item {
        display: flex;
        align-items: center;
        gap: var(--spacing-sm);
        font-family: var(--font-sans);
        font-size: 0.8125rem;
        color: var(--muted);
        padding: 2px 0;
      }

      .checklist-item--met {
        color: var(--verdict-valid);
      }

      .checklist-icon {
        width: 16px;
        text-align: center;
        font-weight: 600;
      }

      .activate-submit {
        margin-top: var(--spacing-sm);
        height: 40px;
      }

      button[mat-flat-button] {
        background-color: var(--ink);
        color: var(--paper);
        border: 1px solid var(--ink);
        border-radius: var(--rounded-md);
        font-family: var(--font-sans);
        font-size: 0.6875rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }

      button[mat-flat-button]:disabled {
        background-color: var(--paper-secondary);
        color: var(--muted);
        border-color: var(--border);
      }

      button[mat-flat-button]:not(:disabled):hover {
        background-color: var(--ink-secondary);
      }

      .button-spinner {
        display: inline-block;
      }

      .activate-error {
        font-family: var(--font-sans);
        font-size: 0.8125rem;
        color: var(--verdict-invalid);
        background: var(--verdict-invalid-bg);
        border: 1px solid var(--verdict-invalid-border);
        border-radius: var(--rounded-sm);
        padding: var(--spacing-sm) var(--spacing-md);
        margin-bottom: var(--spacing-md);
      }

      .activate-error-page {
        text-align: center;
      }

      .activate-error-title {
        font-family: var(--font-display);
        font-size: 1.5rem;
        color: var(--ink);
        margin: 0 0 var(--spacing-md) 0;
      }

      .activate-error-sub {
        font-family: var(--font-sans);
        font-size: 0.9375rem;
        color: var(--muted);
        margin: 0;
      }

      .activate-error-sub a {
        color: var(--ink);
        text-decoration: underline;
      }

      .activate-expired-message {
        font-family: var(--font-sans);
        font-size: 0.9375rem;
        color: var(--ink);
        margin: 0;
        text-align: center;
      }
    `,
  ],
})
export class ActivateAccountComponent implements OnInit, OnDestroy {
  private readonly fb = inject(FormBuilder);
  private readonly http = inject(HttpClient);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  readonly activateForm = this.fb.group(
    {
      password: ['', [Validators.required, passwordStrengthValidator]],
      password_confirm: ['', [Validators.required]],
    },
    { validators: passwordMatchValidator },
  );

  activationToken: string | null = null;
  tokenMissing = false;
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
    if (!token || !this.isValidUuid(token)) {
      this.tokenMissing = true;
      return;
    }
    this.activationToken = token;
  }

  ngOnDestroy(): void {
    this.passwordSub.unsubscribe();
  }

  onSubmit(): void {
    if (this.activateForm.invalid || this.loading || !this.activationToken) {
      return;
    }

    this.loading = true;
    this.submitError = null;

    const { password, password_confirm } = this.activateForm.value;

    this.http
      .post<ActivateResponse>('/api/v1/auth/activate', {
        activation_token: this.activationToken,
        password,
        password_confirm,
      })
      .subscribe({
        next: (response) => {
          setAccessToken(response.access_token);
          this.router.navigate(['/app/dashboard']);
        },
        error: (err: HttpErrorResponse) => {
          this.loading = false;
          if (err.status === 400 || err.status === 410) {
            this.tokenExpired = true;
          } else {
            this.submitError =
              'Error al activar la cuenta. Inténtalo de nuevo.';
          }
        },
      });
  }

  private updatePasswordChecks(value: string): void {
    this.passwordChecks.minLength = value.length >= 12;
    this.passwordChecks.uppercase = /[A-Z]/.test(value);
    this.passwordChecks.number = /\d/.test(value);
    this.passwordChecks.specialChar = /[^a-zA-Z0-9]/.test(value);
  }

  private isValidUuid(value: string): boolean {
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
      value,
    );
  }
}
