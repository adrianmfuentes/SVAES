import { Component, inject, signal } from '@angular/core';
import {
  FormBuilder,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { RouterModule } from '@angular/router';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { catchError, of } from 'rxjs';
import { TranslationService } from '../../core/i18n/translation.service';
import { TranslatePipe } from '../../core/i18n/translate.pipe';

interface AccessRequestResponse {
  id: string;
  status: string;
}

function generateSlug(name: string): string {
  return name
    .toLowerCase()
    .trim()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9-]/g, '')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');
}

@Component({
  selector: 'app-access-request-form',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule, TranslatePipe],
  template: `
    <div class="request-page">
      <a routerLink="/" class="request-back">
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true" focusable="false">
          <path d="M7.5 2.5L4 6l3.5 3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        {{ 'login.back_home' | t }}
      </a>

      <main class="request-main">
        <div class="request-card">

          <ng-container *ngIf="submitted(); else formBlock">
            <div class="success-state step-block">
              <div class="success-icon" aria-hidden="true">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true" focusable="false">
                  <circle cx="12" cy="12" r="10" stroke="var(--verdict-valid)" stroke-width="1.5"/>
                  <path d="M8 12l3 3 5-5" stroke="var(--verdict-valid)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </div>
              <h2 class="card-title">{{ 'access_request.success_title' | t }}</h2>
              <p class="card-desc">{{ 'access_request.success_desc' | t }}</p>
              <a routerLink="/" class="btn-secondary success-back">{{ 'login.back_home' | t }}</a>
            </div>
          </ng-container>

          <ng-template #formBlock>

            <div class="stepper" role="list">
              <div class="stepper-item" role="listitem"
                   [class.done]="currentStep() > 1" [class.active]="currentStep() === 1"
                   [attr.aria-current]="currentStep() === 1 ? 'step' : null">
                <div class="stepper-dot" aria-hidden="true">
                  <svg *ngIf="currentStep() > 1" width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true" focusable="false">
                    <path d="M2 5l2.5 2.5L8 2.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                  <span *ngIf="currentStep() <= 1" aria-hidden="true">1</span>
                </div>
                <span class="stepper-label">{{ 'access_request.step1' | t }}</span>
              </div>
              <div class="stepper-connector" [class.active]="currentStep() > 1" aria-hidden="true"></div>
              <div class="stepper-item" role="listitem"
                   [class.done]="currentStep() > 2" [class.active]="currentStep() === 2"
                   [attr.aria-current]="currentStep() === 2 ? 'step' : null">
                <div class="stepper-dot" aria-hidden="true">
                  <svg *ngIf="currentStep() > 2" width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true" focusable="false">
                    <path d="M2 5l2.5 2.5L8 2.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                  <span *ngIf="currentStep() <= 2" aria-hidden="true">2</span>
                </div>
                <span class="stepper-label">{{ 'access_request.step2' | t }}</span>
              </div>
              <div class="stepper-connector" [class.active]="currentStep() > 2" aria-hidden="true"></div>
              <div class="stepper-item" role="listitem"
                   [class.active]="currentStep() === 3"
                   [attr.aria-current]="currentStep() === 3 ? 'step' : null">
                <div class="stepper-dot" aria-hidden="true"><span aria-hidden="true">3</span></div>
                <span class="stepper-label">{{ 'access_request.step3' | t }}</span>
              </div>
            </div>

            <form [formGroup]="requestForm" (ngSubmit)="handleFormSubmit()" novalidate>

              <div class="step-block" *ngIf="currentStep() === 1">
                <h2 class="card-title">{{ 'access_request.step1' | t }}</h2>

                <div class="form-group">
                  <label for="requester-name">{{ 'access_request.first_name' | t }}<span class="required-star" aria-hidden="true">*</span></label>
                  <input
                    id="requester-name"
                    type="text"
                    formControlName="requester_name"
                    autocomplete="name"
                    aria-required="true"
                    placeholder="Jane Smith"
                    [class.input-error]="fieldHasError('requester_name')"
                  />
                  <div class="field-error" *ngIf="requestForm.get('requester_name')?.hasError('required') && requestForm.get('requester_name')?.touched">
                    {{ 'access_request.first_name_required' | t }}
                  </div>
                </div>

                <div class="form-group">
                  <label for="requester-email">{{ 'access_request.email' | t }}<span class="required-star" aria-hidden="true">*</span></label>
                  <input
                    id="requester-email"
                    type="email"
                    formControlName="requester_email"
                    autocomplete="email"
                    aria-required="true"
                    [placeholder]="'login.email_placeholder' | t"
                    [class.input-error]="fieldHasError('requester_email')"
                  />
                  <div class="field-error" *ngIf="requestForm.get('requester_email')?.hasError('required') && requestForm.get('requester_email')?.touched">
                    {{ 'access_request.email_required' | t }}
                  </div>
                  <div class="field-error" *ngIf="requestForm.get('requester_email')?.hasError('email') && requestForm.get('requester_email')?.touched">
                    {{ 'access_request.email_invalid' | t }}
                  </div>
                </div>

                <div class="step-nav step-nav-end">
                  <button type="submit" class="btn-primary">{{ 'access_request.next' | t }}</button>
                </div>
              </div>

              <div class="step-block" *ngIf="currentStep() === 2">
                <h2 class="card-title">{{ 'access_request.step2' | t }}</h2>

                <div class="form-group">
                  <label for="org-name">{{ 'access_request.org_name' | t }}<span class="required-star" aria-hidden="true">*</span></label>
                  <input
                    id="org-name"
                    type="text"
                    formControlName="organization_name"
                    placeholder="Acme Corp"
                    aria-required="true"
                    (input)="updateSlug()"
                    [class.input-error]="fieldHasError('organization_name')"
                  />
                  <div class="slug-preview" *ngIf="slugPreview()">
                    <span class="slug-label">Slug</span>
                    <code class="slug-value">{{ slugPreview() }}</code>
                  </div>
                  <div class="field-error" *ngIf="requestForm.get('organization_name')?.hasError('required') && requestForm.get('organization_name')?.touched">
                    {{ 'access_request.org_name_required' | t }}
                  </div>
                </div>

                <div class="form-group">
                  <label for="org-description">
                    {{ 'common.description' | t }}
                    <span class="optional-tag">{{ 'common.optional' | t }}</span>
                  </label>
                  <textarea
                    id="org-description"
                    formControlName="organization_description"
                    [placeholder]="'access_request.step2' | t"
                    rows="3"
                    (input)="updateCharCount()"
                  ></textarea>
                  <div class="char-counter" [class.char-counter-over]="charCount() > 500">
                    {{ charCount() }}/500
                  </div>
                </div>

                <div class="step-nav">
                  <button type="button" class="btn-secondary" (click)="prevStep()">{{ 'access_request.back' | t }}</button>
                  <button type="submit" class="btn-primary">{{ 'access_request.next' | t }}</button>
                </div>
              </div>

              <div class="step-block" *ngIf="currentStep() === 3">
                <h2 class="card-title">{{ 'access_request.review_title' | t }}</h2>

                <div class="alert-error" *ngIf="errorMessage()" role="alert">
                  <svg class="alert-icon" width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true" focusable="false">
                    <circle cx="7" cy="7" r="6" stroke="currentColor" stroke-width="1.2"/>
                    <path d="M7 4v3.5M7 10v.5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
                  </svg>
                  <span>{{ errorMessage() }}</span>
                </div>

                <div class="review-block">
                  <div class="review-row">
                    <span class="review-key">{{ 'access_request.review_name' | t }}</span>
                    <span class="review-val">{{ requestForm.get('requester_name')?.value }}</span>
                  </div>
                  <div class="review-row">
                    <span class="review-key">{{ 'access_request.review_email' | t }}</span>
                    <span class="review-val">{{ requestForm.get('requester_email')?.value }}</span>
                  </div>
                  <div class="review-row">
                    <span class="review-key">{{ 'access_request.review_org' | t }}</span>
                    <span class="review-val">{{ requestForm.get('organization_name')?.value }}</span>
                  </div>
                  <div class="review-row" *ngIf="requestForm.get('organization_description')?.value">
                    <span class="review-key">{{ 'common.description' | t }}</span>
                    <span class="review-val review-val-desc">{{ requestForm.get('organization_description')?.value }}</span>
                  </div>
                </div>

                <div class="step-nav">
                  <button type="button" class="btn-secondary" (click)="prevStep()" [disabled]="loading()" [title]="loading() ? ('common.disabled_tooltip.operation_in_progress' | t) : ''">{{ 'access_request.back' | t }}</button>
                  <button
                    type="submit"
                    class="btn-primary btn-submit"
                    [disabled]="loading()"
                    [title]="loading() ? ('common.disabled_tooltip.operation_in_progress' | t) : ''"
                    [class.btn-loading]="loading()"
                  >
                    <span *ngIf="!loading()">{{ 'access_request.submit' | t }}</span>
                    <span *ngIf="loading()">{{ 'access_request.submitting' | t }}</span>
                  </button>
                </div>
              </div>

            </form>
          </ng-template>

        </div>
      </main>

      <footer class="request-footer">
        <span>&copy; 2026 SVAES</span>
        <nav class="footer-links">
          <a routerLink="/legal/privacidad">{{ 'login.footer_privacy' | t }}</a>
          <span aria-hidden="true">&middot;</span>
          <a routerLink="/legal/aviso-legal">{{ 'login.footer_legal' | t }}</a>
        </nav>
      </footer>
    </div>
  `,
  styles: [
    `
      @keyframes stepIn {
        from { opacity: 0; transform: translateX(0.75rem); }
        to   { opacity: 1; transform: translateX(0); }
      }

      :host {
        display: block;
      }

      .request-page {
        height: 100vh;
        display: flex;
        flex-direction: column;
        background: var(--paper);
        overflow: hidden;
      }

      .request-back {
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

      .request-back:hover {
        color: var(--ink);
      }

      .request-back svg {
        flex-shrink: 0;
      }

      .request-main {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0 var(--spacing-xl);
        min-height: 0;
      }

      .request-card {
        background: var(--surface-raised);
        border: 0.0625rem solid var(--border);
        border-radius: var(--rounded-lg);
        padding: var(--spacing-xl);
        width: 100%;
        max-width: 27.5rem;
      }

      /* -- Stepper ---------------------------------------------------- */

      .stepper {
        display: flex;
        align-items: flex-start;
        margin-bottom: var(--spacing-lg);
      }

      .stepper-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.375rem;
      }

      .stepper-dot {
        width: 1.75rem;
        height: 1.75rem;
        border-radius: 50%;
        border: 0.0938rem solid var(--border);
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: var(--font-mono);
        font-size: 0.6875rem;
        color: var(--muted);
        transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease;
      }

      .stepper-item.active .stepper-dot,
      .stepper-item.done .stepper-dot {
        background: var(--ink);
        border-color: var(--ink);
        color: var(--paper);
      }

      .stepper-label {
        font-family: var(--font-sans);
        font-size: 0.625rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--muted);
        white-space: nowrap;
        transition: color 0.2s ease;
      }

      .stepper-item.active .stepper-label,
      .stepper-item.done .stepper-label {
        color: var(--ink);
      }

      .stepper-connector {
        flex: 1;
        height: 0.0625rem;
        background: var(--border);
        margin-top: 0.875rem;
        transition: background 0.2s ease;
      }

      .stepper-connector.active {
        background: var(--ink);
      }

      /* -- Step block ------------------------------------------------─ */

      .step-block {
        animation: stepIn 0.22s ease both;
      }

      .card-title {
        font-family: var(--font-display);
        font-size: 1.5rem;
        font-weight: 400;
        line-height: 1.2;
        letter-spacing: -0.01em;
        color: var(--ink);
        margin: 0 0 var(--spacing-xs);
      }

      .card-subtitle {
        font-family: var(--font-sans);
        font-size: 0.8125rem;
        color: var(--muted);
        line-height: 1.5;
        margin: 0 0 var(--spacing-md);
      }

      .card-desc {
        font-family: var(--font-sans);
        font-size: 0.9375rem;
        color: var(--muted);
        line-height: 1.65;
        margin: 0 0 var(--spacing-md);
      }

      /* -- Form groups ------------------------------------------------ */

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

      .optional-tag {
        font-size: 0.6875rem;
        font-weight: 400;
        letter-spacing: 0;
        text-transform: none;
        color: var(--muted);
        opacity: 0.8;
        margin-left: 0.25rem;
      }

      .required-star {
        color: var(--verdict-invalid);
        margin-left: 0.25rem;
        font-size: 0.75rem;
      }

      .form-group input,
      .form-group textarea {
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
        box-sizing: border-box;
        transition: border-color 0.15s ease, background-color 0.15s ease, box-shadow 0.15s ease;
      }

      .form-group textarea {
        resize: none;
        min-height: 4.5rem;
      }

      .form-group input:focus,
      .form-group textarea:focus {
        border-color: var(--ink);
        background: var(--surface-raised);
        box-shadow: 0 0 0 0.1875rem rgba(232, 213, 163, 0.4);
      }

      .form-group input.input-error,
      .form-group textarea.input-error {
        border-color: var(--verdict-invalid-border);
        background: var(--verdict-invalid-bg);
      }

      .form-group input::placeholder,
      .form-group textarea::placeholder {
        color: var(--muted);
        opacity: 0.6;
      }

      .field-error {
        font-family: var(--font-sans);
        font-size: 0.75rem;
        color: var(--verdict-invalid);
        margin-top: var(--spacing-xs);
      }

      .slug-preview {
        display: flex;
        align-items: center;
        gap: var(--spacing-xs);
        margin-top: var(--spacing-xs);
      }

      .slug-label {
        font-family: var(--font-sans);
        font-size: 0.6875rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--muted);
      }

      .slug-value {
        font-family: var(--font-mono);
        font-size: 0.6875rem;
        color: var(--muted);
      }

      .char-counter {
        font-family: var(--font-mono);
        font-size: 0.6875rem;
        color: var(--muted);
        text-align: right;
        margin-top: var(--spacing-xs);
      }

      .char-counter-over {
        color: var(--verdict-invalid);
      }

      /* -- Step navigation -------------------------------------------- */

      .step-nav {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-top: var(--spacing-md);
        gap: var(--spacing-sm);
      }

      .step-nav-end {
        justify-content: flex-end;
      }

      /* -- Review block ----------------------------------------------─ */

      .review-block {
        background: var(--paper);
        border: 0.0625rem solid var(--border);
        border-radius: var(--rounded-md);
        overflow: hidden;
        margin-bottom: var(--spacing-sm);
      }

      .review-row {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: var(--spacing-md);
        padding: 0.625rem var(--spacing-md);
        border-bottom: 0.0625rem solid var(--border);
      }

      .review-row:last-child {
        border-bottom: none;
      }

      .review-key {
        font-family: var(--font-sans);
        font-size: 0.6875rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--muted);
        flex-shrink: 0;
      }

      .review-val {
        font-family: var(--font-sans);
        font-size: 0.8125rem;
        color: var(--ink);
        text-align: right;
        word-break: break-word;
      }

      .review-val-desc {
        font-size: 0.75rem;
        line-height: 1.5;
        color: var(--muted);
      }

      /* -- Alert ------------------------------------------------------ */

      .alert-error {
        display: flex;
        align-items: flex-start;
        gap: var(--spacing-sm);
        background: var(--verdict-invalid-bg);
        color: var(--verdict-invalid);
        border: 0.0625rem solid var(--verdict-invalid-border);
        border-radius: var(--rounded-md);
        padding: var(--spacing-sm) var(--spacing-md);
        font-family: var(--font-sans);
        font-size: 0.8125rem;
        line-height: 1.5;
        margin-bottom: var(--spacing-md);
      }

      .alert-icon {
        flex-shrink: 0;
        margin-top: 0.125rem;
      }

      /* -- Submit button ---------------------------------------------- */

      .btn-submit.btn-loading {
        opacity: 0.7;
        cursor: wait;
      }

      /* -- Success state ---------------------------------------------- */

      .success-state {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
      }

      .success-icon {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 3rem;
        height: 3rem;
        border-radius: var(--rounded-full);
        background: var(--verdict-valid-bg);
        margin-bottom: var(--spacing-md);
      }

      .success-back {
        margin-top: var(--spacing-sm);
      }

      /* -- Footer ----------------------------------------------------─ */

      .request-footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: var(--spacing-md) var(--spacing-lg);
        border-top: 0.0625rem solid var(--border);
        background: var(--paper);
        font-size: 0.75rem;
        color: var(--muted);
        flex-shrink: 0;
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

      /* -- Responsive ------------------------------------------------─ */

      @media (max-width: 40rem) {
        .request-page {
          height: auto;
          min-height: 100vh;
          overflow: auto;
        }

        .request-main {
          padding: var(--spacing-xxl) var(--spacing-md) var(--spacing-md);
          align-items: flex-start;
        }

        .step-nav {
          flex-direction: column-reverse;
          align-items: stretch;
        }

        .step-nav-end {
          flex-direction: column;
        }

        .step-nav button,
        .step-nav a {
          width: 100%;
          justify-content: center;
        }
      }

      @media (max-width: 30rem) {
        .request-card {
          padding: var(--spacing-lg);
        }

        .request-back {
          top: var(--spacing-md);
          left: var(--spacing-md);
        }
      }

      @media (max-height: 40rem) {
        .request-card {
          padding: var(--spacing-lg);
        }

        .form-group {
          margin-bottom: var(--spacing-sm);
        }

        .stepper {
          margin-bottom: var(--spacing-md);
        }
      }
    `,
  ],
})
export class AccessRequestFormComponent {
  private readonly fb = inject(FormBuilder);
  private readonly http = inject(HttpClient);
  private readonly ts = inject(TranslationService);

