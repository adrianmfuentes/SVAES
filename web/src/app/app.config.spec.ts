import { APP_INITIALIZER } from '@angular/core';
import { appConfig } from './app.config';

describe('appConfig', () => {
  it('should have expected providers configured', () => {
    const providers = appConfig.providers;

    expect(providers).toBeDefined();
    expect(providers.length).toBeGreaterThanOrEqual(4);
  });

  it('should include APP_INITIALIZER for translations', () => {
    const providers = appConfig.providers;

    const initializer = providers.find(
      (p: unknown) => {
        const typed = p as { provide: unknown };
        return typed.provide === APP_INITIALIZER;
      },
    );

    expect(initializer).toBeDefined();
    const asMulti = initializer as unknown as { multi: boolean };
    expect(asMulti.multi).toBe(true);
  });

  it('should include useFactory function in APP_INITIALIZER', () => {
    const providers = appConfig.providers;

    const initializer = providers.find(
      (p: unknown) => {
        const typed = p as { provide: unknown };
        return typed.provide === APP_INITIALIZER;
      },
    );

    expect(initializer).toBeTruthy();

    const useFactory = (initializer as unknown as { useFactory: () => unknown }).useFactory;
    expect(useFactory).toBeDefined();
    expect(typeof useFactory).toBe('function');
  });
});
