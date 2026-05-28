import { Component, inject, OnInit } from '@angular/core';
import {
  FormBuilder,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { AuthService, setAccessToken } from '../../../core/services/auth.service';
import { catchError, of } from 'rxjs';

interface LoginResponse {
  access_token: string;
}

function parseLoginError(err: HttpErrorResponse): string {
  if (err.status === 0 || !err.status) {
    return 'No se pudo conectar con el servidor. Compruebe su conexión a Internet.';
  }
  if (err.status === 401) {
    const detail = err.error?.detail ?? '';
    if (typeof detail === 'string' && detail.length > 0 && detail.length < 200) {
      return detail;
    }
    return 'El correo electrónico o la contraseña no son correctos.';
  }
  if (err.status === 403) {
    return 'Su cuenta está pendiente de activación. Revise su correo electrónico.';
  }
  if (err.status === 429) {
    return 'Demasiados intentos. Espere un momento antes de volver a intentarlo.';
  }
  if (err.status === 502 || err.status === 504) {
    return 'El servidor no responde. Puede estar reiniciándose. Inténtelo en unos segundos.';
  }
  if (err.status >= 500) {
    return 'Error interno del servidor. Inténtelo de nuevo más tarde.';
  }
  if (err.status === 400) {
    const detail = err.error?.detail ?? err.error?.message ?? '';
    if (typeof detail === 'string' && detail.length > 0 && detail.length < 200) {
      return detail;
    }
    return 'Los datos introducidos no son válidos. Revise los campos.';
  }
  if (err.status === 404) {
    return 'El servicio de autenticación no está disponible. Inténtelo de nuevo más tarde.';
  }
  return 'Ha ocurrido un error inesperado. Inténtelo de nuevo.';
}

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  template: `
    <div class="login-page">
      <a routerLink="/" class="login-back">
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
          <path d="M7.5 2.5L4 6l3.5 3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        Volver al inicio
      </a>

      <main class="login-main">
        <div class="login-panel">
          <div class="login-context">
            <div class="context-brand">
              SVAES
              <span class="brand-badge">beta</span>
            </div>
            <h1 class="context-title">
              Verificación<br />automática<br />de entregas
            </h1>
            <p class="context-desc">
              Sistema de trazabilidad operacional para equipos de
              desarrollo. Conecte sus herramientas, defina reglas
              de verificación y controle cada release.
            </p>
            <div class="context-features">
              <div class="context-feature">
                <span class="feature-num">10</span>
                <span class="feature-label">Reglas de verificación</span>
              </div>
              <div class="context-feature">
                <span class="feature-num">5+</span>
                <span class="feature-label">Conectores disponibles</span>
              </div>
            </div>
          </div>

          <div class="login-form">
            <form [formGroup]="loginForm" (ngSubmit)="onSubmit()" novalidate>
              <h2 class="form-title">Iniciar sesión</h2>

              <div class="alert-error" *ngIf="errorMessage">
                <svg class="alert-icon" width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <circle cx="7" cy="7" r="6" stroke="currentColor" stroke-width="1.2"/>
                  <path d="M7 4v3.5M7 10v.5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
                </svg>
                <span>{{ errorMessage }}</span>
              </div>

              <div class="form-group">
                <label for="email">Correo electrónico</label>
                <input
                  id="email"
                  type="email"
                  formControlName="email"
                  autocomplete="email"
                  placeholder="nombre@ejemplo.com"
                  [class.input-error]="fieldHasError('email')"
                />
                <div class="field-error" *ngIf="loginForm.get('email')?.hasError('required') && loginForm.get('email')?.touched">
                  El correo electrónico es obligatorio.
                </div>
                <div class="field-error" *ngIf="loginForm.get('email')?.hasError('email') && loginForm.get('email')?.touched">
                  Ingrese un correo electrónico válido.
                </div>
              </div>

              <div class="form-group">
                <label for="password">Contraseña</label>
                <input
                  id="password"
                  type="password"
                  formControlName="password"
                  autocomplete="current-password"
                  placeholder="&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;"
                  [class.input-error]="fieldHasError('password')"
                />
                <div class="field-error" *ngIf="loginForm.get('password')?.hasError('required') && loginForm.get('password')?.touched">
                  La contraseña es obligatoria.
                </div>
              </div>

              <button
                type="submit"
                class="btn-primary full-width btn-submit"
                [disabled]="loginForm.invalid || loading"
                [class.btn-loading]="loading"
              >
                <span *ngIf="!loading">Iniciar sesión</span>
                <span *ngIf="loading">Verificando&hellip;</span>
              </button>
            </form>
          </div>
        </div>
      </main>

      <footer class="login-footer">
        <span>&copy; 2026 SVAES</span>
        <nav class="footer-links">
          <a routerLink="/legal/privacidad">Privacidad</a>
          <span aria-hidden="true">&middot;</span>
          <a routerLink="/legal/aviso-legal">Aviso legal</a>
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
        gap: 6px;
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
        flex: 0 0 420px;
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
        border: 1px solid rgba(246, 244, 240, 0.15);
        border-radius: var(--rounded-sm);
        padding: 1px 6px;
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
        max-width: 320px;
      }

      .context-features {
        display: flex;
        gap: var(--spacing-xl);
      }

      .context-feature {
        display: flex;
        flex-direction: column;
        gap: 4px;
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
        max-width: 480px;
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

      .form-group input {
        width: 100%;
        background: var(--paper);
        color: var(--ink);
        border: 1px solid var(--border-strong);
        border-radius: var(--rounded-md);
        padding: 9px 12px;
        font-family: var(--font-sans);
        font-size: 0.9375rem;
        line-height: 1.5;
        outline: none;
        transition: border-color 0.15s ease, background-color 0.15s ease, box-shadow 0.15s ease;
      }

      .form-group input:focus {
        border-color: var(--ink);
        background: var(--surface-raised);
        box-shadow: 0 0 0 3px rgba(232, 213, 163, 0.4);
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
        height: 40px;
        transition: opacity 0.2s ease;
      }

      .btn-submit.btn-loading {
        opacity: 0.7;
        cursor: wait;
      }

      .alert-error {
        display: flex;
        align-items: flex-start;
        gap: var(--spacing-sm);
        background: var(--verdict-invalid-bg);
        color: var(--verdict-invalid);
        border: 1px solid var(--verdict-invalid-border);
        border-radius: var(--rounded-md);
        padding: var(--spacing-sm) var(--spacing-md);
        font-family: var(--font-sans);
        font-size: 0.8125rem;
        line-height: 1.5;
        margin-bottom: var(--spacing-md);
      }

      .alert-icon {
        flex-shrink: 0;
        margin-top: 2px;
      }

      .login-footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: var(--spacing-md) var(--spacing-lg);
        border-top: 1px solid var(--border);
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

      @media (max-width: 768px) {
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
      }
    `,
  ],
})
export class LoginComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly authService = inject(AuthService);

  readonly loginForm = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required]],
  });

  loading = false;
  errorMessage: string | null = null;

  ngOnInit(): void {
    if (this.authService.isAuthenticated()) {
      this.router.navigate(['/app/dashboard']);
    }
  }

  fieldHasError(name: string): boolean {
    const ctrl = this.loginForm.get(name);
    return !!(ctrl && ctrl.invalid && ctrl.touched);
  }

  onSubmit(): void {
    if (this.loginForm.invalid || this.loading) {
      this.loginForm.markAllAsTouched();
      return;
    }

    this.loading = true;
    this.errorMessage = null;

    const { email, password } = this.loginForm.value;

    this.http
      .post<LoginResponse>('/api/v1/auth/login', { email, password })
      .pipe(
        catchError((err: HttpErrorResponse) => {
          this.errorMessage = parseLoginError(err);
          this.loading = false;
          return of(null);
        }),
      )
      .subscribe({
        next: (response) => {
          if (!response?.access_token) {
            this.errorMessage =
              'El servidor devolvió una respuesta inesperada. Inténtelo de nuevo.';
            this.loading = false;
            return;
          }

          setAccessToken(response.access_token);
          this.router.navigate(['/app/dashboard']);
        },
        error: () => {
          this.errorMessage =
            'Ha ocurrido un error inesperado. Inténtelo de nuevo.';
          this.loading = false;
        },
      });
  }
}
