import { TestBed } from '@angular/core/testing';
import { NO_ERRORS_SCHEMA } from '@angular/core';
import { of } from 'rxjs';
import { SuccessRateChartComponent } from './success-rate-chart.component';
import { TranslationService } from '../../../../core/i18n/translation.service';

const tsMock = {
  translateInstant: vi.fn((key: string) => {
    const translations: Record<string, string> = {
      'verdict.VALID': 'VALID',
      'verdict.VALID_WITH_WARNINGS': 'WITH_WARNINGS',
      'verdict.INVALID': 'INVALID',
      'verdict.NOT_EVALUATED': 'NOT_EVALUATED',
    };
    return translations[key] ?? key;
  }),
  currentLang: 'es',
  lang$: of('es'),
};

describe('SuccessRateChartComponent', () => {
  let component: SuccessRateChartComponent;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      schemas: [NO_ERRORS_SCHEMA],
      providers: [
        { provide: TranslationService, useValue: tsMock },
      ],
    });

    const fixture = TestBed.createComponent(SuccessRateChartComponent);
    component = fixture.componentInstance;
  });

  afterEach(() => {
    TestBed.resetTestingModule();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('ngOnChanges', () => {
    it('should build chartData from non-empty data as percentages', () => {
      component.data = [
        { date: '2025-01-01', valid: 5, with_warnings: 2, invalid: 1 },
        { date: '2025-01-02', valid: 8, with_warnings: 1, invalid: 0 },
      ];
      component.ngOnChanges();

      expect(component.chartData.labels).toEqual(['2025-01-01', '2025-01-02']);
      expect(component.chartData.datasets).toHaveLength(3);

      const validData = component.chartData.datasets[0].data as number[];
      expect(validData[0]).toBeCloseTo(62.5);
      expect(validData[1]).toBeCloseTo((8 / 9) * 100);

      const warnData = component.chartData.datasets[1].data as number[];
      expect(warnData[0]).toBeCloseTo(25);
      expect(warnData[1]).toBeCloseTo((1 / 9) * 100);

      const invalidData = component.chartData.datasets[2].data as number[];
      expect(invalidData[0]).toBeCloseTo(12.5);
      expect(invalidData[1]).toBeCloseTo(0);
    });

    it('should return 0% for all categories when total is 0', () => {
      component.data = [{ date: '2025-01-01', valid: 0, with_warnings: 0, invalid: 0 }];
      component.ngOnChanges();
      const allZero = component.chartData.datasets.every(ds => (ds.data as number[])[0] === 0);
      expect(allZero).toBe(true);
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
