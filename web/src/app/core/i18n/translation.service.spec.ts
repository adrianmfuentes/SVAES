import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { firstValueFrom } from 'rxjs';
import { TranslationService } from './translation.service';

describe('TranslationService', () => {
  let service: TranslationService;
  let controller: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();

    TestBed.configureTestingModule({
      providers: [
        TranslationService,
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });

    service = TestBed.inject(TranslationService);
    controller = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    controller.verify();
    localStorage.clear();
  });

  describe('currentLang', () => {
    it('should default to es when no stored value', () => {
      expect(service.currentLang).toBe('es');
    });

    it('should update currentLang after setLanguage', () => {
      service.setLanguage('en');
      expect(service.currentLang).toBe('en');
    });
  });

  describe('setLanguage', () => {
    it('should store language and emit new value', () => {
      let emitted = '';
      service.lang$.subscribe((l) => (emitted = l));

      service.setLanguage('en');

      expect(localStorage.getItem('svaes-lang')).toBe('en');
      expect(emitted).toBe('en');
      expect(service.currentLang).toBe('en');
    });

    it('should ignore invalid language codes', () => {
      service.setLanguage('fr');
      expect(service.currentLang).toBe('es');
    });
  });

  describe('loadTranslations', () => {
    it('should GET /assets/i18n/{lang}.json and populate translations', async () => {
      const data = { hello: 'Hola', goodbye: 'Adios' };

      const promise = firstValueFrom(service.loadTranslations('es'));

      const req = controller.expectOne('/assets/i18n/es.json');
      expect(req.request.method).toBe('GET');
      req.flush(data);

      const result = await promise;
      expect(result).toEqual(data);
      expect(service.translateInstant('hello')).toBe('Hola');
      expect(service.translateInstant('goodbye')).toBe('Adios');
    });
  });

  describe('loadTranslationsWithCache', () => {
    it('should return cached translations when available', async () => {
      const cached = { hello: 'Hello cached', world: 'World cached' };
      localStorage.setItem('svaes-i18n-en', JSON.stringify(cached));

      const promise = firstValueFrom(service.loadTranslationsWithCache('en'));

      const result = await promise;
      expect(result).toEqual(cached);
      expect(service.translateInstant('hello')).toBe('Hello cached');

      const bgReq = controller.expectOne('/assets/i18n/en.json');
      bgReq.flush({ hello: 'Updated' });
    });

    it('should fetch and cache when no cache exists', async () => {
      const data = { hello: 'Hola' };

      const promise = firstValueFrom(service.loadTranslationsWithCache('es'));

      const req = controller.expectOne('/assets/i18n/es.json');
      req.flush(data);

      const result = await promise;
      expect(result).toEqual(data);
      expect(localStorage.getItem('svaes-i18n-es')).toBe(JSON.stringify(data));
    });
  });

  describe('translateInstant', () => {
    it('should return translated value for known key', async () => {
      const data = { welcome: 'Bienvenido' };
      const promise = firstValueFrom(service.loadTranslations('es'));
      const req = controller.expectOne('/assets/i18n/es.json');
      req.flush(data);
      await promise;

      expect(service.translateInstant('welcome')).toBe('Bienvenido');
    });

    it('should return key when translation not found', () => {
      expect(service.translateInstant('nonexistent')).toBe('nonexistent');
    });

    it('should interpolate parameters', async () => {
      const data = { greeting: 'Hola {{name}}, tienes {{count}} mensajes' };
      const promise = firstValueFrom(service.loadTranslations('es'));
      const req = controller.expectOne('/assets/i18n/es.json');
      req.flush(data);
      await promise;

      expect(service.translateInstant('greeting', { name: 'Juan', count: 5 })).toBe(
        'Hola Juan, tienes 5 mensajes',
      );
    });
  });

  describe('translate', () => {
    it('should return an observable that emits translation on language change', async () => {
      const data = { hello: 'Hola', hello_en: 'Hello' };
      const p = firstValueFrom(service.loadTranslations('es'));
      const r = controller.expectOne('/assets/i18n/es.json');
      r.flush(data);
      await p;

      const values: string[] = [];
      service.translate('hello').subscribe((v) => values.push(v));

      service.setLanguage('en');

      expect(values).toEqual(['Hola', 'Hola']);
    });
  });
});
