import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { catchError, of } from 'rxjs';
import { TranslationService } from '../../core/i18n/translation.service';
import { TranslatePipe } from '../../core/i18n/translate.pipe';

interface AuditLog {
  id: string;
  timestamp: string;
  action: string;
  category: string;
  actor_id: string;
  actor_role: string;
  target_type?: string;
  target_id?: string;
  result: 'success' | 'failure' | 'denied';
  ip_address?: string;
}

interface AuditLogsResponse {
  total: number;
  logs: AuditLog[];
}

@Component({
  selector: 'app-logs',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslatePipe],
  templateUrl: './logs.component.html',
  styleUrl: './logs.component.scss',
})
export class LogsComponent implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly ts = inject(TranslationService);

  readonly pageSize = 25;

  allLogs = signal<AuditLog[]>([]);
  filtered = signal<AuditLog[]>([]);
  loading = signal(true);
  notAvailable = signal(false);
  page = signal(0);

  filterCategory = '';
  filterResult = '';

  ngOnInit(): void {
    this.http.get<AuditLogsResponse>('/api/v1/audit/logs?limit=500')
      .pipe(catchError(() => of(null)))
      .subscribe(data => {
        if (data === null) {
          this.notAvailable.set(true);
        } else {
          this.allLogs.set(data.logs);
          this.filtered.set(data.logs);
        }
        this.loading.set(false);
      });
  }

  applyFilters(): void {
    this.page.set(0);
    this.filtered.set(
      this.allLogs().filter(log => {
        const matchCat = !this.filterCategory || log.category === this.filterCategory;
        const matchResult = !this.filterResult || log.result === this.filterResult;
        return matchCat && matchResult;
      })
    );
  }

  resetFilters(): void {
    this.filterCategory = '';
    this.filterResult = '';
    this.applyFilters();
  }

  paginated(): AuditLog[] {
    const start = this.page() * this.pageSize;
    return this.filtered().slice(start, start + this.pageSize);
  }

  totalPages(): number {
    return Math.ceil(this.filtered().length / this.pageSize);
  }

  prevPage(): void { this.page.update(p => Math.max(0, p - 1)); }
  nextPage(): void { this.page.update(p => Math.min(this.totalPages() - 1, p + 1)); }

  maskId(id: string): string {
    if (!id || id.length < 8) return '••••••••';
    if (id.startsWith('sha256:')) return id.slice(0, 16) + '…';
    return id.slice(0, 4) + '••••' + id.slice(-4);
  }

  maskIp(ip: string): string {
    if (ip.startsWith('sha256:')) return ip.slice(0, 14) + '…';
    const parts = ip.split('.');
    if (parts.length === 4) return `${parts[0]}.${parts[1]}.•••.•••`;
    return ip.slice(0, 4) + '•••';
  }

  resultLabel(result: string): string {
    const map: Record<string, string> = {
      success: this.ts.translateInstant('logs.result_success'),
      failure: this.ts.translateInstant('logs.result_failure'),
      denied: this.ts.translateInstant('logs.result_denied'),
    };
    return map[result] ?? result;
  }
}
