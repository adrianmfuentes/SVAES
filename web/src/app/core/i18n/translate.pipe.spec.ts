import { TestBed } from '@angular/core/testing';
import { ChangeDetectorRef } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { TranslatePipe } from './translate.pipe';
import { TranslationService } from './translation.service';

describe('TranslatePipe', () => {
  let pipe: TranslatePipe;
  let lang$: BehaviorSubject<string>;
  let translateInstantSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    lang$ = new BehaviorSubject('es');
    translateInstantSpy = vi.fn();

    const tsMock = {
      translateInstant: translateInstantSpy,
      lang$: lang$.asObservable(),
    } as unknown as TranslationService;

    const cdrMock = {
      markForCheck: vi.fn(),
    } as unknown as ChangeDetectorRef;

    TestBed.configureTestingModule({
      providers: [
        TranslatePipe,
        { provide: TranslationService, useValue: tsMock },
        { provide: ChangeDetectorRef, useValue: cdrMock },
      ],
    });

    pipe = TestBed.inject(TranslatePipe);
  });

  afterEach(() => {
    pipe.ngOnDestroy();
  });

  it('should call translateInstant and return translated value', () => {
    translateInstantSpy.mockReturnValue('Hola Mundo');

    const result = pipe.transform('hello_world');

    expect(result).toBe('Hola Mundo');
  });

  it('should pass params to translateInstant', () => {
    translateInstantSpy.mockReturnValue('Hola Juan');

    pipe.transform('greeting', { name: 'Juan' });

    expect(translateInstantSpy).toHaveBeenCalledWith('greeting', { name: 'Juan' });
  });

  it('should return same value for repeated calls with same key and params', () => {
    translateInstantSpy.mockReturnValue('Same Value');

    const result1 = pipe.transform('my_key', { x: 1 });
    const result2 = pipe.transform('my_key', { x: 1 });

    expect(result1).toBe('Same Value');
    expect(result2).toBe('Same Value');
  });

  it('should destroy subscription on ngOnDestroy', () => {
    translateInstantSpy.mockReturnValue('test');
    pipe.transform('test_key');
    expect(() => pipe.ngOnDestroy()).not.toThrow();
  });
});
