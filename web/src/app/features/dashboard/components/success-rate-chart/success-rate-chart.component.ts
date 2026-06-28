import { Component, Input, OnChanges, inject } from '@angular/core';
import { BaseChartDirective } from 'ng2-charts';
import { ChartData, ChartOptions, TooltipItem } from 'chart.js';
import { TemporalPoint } from '../../services/dashboard.service';
import { TranslatePipe } from '../../../../core/i18n/translate.pipe';
import { TranslationService } from '../../../../core/i18n/translation.service';

@Component({
  selector: 'app-success-rate-chart',
  standalone: true,
  imports: [BaseChartDirective, TranslatePipe],
  templateUrl: './success-rate-chart.component.html',
  styleUrls: ['./success-rate-chart.component.scss'],
})
export class SuccessRateChartComponent implements OnChanges {
  private readonly ts = inject(TranslationService);

  @Input() data: TemporalPoint[] = [];
  @Input() loading = false;
  @Input() error: string | null = null;

  chartData: ChartData<'line'> = { labels: [], datasets: [] };

  chartOptions: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: {
        display: true,
        position: 'bottom',
        labels: {
          font: { family: 'IBM Plex Sans', size: 11 },
          color: '#7A7670',
          usePointStyle: true,
          pointStyleWidth: 8,
          padding: 16,
          boxHeight: 6,
        },
      },
      tooltip: {
        enabled: true,
        callbacks: {
          label: (item: TooltipItem<'line'>) => {
            const pct = (item.raw as number).toFixed(1);
            return ` ${item.dataset.label}: ${pct}%`;
          },
        },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { font: { family: 'IBM Plex Sans', size: 11 }, color: '#7A7670', maxRotation: 45 },
        border: { color: '#D4CFC7' },
      },
      y: {
        min: 0,
        max: 100,
        grid: { color: '#D4CFC7' },
        ticks: {
          font: { family: 'IBM Plex Sans', size: 11 },
          color: '#7A7670',
          callback: (v) => `${v}%`,
          stepSize: 25,
        },
        border: { color: '#D4CFC7' },
      },
    },
  };

  ngOnChanges(): void {
    if (this.data?.length) {
      const pct = (n: number, total: number) => (total > 0 ? (n / total) * 100 : 0);
      const single = this.data.length === 1;

      this.chartData = {
        labels: this.data.map((d) => d.date),
        datasets: [
          {
            label: this.ts.translateInstant('verdict.VALID'),
            data: this.data.map((d) => pct(d.valid, d.valid + d.with_warnings + d.invalid)),
            borderColor: '#2E7D46',
            backgroundColor: 'rgba(46,125,70,0.08)',
            fill: !single,
            tension: 0.35,
            borderWidth: 2,
            pointRadius: single ? 5 : 3,
            pointHoverRadius: single ? 7 : 5,
            pointBackgroundColor: '#2E7D46',
            pointBorderColor: '#fff',
            pointBorderWidth: single ? 2 : 0,
          },
          {
            label: this.ts.translateInstant('verdict.VALID_WITH_WARNINGS'),
            data: this.data.map((d) => pct(d.with_warnings, d.valid + d.with_warnings + d.invalid)),
            borderColor: '#B07800',
            backgroundColor: 'rgba(176,120,0,0.06)',
            fill: !single,
            tension: 0.35,
            borderWidth: 2,
            pointRadius: single ? 5 : 3,
            pointHoverRadius: single ? 7 : 5,
            pointBackgroundColor: '#B07800',
            pointBorderColor: '#fff',
            pointBorderWidth: single ? 2 : 0,
          },
          {
            label: this.ts.translateInstant('verdict.INVALID'),
            data: this.data.map((d) => pct(d.invalid, d.valid + d.with_warnings + d.invalid)),
            borderColor: '#C0392B',
            backgroundColor: 'rgba(192,57,43,0.06)',
            fill: !single,
            tension: 0.35,
            borderWidth: 2,
            pointRadius: single ? 5 : 3,
            pointHoverRadius: single ? 7 : 5,
            pointBackgroundColor: '#C0392B',
            pointBorderColor: '#fff',
            pointBorderWidth: single ? 2 : 0,
          },
        ],
      };
    }
  }
}
