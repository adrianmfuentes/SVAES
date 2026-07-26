import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { TranslationService } from '../../core/i18n/translation.service';
import { TranslatePipe } from '../../core/i18n/translate.pipe';
import { catchError, of } from 'rxjs';
import { ReleaseService, ReleaseSummary as Release } from './services/release.service';

@Component({
  selector: 'app-releases',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, TranslatePipe],
  templateUrl: './releases.component.html',
  styleUrls: ['./releases.component.scss'],
})
export class ReleasesComponent implements OnInit {
  private readonly releaseService = inject(ReleaseService);
  private readonly authService = inject(AuthService);
  private readonly ts = inject(TranslationService);

  readonly isAdmin = this.authService.isAdmin();
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
    this.releaseService.listAll()
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
    this.releaseService.deleteRelease(release.id)
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
