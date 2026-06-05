import { TestBed } from '@angular/core/testing';
import { BehaviorSubject } from 'rxjs';
import { App } from './app';
import { TranslationService } from './core/i18n/translation.service';
import { provideRouter } from '@angular/router';

describe('App', () => {
  let langSubject: BehaviorSubject<string>;

  beforeEach(async () => {
    langSubject = new BehaviorSubject<string>('es');
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [
        provideRouter([]),
        {
          provide: TranslationService,
          useValue: {
            currentLang: 'es',
            lang$: langSubject.asObservable(),
            translateInstant: () => '',
          },
        },
      ],
    }).compileComponents();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });

  it('should render router-outlet', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('router-outlet')).toBeTruthy();
  });

  it('should set document.documentElement.lang on ngOnInit', () => {
    const fixture = TestBed.createComponent(App);
    fixture.componentInstance.ngOnInit();
    expect(document.documentElement.lang).toBe('es');
  });

  it('should update document lang when lang$ emits', () => {
    const fixture = TestBed.createComponent(App);
    fixture.componentInstance.ngOnInit();
    langSubject.next('en');
    expect(document.documentElement.lang).toBe('en');
  });
});
