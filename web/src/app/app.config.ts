import { ApplicationConfig, provideBrowserGlobalErrorListeners, inject, provideAppInitializer } from '@angular/core';
import { provideRouter, withPreloading, PreloadAllModules } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { routes } from './app.routes';
import { jwtInterceptor } from './core/interceptors/jwt.interceptor';
import { errorInterceptor } from './core/interceptors/error.interceptor';
import { timeoutInterceptor } from './core/interceptors/timeout.interceptor';
import { TranslationService } from './core/i18n/translation.service';
import { firstValueFrom } from 'rxjs';

export function initializeTranslations(): Promise<void> {
  const ts = inject(TranslationService);
  return firstValueFrom(ts.loadTranslationsWithCache(ts.currentLang)).then(() => undefined);
}

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes, withPreloading(PreloadAllModules)),
    provideHttpClient(withInterceptors([jwtInterceptor, errorInterceptor, timeoutInterceptor])),
    provideAppInitializer(initializeTranslations),
  ],
};
