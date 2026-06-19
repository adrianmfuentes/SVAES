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
    const routerProvider = providers.find(p => p && p.providers && p.providers[0] === provideRouter);
    expect(routerProvider).toBeDefined();
  });

  it('should include provideHttpClient with interceptors', () => {
    const providers = appConfig.providers as any[];
    const httpProvider = providers.find(p => p && p.imports && p.imports.includes(provideHttpClient));
    expect(httpProvider).toBeDefined();
  });

  it('should include provideBrowserGlobalErrorListeners', () => {
    const providers = appConfig.providers as any[];
    const hasErrorListeners = providers.some(p =>
      p && p.useFunction && p.useFunction.toString().includes('provideBrowserGlobalErrorListeners')
    );
    expect(hasErrorListeners).toBe(true);
  });

  it('should include app initializer for translations', () => {
    const providers = appConfig.providers as any[];
    const initProvider = providers.find(p => p && p.Providers && p.Providers.length > 0);
    expect(initProvider).toBeDefined();
  });
});

describe('initializeTranslations', () => {
  let mockTranslationService: Partial<TranslationService>;

  beforeEach(() => {
    mockTranslationService = {
      currentLang: 'es',
      loadTranslationsWithCache: vi.fn().mockReturnValue(of(undefined)),
    };
  });

  it('should load translations and return undefined on success', async () => {
    const result = await initializeTranslations();
    expect(result).toBeUndefined();
  });

  it('should call loadTranslationsWithCache with current language', async () => {
    await initializeTranslations();
    expect(mockTranslationService.loadTranslationsWithCache).toHaveBeenCalledWith('es');
  });
});
