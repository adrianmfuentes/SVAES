import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { roleGuard } from './core/guards/role.guard';
import { businessRouteGuard } from './core/guards/business-route.guard';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./features/landing/landing.component').then(
        (m) => m.LandingComponent,
      ),
  },
  {
    path: 'auth',
    children: [
      {
        path: 'login',
        loadComponent: () =>
          import('./features/auth/login/login.component').then(
            (m) => m.LoginComponent,
          ),
      },
      {
        path: 'activate',
        loadComponent: () =>
          import(
            './features/auth/activate/activate-account.component'
          ).then((m) => m.ActivateAccountComponent),
      },
      { path: '', redirectTo: 'login', pathMatch: 'full' },
    ],
  },
  {
    path: 'app',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/layout/shell/shell.component').then(
        (m) => m.ShellComponent,
      ),
    children: [
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
      {
        path: 'dashboard',
        canActivate: [businessRouteGuard],
        loadComponent: () =>
          import('./features/dashboard/dashboard.component').then(
            (m) => m.DashboardComponent,
          ),
      },
      {
        path: 'releases',
        canActivate: [businessRouteGuard],
        loadComponent: () =>
          import('./features/releases/releases.component').then(
            (m) => m.ReleasesComponent,
          ),
      },
      {
        path: 'connectors',
        canActivate: [businessRouteGuard],
        loadComponent: () =>
          import('./features/connectors/connectors.component').then(
            (m) => m.ConnectorsComponent,
          ),
      },
      {
        path: 'profiles',
        canActivate: [businessRouteGuard],
        loadComponent: () =>
          import('./features/profiles/profiles.component').then(
            (m) => m.ProfilesComponent,
          ),
      },
      {
        path: 'system',
        canActivate: [roleGuard],
        data: { role: 'ADMIN' },
        loadComponent: () =>
          import('./features/system/system.component').then(
            (m) => m.SystemComponent,
          ),
      },
      {
        path: 'logs',
        canActivate: [roleGuard],
        data: { role: 'ADMIN' },
        loadComponent: () =>
          import('./features/logs/logs.component').then(
            (m) => m.LogsComponent,
          ),
      },
      {
        path: 'admin',
        canActivate: [roleGuard],
        data: { role: 'ADMIN' },
        loadComponent: () =>
          import('./features/admin/admin.component').then(
            (m) => m.AdminComponent,
          ),
      },
    ],
  },
  {
    path: 'legal/aviso-legal',
    loadComponent: () =>
      import('./features/legal/aviso-legal/aviso-legal.component').then(
        (m) => m.AvisoLegalComponent,
      ),
  },
  {
    path: 'legal/privacidad',
    loadComponent: () =>
      import('./features/legal/privacidad/privacidad.component').then(
        (m) => m.PrivacidadComponent,
      ),
  },
  { path: '**', redirectTo: '' },
];
