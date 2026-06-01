import { Component, DestroyRef, OnInit, inject, signal } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { finalize } from 'rxjs';
import { provideCharts, withDefaultRegisterables } from 'ng2-charts';
import {
  DashboardService,
  DashboardMetrics,
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

  metricsLoading = signal(true);
  metricsError = signal<string | null>(null);
  metrics = signal<DashboardMetrics | null>(null);

  releasesLoading = signal(true);
  releasesError = signal<string | null>(null);
  recentReleases = signal<RecentRelease[]>([]);

  ngOnInit(): void {
    this.loadMetrics();
    this.loadRecentReleases();
  }

  passRateClass(rate: number): string {
    if (rate >= 80) return 'rate--valid';
    if (rate >= 50) return 'rate--warning';
    return 'rate--invalid';
  }

  private loadMetrics(): void {
    this.metricsLoading.set(true);
    this.metricsError.set(null);
    this.svc
      .getMetrics()
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.metricsLoading.set(false)),
      )
      .subscribe({
        next: (data) => this.metrics.set(data),
        error: () => this.metricsError.set('Error al cargar métricas'),
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
        error: () => this.releasesError.set('Error al cargar entregas'),
      });
  }
}
