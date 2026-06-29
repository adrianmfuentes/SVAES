import { Component, Input, OnChanges, inject } from '@angular/core';
import { BaseChartDirective } from 'ng2-charts';
import { ChartData, ChartOptions, TooltipItem } from 'chart.js';
import { TemporalPoint } from '../../services/dashboard.service';
import { TranslatePipe } from '../../../../core/i18n/translate.pipe';
import { TranslationService } from '../../../../core/i18n/translation.service';

type GradientStop = [number, string];

function makeGradient(ctx: CanvasRenderingContext2D, top: number, bottom: number, stops: GradientStop[]): CanvasGradient {
  const g = ctx.createLinearGradient(0, top, 0, bottom);
  stops.forEach(([offset, color]) => g.addColorStop(offset, color));
  return g;
}

function gradientFill(stops: GradientStop[]) {
  return (context: { chart: { ctx: CanvasRenderingContext2D; chartArea?: { top: number; bottom: number } } }) => {
    const { ctx, chartArea } = context.chart;
    if (!chartArea) return 'transparent';
    return makeGradient(ctx, chartArea.top, chartArea.bottom, stops);
  };
}

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
    animation: { duration: 700, easing: 'easeInOutQuart' },
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: {
        display: true,
        position: 'bottom',
        labels: {
          font: { family: 'IBM Plex Sans', size: 11, weight: 500 },
          color: '#7A7670',
          usePointStyle: true,
          pointStyle: 'line',
          pointStyleWidth: 20,
          padding: 20,
          boxHeight: 2,
        },
      },
      tooltip: {
        enabled: true,
        backgroundColor: 'rgba(30,27,22,0.88)',
        titleColor: '#F5F2ED',
        bodyColor: '#C8C3BB',
        borderColor: 'rgba(255,255,255,0.08)',
        borderWidth: 1,
        padding: { x: 14, y: 10 },
        cornerRadius: 8,
        titleFont: { family: 'IBM Plex Sans', size: 11 },
        bodyFont: { family: 'IBM Plex Sans', size: 12 },
        callbacks: {
          label: (item: TooltipItem<'line'>) =>
            `  ${item.dataset.label}  ${(item.raw as number).toFixed(1)}%`,
        },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: {
          font: { family: 'IBM Plex Sans', size: 11 },
          color: '#9E9890',
          maxRotation: 30,
          maxTicksLimit: 8,
        },
        border: { display: false },
      },
      y: {
        min: 0,
        max: 100,
        grid: {
          color: 'rgba(180,170,158,0.18)',
          lineWidth: 1,
        },
        ticks: {
          font: { family: 'IBM Plex Sans', size: 11 },
          color: '#9E9890',
          callback: (v) => `${v}%`,
          stepSize: 25,
          maxTicksLimit: 5,
        },
        border: { display: false, dash: [4, 4] },
      },
    },
  };

  ngOnChanges(): void {
    if (!this.data?.length) return;

    const pct = (n: number, total: number) => (total > 0 ? (n / total) * 100 : 0);
    const single = this.data.length === 1;

    const buildDataset = (
      verdictKey: 'valid' | 'with_warnings' | 'invalid',
      labelKey: string,
      color: string,
      gradStops: GradientStop[],
    ) => ({
      label: this.ts.translateInstant(labelKey),
      data: this.data.map((d) => pct(d[verdictKey], d.valid + d.with_warnings + d.invalid)),
      borderColor: color,
      backgroundColor: single ? color + '33' : gradientFill(gradStops) as unknown as string,
      fill: true,
      tension: 0.45,
      borderWidth: 2.5,
      pointRadius: single ? 5 : 0,
      pointHoverRadius: 6,
      pointHitRadius: 24,
      pointBackgroundColor: color,
      pointBorderColor: '#fff',
      pointBorderWidth: 2,
    });

    this.chartData = {
      labels: this.data.map((d) => d.date),
      datasets: [
        buildDataset('valid', 'verdict.VALID', '#27AE60', [
          [0, 'rgba(39,174,96,0.22)'],
          [0.6, 'rgba(39,174,96,0.06)'],
          [1, 'rgba(39,174,96,0.0)'],
        ]),
        buildDataset('with_warnings', 'verdict.VALID_WITH_WARNINGS', '#E0991A', [
          [0, 'rgba(224,153,26,0.16)'],
          [0.6, 'rgba(224,153,26,0.04)'],
          [1, 'rgba(224,153,26,0.0)'],
        ]),
        buildDataset('invalid', 'verdict.INVALID', '#D94F3D', [
          [0, 'rgba(217,79,61,0.16)'],
          [0.6, 'rgba(217,79,61,0.04)'],
          [1, 'rgba(217,79,61,0.0)'],
        ]),
      ],
    };
  }
}
