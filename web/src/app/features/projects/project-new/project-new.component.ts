import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { catchError, of } from 'rxjs';
import { AuthService } from '../../../core/services/auth.service';
import { TranslationService } from '../../../core/i18n/translation.service';
import { TranslatePipe } from '../../../core/i18n/translate.pipe';
import { ProjectProfile, ProjectService } from '../services/project.service';

@Component({
  selector: 'app-project-new',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule, TranslatePipe],
  templateUrl: './project-new.component.html',
  styleUrls: ['./project-new.component.scss'],
})
export class ProjectNewComponent implements OnInit {
  private readonly projectService = inject(ProjectService);
  private readonly fb = inject(FormBuilder);
  private readonly router = inject(Router);
  private readonly authService = inject(AuthService);
  private readonly ts = inject(TranslationService);

  profiles = signal<ProjectProfile[]>([]);
  profilesLoading = signal(true);
  submitting = signal(false);
  submitError = signal<string | null>(null);

  customProfiles = computed(() => this.profiles().filter(p => !p.is_system));

  form = this.fb.group({
    name: ['', [Validators.required, Validators.maxLength(100)]],
    description: ['', [Validators.maxLength(500)]],
    profile_id: ['', [Validators.required]],
  });

  ngOnInit(): void {
    const orgId = this.authService.getUser()?.organization_id;
    if (!orgId) {
      this.profilesLoading.set(false);
      return;
    }
    this.projectService.listProfiles(orgId)
      .pipe(catchError(() => of([] as ProjectProfile[])))
      .subscribe(data => {
        this.profiles.set(data);
        const systemProfile = data.find(p => p.is_system);
        const defaultCustom = data.find(p => !p.is_system && p.is_default);
        const autoSelect = defaultCustom ?? systemProfile;
        if (autoSelect) {
          this.form.patchValue({ profile_id: autoSelect.id });
        }
        this.profilesLoading.set(false);
      });
  }

  submit(): void {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    const orgId = this.authService.getUser()?.organization_id;
    if (!orgId) return;

    this.submitting.set(true);
    this.submitError.set(null);

    const { name, description, profile_id } = this.form.value;
    const body = { name, description: description || '', profile_id };

    this.projectService.create(orgId, body)
      .pipe(
        catchError((err: HttpErrorResponse) => {
          this.submitError.set(err.error?.detail ?? this.ts.translateInstant('project_new.error'));
          this.submitting.set(false);
          return of(null);
        })
      )
      .subscribe(res => {
        if (res) {
          this.router.navigate(['/app/projects']);
        }
      });
  }
}
