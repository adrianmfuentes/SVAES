import { TestBed } from '@angular/core/testing';
import { Subject } from 'rxjs';
import { App } from './app';
import { TranslationService } from './core/i18n/translation.service';

describe('App', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [
        {
          provide: TranslationService,
          useValue: {
            currentLang: 'es',
            lang$: new Subject<string>().asObservable(),
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
});
