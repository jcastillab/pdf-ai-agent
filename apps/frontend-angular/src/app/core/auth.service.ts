import { Injectable, computed, signal } from '@angular/core';
import { Router } from '@angular/router';
import { AuthChangeEvent, Session, SupabaseClient, User, createClient } from '@supabase/supabase-js';

import { RuntimeConfigService } from './runtime-config.service';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly client: SupabaseClient;
  private readonly userSignal = signal<User | null>(null);
  private initialized = false;

  readonly user = this.userSignal.asReadonly();
  readonly authenticated = computed(() => this.userSignal() !== null);

  constructor(config: RuntimeConfigService, private readonly router: Router) {
    const runtime = config.config;
    this.client = createClient(runtime.supabaseUrl, runtime.supabaseAnonKey, {
      auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
    });
    this.client.auth.onAuthStateChange((_event: AuthChangeEvent, session: Session | null) => {
      this.userSignal.set(session?.user ?? null);
    });
  }

  async initialize(): Promise<void> {
    if (this.initialized) return;
    const { data } = await this.client.auth.getSession();
    this.userSignal.set(data.session?.user ?? null);
    this.initialized = true;
  }

  async signIn(email: string, password: string): Promise<void> {
    const { error } = await this.client.auth.signInWithPassword({ email, password });
    if (error) throw error;
  }

  async signUp(email: string, password: string): Promise<void> {
    const { error } = await this.client.auth.signUp({ email, password });
    if (error) throw error;
  }

  async resetPassword(email: string): Promise<void> {
    const { error } = await this.client.auth.resetPasswordForEmail(email, {
      redirectTo: `${location.origin}/login`,
    });
    if (error) throw error;
  }

  async signOut(): Promise<void> {
    await this.client.auth.signOut();
    await this.router.navigateByUrl('/login');
  }

  async accessToken(): Promise<string | null> {
    const { data } = await this.client.auth.getSession();
    return data.session?.access_token ?? null;
  }
}

