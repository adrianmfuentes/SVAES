import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ElementRef,
  afterNextRender,
  effect,
  inject,
  input,
  output,
  viewChild,
} from '@angular/core';

/** One word of a scene (a verdict, drawn big with its mark). */
export interface GlassWord {
  readonly text: string;
  readonly color: string;
  /** Which small mark is drawn before the word. */
  readonly mark: 'check' | 'warn' | 'cross' | 'dash';
}

/** A disc of colour in a scene. */
export interface GlassBlob {
  readonly x: number;
  readonly y: number;
  /** Radius as a fraction of the viewport width. */
  readonly r: number;
  readonly color: string;
  readonly alpha?: number;
}

/**
 * What stands behind the glass for one section of the page: a flat band in the section's own
 * colour plus, optionally, one huge figure or a set of verdict words. `selector` finds the
 * section element, so the scene scrolls with it.
 */
export interface GlassScene {
  readonly selector: string;
  readonly coveredBy?: string;
  readonly ground: string;
  /** A huge, low-contrast figure (a real count from the product), set on the right. */
  readonly art?: string;
  readonly artColor?: string;
  /** Masses of colour behind the glass; the flutes smear them into streaks. x, y, r are fractions of the section width/height. */
  readonly blobs?: readonly GlassBlob[];
  /** Verdict words drawn on the right half of the section. */
  readonly words?: readonly GlassWord[];
  /** How hard the glass bends this section. Lower reads better (default 2.1). */
  readonly squeeze?: number;
  /** How far each flute shifts its slice, as a fraction of its width (default 0.9). */
  readonly pull?: number;
  /** Clarity the glass always has here, 0..1, before any pointer or scroll. */
  readonly rest?: number;
  /** When set, scrolling through the section clears the glass (the page "verifies" as you go). */
  readonly scrollClear?: boolean;
}

/** A scene as laid out on screen this frame. */
interface Band {
  readonly top: number;
  readonly bottom: number;
  readonly squeeze: number;
  readonly pull: number;
  /** Lowest clarity the glass may have inside this band right now. */
  readonly floor: number;
}

/** Geometry of one flute: which slice of the scene it shows and how squeezed it is. */
export interface Flute {
  /** Left edge of the flute on screen, px. */
  readonly x: number;
  /** Left edge of the slice sampled from the scene, px. */
  readonly sx: number;
  /** Width of the slice sampled from the scene, px (wider than the flute = squeezed). */
  readonly sw: number;
}

/**
 * How a ribbed pane bends the scene. Far from the pointer every flute shows a slice `squeeze`
 * times wider than itself, centred on a point pulled `pull` of the way toward the nearest flute
 * edge (the look of fluted glass). Near the pointer `clarity` goes to 1 and the flute shows
 * exactly what is behind it. Pure, so it is testable without a canvas.
 */
export function fluteAt(
  x: number,
  width: number,
  clarity: number,
  squeeze: number,
  pull: number,
): Flute {
  const c = Math.min(1, Math.max(0, clarity));
  const k = 1 + (squeeze - 1) * (1 - c);
  const centre = x + width / 2;
  // Each flute is a small cylindrical lens: its slice is offset from its own centre.
  const offset = (1 - c) * pull * width;
  const sw = width * k;
  return { x, sx: centre + offset - sw / 2, sw };
}

const SQUEEZE = 2.1;
const PULL = 0.9;
const FLUTE = 18; // px per flute
const TILE = 120; // px tall: the glass clears in tiles, so the lens is round, not a column
const RADIUS = 260; // px of the clear lens around the pointer

/**
 * The page itself seen through a pane of fluted glass. A fixed canvas behind the whole landing
 * paints one scene per section (a band in the section colour and a huge figure) and bends it
 * through vertical flutes. Where the pointer is, the glass clears and the scene reads sharp.
 * Decorative (aria-hidden): everything it shows is also real text in the page. Without it
 * (SSR, no canvas) the sections keep their own backgrounds; under prefers-reduced-motion it
 * paints a half-clear pane that follows the scroll but ignores the pointer.
 */
