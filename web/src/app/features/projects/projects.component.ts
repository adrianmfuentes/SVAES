import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { AuthService } from '../../core/services/auth.service';
import { TranslationService } from '../../core/i18n/translation.service';
import { TranslatePipe } from '../../core/i18n/translate.pipe';
import { catchError, of } from 'rxjs';
import { Project, ProjectProfile, ProjectService } from './services/project.service';

@Component({
  selector: 'app-projects',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule, TranslatePipe],
  templateUrl: './projects.component.html',
  styleUrls: ['./projects.component.scss'],
})
export class ProjectsComponent implements OnInit {
  private readonly projectService = inject(ProjectService);
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
  editProfiles = signal<ProjectProfile[]>([]);
  editName = signal('');
  editDescription = signal('');
  editProfileId = signal('');
  editSubmitting = signal(false);
  editError = signal<string | null>(null);

  ngOnInit(): void {
    this.projectService.list(this.orgId)
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

    this.projectService.archive(this.orgId, project.id)
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
    this.projectService.unarchive(this.orgId, project.id)
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

    this.projectService.listProfiles(this.orgId)
      .pipe(catchError(() => of([] as ProjectProfile[])))
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

    this.projectService.update(project.id, body)
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
