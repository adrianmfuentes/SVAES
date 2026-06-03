import { HttpInterceptorFn } from '@angular/common/http';
import { timeout } from 'rxjs';

const REQUEST_TIMEOUT_MS = 30_000;

export const timeoutInterceptor: HttpInterceptorFn = (req, next) =>
  next(req).pipe(timeout(REQUEST_TIMEOUT_MS));