@Component({
  selector: 'app-fluted-glass',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: '<canvas #canvas aria-hidden="true"></canvas>',
  styles: [
    `
      :host {
        position: fixed;
        inset: 0;
        z-index: 0;
        display: block;
        pointer-events: none;
      }
      canvas {
        display: block;
        width: 100%;
        height: 100%;
      }
    `,
  ],
})
export class FlutedGlassComponent {
  readonly scenes = input.required<readonly GlassScene[]>();
  /** Fires once the glass is painted, so the page can let its sections go transparent. */
  readonly ready = output<void>();

  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly destroyRef = inject(DestroyRef);
  private readonly canvas = viewChild.required<ElementRef<HTMLCanvasElement>>('canvas');

  /** Set once the canvas is running; repaints when the scenes change (language switch). */
  private redraw: (() => void) | null = null;

  constructor() {
    effect(() => {
      this.scenes();
      this.redraw?.();
    });
    afterNextRender(() => {
      // Wait for the web fonts so the figures are drawn with the real typeface.
      const fonts = document.fonts?.ready ?? Promise.resolve();
      void fonts.then(() => this.start());
    });
  }

  private start(): void {
    const canvas = this.canvas().nativeElement;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const scene = document.createElement('canvas');
    const sctx = scene.getContext('2d');
    if (!sctx) return;

    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let width = 0;
    let height = 0;
    let dpr = 1;
    let frame = 0;
    let pointer: { x: number; y: number } | null = null;
    let cols = 0;
    let rows = 0;
    let clarity: Float32Array = new Float32Array(0);
    let announced = false;
    let bands: Band[] = [];
    // One flute seen from the front is a half cylinder: a bright specular edge on the left, a clear
    // body, a deepening shadow on the right. Drawn once, stretched over every flute.
    const shade = document.createElement('canvas');
    shade.width = FLUTE * 4;
    shade.height = 1;
    const shx = shade.getContext('2d');
    if (shx) {
      const g = shx.createLinearGradient(0, 0, shade.width, 0);
      g.addColorStop(0, 'rgba(255, 255, 255, 0.62)');
      g.addColorStop(0.14, 'rgba(255, 255, 255, 0.18)');
      g.addColorStop(0.4, 'rgba(255, 255, 255, 0)');
      g.addColorStop(0.72, 'rgba(29, 78, 118, 0.07)');
      g.addColorStop(1, 'rgba(11, 22, 32, 0.24)');
      shx.fillStyle = g;
      shx.fillRect(0, 0, shade.width, 1);
    }
    /** Glass is never perfectly even: a stable, small variation from flute to flute. */
    const grain = (col: number): number => 0.72 + 0.28 * Math.abs(Math.sin(col * 12.9898) * 43758.5453 % 1);

    const drawWords = (words: readonly GlassWord[], top: number, h: number): void => {
      const margin = Math.min(Math.max(width * 0.08, 24), 128); // the page gutter
      const left = Math.max(width * 0.58, margin);
      const face = (px: number): string =>
        `800 ${px}px "Manrope Variable", Manrope, system-ui, sans-serif`;
      // Size to the pane, then shrink until the longest word fits between the mark and the margin.
      let size = Math.min(h / (words.length * 1.9), width * 0.052);
      sctx.font = face(100);
      const widest = Math.max(...words.map((w) => sctx.measureText(w.text).width)) / 100;
      const room = width - left - margin;
      size = Math.min(size, room / (widest + 1.1));
      // A tight stack, centred in the section: the four verdicts read as one list.
      const step = size * 1.75;
      const first = top + h / 2 - (step * (words.length - 1)) / 2;
      sctx.textBaseline = 'middle';
      sctx.textAlign = 'left';
      sctx.font = face(size);
      words.forEach((w, i) => {
        const cy = first + step * i;
        const m = size * 0.34;
        const mx = left;
        sctx.strokeStyle = w.color;
        sctx.fillStyle = w.color;
        sctx.lineWidth = Math.max(3, size * 0.11);
        sctx.lineCap = 'square';
        sctx.beginPath();
        if (w.mark === 'check') {
          sctx.moveTo(mx - m, cy);
          sctx.lineTo(mx - m * 0.25, cy + m * 0.75);
          sctx.lineTo(mx + m, cy - m * 0.8);
        } else if (w.mark === 'cross') {
          sctx.moveTo(mx - m, cy - m);
          sctx.lineTo(mx + m, cy + m);
          sctx.moveTo(mx + m, cy - m);
          sctx.lineTo(mx - m, cy + m);
        } else if (w.mark === 'warn') {
          sctx.moveTo(mx, cy - m);
          sctx.lineTo(mx + m * 1.1, cy + m * 0.9);
          sctx.lineTo(mx - m * 1.1, cy + m * 0.9);
          sctx.closePath();
        } else {
          sctx.moveTo(mx - m, cy);
          sctx.lineTo(mx + m, cy);
        }
        sctx.stroke();
        sctx.fillText(w.text, left + size * 1.1, cy);
      });
    };

    /** Paints what stands behind the glass at the current scroll position. */
    const drawScene = (): void => {
      sctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      sctx.fillStyle = '#f5f8fb';
      sctx.fillRect(0, 0, width, height);
      const laid: Band[] = [];
      for (const s of this.scenes()) {
        const el = document.querySelector(s.selector);
        if (!el) continue;
        const r = el.getBoundingClientRect();
        const edge = s.coveredBy ? document.querySelector(s.coveredBy)?.getBoundingClientRect().top : undefined;
        const bottom = Math.min(r.bottom, edge ?? r.bottom);
        if (bottom <= Math.max(0, r.top) || r.top >= height) continue;
        if (edge !== undefined) {
          sctx.save();
          sctx.beginPath();
          sctx.rect(0, r.top, width, bottom - r.top);
          sctx.clip();
        }
        sctx.fillStyle = s.ground;
        sctx.fillRect(0, r.top, width, r.height);
        if (s.blobs) {
          sctx.save();
          sctx.beginPath();
          sctx.rect(0, r.top, width, r.height);
          sctx.clip();
          for (const b of s.blobs) {
            sctx.globalAlpha = b.alpha ?? 0.5;
            sctx.fillStyle = b.color;
            sctx.beginPath();
            sctx.arc(b.x * width, r.top + b.y * r.height, b.r * width, 0, Math.PI * 2);
            sctx.fill();
          }
          sctx.restore();
        }
        // Scrolling through a "scrollClear" section cleans the glass: the page verifies as you go.
        const through = s.scrollClear ? Math.min(1, Math.max(0, -r.top / (r.height * 0.55))) : 0;
        const rest = s.rest ?? 0;
        laid.push({
          top: r.top,
          bottom,
          squeeze: s.squeeze ?? SQUEEZE,
          pull: s.pull ?? PULL,
          floor: rest + (1 - rest) * through,
        });
        if (s.art) {
          // Clip to the section so a figure never bleeds into its neighbour.
          sctx.save();
          sctx.beginPath();
          sctx.rect(0, r.top, width, r.height);
          sctx.clip();
          const size = Math.min(r.height * 0.95, width * 0.42);
          sctx.font = `800 ${size}px "Manrope Variable", Manrope, system-ui, sans-serif`;
          sctx.textBaseline = 'middle';
          sctx.textAlign = 'right';
          sctx.fillStyle = s.artColor ?? '#e3edf5';
          // Parallax: the figure sits deeper than the text, so it travels slower than the page.
          const mid = r.top + r.height / 2;
          sctx.fillText(s.art, width - width * 0.04, mid + (height / 2 - mid) * 0.3);
          sctx.restore();
        }
        // On narrow screens the verdicts are real text in the page, so the glass does not draw them.
        if (s.words && width >= 1024) drawWords(s.words, r.top, r.height);
        // A sheet that the next one is covering recedes: the glass behind it darkens. Painted here,
        // in the scene, so the sheet sliding over it hides the veil exactly where it covers.
        // A scene may be one part of a sheet: the cover belongs to the section that holds it.
        const sheet = el.closest('section') ?? el;
        const cover = Number.parseFloat(getComputedStyle(sheet).getPropertyValue('--cover')) || 0;
        if (cover > 0) {
          sctx.fillStyle = `rgba(11, 22, 32, ${(0.5 * cover).toFixed(3)})`;
          sctx.fillRect(0, r.top, width, r.height);
        }
        if (edge !== undefined) sctx.restore();
      }
      bands = laid;
    };

    const paint = (): void => {
      drawScene();
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, width, height);
      for (let row = 0; row < rows; row++) {
        const y = row * TILE;
        const h = Math.min(TILE, height - y);
        const cy = y + h / 2;
        const band = bands.find((b) => cy >= b.top && cy < b.bottom);
        for (let col = 0; col < cols; col++) {
          const x = col * FLUTE;
          const w = Math.min(FLUTE, width - x);
          const c = Math.max(clarity[row * cols + col], band?.floor ?? 0);
          const f = fluteAt(x, w, c, band?.squeeze ?? SQUEEZE, band?.pull ?? PULL);
          // An out-of-bounds source would also clip the destination at the last flute.
          const sampleWidth = Math.min(f.sw * dpr, scene.width);
          const sampleX = Math.max(0, Math.min(f.sx * dpr, scene.width - sampleWidth));
          ctx.drawImage(scene, sampleX, y * dpr, sampleWidth, h * dpr, x, y, w, h);
        }
      }
      // Cylinder shading on every flute, varying a little from one to the next.
      for (let col = 0; col < cols; col++) {
        ctx.globalAlpha = grain(col);
        ctx.drawImage(shade, col * FLUTE, 0, FLUTE, height);
      }
      ctx.globalAlpha = 1;
      // Light through the glass: a soft spot where the pointer is.
      if (pointer) {
        const g = ctx.createRadialGradient(pointer.x, pointer.y, 0, pointer.x, pointer.y, RADIUS * 0.9);
        g.addColorStop(0, 'rgba(255, 255, 255, 0.34)');
        g.addColorStop(1, 'rgba(255, 255, 255, 0)');
        ctx.fillStyle = g;
        ctx.fillRect(pointer.x - RADIUS, pointer.y - RADIUS, RADIUS * 2, RADIUS * 2);
      }
      if (!announced) {
        announced = true;
        this.ready.emit();
      }
    };