  readonly requestForm = this.fb.group({
    requester_name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(80)]],
    requester_email: ['', [Validators.required, Validators.email]],
    organization_name: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(80)]],
    organization_description: ['', [Validators.maxLength(500)]],
  });

  readonly loading = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly submitted = signal(false);
  readonly slugPreview = signal('');
  readonly charCount = signal(0);
  readonly currentStep = signal(1);

  get step1Valid(): boolean {
    return (this.requestForm.get('requester_name')?.valid ?? false) &&
           (this.requestForm.get('requester_email')?.valid ?? false);
  }

  get step2Valid(): boolean {
    return (this.requestForm.get('organization_name')?.valid ?? false) &&
           (this.requestForm.get('organization_description')?.valid ?? false);
  }

  fieldHasError(name: string): boolean {
    const ctrl = this.requestForm.get(name);
    return !!(ctrl?.invalid && ctrl?.touched);
  }

  updateSlug(): void {
    const name = this.requestForm.get('organization_name')?.value ?? '';
    this.slugPreview.set(generateSlug(name));
  }

  updateCharCount(): void {
    const desc = this.requestForm.get('organization_description')?.value ?? '';
    this.charCount.set(desc.length);
  }

  prevStep(): void {
    if (this.currentStep() > 1) {
      this.currentStep.update(s => s - 1);
    }
  }

  handleFormSubmit(): void {
    if (this.currentStep() === 1) {
      this.requestForm.get('requester_name')?.markAsTouched();
      this.requestForm.get('requester_email')?.markAsTouched();
      if (this.step1Valid) {
        this.currentStep.set(2);
      }
    } else if (this.currentStep() === 2) {
      this.requestForm.get('organization_name')?.markAsTouched();
      this.requestForm.get('organization_description')?.markAsTouched();
      if (this.step2Valid) {
        this.currentStep.set(3);
      }
    } else if (this.currentStep() === 3) {
      this.onSubmit();
    }
  }

  onSubmit(): void {
    if (this.requestForm.invalid || this.loading()) {
      this.requestForm.markAllAsTouched();
      return;
    }

    this.loading.set(true);
    this.errorMessage.set(null);

    const body = this.requestForm.value;

    this.http
      .post<AccessRequestResponse>('/api/v1/access-requests', body)
      .pipe(
        catchError((err: HttpErrorResponse) => {
          if (err.status === 409) {
            this.errorMessage.set(this.ts.translateInstant('access_request.error.conflict'));
          } else if (err.status === 0 || !err.status) {
            this.errorMessage.set(this.ts.translateInstant('login.error.no_connection'));
          } else {
            this.errorMessage.set(this.ts.translateInstant('access_request.error.submission'));
          }
          this.loading.set(false);
          return of(null);
        }),
      )
      .subscribe((response) => {
        if (response) {
          this.submitted.set(true);
        }
        this.loading.set(false);
      });
  }
}
