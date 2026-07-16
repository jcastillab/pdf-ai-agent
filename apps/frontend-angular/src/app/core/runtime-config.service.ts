import { Injectable } from '@angular/core';

export interface RuntimeConfig {
  apiUrl: string;
  supabaseUrl: string;
  supabaseAnonKey: string;
  maxPdfSizeMb: number;
}

@Injectable({ providedIn: 'root' })
export class RuntimeConfigService {
  private value?: RuntimeConfig;

  async load(): Promise<void> {
    const response = await fetch('/assets/config.json', { cache: 'no-store' });
    if (!response.ok) {
      throw new Error('No se encontró assets/config.json');
    }
    this.value = (await response.json()) as RuntimeConfig;
  }

  get config(): RuntimeConfig {
    if (!this.value) {
      throw new Error('La configuración aún no está cargada');
    }
    return this.value;
  }
}

