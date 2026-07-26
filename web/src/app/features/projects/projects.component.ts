import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { AuthService } from '../../core/services/auth.service';
import { TranslationService } from '../../core/i18n/translation.service';
import { TranslatePipe } from '../../core/i18n/translate.pipe';
import { catchError, of } from 'rxjs';

interface Project {
  id: string;
  name: string;
  description: string;
  profile_id: string | null;
  is_archived: boolean;
  created_at: string | null;
}

interface Profile {
  id: string;
  name: string;
  is_system?: boolean;
}

@Component({
  selector: 'app-projects',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule, TranslatePipe],
  templateUrl: './projects.component.html',
  styleUrls: ['./projects.component.scss'],
})
export class ProjectsComponent implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly authService = inject(AuthService);
  private readonly ts = inject(TranslationService);

  readonly isManager = this.authService.getUserRole() === 'MANAGER';
  readonly orgId = this.authService.getUser()?.organization_id ?? '';

  projects = signal<Project[]>([]);
  loading = signal(true);
  error = signal<string | null>(null);
  projectToArchive = signal<Project | null>(null);
  archiving = signal(false);

  editingProject = signal<Project | null>(null);
  editProfiles = signal<Profile[]>([]);
  editName = signal('');
  editDescription = signal('');
  editProfileId = signal('');
  editSubmitting = signal(false);
  editError = signal<string | null>(null);

  ngOnInit(): void {
    this.http.get<Project[]>(`/api/v1/organizations/${this.orgId}/projects`)
      .pipe(catchError(() => {
        this.error.set(this.ts.translateInstant('projects.load_error'));
        return of([] as Project[]);
      }))
      .subscribe(data => {
        this.projects.set(data);
        this.loading.set(false);
      });
  }

  confirmArchive(project: Project): void {
    this.projectToArchive.set(project);
  }

  cancelArchive(): void {
    this.projectToArchive.set(null);
  }

  archive(): void {
    const project = this.projectToArchive();
    if (!project) return;
    this.archiving.set(true);

    this.http.post(`/api/v1/organizations/${this.orgId}/projects/${project.id}/archive`, {})
      .pipe(catchError(() => {
        this.archiving.set(false);
        return of(null);
      }))
      .subscribe(() => {
        this.archiving.set(false);
        this.projects.update(projects => projects.map(p =>
          p.id === project.id ? { ...p, is_archived: true } : p
        ));
        this.projectToArchive.set(null);
      });
  }

  unarchive(project: Project): void {
    this.http.post(`/api/v1/organizations/${this.orgId}/projects/${project.id}/unarchive`, {})
      .pipe(catchError(() => of(null)))
      .subscribe(res => {
        if (res === null) return;
        this.projects.update(projects => projects.map(p =>
          p.id === project.id ? { ...p, is_archived: false } : p
        ));
      });
  }

  openEdit(project: Project): void {
    this.editingProject.set(project);
    this.editName.set(project.name);
    this.editDescription.set(project.description ?? '');
    this.editProfileId.set(project.profile_id ?? '');
    this.editError.set(null);

    this.http.get<Profile[]>(`/api/v1/organizations/${this.orgId}/profiles`)
      .pipe(catchError(() => of([] as Profile[])))
      .subscribe(data => this.editProfiles.set(data));
  }

  cancelEdit(): void {
    this.editingProject.set(null);
  }

  saveEdit(): void {
    const project = this.editingProject();
    if (!project || !this.editName().trim()) return;

    this.editSubmitting.set(true);
    this.editError.set(null);

    const body = {
      name: this.editName().trim(),
      description: this.editDescription(),
      profile_id: this.editProfileId() || null,
    };

    this.http.patch<Project>(`/api/v1/projects/${project.id}`, body)
      .pipe(catchError((err: HttpErrorResponse) => {
        this.editError.set(err.error?.detail ?? this.ts.translateInstant('projects.edit_error'));
        this.editSubmitting.set(false);
        return of(null);
      }))
      .subscribe(updated => {
        this.editSubmitting.set(false);
        if (!updated) return;
        this.projects.update(projects => projects.map(p =>
          p.id === project.id ? { ...p, name: updated.name, description: updated.description, profile_id: updated.profile_id } : p
        ));
        this.editingProject.set(null);
      });
  }
}
