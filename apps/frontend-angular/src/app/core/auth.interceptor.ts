import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { from, switchMap } from 'rxjs';

import { AuthService } from './auth.service';
import { RuntimeConfigService } from './runtime-config.service';

export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const auth = inject(AuthService);
  const config = inject(RuntimeConfigService).config;
  if (!request.url.startsWith(config.apiUrl)) return next(request);
  return from(auth.accessToken()).pipe(
    switchMap((token) =>
      next(
        token
          ? request.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
          : request,
      ),
    ),
  );
};

