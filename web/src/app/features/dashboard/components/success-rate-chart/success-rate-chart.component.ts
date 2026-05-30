import { Component, Input, OnChanges } from '@angular/core';
import { BaseChartDirective } from 'ng2-charts';
import { ChartData, ChartOptions } from 'chart.js';
import { TemporalPoint } from '../../services/dashboard.service';

@Component({
  selector: 'app-success-rate-chart',
  standalone: true,
  imports: [BaseChartDirective],
  templateUrl: './success-rate-chart.component.html',
  styleUrls: ['./success-rate-chart.component.scss'],
})
export class SuccessRateChartComponent implements OnChanges {
  @Input() data: TemporalPoint[] = [];
  @Input() loading = false;
  @Input() error: string | null = null;

  chartData: ChartData<'bar'> = { labels: [], datasets: [] };

  chartOptions: ChartOptions<'bar'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: { enabled: true },
    },
    scales: {
      x: {
        stacked: true,
        grid: { display: false },
        ticks: { font: { family: 'IBM Plex Sans', size: 11 }, color: '#7A7670' },
        border: { color: '#D4CFC7' },
      },
      y: {
        stacked: true,
        grid: { color: '#D4CFC7' },
        ticks: { font: { family: 'IBM Plex Sans', size: 11 }, color: '#7A7670' },
        border: { color: '#D4CFC7' },
      },
    },
  };

  ngOnChanges(): void {
    if (this.data?.length) {
      this.chartData = {
        labels: this.data.map((d) => d.date),
        datasets: [
          {
            label: 'VALID',
            data: this.data.map((d) => d.valid),
            backgroundColor: '#2A6B3C',
            borderWidth: 0,
          },
          {
            label: 'WITH_WARNINGS',
            data: this.data.map((d) => d.with_warnings),
            backgroundColor: '#8B5E00',
            borderWidth: 0,
          },
          {
            label: 'INVALID',
            data: this.data.map((d) => d.invalid),
            backgroundColor: '#8B1A1A',
            borderWidth: 0,
          },
        ],
      };
    }
  }
}
