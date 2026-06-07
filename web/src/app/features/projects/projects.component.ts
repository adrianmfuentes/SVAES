import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { HttpClient } from '@angular/common/http';
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

@Component({
  selector: 'app-projects',
  standalone: true,
  imports: [CommonModule, RouterModule, TranslatePipe],
  template: `
    <div class="projects-page">
      <div class="page-header">
        <h1 class="page-title">{{ 'projects.title' | t }}</h1>
        <a *ngIf="isManager" routerLink="/app/projects/new" class="btn-primary">
          {{ 'projects.new_btn' | t }}
        </a>
      </div>

      <div *ngIf="loading()" class="skeleton-list">
        <div class="skeleton skeleton-row" *ngFor="let i of [1,2,3,4]"></div>
      </div>

      <div *ngIf="error() && !loading()" class="error-banner">{{ error() }}</div>

      <div *ngIf="!loading() && !error()">
        <div class="data-table-wrap" *ngIf="projects().length > 0; else emptyState">
          <table class="data-table">
            <thead>
              <tr>
                <th>{{ 'projects.col_name' | t }}</th>
                <th>{{ 'projects.col_description' | t }}</th>
                <th>{{ 'projects.col_status' | t }}</th>
                <th>{{ 'projects.col_created' | t }}</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let p of projects()">
                <td class="cell-primary">{{ p.name }}</td>
                <td class="cell-muted">{{ p.description || '—' }}</td>
                <td>
                  <span class="status-badge" [class.status-archived]="p.is_archived">
                    {{ (p.is_archived ? 'projects.status_archived' : 'projects.status_active') | t }}
                  </span>
                </td>
                <td class="cell-muted">{{ p.created_at | date:'dd MMM yyyy' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <ng-template #emptyState>
          <div class="empty-state">
            <p class="empty-text">{{ 'projects.empty_text' | t }}</p>
            <a *ngIf="isManager" routerLink="/app/projects/new" class="btn-primary">
              {{ 'projects.empty_cta' | t }}
            </a>
          </div>
        </ng-template>
      </div>
    </div>
  `,
  styles: [`
    :host { display: block; }
    .projects-page { padding: 0; }

    .page-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
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

    .btn-primary {
      display: inline-flex;
      align-items: center;
      background: var(--ink);
      color: var(--paper);
      border: 1px solid var(--ink);
      border-radius: var(--rounded-md);
      padding: 9px 18px;
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      cursor: pointer;
      text-decoration: none;
      transition: background-color 0.15s ease;
    }

    .btn-primary:hover { background: var(--ink-secondary); }

    .data-table-wrap {
      background: var(--surface-raised);
      border: 1px solid var(--border);
      border-radius: var(--rounded-lg);
      overflow: hidden;
    }

    .data-table {
      width: 100%;
      border-collapse: collapse;
    }

    .data-table th {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
      padding: var(--spacing-sm) var(--spacing-md);
      text-align: left;
      border-bottom: 1px solid var(--border);
      background: var(--paper-secondary);
    }

    .data-table td {
      font-size: 0.8125rem;
      color: var(--ink);
      padding: var(--spacing-sm) var(--spacing-md);
      border-bottom: 1px solid var(--border);
      vertical-align: middle;
      height: 44px;
    }

    .data-table tr:last-child td { border-bottom: none; }

    .cell-primary { font-weight: 500; }
    .cell-muted { color: var(--muted); }

    .status-badge {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      border-radius: var(--rounded-sm);
      padding: 2px 8px;
      background: var(--verdict-valid-bg);
      color: var(--verdict-valid);
      border: 1px solid var(--verdict-valid-border);
    }

    .status-badge.status-archived {
      background: var(--verdict-unevaluated-bg);
      color: var(--verdict-unevaluated);
      border-color: var(--verdict-unevaluated-border);
    }

    .error-banner {
      background: var(--verdict-invalid-bg);
      color: var(--verdict-invalid);
      border: 1px solid var(--verdict-invalid-border);
      border-radius: var(--rounded-md);
      padding: var(--spacing-sm) var(--spacing-md);
      font-size: 0.8125rem;
    }

    .skeleton-list { display: flex; flex-direction: column; gap: var(--spacing-sm); }

    .skeleton {
      border-radius: var(--rounded-md);
      background: linear-gradient(90deg, var(--paper-secondary) 25%, #e5e2db 50%, var(--paper-secondary) 75%);
      background-size: 200% 100%;
      animation: shimmer 1.6s linear infinite;
    }

    .skeleton-row { height: 44px; }

    @keyframes shimmer {
      0% { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: var(--spacing-md);
      padding: var(--spacing-xl) var(--spacing-lg);
      text-align: center;
    }

    .empty-text {
      font-size: 0.9375rem;
      color: var(--muted);
      margin: 0;
    }
  `],
})
export class ProjectsComponent implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly authService = inject(AuthService);
  private readonly ts = inject(TranslationService);

  readonly isManager = this.authService.getUserRole() === 'MANAGER';

  projects = signal<Project[]>([]);
  loading = signal(true);
  error = signal<string | null>(null);

  ngOnInit(): void {
    this.http.get<Project[]>('/api/v1/projects')
      .pipe(catchError(() => {
        this.error.set(this.ts.translateInstant('projects.load_error'));
        return of([] as Project[]);
      }))
      .subscribe(data => {
        this.projects.set(data);
        this.loading.set(false);
      });
  }
}
