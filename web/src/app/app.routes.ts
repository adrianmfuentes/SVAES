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
        path: 'releases/new',
        canActivate: [businessRouteGuard],
        loadComponent: () =>
          import('./features/releases/release-new/release-new.component').then(
            (m) => m.ReleaseNewComponent,
          ),
      },
      {
        path: 'releases/:id',
        canActivate: [businessRouteGuard],
        loadComponent: () =>
          import('./features/releases/release-detail/release-detail.component').then(
            (m) => m.ReleaseDetailComponent,
          ),
      },
      {
        path: 'releases/:id/edit',
        canActivate: [businessRouteGuard],
        loadComponent: () =>
          import('./features/releases/release-new/release-new.component').then(
            (m) => m.ReleaseNewComponent,
          ),
      },
      {
        path: 'projects',
        canActivate: [businessRouteGuard],
        loadComponent: () =>
          import('./features/projects/projects.component').then(
            (m) => m.ProjectsComponent,
          ),
      },
      {
        path: 'projects/new',
        canActivate: [businessRouteGuard],
        loadComponent: () =>
          import('./features/projects/project-new/project-new.component').then(
            (m) => m.ProjectNewComponent,
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
      {
        path: 'org-settings',
        canActivate: [roleGuard],
        data: { role: 'MANAGER' },
        loadComponent: () =>
          import('./features/organization/org-settings.component').then(
            (m) => m.OrgSettingsComponent,
          ),
      },
      {
        path: 'profile',
        loadComponent: () =>
          import('./features/profile/profile.component').then(
            (m) => m.ProfileComponent,
          ),
      },
      {
        path: '403',
        loadComponent: () =>
          import('./features/errors/forbidden.component').then(
            (m) => m.ForbiddenComponent,
          ),
      },
    ],
  },
  {
    path: 'request-access',
    loadComponent: () =>
      import('./features/access-request/access-request-form.component').then(
        (m) => m.AccessRequestFormComponent,
      ),
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
  {
    path: '**',
    loadComponent: () =>
      import('./features/errors/not-found.component').then(
        (m) => m.NotFoundComponent,
      ),
  },
];
