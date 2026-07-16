import { writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const required = ['FRONTEND_API_URL', 'SUPABASE_URL', 'SUPABASE_ANON_KEY'];
const missing = required.filter((name) => !process.env[name]);
if (missing.length) {
  throw new Error(`Faltan variables: ${missing.join(', ')}`);
}

const config = {
  apiUrl: process.env.FRONTEND_API_URL,
  supabaseUrl: process.env.SUPABASE_URL,
  supabaseAnonKey: process.env.SUPABASE_ANON_KEY,
  maxPdfSizeMb: Number(process.env.FRONTEND_MAX_PDF_SIZE_MB || 25),
};
const destination = resolve('apps/frontend-angular/src/assets/config.json');
await writeFile(destination, `${JSON.stringify(config, null, 2)}\n`, 'utf8');
console.log(`Configuración pública escrita en ${destination}`);

