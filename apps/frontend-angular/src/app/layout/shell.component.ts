import { ChangeDetectionStrategy, Component } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatToolbarModule } from '@angular/material/toolbar';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { AuthService } from '../core/auth.service';

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [MatButtonModule, MatToolbarModule, RouterLink, RouterLinkActive, RouterOutlet],
  template: `
    <mat-toolbar class="topbar">
      <a class="brand" routerLink="/dashboard">
        <span class="brand-mark">D</span>
        <span>DocuMind</span>
      </a>
      <nav aria-label="Navegación principal">
        <a mat-button routerLink="/dashboard" routerLinkActive="active">Panel</a>
        <a mat-button routerLink="/documents" routerLinkActive="active">Documentos</a>
      </nav>
      <span class="spacer"></span>
      <span class="email">{{ auth.user()?.email }}</span>
      <button mat-stroked-button type="button" (click)="auth.signOut()">Salir</button>
    </mat-toolbar>
    <main class="content"><router-outlet /></main>
  `,
  styles: `
    .topbar { position: sticky; top: 0; z-index: 10; gap: 1rem; background: #fff; color: #14213d; border-bottom: 1px solid #e6eaf1; }
    .brand { display: flex; align-items: center; gap: .65rem; color: inherit; text-decoration: none; font-weight: 750; letter-spacing: -.02em; }
    .brand-mark { display: grid; place-items: center; width: 34px; height: 34px; color: #fff; background: #f97316; border-radius: 10px; }
    nav { display: flex; }
    nav .active { background: #eef2ff; color: #3730a3; }
    .spacer { flex: 1; }
    .email { color: #64748b; font-size: .85rem; }
    .content { width: min(1180px, calc(100% - 2rem)); margin: 0 auto; padding: 2rem 0 4rem; }
    @media (max-width: 720px) { .email { display: none; } .topbar { padding: 0 .75rem; } .brand > span:last-child { display: none; } }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ShellComponent {
  constructor(readonly auth: AuthService) {}
}

