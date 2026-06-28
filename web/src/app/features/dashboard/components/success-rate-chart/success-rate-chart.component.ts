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
    if (!this.data?.length) return;

    const pct = (n: number, total: number) => (total > 0 ? (n / total) * 100 : 0);
    const single = this.data.length === 1;
    const basePointRadius = single ? 5 : 3;
    const basePointHoverRadius = single ? 7 : 5;

    const buildDataset = (
      verdictKey: 'valid' | 'with_warnings' | 'invalid',
      labelKey: string,
      color: string,
      bgColor: string,
    ) => ({
      label: this.ts.translateInstant(labelKey),
      data: this.data.map((d) => pct(d[verdictKey], d.valid + d.with_warnings + d.invalid)),
      borderColor: color,
      backgroundColor: bgColor,
      fill: !single,
      tension: 0.35,
      borderWidth: 2,
      pointRadius: basePointRadius,
      pointHoverRadius: basePointHoverRadius,
      pointBackgroundColor: color,
      pointBorderColor: '#fff',
      pointBorderWidth: single ? 2 : 0,
    });

    this.chartData = {
      labels: this.data.map((d) => d.date),
      datasets: [
        buildDataset('valid', 'verdict.VALID', '#2E7D46', 'rgba(46,125,70,0.08)'),
        buildDataset('with_warnings', 'verdict.VALID_WITH_WARNINGS', '#B07800', 'rgba(176,120,0,0.06)'),
        buildDataset('invalid', 'verdict.INVALID', '#C0392B', 'rgba(192,57,43,0.06)'),
      ],
    };
  }
}
