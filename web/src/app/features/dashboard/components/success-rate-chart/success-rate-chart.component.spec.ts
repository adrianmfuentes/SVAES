import { TestBed } from '@angular/core/testing';
import { NO_ERRORS_SCHEMA } from '@angular/core';
import { of } from 'rxjs';
import { SuccessRateChartComponent } from './success-rate-chart.component';
import { TranslationService } from '../../../../core/i18n/translation.service';

const tsMock = {
  translateInstant: vi.fn((key: string) => key),
  currentLang: 'es',
  lang$: of('es'),
};

describe('SuccessRateChartComponent', () => {
  let component: SuccessRateChartComponent;

  beforeEach(() => {
    TestBed.configureTestingModule({
      schemas: [NO_ERRORS_SCHEMA],
      providers: [
        { provide: TranslationService, useValue: tsMock },
      ],
    });

    const fixture = TestBed.createComponent(SuccessRateChartComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('ngOnChanges', () => {
    it('should build chartData from non-empty data', () => {
      component.data = [
        { date: '2025-01-01', valid: 5, with_warnings: 2, invalid: 1 },
        { date: '2025-01-02', valid: 8, with_warnings: 1, invalid: 0 },
      ];
      component.ngOnChanges();

      expect(component.chartData.labels).toEqual(['2025-01-01', '2025-01-02']);
      expect(component.chartData.datasets).toHaveLength(3);
      expect(component.chartData.datasets[0].data).toEqual([5, 8]);
      expect(component.chartData.datasets[1].data).toEqual([2, 1]);
      expect(component.chartData.datasets[2].data).toEqual([1, 0]);
    });

    it('should not update chartData when data is empty', () => {
      component.data = [];
      const initial = component.chartData;
      component.ngOnChanges();
      expect(component.chartData).toBe(initial);
    });

    it('should set correct labels for each dataset', () => {
      component.data = [{ date: '2025-01', valid: 1, with_warnings: 0, invalid: 0 }];
      component.ngOnChanges();

      expect(component.chartData.datasets[0].label).toBe('VALID');
      expect(component.chartData.datasets[1].label).toBe('WITH_WARNINGS');
      expect(component.chartData.datasets[2].label).toBe('INVALID');
    });
  });
});
