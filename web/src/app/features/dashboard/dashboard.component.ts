import { Component, DestroyRef, OnInit, inject, signal } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { finalize } from 'rxjs';
import { provideCharts, withDefaultRegisterables } from 'ng2-charts';
import {
  DashboardService,
  DashboardMetrics,
  Project,
  RecentRelease,
} from './services/dashboard.service';
import { KpiCardComponent } from './components/kpi-card/kpi-card.component';
import { SuccessRateChartComponent } from './components/success-rate-chart/success-rate-chart.component';
import { TopFailedRulesComponent } from './components/top-failed-rules/top-failed-rules.component';
import { RecentReleasesTableComponent } from './components/recent-releases-table/recent-releases-table.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    DecimalPipe,
    KpiCardComponent,
    SuccessRateChartComponent,
    TopFailedRulesComponent,
    RecentReleasesTableComponent,
  ],
  providers: [provideCharts(withDefaultRegisterables())],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss'],
})
export class DashboardComponent implements OnInit {
  private readonly svc = inject(DashboardService);
  private readonly destroyRef = inject(DestroyRef);

  readonly periods = ['7d', '30d', '90d', 'Year'] as const;

  private readonly periodApiMap: Record<string, string> = {
    '7d': 'last_7d',
    '30d': 'last_30d',
    '90d': 'last_90d',
    Year: 'last_year',
  };

  activePeriod = signal<string>('30d');
  activeProjectId = signal<string>('');

  metricsLoading = signal(true);
  metricsError = signal<string | null>(null);
  metrics = signal<DashboardMetrics | null>(null);

  projectsLoading = signal(true);
  projects = signal<Project[]>([]);

  releasesLoading = signal(true);
  releasesError = signal<string | null>(null);
  recentReleases = signal<RecentRelease[]>([]);

  ngOnInit(): void {
    this.loadProjects();
    this.loadMetrics();
    this.loadRecentReleases();
  }

  selectPeriod(period: string): void {
    if (this.activePeriod() === period) return;
    this.activePeriod.set(period);
    this.loadMetrics();
  }

  onProjectChange(event: Event): void {
    this.activeProjectId.set((event.target as HTMLSelectElement).value);
    this.loadMetrics();
  }

  successRateClass(rate: number): string {
    if (rate >= 80) return 'rate--valid';
    if (rate >= 50) return 'rate--warning';
    return 'rate--invalid';
  }

  formatTime(minutes: number): string {
    const h = Math.floor(minutes / 60);
    const m = Math.round(minutes % 60);
    if (h === 0) return `${m}m`;
    return `${h}h ${m}m`;
  }

  private loadMetrics(): void {
    this.metricsLoading.set(true);
    this.metricsError.set(null);
    const period = this.periodApiMap[this.activePeriod()] ?? 'last_30d';
    this.svc
      .getMetrics(period, this.activeProjectId())
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.metricsLoading.set(false)),
      )
      .subscribe({
        next: (data) => this.metrics.set(data),
        error: () => this.metricsError.set('Failed to load metrics'),
      });
  }

  private loadProjects(): void {
    this.projectsLoading.set(true);
    this.svc
      .getProjects()
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.projectsLoading.set(false)),
      )
      .subscribe({
        next: (data) => this.projects.set(data),
        error: () => this.projects.set([]),
      });
  }

  private loadRecentReleases(): void {
    this.releasesLoading.set(true);
    this.releasesError.set(null);
    this.svc
      .getRecentReleases()
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.releasesLoading.set(false)),
      )
      .subscribe({
        next: (data) => this.recentReleases.set(data),
        error: () => this.releasesError.set('Failed to load releases'),
      });
  }
}
