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
import { AuthService } from '../../../core/services/auth.service';
import { finalize, Subscription } from 'rxjs';
import { TranslatePipe } from '../../../core/i18n/translate.pipe';
import { TranslationService } from '../../../core/i18n/translation.service';

interface ActivateResponse {
  access_token: string;
  refresh_token?: string;
  token_type?: string;
}

interface PasswordChecks {
  minLength: boolean;
  uppercase: boolean;
  number: boolean;
  specialChar: boolean;
}

export function passwordMatchValidator(control: AbstractControl): ValidationErrors | null {
  const password = control.get('password');
  const confirm = control.get('password_confirm');
  if (!password || !confirm) return null;
  return password.value === confirm.value ? null : { mismatch: true };
}

export function passwordStrengthValidator(control: AbstractControl): ValidationErrors | null {
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
  templateUrl: './activate-account.component.html',
  styleUrl: './activate-account.component.scss',
})
export class ActivateAccountComponent implements OnInit, OnDestroy {
  private readonly fb = inject(FormBuilder);
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly ts = inject(TranslationService);
  private readonly authService = inject(AuthService);

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
          this.authService.storeTokens({ requires_2fa: false, ...response }, '');
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
