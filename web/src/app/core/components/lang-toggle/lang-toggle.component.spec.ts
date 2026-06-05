import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { LangToggleComponent } from './lang-toggle.component';
import { TranslationService } from '../../i18n/translation.service';

describe('LangToggleComponent', () => {
  let component: LangToggleComponent;
  let fixture: ComponentFixture<LangToggleComponent>;
  let tsMock: {
    currentLang: string;
    setLanguage: ReturnType<typeof vi.fn>;
    loadTranslationsWithCache: ReturnType<typeof vi.fn>;
    lang$: ReturnType<typeof vi.fn>;
  };

  beforeEach(async () => {
    TestBed.resetTestingModule();
    tsMock = {
      currentLang: 'es',
      setLanguage: vi.fn(),
      loadTranslationsWithCache: vi.fn().mockReturnValue(of({})),
      lang$: vi.fn(),
    };

    await TestBed.configureTestingModule({
      imports: [LangToggleComponent],
      providers: [
        { provide: TranslationService, useValue: tsMock },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(LangToggleComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    TestBed.resetTestingModule();
  });

  it('TC-UNI-FE-COM-01: should create the component', () => {
    console.log('TC-UNI-FE-COM-01 PASS');
    expect(component).toBeTruthy();
  });

  it('should display current language from TranslationService', () => {
    expect(component.currentLang).toBe('es');
  });

  it('should call setLang switching to other language', () => {
    component.setLang('en');

    expect(tsMock.loadTranslationsWithCache).toHaveBeenCalledWith('en');
    expect(tsMock.setLanguage).toHaveBeenCalledWith('en');
  });

  it('should not call setLanguage when same language is selected', () => {
    component.setLang('es');

    expect(tsMock.loadTranslationsWithCache).not.toHaveBeenCalled();
    expect(tsMock.setLanguage).not.toHaveBeenCalled();
  });

  it('should render both ES and EN buttons', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const buttons = compiled.querySelectorAll('.lt-btn');
    expect(buttons).toHaveLength(2);
    expect(buttons[0].textContent?.trim()).toBe('ES');
    expect(buttons[1].textContent?.trim()).toBe('EN');
  });

  it('should mark ES as active when currentLang is es', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const esBtn = compiled.querySelectorAll('.lt-btn')[0];
    expect(esBtn.classList.contains('lt-btn--on')).toBe(true);
  });

  it('should handle theme input (default light)', () => {
    expect(component.theme).toBe('light');
  });

  it('should accept dark theme input', () => {
    const fixture2 = TestBed.createComponent(LangToggleComponent);
    const comp2 = fixture2.componentInstance;
    comp2.theme = 'dark';
    fixture2.autoDetectChanges();
    const compiled = fixture2.nativeElement as HTMLElement;
    expect(compiled.querySelector('.lt--dark')).toBeTruthy();
  });
});
