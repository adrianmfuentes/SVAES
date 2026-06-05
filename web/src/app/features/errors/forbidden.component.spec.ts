import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { ForbiddenComponent } from './forbidden.component';
import { AuthService } from '../../core/services/auth.service';
import { TranslationService } from '../../core/i18n/translation.service';

const tsMock = {
  translateInstant: vi.fn((key: string) => key),
  currentLang: 'es',
  lang$: of('es'),
};

describe('ForbiddenComponent — as admin', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: { isAdmin: vi.fn().mockReturnValue(true) } },
        { provide: TranslationService, useValue: tsMock },
      ],
    });
  });

  it('should create and set isAdmin true', () => {
    const comp = TestBed.createComponent(ForbiddenComponent).componentInstance;
    expect(comp).toBeTruthy();
    expect(comp.isAdmin).toBe(true);
  });
});

describe('ForbiddenComponent — as non-admin', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: { isAdmin: vi.fn().mockReturnValue(false) } },
        { provide: TranslationService, useValue: tsMock },
      ],
    });
  });

  it('should create and set isAdmin false', () => {
    const comp = TestBed.createComponent(ForbiddenComponent).componentInstance;
    expect(comp).toBeTruthy();
    expect(comp.isAdmin).toBe(false);
  });
});
