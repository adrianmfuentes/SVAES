import { RenderMode, ServerRoute } from '@angular/ssr';

export const serverRoutes: ServerRoute[] = [
  { path: '', renderMode: RenderMode.Prerender },
  { path: 'request-access', renderMode: RenderMode.Prerender },
  { path: 'auth/login', renderMode: RenderMode.Prerender },
  { path: 'legal/aviso-legal', renderMode: RenderMode.Prerender },
  { path: 'legal/privacidad', renderMode: RenderMode.Prerender },
  { path: '**', renderMode: RenderMode.Client },
];
