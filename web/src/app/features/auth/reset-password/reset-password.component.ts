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
import { SeoService } from '../../../core/services/seo.service';

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
  templateUrl: './reset-password.component.html',
  styleUrls: ['./reset-password.component.scss'],
})
export class ResetPasswordComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly http = inject(HttpClient);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly cdr = inject(ChangeDetectorRef);
  private readonly seo = inject(SeoService);

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
    this.seo.setNoIndex('Restablecer contraseña');
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
