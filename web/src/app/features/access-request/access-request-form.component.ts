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
  templateUrl: './access-request-form.component.html',
  styleUrl: './access-request-form.component.scss',
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
