import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Router } from '@angular/router';

import { AuthService } from '../../core/auth.service';

@Component({
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
  ],
  template: `
    <main class="auth-page">
      <section class="intro">
        <div class="logo">D</div>
        <p class="eyebrow">AGENTE DOCUMENTAL</p>
        <h1>Tus PDF, listos para responder.</h1>
        <p>Extrae texto, aplica OCR, consulta con citas y conserva cada archivo bajo TU control.</p>
        <div class="trust"><span>✓ IA local con Ollama</span><span>✓ Citas por página</span><span>✓ Trazabilidad</span></div>
      </section>
      <mat-card class="login-card">
        <mat-card-header>
          <mat-card-title>{{ registerMode() ? 'Crear cuenta' : 'Iniciar sesión' }}</mat-card-title>
          <mat-card-subtitle>Accede al espacio de documentos</mat-card-subtitle>
        </mat-card-header>
        <mat-card-content>
          <form [formGroup]="form" (ngSubmit)="submit()">
            <mat-form-field appearance="outline">
              <mat-label>Correo</mat-label>
              <input matInput type="email" autocomplete="email" formControlName="email" />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Contraseña</mat-label>
              <input matInput type="password" autocomplete="current-password" formControlName="password" />
              <mat-hint>Mínimo 8 caracteres</mat-hint>
            </mat-form-field>
            @if (message()) { <p class="message" [class.error]="error()">{{ message() }}</p> }
            <button mat-flat-button color="primary" type="submit" [disabled]="form.invalid || loading()">
              @if (loading()) { <mat-spinner diameter="20" /> } @else { {{ registerMode() ? 'Registrarme' : 'Entrar' }} }
            </button>
          </form>
        </mat-card-content>
        <mat-card-actions>
          <button mat-button type="button" (click)="toggleMode()">
            {{ registerMode() ? 'Ya tengo cuenta' : 'Crear una cuenta' }}
          </button>
          <button mat-button type="button" (click)="reset()">Olvidé mi contraseña</button>
        </mat-card-actions>
      </mat-card>
    </main>
  `,
  styles: `
    .auth-page { min-height: 100dvh; display: grid; grid-template-columns: 1.1fr .9fr; align-items: center; gap: clamp(2rem, 8vw, 8rem); width: min(1100px, calc(100% - 2rem)); margin: auto; padding: 2rem 0; }
    .intro { max-width: 620px; }
    .logo { display: grid; place-items: center; width: 48px; height: 48px; color: white; background: #f97316; border-radius: 14px; font-size: 1.5rem; font-weight: 800; }
    .eyebrow { margin: 2rem 0 .7rem; color: #4f46e5; font-weight: 800; letter-spacing: .12em; font-size: .78rem; }
    h1 { margin: 0; max-width: 580px; color: #14213d; font-size: clamp(2.6rem, 6vw, 5rem); line-height: .98; letter-spacing: -.055em; }
    .intro > p:not(.eyebrow) { max-width: 520px; color: #64748b; font-size: 1.1rem; line-height: 1.7; }
    .trust { display: flex; flex-wrap: wrap; gap: .65rem; margin-top: 2rem; }
    .trust span { padding: .55rem .8rem; color: #334155; background: #fff; border: 1px solid #e2e8f0; border-radius: 999px; font-size: .82rem; }
    .login-card { padding: 1rem; border-radius: 24px; box-shadow: 0 24px 70px rgba(15, 23, 42, .12); }
    mat-card-header { margin-bottom: 1.4rem; } mat-card-title { font-size: 1.55rem; }
    form, mat-form-field { display: block; width: 100%; } form { display: grid; gap: .8rem; }
    form > button { min-height: 48px; } mat-spinner { display: inline-block; }
    mat-card-actions { display: flex; justify-content: space-between; }
    .message { color: #166534; padding: .7rem; background: #f0fdf4; border-radius: 8px; } .message.error { color: #991b1b; background: #fef2f2; }
    @media (max-width: 820px) { .auth-page { grid-template-columns: 1fr; padding: 3rem 0; } .intro h1 { font-size: 3rem; } }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LoginComponent {
  readonly registerMode = signal(false);
  readonly loading = signal(false);
  readonly message = signal('');
  readonly error = signal(false);
  readonly form = this.formBuilder.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
  });

  constructor(
    private readonly formBuilder: FormBuilder,
    private readonly auth: AuthService,
    private readonly router: Router,
  ) {}

  toggleMode(): void {
    this.registerMode.update((value) => !value);
    this.message.set('');
  }

  async submit(): Promise<void> {
    if (this.form.invalid) return;
    this.loading.set(true);
    this.message.set('');
    try {
      const { email, password } = this.form.getRawValue();
      if (this.registerMode()) {
        await this.auth.signUp(email, password);
        this.error.set(false);
        this.message.set('Revisa TU correo para confirmar la cuenta.');
      } else {
        await this.auth.signIn(email, password);
        await this.router.navigateByUrl('/dashboard');
      }
    } catch (error) {
      this.error.set(true);
      this.message.set(error instanceof Error ? error.message : 'No fue posible autenticarte');
    } finally {
      this.loading.set(false);
    }
  }

  async reset(): Promise<void> {
    const email = this.form.controls.email.value;
    if (!email) {
      this.message.set('Escribe TU correo primero.');
      this.error.set(true);
      return;
    }
    await this.auth.resetPassword(email);
    this.error.set(false);
    this.message.set('Enviamos el enlace de recuperación.');
  }
}

