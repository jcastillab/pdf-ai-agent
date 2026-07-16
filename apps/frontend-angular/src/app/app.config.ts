import { APP_INITIALIZER, ApplicationConfig } from '@angular/core';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideRouter } from '@angular/router';

import { routes } from './app.routes';
import { RuntimeConfigService } from './core/runtime-config.service';
import { authInterceptor } from './core/auth.interceptor';

function loadConfig(config: RuntimeConfigService): () => Promise<void> {
  return () => config.load();
}

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),
    provideHttpClient(withInterceptors([authInterceptor])),
    provideAnimationsAsync(),
    {
      provide: APP_INITIALIZER,
      useFactory: loadConfig,
      deps: [RuntimeConfigService],
      multi: true,
    },
  ],
};