    const layout = (): void => {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = Math.max(1, Math.round(width * dpr));
      canvas.height = Math.max(1, Math.round(height * dpr));
      scene.width = canvas.width;
      scene.height = canvas.height;
      cols = Math.ceil(width / FLUTE);
      rows = Math.ceil(height / TILE);
      clarity = new Float32Array(cols * rows).fill(reduce ? 0.45 : 0);
      paint();
    };

    const step = (): void => {
      frame = 0;
      let moving = false;
      for (let row = 0; row < rows; row++) {
        const cy = row * TILE + TILE / 2;
        for (let col = 0; col < cols; col++) {
          const cx = col * FLUTE + FLUTE / 2;
          const target = pointer
            ? Math.max(0, 1 - Math.hypot(cx - pointer.x, cy - pointer.y) / RADIUS)
            : 0;
          const i = row * cols + col;
          const next = clarity[i] + (target - clarity[i]) * 0.16;
          if (Math.abs(next - target) > 0.003) moving = true;
          clarity[i] = next;
        }
      }
      paint();
      if (moving) frame = requestAnimationFrame(step);
    };

    const kick = (): void => {
      if (!frame) frame = requestAnimationFrame(step);
    };

    this.redraw = () => paint();
    layout();

    // The scene follows the page: repaint on scroll and whenever the page changes height.
    const onScroll = (): void => kick();
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('sheet-cover', onScroll);
    const ro = new ResizeObserver(() => {
      layout();
    });
    ro.observe(document.documentElement);
    window.addEventListener('resize', layout, { passive: true });

    if (!reduce) {
      const onMove = (e: PointerEvent): void => {
        pointer = { x: e.clientX, y: e.clientY };
        kick();
      };
      const onLeave = (): void => {
        pointer = null;
        kick();
      };
      document.addEventListener('pointermove', onMove, { passive: true });
      document.addEventListener('pointerdown', onMove, { passive: true });
      document.documentElement.addEventListener('pointerleave', onLeave, { passive: true });
      this.destroyRef.onDestroy(() => {
        document.removeEventListener('pointermove', onMove);
        document.removeEventListener('pointerdown', onMove);
        document.documentElement.removeEventListener('pointerleave', onLeave);
      });
    }

    this.destroyRef.onDestroy(() => {
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('sheet-cover', onScroll);
      window.removeEventListener('resize', layout);
      ro.disconnect();
      if (frame) cancelAnimationFrame(frame);
    });
  }
}
