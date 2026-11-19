import { Injectable } from '@angular/core';
import { PreloadingStrategy, Route } from '@angular/router';
import { Observable, of, timer, mergeMap } from 'rxjs';

/**
 * Preloads only the routes flagged `data: { preload: true }`, a few seconds after the first
 * render. Preloading every lazy chunk (the old behaviour) downloaded and parsed the whole
 * application behind a public landing page.
 */
@Injectable({ providedIn: 'root' })
export class SelectivePreloadStrategy implements PreloadingStrategy {
  preload(route: Route, load: () => Observable<unknown>): Observable<unknown> {
    if (!route.data?.['preload']) return of(null);
    return timer(3000).pipe(mergeMap(() => load()));
  }
}
