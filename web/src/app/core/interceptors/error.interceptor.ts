import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { clearAccessToken } from '../services/auth.service';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);

  const isAuthEndpoint =
    req.url.includes('/api/v1/auth/login') ||
    req.url.includes('/api/v1/auth/2fa/verify');

  return next(req).pipe(
    catchError((error) => {
      if (error.status === 401 && !isAuthEndpoint) {
        clearAccessToken();
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        router.navigate(['/auth/login']);
      }
      return throwError(() => error);
    }),
  );
};
