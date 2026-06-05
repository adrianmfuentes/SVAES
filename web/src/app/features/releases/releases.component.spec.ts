import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { of } from 'rxjs';
import { ReleasesComponent } from './releases.component';
import { AuthService } from '../../core/services/auth.service';
import { TranslationService } from '../../core/i18n/translation.service';
import { provideRouter } from '@angular/router';

const tsMock = {
  translateInstant: vi.fn((key: string) => key),
  currentLang: 'es',
  lang$: of('es'),
};

const authMock = {
  isAdmin: vi.fn().mockReturnValue(false),
  getUserRole: vi.fn().mockReturnValue('OPERATOR'),
  getUser: vi.fn().mockReturnValue(null),
};

const mockReleases = [
  { id: 'aaa111', name: 'alpha', verdict: 'VALID', created_at: '2025-01-01T00:00:00Z' },
  { id: 'bbb222', name: 'beta', verdict: 'INVALID', created_at: '2025-01-02T00:00:00Z' },
  { id: 'ccc333', name: 'gamma', verdict: 'WITH_WARNINGS', created_at: '2025-01-03T00:00:00Z' },
];

describe('ReleasesComponent', () => {
  let component: ReleasesComponent;
  let fixture: ComponentFixture<ReleasesComponent>;
  let httpCtrl: HttpTestingController;

  beforeEach(() => {
    vi.clearAllMocks();
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: authMock },
        { provide: TranslationService, useValue: tsMock },
      ],
    });

    fixture = TestBed.createComponent(ReleasesComponent);
    component = fixture.componentInstance;
    httpCtrl = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpCtrl?.verify();
    TestBed.resetTestingModule();
  });

  describe('ngOnInit / HTTP', () => {
    it('should load releases on init', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/releases').flush(mockReleases);
      expect(component.releases()).toEqual(mockReleases);
      expect(component.filtered()).toEqual(mockReleases);
      expect(component.loading()).toBe(false);
    });

    it('should set error on HTTP failure', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/releases').flush('', { status: 500, statusText: 'Error' });
      expect(component.error()).toBe('releases.loading_error');
      expect(component.loading()).toBe(false);
    });
  });

  describe('verdictClass', () => {
    it('should return verdict-valid for VALID', () => {
      const cls = component.verdictClass('VALID');
      expect(cls['verdict-valid']).toBe(true);
      expect(cls['verdict-invalid']).toBe(false);
    });

    it('should return verdict-warning for WITH_WARNINGS', () => {
      expect(component.verdictClass('WITH_WARNINGS')['verdict-warning']).toBe(true);
    });

    it('should return verdict-invalid for INVALID', () => {
      expect(component.verdictClass('INVALID')['verdict-invalid']).toBe(true);
    });

    it('should return verdict-unevaluated for empty string', () => {
      expect(component.verdictClass('')['verdict-unevaluated']).toBe(true);
    });

    it('should return verdict-unevaluated for NOT_EVALUATED', () => {
      expect(component.verdictClass('NOT_EVALUATED')['verdict-unevaluated']).toBe(true);
    });
  });

  describe('onFilterChange', () => {
    beforeEach(() => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/releases').flush(mockReleases);
    });

    it('should filter by text match on id', () => {
      component.filterText = 'aaa';
      component.onFilterChange();
      expect(component.filtered()).toHaveLength(1);
      expect(component.filtered()[0].id).toBe('aaa111');
    });

    it('should filter by verdict', () => {
      component.filterVerdict = 'INVALID';
      component.onFilterChange();
      expect(component.filtered()).toHaveLength(1);
      expect(component.filtered()[0].verdict).toBe('INVALID');
    });

    it('should combine text and verdict filters', () => {
      component.filterText = 'alpha';
      component.filterVerdict = 'INVALID';
      component.onFilterChange();
      expect(component.filtered()).toHaveLength(0);
    });

    it('should reset page to 0 on filter', () => {
      component.page.set(3);
      component.onFilterChange();
      expect(component.page()).toBe(0);
    });
  });

  describe('pagination', () => {
    it('should paginate filtered results', () => {
      const many = Array.from({ length: 45 }, (_, i) => ({
        id: `r${i}`,
        name: `r${i}`,
        verdict: 'VALID',
        created_at: '2025-01-01T00:00:00Z',
      }));
      component.releases.set(many);
      component.filtered.set(many);
      expect(component.paginated()).toHaveLength(20);
      expect(component.totalPages()).toBe(3);
    });

    it('nextPage/prevPage should clamp to valid range', () => {
      component.filtered.set(Array.from({ length: 25 }, (_, i) => ({
        id: `r${i}`, name: `n${i}`, verdict: 'VALID', created_at: '',
      })));
      expect(component.page()).toBe(0);
      component.prevPage();
      expect(component.page()).toBe(0);
      component.nextPage();
      expect(component.page()).toBe(1);
      component.nextPage();
      expect(component.page()).toBe(1);
    });
  });

  describe('template rendering', () => {
    const renderTemplate = () => {
      vi.spyOn(component, 'ngOnInit').mockImplementation(() => {});
      fixture.detectChanges();
      httpCtrl.expectOne('/api/v1/releases').flush([]);
    };

    it('should render loading skeleton', () => {
      component.loading.set(true);
      renderTemplate();
    });

    it('should render error state', () => {
      component.loading.set(false);
      component.error.set('releases.loading_error');
      renderTemplate();
    });

    it('should render releases list with various verdicts', () => {
      component.loading.set(false);
      component.releases.set(mockReleases);
      component.filtered.set(mockReleases);
      renderTemplate();
    });

    it('should render empty state', () => {
      component.loading.set(false);
      component.releases.set([]);
      component.filtered.set([]);
      renderTemplate();
    });

    it('should render with pagination', () => {
      const many = Array.from({ length: 45 }, (_, i) => ({
        id: `r${i}`, name: `release-${i}`, verdict: 'VALID', created_at: '2025-01-01T00:00:00Z',
      }));
      component.loading.set(false);
      component.releases.set(many);
      component.filtered.set(many);
      renderTemplate();
    });
  });
});
