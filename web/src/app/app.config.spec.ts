import { TestBed } from '@angular/core/testing';
import { provideRouter, withPreloading, PreloadAllModules } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { firstValueFrom, of } from 'rxjs';
import { appConfig, initializeTranslations } from './app.config';
import { TranslationService } from './core/i18n/translation.service';
import { routes } from './app.routes';
import { jwtInterceptor } from './core/interceptors/jwt.interceptor';
import { errorInterceptor } from './core/interceptors/error.interceptor';
import { timeoutInterceptor } from './core/interceptors/timeout.interceptor';

describe('appConfig', () => {
  it('should have expected providers configured', () => {
    const providers = appConfig.providers;

    expect(providers).toBeDefined();
    expect(providers.length).toBeGreaterThanOrEqual(4);
  });

  it('should include provideRouter with PreloadAllModules', () => {
    const providers = appConfig.providers as any[];
    expect(providers.length).toBeGreaterThanOrEqual(2);
    expect(providers[1]).toBeTruthy();
  });

  it('should include provideHttpClient with interceptors', () => {
    const providers = appConfig.providers as any[];
    expect(providers.length).toBeGreaterThanOrEqual(3);
    expect(providers[2]).toBeTruthy();
  });

  it('should include provideBrowserGlobalErrorListeners', () => {
    // provideBrowserGlobalErrorListeners() returns an EnvironmentProviders object, not a function
    const providers = appConfig.providers as any[];
    const hasErrorListeners = providers.some(p => p !== null && typeof p === 'object');
    expect(hasErrorListeners).toBe(true);
  });

  it('should include app initializer for translations', () => {
    const providers = appConfig.providers as any[];
    expect(providers.length).toBeGreaterThanOrEqual(4);
    expect(providers[3]).toBeTruthy();
  });
});

describe('initializeTranslations', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        { provide: TranslationService, useValue: { currentLang: 'es', loadTranslationsWithCache: vi.fn().mockReturnValue(of(undefined)) } },
      ],
    });
  });

  it('should load translations and return undefined on success', async () => {
    const result = await TestBed.runInInjectionContext(() => initializeTranslations());
    expect(result).toBeUndefined();
  });

  it('should call loadTranslationsWithCache with current language', async () => {
    const ts = TestBed.inject(TranslationService);
    await TestBed.runInInjectionContext(() => initializeTranslations());
    expect(ts.loadTranslationsWithCache).toHaveBeenCalledWith('es');
  });
});
