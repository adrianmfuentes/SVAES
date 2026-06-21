import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { AuthService } from '../../core/services/auth.service';
import { TranslationService } from '../../core/i18n/translation.service';
import { TranslatePipe } from '../../core/i18n/translate.pipe';
import { catchError, of } from 'rxjs';

interface Release {
  id: string;
  name?: string;
  verdict: string;
  organization_id?: string;
  organization_name?: string;
  created_at: string;
  created_by?: string;
}

@Component({
  selector: 'app-releases',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, TranslatePipe],
  template: `
    <div class="releases-page">
      <div class="page-header">
        <div class="page-header-left">
          <h1 class="page-title">{{ 'releases.title' | t }}</h1>
          <span *ngIf="isAdmin" class="global-badge">{{ 'releases.global_view' | t }}</span>
        </div>
        <a *ngIf="!isAdmin && !isViewer" routerLink="/app/releases/new" class="btn-primary">{{ 'releases.new_release' | t }}</a>
      </div>

      <div class="filters-bar">
        <input
          type="text"
          class="filter-input"
          [placeholder]="'releases.filter_placeholder' | t"
          [(ngModel)]="filterText"
          (ngModelChange)="onFilterChange()"
        />
        <select class="filter-select" [(ngModel)]="filterVerdict" (ngModelChange)="onFilterChange()">
          <option value="">{{ 'releases.filter_all' | t }}</option>
          <option value="VALID">{{ 'releases.verdict_valid' | t }}</option>
          <option value="WITH_WARNINGS">{{ 'releases.verdict_with_warnings' | t }}</option>
          <option value="INVALID">{{ 'releases.verdict_invalid' | t }}</option>
          <option value="NOT_EVALUATED">{{ 'releases.verdict_not_evaluated' | t }}</option>
        </select>
      </div>

      <div *ngIf="loading()" class="skeleton-list">
        <div class="skeleton skeleton-row" *ngFor="let i of [1,2,3,4,5,6]"></div>
      </div>

      <div *ngIf="error() && !loading()" class="error-banner">{{ error() }}</div>

      <div *ngIf="!loading() && !error()" class="data-table-wrap">
        <table class="data-table" *ngIf="filtered().length > 0; else emptyState">
          <thead>
            <tr>
              <th scope="col">{{ 'releases.table_id' | t }}</th>
              <th scope="col">{{ 'releases.table_name' | t }}</th>
              <th scope="col" *ngIf="isAdmin">{{ 'releases.col_org' | t }}</th>
              <th scope="col">{{ 'releases.table_verdict' | t }}</th>
              <th scope="col">{{ 'releases.table_date' | t }}</th>
              <th scope="col" *ngIf="!isAdmin && !isViewer" class="col-actions">{{ 'releases.table_actions' | t }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              *ngFor="let r of paginated()"
              [routerLink]="['/app/releases', r.id]"
              class="clickable-row"
            >
              <td><code class="mono-sm">{{ r.id | slice:0:8 }}</code></td>
              <td class="cell-primary">{{ r.name || ('common.dash' | t) }}</td>
              <td *ngIf="isAdmin" class="cell-muted">{{ r.organization_name || ('common.dash' | t) }}</td>
              <td>
                <span class="verdict-badge" [ngClass]="verdictClass(r.verdict)">
                  {{ (r.verdict ? ('verdict.' + r.verdict | t) : ('verdict.NOT_EVALUATED' | t)) }}
                </span>
              </td>
              <td class="cell-muted">{{ r.created_at | date:'dd MMM yyyy, HH:mm' }}</td>
              <td *ngIf="!isAdmin && !isViewer" class="cell-actions" (click)="$event.stopPropagation()">
                <a [routerLink]="['/app/releases', r.id, 'edit']" class="btn-action btn-edit" title="{{ 'common.edit' | t }}">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                  </svg>
                </a>
                <button class="btn-action btn-delete" title="{{ 'common.delete' | t }}" (click)="confirmDelete(r)">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="3 6 5 6 21 6"/>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                  </svg>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <ng-template #emptyState>
          <div class="empty-state">{{ 'releases.no_releases_filter' | t }}</div>
        </ng-template>

        <div class="pagination" *ngIf="filtered().length > pageSize">
          <button class="btn-ghost" [disabled]="page() === 0" [title]="page() === 0 ? ('common.disabled_tooltip.first_page' | t) : ''" (click)="prevPage()">{{ 'common.previous' | t }}</button>
          <span class="page-info">
            {{ page() + 1 }} / {{ totalPages() }}
          </span>
          <button class="btn-ghost" [disabled]="page() >= totalPages() - 1" [title]="page() >= totalPages() - 1 ? ('common.disabled_tooltip.last_page' | t) : ''" (click)="nextPage()">{{ 'common.next' | t }}</button>
        </div>
      </div>

      @if (showDeleteModal()) {
        <div class="modal-overlay" (click)="cancelDelete()">
          <div class="modal-content" (click)="$event.stopPropagation()">
            <h3 class="modal-title">{{ 'common.confirm' | t }}</h3>
            <p class="modal-message">{{ 'releases.delete_confirm' | t }}</p>
            <div class="modal-footer">
              <button class="btn-secondary" (click)="cancelDelete()">{{ 'common.cancel' | t }}</button>
              <button class="btn-danger" [disabled]="deleting()" [title]="deleting() ? ('common.disabled_tooltip.operation_in_progress' | t) : ''" (click)="executeDelete()">
                {{ deleting() ? ('common.deleting' | t) : ('common.delete' | t) }}
              </button>
            </div>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    :host { display: block; }

    .releases-page { padding: 0; }

    .page-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: var(--spacing-lg);
    }

    .page-header-left {
      display: flex;
      align-items: baseline;
      gap: var(--spacing-md);
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

    .global-badge {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--muted);
      background: var(--paper-secondary);
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-sm);
      padding: 0.125rem 0.5rem;
    }

    .filters-bar {
      display: flex;
      gap: var(--spacing-sm);
      margin-bottom: var(--spacing-md);
    }

    .filter-input {
      flex: 1;
      max-width: 20rem;
    }

    .filter-select {
      width: auto;
    }

    .data-table-wrap {
      background: var(--surface-raised);
      border: 0.0625rem solid var(--border);
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
      border-bottom: 0.0625rem solid var(--border);
      background: var(--paper-secondary);
    }

    .data-table td {
      font-size: 0.8125rem;
      color: var(--ink);
      padding: var(--spacing-sm) var(--spacing-md);
      border-bottom: 0.0625rem solid var(--border);
      vertical-align: middle;
      height: 2.75rem;
    }

    .data-table tr:last-child td { border-bottom: none; }

    .clickable-row { cursor: pointer; }
    .clickable-row:hover td { background: var(--paper-secondary); }

    .cell-primary { font-weight: 500; }
    .cell-muted { color: var(--muted); }
    .cell-actions { white-space: nowrap; }

    .col-actions { width: 6rem; text-align: center; }

    .mono-sm {
      font-family: var(--font-mono);
      font-size: 0.6875rem;
      color: var(--muted);
    }

    .verdict-badge {
      display: inline-flex;
      align-items: center;
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      border-radius: var(--rounded-sm);
      padding: 0.125rem 0.5rem;
      border: 0.0625rem solid;
    }

    .verdict-valid { color: var(--verdict-valid); background: var(--verdict-valid-bg); border-color: var(--verdict-valid-border); }
    .verdict-warning { color: var(--verdict-warning); background: var(--verdict-warning-bg); border-color: var(--verdict-warning-border); }
    .verdict-invalid { color: var(--verdict-invalid); background: var(--verdict-invalid-bg); border-color: var(--verdict-invalid-border); }
    .verdict-unevaluated { color: var(--verdict-unevaluated); background: var(--verdict-unevaluated-bg); border-color: var(--verdict-unevaluated-border); }

    .btn-action {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 1.75rem;
      height: 1.75rem;
      border-radius: var(--rounded-sm);
      border: 0.0625rem solid var(--border);
      background: var(--paper);
      cursor: pointer;
      transition: all 0.12s ease;
      margin: 0 0.125rem;
    }

    .btn-action svg { color: var(--muted); }

    .btn-edit:hover {
      background: var(--paper-secondary);
      border-color: var(--ink);
    }

    .btn-edit:hover svg { color: var(--ink); }

    .btn-delete:hover {
      background: var(--verdict-invalid-bg);
      border-color: var(--verdict-invalid-border);
    }

    .btn-delete:hover svg { color: var(--verdict-invalid); }

    .pagination {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: var(--spacing-md);
      padding: var(--spacing-md);
      border-top: 0.0625rem solid var(--border);
    }

    .page-info {
      font-size: 0.8125rem;
      color: var(--muted);
    }

    .btn-ghost {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--muted);
      background: none;
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-md);
      padding: 0.3125rem 0.75rem;
      cursor: pointer;
      transition: color 0.12s ease, background-color 0.12s ease;
    }

    .btn-ghost:hover:not(:disabled) { color: var(--ink); background: var(--paper-secondary); }
    .btn-ghost:disabled { opacity: 0.4; cursor: not-allowed; }

    .btn-primary {
      display: inline-flex;
      align-items: center;
      background: var(--ink);
      color: var(--paper);
      border: 0.0625rem solid var(--ink);
      border-radius: var(--rounded-md);
      padding: 0.5625rem 1.125rem;
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      cursor: pointer;
      transition: background-color 0.15s ease;
    }

    .btn-primary:hover { background: var(--ink-secondary); }

    .btn-secondary {
      display: inline-flex;
      align-items: center;
      background: transparent;
      color: var(--ink);
      border: 0.0625rem solid var(--border-strong);
      border-radius: var(--rounded-md);
      padding: 0.5625rem 1.125rem;
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      cursor: pointer;
      transition: background-color 0.15s ease;
      text-decoration: none;
    }

    .btn-secondary:hover { background: var(--paper-secondary); }

    .btn-danger {
      display: inline-flex;
      align-items: center;
      background: var(--verdict-invalid);
      color: var(--paper);
      border: 0.0625rem solid var(--verdict-invalid);
      border-radius: var(--rounded-md);
      padding: 0.5625rem 1.125rem;
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      cursor: pointer;
      transition: background-color 0.15s ease;
    }

    .btn-danger:hover:not(:disabled) { background: #c41e1e; }
    .btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }

    .modal-overlay {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
    }

    .modal-content {
      background: var(--surface-raised);
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-lg);
      padding: var(--spacing-lg);
      max-width: 24rem;
      width: 90%;
      box-shadow: 0 0.5rem 2rem rgba(0, 0, 0, 0.2);
    }

    .modal-title {
      font-family: var(--font-display);
      font-size: 1.25rem;
      font-weight: 400;
      margin: 0 0 var(--spacing-sm);
      color: var(--ink);
    }

    .modal-message {
      font-size: 0.9375rem;
      color: var(--muted);
      margin: 0 0 var(--spacing-lg);
      line-height: 1.5;
    }

    .modal-footer {
      display: flex;
      justify-content: flex-end;
      gap: var(--spacing-sm);
    }

    .error-banner {
      background: var(--verdict-invalid-bg);
      color: var(--verdict-invalid);
      border: 0.0625rem solid var(--verdict-invalid-border);
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

    .skeleton-row { height: 2.75rem; }

    @keyframes shimmer {
      0% { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }

    .empty-state {
      padding: var(--spacing-xl) var(--spacing-lg);
      text-align: center;
      font-size: 0.8125rem;
      color: var(--muted);
    }

    @media (max-width: 48rem) {
      .page-header {
        flex-direction: column;
        align-items: flex-start;
        gap: var(--spacing-sm);
      }

      .page-title { font-size: 1.75rem; }

      .filters-bar {
        flex-wrap: wrap;
        gap: var(--spacing-sm);
      }

      .filter-input { max-width: 100%; }

      .data-table-wrap { overflow-x: auto; }

      .modal-footer {
        flex-direction: column-reverse;
      }

      .btn-secondary,
      .btn-danger {
        justify-content: center;
        width: 100%;
      }
    }
  `],
})
export class ReleasesComponent implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly authService = inject(AuthService);
  private readonly ts = inject(TranslationService);

  readonly isAdmin = this.authService.isAdmin();
  readonly isViewer = this.authService.getUserRole() === 'VIEWER';
  readonly pageSize = 20;

  releases = signal<Release[]>([]);
  filtered = signal<Release[]>([]);
  loading = signal(true);
  error = signal<string | null>(null);
  page = signal(0);

  showDeleteModal = signal(false);
  releaseToDelete = signal<Release | null>(null);
  deleting = signal(false);

  filterText = '';
  filterVerdict = '';

  ngOnInit(): void {
    const url = '/api/v1/releases';
    this.http.get<Release[]>(url)
      .pipe(catchError(() => { this.error.set(this.ts.translateInstant('releases.loading_error')); return of([]); }))
      .subscribe(data => {
        this.releases.set(data);
        this.filtered.set(data);
        this.loading.set(false);
      });
  }

  onFilterChange(): void {
    this.page.set(0);
    const text = this.filterText.toLowerCase();
    const verdict = this.filterVerdict;
    this.filtered.set(
      this.releases().filter(r => {
        const matchText = !text || r.id.toLowerCase().includes(text) || (r.name ?? '').toLowerCase().includes(text);
        const matchVerdict = !verdict || r.verdict === verdict;
        return matchText && matchVerdict;
      })
    );
  }

  paginated(): Release[] {
    const start = this.page() * this.pageSize;
    return this.filtered().slice(start, start + this.pageSize);
  }

  totalPages(): number {
    return Math.ceil(this.filtered().length / this.pageSize);
  }

  prevPage(): void { this.page.update(p => Math.max(0, p - 1)); }
  nextPage(): void { this.page.update(p => Math.min(this.totalPages() - 1, p + 1)); }

  verdictClass(verdict: string): Record<string, boolean> {
    return {
      'verdict-valid': verdict === 'VALID',
      'verdict-warning': verdict === 'WITH_WARNINGS',
      'verdict-invalid': verdict === 'INVALID',
      'verdict-unevaluated': verdict === 'NOT_EVALUATED' || !verdict,
    };
  }

  confirmDelete(release: Release): void {
    this.releaseToDelete.set(release);
    this.showDeleteModal.set(true);
  }

  cancelDelete(): void {
    this.showDeleteModal.set(false);
    this.releaseToDelete.set(null);
  }

  executeDelete(): void {
    const release = this.releaseToDelete();
    if (!release) return;

    this.deleting.set(true);
    this.http.delete(`/api/v1/releases/${release.id}`)
      .pipe(
        catchError(err => {
          this.error.set(this.ts.translateInstant('releases.delete_error'));
          this.deleting.set(false);
          this.cancelDelete();
          return of(null);
        })
      )
      .subscribe(() => {
        this.releases.update(list => list.filter(r => r.id !== release.id));
        this.filtered.update(list => list.filter(r => r.id !== release.id));
        this.deleting.set(false);
        this.cancelDelete();
      });
  }
}
