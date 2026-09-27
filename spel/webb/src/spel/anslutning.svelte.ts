// Förbindelsen med servern: REST för att skapa och lista partier, en WebSocket per enhet i ett parti.
// Läget (vad servern skickar) är reaktivt, så sidorna ritas om när något händer.

export interface Alternativ { text: string; detalj?: string; kod: unknown; bild?: string; typ?: string; kort?: Kortvy }
export interface Vy {
  typ: 'janej' | 'val' | 'flerval' | 'tal' | 'pussel' | 'markexpansion' | 'forslag' | 'fasspel' | 'kast';
  tarning?: string;
  rubrik: string;
  kvarter?: string | null;
  forslag_text?: string;
  alternativ?: Alternativ[];
  min?: number;
  max?: number;
  sok?: boolean;
  mark?: [number, number][];
  grundmark?: [number, number][];
  projekt?: { namn: string; typ: string; form: [number, number][] }[];
  form?: [number, number][];
  platser?: [number, number][][];
  id?: string;                          // den nya markexpansionens id
  valda?: number[];                     // förvalda alternativ (flerval)
  hjalp?: string;
  konsekvens?: string;                  // vad som händer om man svarar nej (händelsekort)
  kort?: Kortvy;                        // kortet frågan gäller
  ja?: string;
  nej?: string;
  markbitar?: { id: string; form: [number, number][]; celler: [number, number][] }[];
}
export interface Visning {
  nr: number; typ: 'tarning' | 'kort'; kvarter: string | null; skede: string | null;
  sidor?: number; varde?: number; lek?: string; grupp?: string | null;
  kort?: Kortvy;
}
export interface Kortvy { id: string; rubrik: string; text: string; typ: string; rader: [string, string][]; bild?: string; lek?: string }
export interface Ledare {
  skede: string; steg: { id: string; namn: string }[]; nu: string; plats: string; gor: string; regler: string[]; tur?: string;
}
export interface Fraga { nr: number; kanal: 'beslut' | 'slump' | 'kast'; kvarter: string | null; skede: string | null; vy: Vy; min: boolean }
export interface Lage {
  rum: string;
  slump: 'digital' | 'inmatad';
  kvarter: { namn: string; styrning: string }[];
  bild: Bild | null;
  fraga: Fraga | null;
  svar: { nr: number; kvarter: string; rubrik: string; svar: string }[];
  drag: string[];                       // senaste tärningsslag och dragna kort
  bordet?: Visning[];
  ledare?: Ledare | null;                // spelledaren: steg, vad som görs nu, regler                   // samma, med kortens innehåll (för bordet på skärmen)
  klart: boolean;
  resultat: Record<string, unknown>[] | null;
  fel: string | null;
}
export interface Bild {
  skede: string;
  namn: string;
  kvartal?: number;
  fas?: string | null;
  faser?: string[][];
  yield?: Record<string, number>;
  yieldbana?: Record<string, number[]>;
  startyield?: Record<string, number>;
  handelser: string[];
  kvarter: Record<string, any>[];
  projektbank?: string[];
  fas_kort?: Kortvy;
  marknad?: Record<string, any>[];
}

export type Svar = { val: number } | { flera: number[] } | { svar: boolean | number } | { placering: unknown[]; mark?: unknown[] } | { mark: unknown[] } | { forslag: true };

const bas = () => (import.meta.env.DEV ? '' : '');

export async function skapaParti(kropp: unknown): Promise<string> {
  const r = await fetch(`${bas()}/api/rum`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(kropp) });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail ?? `Servern svarade ${r.status}`);
  return (await r.json()).id;
}

export async function listaPartier(): Promise<{ id: string; kvarter: string[]; slump: string; svarighet?: string; klart: boolean; skede?: string; skapad: number }[]> {
  const r = await fetch(`${bas()}/api/rum`);
  return r.ok ? r.json() : [];
}

export async function raderaParti(id: string): Promise<void> {
  const r = await fetch(`${bas()}/api/rum/${encodeURIComponent(id)}`, { method: 'DELETE' });
  if (!r.ok && r.status !== 404) throw new Error(`Servern svarade ${r.status}`);
}

/** Spela ett handkort: det spelas när nästa station på spiralen börjar. */
export async function spelaKort(id: string, kvarter: string, kort: string): Promise<void> {
  const r = await fetch(`${bas()}/api/rum/${encodeURIComponent(id)}/kort`, {
    method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ kvarter, kort }) });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail ?? `Servern svarade ${r.status}`);
}

/** Datorn spelar kvarteret från och med nu (om ingen anslöt som det). */
export async function latDatorn(id: string, kvarter: string): Promise<void> {
  const r = await fetch(`${bas()}/api/rum/${encodeURIComponent(id)}/datorn`, {
    method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ kvarter }) });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail ?? `Servern svarade ${r.status}`);
}

export async function hamtaLage(id: string): Promise<Lage | null> {
  const r = await fetch(`${bas()}/api/rum/${encodeURIComponent(id)}`);
  return r.ok ? r.json() : null;
}

/** En enhets förbindelse med ett parti. Återansluter själv om nätet går. */
export class Anslutning {
  lage = $state<Lage | null>(null);
  status = $state<'ansluter' | 'ansluten' | 'borta'>('ansluter');
  raderat = $state(false);
  fel = $state('');
  skickar = $state(false);
  #ws: WebSocket | null = null;
  #stangd = false;
  #forsok = 0;

  constructor(public id: string, public kvarter: string) {
    this.#oppna();
  }

  #oppna() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${proto}://${location.host}/ws/${encodeURIComponent(this.id)}/${encodeURIComponent(this.kvarter)}`);
    this.#ws = ws;
    this.status = 'ansluter';
    ws.onopen = () => { this.status = 'ansluten'; this.#forsok = 0; };
    ws.onmessage = e => {
      const msg = JSON.parse(e.data);
      if (msg.typ === 'lage') { this.lage = msg; this.skickar = false; this.fel = ''; }
      else if (msg.typ === 'fel') { this.fel = msg.text; this.skickar = false; }
      else if (msg.typ === 'raderat') { this.raderat = true; this.stang(); }
    };
    ws.onclose = () => {
      this.status = 'borta';
      if (this.#stangd) return;
      const vanta = Math.min(8000, 500 * 2 ** this.#forsok++);
      setTimeout(() => !this.#stangd && this.#oppna(), vanta);
    };
  }

  svara(nr: number, svar: Svar) {
    if (!this.#ws || this.#ws.readyState !== WebSocket.OPEN) { this.fel = 'Ingen förbindelse med servern just nu.'; return; }
    this.skickar = true;
    this.fel = '';
    this.#ws.send(JSON.stringify({ typ: 'svar', nr, svar }));
  }

  stang() {
    this.#stangd = true;
    this.#ws?.close();
  }
}
