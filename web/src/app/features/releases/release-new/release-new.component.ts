import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterModule, ActivatedRoute } from '@angular/router';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { catchError, of } from 'rxjs';
import { AuthService } from '../../../core/services/auth.service';
import { TranslationService } from '../../../core/i18n/translation.service';
import { TranslatePipe } from '../../../core/i18n/translate.pipe';

interface Project {
  id: string;
  name: string;
}

@Component({
  selector: 'app-release-new',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule, TranslatePipe],
  templateUrl: './release-new.component.html',
  styleUrls: ['./release-new.component.scss'],
})
export class ReleaseNewComponent implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly fb = inject(FormBuilder);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly authService = inject(AuthService);
  private readonly ts = inject(TranslationService);

  readonly isManager = this.authService.getUserRole() === 'MANAGER';
  readonly isEditMode = signal(false);
  readonly loading = signal(true);
  readonly submitting = signal(false);
  readonly submitError = signal<string | null>(null);

  projects = signal<Project[]>([]);
  releaseId: string | null = null;

  form = this.fb.group({
    project_id: ['', [Validators.required]],
    name: ['', [Validators.required, Validators.maxLength(100)]],
    version: ['', [Validators.required]],
    description: ['', [Validators.maxLength(1000)]],
  });

  ngOnInit(): void {
    this.releaseId = this.route.snapshot.paramMap.get('id');

    if (this.releaseId) {
      this.isEditMode.set(true);
      this.loadRelease();
    } else {
      this.loadProjects();
    }
  }

  private loadRelease(): void {
    this.http.get<{ id: string; name: string; version: string; description: string; project_id?: string }>(
      `/api/v1/releases/${this.releaseId}`
    ).pipe(
      catchError(() => {
        this.router.navigate(['/app/releases']);
        return of(null);
      })
    ).subscribe(data => {
      if (data) {
        this.form.patchValue({
          name: data.name ?? '',
          version: data.version ?? '',
          description: data.description ?? '',
        });
        this.form.get('project_id')?.clearValidators();
        this.form.get('project_id')?.updateValueAndValidity();
      }
      this.loading.set(false);
    });
  }

  private loadProjects(): void {
    this.http.get<Project[]>('/api/v1/projects')
      .pipe(catchError(() => of([] as Project[])))
      .subscribe(data => {
        this.projects.set(data);
        this.loading.set(false);
      });
  }

  submit(): void {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.submitting.set(true);
    this.submitError.set(null);

    const { name, version, description } = this.form.value;
    const body: Record<string, unknown> = { name, version, description: description || '' };

    if (this.isEditMode() && this.releaseId) {
      this.http.patch<{ id: string }>(
        `/api/v1/releases/${this.releaseId}`, body
      ).pipe(
        catchError((err: HttpErrorResponse) => {
          this.submitError.set(err.error?.detail ?? this.ts.translateInstant('release_new.edit_error'));
          this.submitting.set(false);
          return of(null);
        })
      ).subscribe(res => {
        if (res) {
          this.router.navigate(['/app/releases', this.releaseId]);
        }
      });
    } else {
      const { project_id } = this.form.value;
      this.http.post<{ id: string; status: string }>(
        `/api/v1/projects/${project_id}/releases`, body
      ).pipe(
        catchError((err: HttpErrorResponse) => {
          this.submitError.set(err.error?.detail ?? this.ts.translateInstant('release_new.error'));
          this.submitting.set(false);
          return of(null);
        })
      ).subscribe(res => {
        if (res) {
          this.router.navigate(['/app/releases', res.id]);
        }
      });
    }
  }
}
