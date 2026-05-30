import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { catchError, of } from 'rxjs';

interface UserProfile {
  id: string;
  email: string;
  display_name: string;
  role: string;
}

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  template: `
    <div class="profile-page">
      <div class="page-header">
        <h1 class="page-title">Mi perfil</h1>
      </div>

      <div *ngIf="loading()" class="skeleton-list">
        <div class="skeleton sk-row"></div>
        <div class="skeleton sk-row" style="width:60%"></div>
      </div>

      <div *ngIf="!loading()" class="profile-grid">

        <!-- Profile info card -->
        <div class="card">
          <h2 class="card-title">Informaci&oacute;n del perfil</h2>

          <div class="field-readonly">
            <div class="field-label">Correo electr&oacute;nico</div>
            <div class="field-value">{{ profile()?.email }}</div>
            <div class="field-hint">El email no se puede modificar.</div>
          </div>

          <div class="field-readonly">
            <div class="field-label">Rol</div>
            <div class="field-value">{{ roleLabel(profile()?.role ?? '') }}</div>
          </div>

          <form [formGroup]="nameForm" (ngSubmit)="saveName()">
            <div class="form-group">
              <label for="display-name">Nombre de visualizaci&oacute;n</label>
              <input
                id="display-name"
                type="text"
                formControlName="display_name"
                placeholder="Tu nombre"
              />
              <div class="field-error" *ngIf="nameForm.get('display_name')?.hasError('required') && nameForm.get('display_name')?.touched">
                El nombre es obligatorio.
              </div>
            </div>

            <div *ngIf="nameSaveError()" class="alert-error">{{ nameSaveError() }}</div>

            <div class="form-footer">
              <span class="save-confirm" *ngIf="nameSaved()">Nombre actualizado</span>
              <button type="submit" class="btn-primary" [disabled]="nameForm.invalid || nameSaving()">
                {{ nameSaving() ? 'Guardando…' : 'Guardar nombre' }}
              </button>
            </div>
          </form>
        </div>

        <!-- Password card -->
        <div class="card">
          <h2 class="card-title">Cambiar contrase&ntilde;a</h2>

          <form [formGroup]="pwForm" (ngSubmit)="savePassword()">
            <div class="form-group">
              <label for="current-pw">Contrase&ntilde;a actual</label>
              <input
                id="current-pw"
                type="password"
                formControlName="current_password"
                autocomplete="current-password"
                placeholder="Tu contrase&ntilde;a actual"
              />
            </div>

            <div class="form-group">
              <label for="new-pw">Nueva contrase&ntilde;a</label>
              <input
                id="new-pw"
                type="password"
                formControlName="new_password"
                autocomplete="new-password"
                placeholder="M&iacute;nimo 8 caracteres"
              />
              <div class="field-error" *ngIf="pwForm.get('new_password')?.hasError('minlength') && pwForm.get('new_password')?.touched">
                M&iacute;nimo 8 caracteres.
              </div>
            </div>

            <div class="form-group">
              <label for="confirm-pw">Confirmar nueva contrase&ntilde;a</label>
              <input
                id="confirm-pw"
                type="password"
                formControlName="confirm_password"
                autocomplete="new-password"
                placeholder="Repite la nueva contrase&ntilde;a"
              />
              <div class="field-error" *ngIf="pwForm.errors?.['mismatch'] && pwForm.get('confirm_password')?.touched">
                Las contrase&ntilde;as no coinciden.
              </div>
            </div>

            <div *ngIf="pwSaveError()" class="alert-error">{{ pwSaveError() }}</div>

            <div class="form-footer">
              <span class="save-confirm" *ngIf="pwSaved()">Contrase&ntilde;a actualizada</span>
              <button type="submit" class="btn-primary" [disabled]="pwForm.invalid || pwSaving()">
                {{ pwSaving() ? 'Guardando…' : 'Cambiar contrase&ntilde;a' }}
              </button>
            </div>
          </form>
        </div>

      </div>
    </div>
  `,
  styles: [`
    :host { display: block; }
    .profile-page { padding: 0; }

    .page-header {
      margin-bottom: var(--spacing-lg);
    }

    .page-title {
      font-family: var(--font-display);
      font-size: 2.25rem;
      font-weight: 400;
      line-height: 1.1;
      letter-spacing: -0.02em;
      margin: 0;
      color: var(--ink);
    }

    .profile-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: var(--spacing-lg);
      align-items: start;
    }

    .card {
      background: var(--surface-raised);
      border: 1px solid var(--border);
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

    .field-readonly {
      margin-bottom: var(--spacing-md);
      padding-bottom: var(--spacing-md);
      border-bottom: 1px solid var(--border);
    }

    .field-label {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 4px;
    }

    .field-value {
      font-size: 0.9375rem;
      color: var(--ink);
    }

    .field-hint {
      font-size: 0.75rem;
      color: var(--muted);
      margin-top: 2px;
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
      outline: none;
      transition: border-color 0.15s ease, background-color 0.15s ease, box-shadow 0.15s ease;
      box-sizing: border-box;
    }

    .form-group input:focus {
      border-color: var(--ink);
      background: var(--surface-raised);
      box-shadow: 0 0 0 3px rgba(232, 213, 163, 0.4);
    }

    .field-error {
      font-size: 0.75rem;
      color: var(--verdict-invalid);
      margin-top: var(--spacing-xs);
    }

    .alert-error {
      background: var(--verdict-invalid-bg);
      color: var(--verdict-invalid);
      border: 1px solid var(--verdict-invalid-border);
      border-radius: var(--rounded-md);
      padding: var(--spacing-sm) var(--spacing-md);
      font-size: 0.8125rem;
      margin-bottom: var(--spacing-md);
    }

    .form-footer {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: var(--spacing-md);
      padding-top: var(--spacing-md);
      border-top: 1px solid var(--border);
      margin-top: var(--spacing-md);
    }

    .save-confirm {
      font-size: 0.8125rem;
      color: var(--verdict-valid);
    }

    .skeleton-list {
      display: flex;
      flex-direction: column;
      gap: var(--spacing-sm);
    }

    .skeleton {
      border-radius: var(--rounded-md);
      background: linear-gradient(90deg, var(--paper-secondary) 25%, #e5e2db 50%, var(--paper-secondary) 75%);
      background-size: 200% 100%;
      animation: shimmer 1.6s linear infinite;
    }

    .sk-row { height: 120px; }

    @keyframes shimmer {
      0% { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }
  `],
})
export class ProfileComponent implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly fb = inject(FormBuilder);

  profile = signal<UserProfile | null>(null);
  loading = signal(true);

  nameSaving = signal(false);
  nameSaved = signal(false);
  nameSaveError = signal<string | null>(null);

  pwSaving = signal(false);
  pwSaved = signal(false);
  pwSaveError = signal<string | null>(null);

  nameForm = this.fb.group({
    display_name: ['', [Validators.required, Validators.minLength(1), Validators.maxLength(100)]],
  });

  pwForm = this.fb.group(
    {
      current_password: ['', [Validators.required]],
      new_password: ['', [Validators.required, Validators.minLength(8), Validators.maxLength(255)]],
      confirm_password: ['', [Validators.required]],
    },
    { validators: this.passwordsMatch }
  );

  ngOnInit(): void {
    this.http.get<UserProfile>('/api/v1/users/me')
      .pipe(catchError(() => of(null)))
      .subscribe(user => {
        this.profile.set(user);
        if (user) {
          this.nameForm.patchValue({ display_name: user.display_name });
        }
        this.loading.set(false);
      });
  }

  saveName(): void {
    if (this.nameForm.invalid) { this.nameForm.markAllAsTouched(); return; }
    this.nameSaving.set(true);
    this.nameSaved.set(false);
    this.nameSaveError.set(null);
    this.http.patch<UserProfile>('/api/v1/users/me', this.nameForm.value)
      .pipe(catchError((err: HttpErrorResponse) => {
        this.nameSaveError.set(err.error?.detail ?? 'Error al guardar el nombre');
        this.nameSaving.set(false);
        return of(null);
      }))
      .subscribe(user => {
        if (user) {
          this.profile.update(p => p ? { ...p, display_name: user.display_name } : p);
          this.nameSaved.set(true);
          setTimeout(() => this.nameSaved.set(false), 3000);
        }
        this.nameSaving.set(false);
      });
  }

  savePassword(): void {
    if (this.pwForm.invalid) { this.pwForm.markAllAsTouched(); return; }
    this.pwSaving.set(true);
    this.pwSaved.set(false);
    this.pwSaveError.set(null);
    const { current_password, new_password, confirm_password } = this.pwForm.value;
    this.http.post('/api/v1/users/me/password', { current_password, new_password, confirm_password })
      .pipe(catchError((err: HttpErrorResponse) => {
        this.pwSaveError.set(err.error?.detail ?? 'Error al cambiar la contraseña');
        this.pwSaving.set(false);
        return of(null);
      }))
      .subscribe(res => {
        if (res !== null) {
          this.pwSaved.set(true);
          this.pwForm.reset();
          setTimeout(() => this.pwSaved.set(false), 3000);
        }
        this.pwSaving.set(false);
      });
  }

  private passwordsMatch(group: import('@angular/forms').AbstractControl) {
    const pw = group.get('new_password')?.value;
    const confirm = group.get('confirm_password')?.value;
    return pw && confirm && pw !== confirm ? { mismatch: true } : null;
  }

  roleLabel(role: string): string {
    const map: Record<string, string> = {
      ADMIN: 'Administrador global',
      MANAGER: 'Manager',
      OPERATOR: 'Operator',
      VIEWER: 'Viewer',
    };
    return map[role] ?? role;
  }
}
