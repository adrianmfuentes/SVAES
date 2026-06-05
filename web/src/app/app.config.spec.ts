import { appConfig } from './app.config';

describe('appConfig', () => {
  it('should have expected providers configured', () => {
    const providers = appConfig.providers;

    expect(providers).toBeDefined();
    expect(providers.length).toBeGreaterThanOrEqual(4);
  });
});
