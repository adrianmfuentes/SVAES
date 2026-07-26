import { Component, inject, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
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
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss'],
})
export class LoginComponent implements OnInit, OnDestroy {
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
  errorParams: Record<string, string | number> | undefined;
  totpRequired = false;
  forgotMode = false;
  forgotSent = false;
  cooldownSeconds = 0;
  private pendingTotpToken: string | null = null;
  private pendingEmail = '';
  private cooldownTimer?: ReturnType<typeof setInterval>;

  ngOnInit(): void {
    if (this.authService.isAuthenticated()) {
      this.router.navigate(['/app/dashboard']);
    }
  }

  ngOnDestroy(): void {
    if (this.cooldownTimer) {
      clearInterval(this.cooldownTimer);
    }
  }

  private handleError(err: HttpErrorResponse): void {
    if (err.status === 429) {
      this.startCooldown(err);
      return;
    }
    this.errorKey = parseLoginErrorKey(err);
    this.errorParams = undefined;
  }

  private startCooldown(err: HttpErrorResponse): void {
    const retryAfterHeader = err.headers?.get('Retry-After');
    const parsed = retryAfterHeader ? Number.parseInt(retryAfterHeader, 10) : Number.NaN;
    const seconds = Number.isFinite(parsed) && parsed > 0 ? parsed : 60;

    if (this.cooldownTimer) {
      clearInterval(this.cooldownTimer);
    }
    this.cooldownSeconds = seconds;
    this.errorKey = 'login.error.too_many';
    this.errorParams = { seconds: this.cooldownSeconds };

    this.cooldownTimer = setInterval(() => {
      this.cooldownSeconds -= 1;
      if (this.cooldownSeconds <= 0) {
        clearInterval(this.cooldownTimer);
        this.cooldownTimer = undefined;
        this.cooldownSeconds = 0;
        this.errorKey = null;
        this.errorParams = undefined;
      } else {
        this.errorParams = { seconds: this.cooldownSeconds };
      }
      this.cdr.detectChanges();
    }, 1000);
  }

  fieldHasError(name: string): boolean {
    const ctrl = this.loginForm.get(name);
    return !!(ctrl?.invalid && ctrl?.touched);
  }

  onSubmit(): void {
    if (this.loginForm.invalid || this.loading || this.cooldownSeconds > 0) {
      this.loginForm.markAllAsTouched();
      return;
    }

    this.loading = true;
    this.errorKey = null;
    this.errorParams = undefined;

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
          this.handleError(err);
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
    if (this.totpForm.invalid || this.loading || this.cooldownSeconds > 0 || !this.pendingTotpToken) {
      this.totpForm.markAllAsTouched();
      return;
    }

    this.loading = true;
    this.errorKey = null;
    this.errorParams = undefined;

    const { code } = this.totpForm.value;

    this.authService
      .verify2fa(this.pendingTotpToken, code as string)
      .pipe(
        finalize(() => {
          this.loading = false;
          this.cdr.detectChanges();
        }),
        catchError((err: HttpErrorResponse) => {
          this.handleError(err);
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
