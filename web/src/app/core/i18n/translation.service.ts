import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, catchError, map, of, tap } from 'rxjs';

const STORAGE_KEY = 'svaes-lang';
const DEFAULT_LANG = 'es';
const I18N_CACHE_PREFIX = 'svaes-i18n-v2-';

@Injectable({ providedIn: 'root' })
export class TranslationService {
  private readonly http = inject(HttpClient);

  private translations = new Map<string, string>();
  private readonly currentLang$ = new BehaviorSubject<string>(this.loadStoredLang());

  readonly lang$ = this.currentLang$.asObservable();

  get currentLang(): string {
    return this.currentLang$.value;
  }

  private loadStoredLang(): string {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored && (stored === 'es' || stored === 'en')) {
        return stored;
      }
    } catch {
      // localStorage not available
    }
    return DEFAULT_LANG;
  }

  setLanguage(lang: string): void {
    if (lang !== 'es' && lang !== 'en') return;
    try {
      localStorage.setItem(STORAGE_KEY, lang);
    } catch {
      // ignore
    }
    this.currentLang$.next(lang);
  }

  loadTranslations(lang: string): Observable<Record<string, string>> {
    return this.http
      .get<Record<string, string>>(`/assets/i18n/${lang}.json`)
      .pipe(
        map((data) => {
          this.translations = new Map(Object.entries(data));
          return data;
        }),
      );
  }

  loadTranslationsWithCache(lang: string): Observable<Record<string, string>> {
    try {
      const raw = localStorage.getItem(`${I18N_CACHE_PREFIX}${lang}`);
      if (raw) {
        const cached = JSON.parse(raw) as Record<string, string>;
        this.translations = new Map(Object.entries(cached));
        this.http.get<Record<string, string>>(`/assets/i18n/${lang}.json`).pipe(
          tap(fresh => {
            try { localStorage.setItem(`${I18N_CACHE_PREFIX}${lang}`, JSON.stringify(fresh)); } catch { /* ignore */ }
          }),
          catchError(() => of({})),
        ).subscribe();
        return of(cached);
      }
    } catch { /* localStorage unavailable */ }
    return this.loadTranslations(lang).pipe(
      tap(data => {
        try { localStorage.setItem(`${I18N_CACHE_PREFIX}${lang}`, JSON.stringify(data)); } catch { /* ignore */ }
      }),
    );
  }

  translateInstant(key: string, params?: Record<string, string | number>): string {
    const raw = this.translations.get(key);
    if (raw === undefined) return key;
    return this.interpolate(raw, params);
  }

  translate(key: string, params?: Record<string, string | number>): Observable<string> {
    return this.currentLang$.pipe(
      map(() => this.translateInstant(key, params)),
    );
  }

  private interpolate(text: string, params?: Record<string, string | number>): string {
    if (!params) return text;
    return text.replace(/\{\{(\w+)\}\}/g, (_, name) =>
      String(params[name] ?? `{{${name}}}`),
    );
  }
}
