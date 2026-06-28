import { Component, DestroyRef, OnInit, inject, signal } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { TranslationService } from '../../core/i18n/translation.service';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { finalize, interval, switchMap, startWith } from 'rxjs';
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
import { TranslatePipe } from '../../core/i18n/translate.pipe';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    DecimalPipe,
    TranslatePipe,
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
  private readonly ts = inject(TranslationService);

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

  passRateLabel(rate: number): string {
    if (rate >= 80) return 'a11y.pass_rate_good';
    if (rate >= 50) return 'a11y.pass_rate_fair';
    return 'a11y.pass_rate_poor';
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
        error: () => this.metricsError.set(this.ts.translateInstant('system.error.loading_metrics')),
      });
  }

  private loadRecentReleases(): void {
    this.releasesLoading.set(true);
    this.releasesError.set(null);
    interval(10000).pipe(
      startWith(0),
      takeUntilDestroyed(this.destroyRef),
      switchMap(() => this.svc.getRecentReleases()),
    ).subscribe({
      next: (data) => {
        this.releasesLoading.set(false);
        this.recentReleases.set(data);
      },
      error: () => {
        this.releasesLoading.set(false);
        this.releasesError.set(this.ts.translateInstant('releases.loading_error'));
      },
    });
  }
}
