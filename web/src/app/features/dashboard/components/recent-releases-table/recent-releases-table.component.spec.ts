import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { RecentReleasesTableComponent } from './recent-releases-table.component';
import { TranslationService } from '../../../../core/i18n/translation.service';
import { provideRouter } from '@angular/router';

const tsMock = {
  translateInstant: vi.fn((key: string) => key),
  currentLang: 'es',
  lang$: of('es'),
};

describe('RecentReleasesTableComponent', () => {
  let component: RecentReleasesTableComponent;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        { provide: TranslationService, useValue: tsMock },
      ],
    });

    const fixture = TestBed.createComponent(RecentReleasesTableComponent);
    component = fixture.componentInstance;
  });

  describe('shortId', () => {
    it('should return first 8 chars', () => {
      expect(component.shortId('abcdef1234567890')).toBe('abcdef12');
    });

    it('should handle short ids', () => {
      expect(component.shortId('abc')).toBe('abc');
    });
  });

  describe('verdictClass', () => {
    it('should return badge--valid for VALID', () => {
      const cls = component.verdictClass('VALID');
      expect(cls['badge--valid']).toBe(true);
      expect(cls['badge--invalid']).toBe(false);
    });

    it('should return badge--warning for WITH_WARNINGS', () => {
      const cls = component.verdictClass('WITH_WARNINGS');
      expect(cls['badge--warning']).toBe(true);
    });

    it('should return badge--invalid for INVALID', () => {
      const cls = component.verdictClass('INVALID');
      expect(cls['badge--invalid']).toBe(true);
    });

    it('should return badge--unevaluated for NOT_EVALUATED', () => {
      const cls = component.verdictClass('NOT_EVALUATED');
      expect(cls['badge--unevaluated']).toBe(true);
    });

    it('should return badge--unevaluated for empty string', () => {
      const cls = component.verdictClass('');
      expect(cls['badge--unevaluated']).toBe(true);
    });
  });

  describe('relativeDate', () => {
    it('should return just_now key for <1 min', () => {
      const recent = new Date(Date.now() - 30000).toISOString();
      const result = component.relativeDate(recent);
      expect(tsMock.translateInstant).toHaveBeenCalledWith('releases.relative_just_now');
      expect(result).toBe('releases.relative_just_now');
    });

    it('should return minutes key for <60 min', () => {
      const mins5 = new Date(Date.now() - 5 * 60000).toISOString();
      component.relativeDate(mins5);
      expect(tsMock.translateInstant).toHaveBeenCalledWith('releases.relative_minutes', { n: 5 });
    });

    it('should return hours key for <24h', () => {
      const hours2 = new Date(Date.now() - 2 * 3600000).toISOString();
      component.relativeDate(hours2);
      expect(tsMock.translateInstant).toHaveBeenCalledWith('releases.relative_hours', { n: 2 });
    });

    it('should return days key for >24h', () => {
      const days3 = new Date(Date.now() - 3 * 86400000).toISOString();
      component.relativeDate(days3);
      expect(tsMock.translateInstant).toHaveBeenCalledWith('releases.relative_days', { n: 3 });
    });
  });
});
