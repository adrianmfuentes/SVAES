import { Component, inject, OnInit } from '@angular/core';
import {
  FormBuilder,
  FormControl,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { Router } from '@angular/router';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { AuthService, setAccessToken } from '../../../core/services/auth.service';
import { catchError, of } from 'rxjs';

interface Phase1Response {
  temp_token: string;
  organizations: OrganizationOption[];
}

interface Phase2Response {
  access_token: string;
}

interface OrganizationOption {
  id: string;
  name: string;
  role: string;
}

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatSelectModule,
    MatProgressSpinnerModule,
  ],
  template: `
    <div class="login-view">
      <mat-card class="login-card">
        <mat-card-header>
          <mat-card-title>SVAES</mat-card-title>
        </mat-card-header>

        <mat-card-content>
          <form
            [formGroup]="loginForm"
            (ngSubmit)="onSubmit()"
            novalidate
            class="login-form"
          >
            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Correo electrónico</mat-label>
              <input
                matInput
                type="email"
                formControlName="email"
                autocomplete="email"
              />
              <mat-error
                *ngIf="
                  loginForm.get('email')?.hasError('required') &&
                  loginForm.get('email')?.touched
                "
              >
                El correo electrónico es obligatorio.
              </mat-error>
              <mat-error
                *ngIf="
                  loginForm.get('email')?.hasError('email') &&
                  loginForm.get('email')?.touched
                "
              >
                Ingrese un correo válido.
              </mat-error>
            </mat-form-field>

            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Contraseña</mat-label>
              <input
                matInput
                type="password"
                formControlName="password"
                autocomplete="current-password"
              />
              <mat-error
                *ngIf="
                  loginForm.get('password')?.hasError('required') &&
                  loginForm.get('password')?.touched
                "
              >
                La contraseña es obligatoria.
              </mat-error>
            </mat-form-field>

            <div class="login-error" *ngIf="phase1Error">
              {{ phase1Error }}
            </div>

            <button
              mat-flat-button
              type="submit"
              class="full-width login-submit"
              [disabled]="loginForm.invalid || loading"
            >
              <mat-spinner
                *ngIf="loading"
                diameter="20"
                class="button-spinner"
              ></mat-spinner>
              <span *ngIf="!loading">Iniciar sesión</span>
            </button>
          </form>

          <div class="org-selector" *ngIf="showOrgSelector">
            <p class="org-selector-label">
              Seleccione la organización con la que desea ingresar:
            </p>

            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Organización</mat-label>
              <mat-select
                [formControl]="orgControl"
                (selectionChange)="onOrgSelected($event.value)"
              >
                <mat-option
                  *ngFor="let org of organizations"
                  [value]="org.id"
                >
                  <span class="org-option">
                    <span>{{ org.name }}</span>
                    <span class="role-badge" [ngClass]="org.role.toLowerCase()">
                      {{ org.role }}
                    </span>
                  </span>
                </mat-option>
              </mat-select>
            </mat-form-field>

            <div class="login-error" *ngIf="phase2Error">
              {{ phase2Error }}
            </div>
          </div>
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: [
    `
      :host {
        display: block;
      }

      .login-view {
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--paper);
        padding: var(--spacing-lg);
      }

      .login-card {
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

      .login-form {
        display: flex;
        flex-direction: column;
      }

      .full-width {
        width: 100%;
      }

      .login-submit {
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

      .org-selector {
        margin-top: var(--spacing-lg);
        padding-top: var(--spacing-lg);
        border-top: 1px solid var(--border);
      }

      .org-selector-label {
        font-family: var(--font-sans);
        font-size: 0.8125rem;
        color: var(--ink);
        margin: 0 0 var(--spacing-md) 0;
      }

      .org-option {
        display: flex;
        align-items: center;
        justify-content: space-between;
        width: 100%;
      }

      .role-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: var(--rounded-sm);
        font-family: var(--font-sans);
        font-size: 0.6875rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        white-space: nowrap;
        margin-left: var(--spacing-sm);
      }

      .role-badge.admin {
        background: var(--verdict-invalid-bg);
        color: var(--verdict-invalid);
        border: 1px solid var(--verdict-invalid-border);
      }

      .role-badge.manager {
        background: var(--verdict-warning-bg);
        color: var(--verdict-warning);
        border: 1px solid var(--verdict-warning-border);
      }

      .role-badge.member {
        background: var(--verdict-unevaluated-bg);
        color: var(--verdict-unevaluated);
        border: 1px solid var(--verdict-unevaluated-border);
      }

      .login-error {
        font-family: var(--font-sans);
        font-size: 0.8125rem;
        color: var(--verdict-invalid);
        background: var(--verdict-invalid-bg);
        border: 1px solid var(--verdict-invalid-border);
        border-radius: var(--rounded-sm);
        padding: var(--spacing-sm) var(--spacing-md);
        margin-bottom: var(--spacing-md);
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

  orgControl = new FormControl('');

  tempToken: string | null = null;
  organizations: OrganizationOption[] = [];
  showOrgSelector = false;
  loading = false;
  phase1Error: string | null = null;
  phase2Error: string | null = null;

  ngOnInit(): void {
    if (this.authService.isAuthenticated()) {
      this.router.navigate(['/app/dashboard']);
    }
  }

  onSubmit(): void {
    if (this.loginForm.invalid || this.loading) {
      return;
    }

    this.loading = true;
    this.phase1Error = null;
    this.phase2Error = null;
    this.showOrgSelector = false;
    this.tempToken = null;
    this.organizations = [];

    const { email, password } = this.loginForm.value;

    this.http
      .post<Phase1Response>('/api/v1/auth/login', { email, password })
      .pipe(
        catchError((_err: HttpErrorResponse) => {
          this.phase1Error = 'Credenciales incorrectas';
          this.loading = false;
          return of(null);
        }),
      )
      .subscribe((response) => {
        if (!response) {
          return;
        }

        this.tempToken = response.temp_token;
        this.organizations = response.organizations;

        if (response.organizations.length === 1) {
          this.doPhase2(response.organizations[0].id);
        } else if (response.organizations.length > 1) {
          this.showOrgSelector = true;
          this.loading = false;
        } else {
          this.phase1Error =
            'No se encontraron organizaciones asociadas a esta cuenta.';
          this.loading = false;
        }
      });
  }

  onOrgSelected(orgId: string): void {
    if (!orgId) {
      return;
    }
    this.doPhase2(orgId);
  }

  private doPhase2(orgId: string): void {
    this.loading = true;
    this.phase2Error = null;

    this.http
      .post<Phase2Response>('/api/v1/auth/token', {
        temp_token: this.tempToken,
        org_id: orgId,
      })
      .pipe(
        catchError((_err: HttpErrorResponse) => {
          this.phase2Error = 'No se pudo seleccionar la organización';
          this.loading = false;
          this.orgControl.reset();
          return of(null);
        }),
      )
      .subscribe((response) => {
        if (!response) {
          return;
        }

        setAccessToken(response.access_token);
        this.router.navigate(['/app/dashboard']);
      });
  }
}
