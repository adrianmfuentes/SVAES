import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';

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
        loadComponent: () =>
          import('./features/dashboard/dashboard.component').then(
            (m) => m.DashboardComponent,
          ),
      },
      {
        path: 'releases',
        loadComponent: () =>
          import('./features/releases/releases.component').then(
            (m) => m.ReleasesComponent,
          ),
      },
      {
        path: 'connectors',
        loadComponent: () =>
          import('./features/connectors/connectors.component').then(
            (m) => m.ConnectorsComponent,
          ),
      },
      {
        path: 'profiles',
        loadComponent: () =>
          import('./features/profiles/profiles.component').then(
            (m) => m.ProfilesComponent,
          ),
      },
    ],
  },
  { path: '**', redirectTo: '' },
];
