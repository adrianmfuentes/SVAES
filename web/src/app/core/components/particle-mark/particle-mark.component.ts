import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ElementRef,
  afterNextRender,
  inject,
  input,
  viewChild,
} from '@angular/core';

/** One dot of the stipple. `hx`/`hy` is where it belongs in the mark, as a 0..1 fraction of its box. */
export interface Dot {
  hx: number;
  hy: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
  /** ms to wait before the dot starts finding its place (staggers the assembly). */
  delay: number;
  /** 0 = ink, 1 = glacier blue, 2 = faint dust around the mark. */
  tint: number;
  size: number;
}

const INK = '11, 22, 32';
const GLACIER = '29, 78, 118';
const SAMPLE = 320; // px of the offscreen raster the mark is sampled from

/**
 * Picks stipple points from an alpha mask. Pure, so it can be tested without a canvas.
 * `alpha` is a size x size array of 0..255 values; `rand` supplies randomness.
 */
export function pickPoints(
  alpha: ArrayLike<number>,
  size: number,
  density: number,
  rand: () => number,
): { x: number; y: number }[] {
  const points: { x: number; y: number }[] = [];
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      if (alpha[y * size + x] > 128 && rand() < density) {
        // Jitter inside the pixel so the dots do not line up on the raster grid.
        points.push({ x: (x + rand()) / size, y: (y + rand()) / size });
      }
    }
  }
  return points;
}

/**
 * The SVAES mark drawn as a stipple of dots that assemble on load and scatter away from the
 * pointer, then settle back. Decorative (aria-hidden): the real logo is in the header. It listens
 * on its positioned parent so text and buttons above it stay clickable. Under
 * prefers-reduced-motion it paints the assembled mark once and ignores the pointer.
 */
@Component({
  selector: 'app-particle-mark',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: '<canvas #canvas aria-hidden="true"></canvas>',
  styles: [
    `
      :host {
        position: absolute;
        inset: 0;
        display: block;
        pointer-events: none;
        overflow: hidden;
      }
      canvas {
        display: block;
        width: 100%;
        height: 100%;
      }
    `,
  ],
})
export class ParticleMarkComponent {
  /** URL of the SVG the stipple is sampled from. */
  readonly src = input.required<string>();

  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly destroyRef = inject(DestroyRef);
  private readonly canvas = viewChild.required<ElementRef<HTMLCanvasElement>>('canvas');

  constructor() {
    afterNextRender(() => {
      const image = new Image();
      image.onload = () => this.start(image);
      image.src = this.src();
    });
  }

  private start(image: HTMLImageElement): void {
    const canvas = this.canvas().nativeElement;
    const ctx = canvas.getContext('2d');
    const parent = this.host.nativeElement.parentElement;
    if (!ctx || !parent) return;

    // 1. Sample the mark into stipple points.
    const off = document.createElement('canvas');
    off.width = SAMPLE;
    off.height = SAMPLE;
    const octx = off.getContext('2d', { willReadFrequently: true });
    if (!octx) return;
    const pad = SAMPLE * 0.06; // strokes never touch the raster edge
    octx.drawImage(image, pad, pad, SAMPLE - 2 * pad, SAMPLE - 2 * pad);
    const raw = octx.getImageData(0, 0, SAMPLE, SAMPLE).data;
    const alpha = new Uint8Array(SAMPLE * SAMPLE);
    for (let i = 0; i < alpha.length; i++) alpha[i] = raw[i * 4 + 3];
    const points = pickPoints(alpha, SAMPLE, 0.5, Math.random);

    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let width = 0;
    let height = 0;
    let box = { x: 0, y: 0, s: 0 };
    let frame = 0;
    let visible = true;
    let pointer: { x: number; y: number } | null = null;
    let burst = 0;
    let started = performance.now();

    const dots: Dot[] = points.map((p) => ({
      hx: p.x,
      hy: p.y,
      x: 0,
      y: 0,
      vx: 0,
      vy: 0,
      delay: Math.random() * 700,
      tint: Math.random() < 0.14 ? 1 : 0,
      size: 0.9 + Math.random() * 1.1,
    }));
    // Dust: faint dots that wander off the strokes, so the edges read as stipple, not as outline.
    const gauss = (): number => (Math.random() + Math.random() + Math.random() - 1.5) / 1.5;
    for (let i = 0; i < points.length * 0.4; i++) {
      const p = points[Math.floor(Math.random() * points.length)];
      dots.push({
        hx: p.x + gauss() * 0.07,
        hy: p.y + gauss() * 0.07,
        x: 0,
        y: 0,
        vx: 0,
        vy: 0,
        delay: Math.random() * 900,
        tint: 2,
        size: 0.7 + Math.random() * 0.8,
      });
    }

    const layout = (): void => {
      const rect = this.host.nativeElement.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = rect.width;
      height = rect.height;
      canvas.width = Math.max(1, Math.round(width * dpr));
      canvas.height = Math.max(1, Math.round(height * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      if (width < 900) {
        // Stacked layout: the mark sits under the text.
        const s = Math.min(width * 0.78, 320);
        box = { x: (width - s) / 2, y: height - s - 16, s };
      } else {
        const s = Math.min(height * 0.9, width * 0.42, 600);
        box = { x: width * 0.55 + (width * 0.45 - s) / 2, y: (height - s) / 2, s };
      }
      for (const d of dots) {
        if (reduce) {
          d.x = box.x + d.hx * box.s;
          d.y = box.y + d.hy * box.s;
        } else if (d.x === 0 && d.y === 0) {
          // Born scattered across the right two thirds, then drawn in.
          d.x = width * (0.3 + Math.random() * 0.7);
          d.y = Math.random() * height;
        }
      }
    };

    const paint = (): void => {
      ctx.clearRect(0, 0, width, height);
      for (const tint of [2, 0, 1]) {
        ctx.fillStyle =
          tint === 1 ? `rgba(${GLACIER}, 0.9)` : tint === 2 ? `rgba(${INK}, 0.32)` : `rgba(${INK}, 0.82)`;
        for (const d of dots) {
          if (d.tint === tint) ctx.fillRect(d.x, d.y, d.size, d.size);
        }
      }
    };

    const step = (now: number): void => {
      frame = 0;
      const elapsed = now - started;
      const radius = 110;
      for (const d of dots) {
        if (elapsed < d.delay) continue;
        const tx = box.x + d.hx * box.s;
        const ty = box.y + d.hy * box.s;
        let ax = (tx - d.x) * 0.045;
        let ay = (ty - d.y) * 0.045;
        if (pointer) {
          const dx = d.x - pointer.x;
          const dy = d.y - pointer.y;
          const dist = Math.hypot(dx, dy);
          if (dist < radius && dist > 0.01) {
            const push = (1 - dist / radius) * 5.5;
            ax += (dx / dist) * push;
            ay += (dy / dist) * push;
          }
          if (burst > 0 && dist < 260 && dist > 0.01) {
            const push = (1 - dist / 260) * burst;
            ax += (dx / dist) * push;
            ay += (dy / dist) * push;
          }
        }
        // A little unrest, so the settled mark still breathes.
        ax += (Math.random() - 0.5) * 0.05;
        ay += (Math.random() - 0.5) * 0.05;
        d.vx = (d.vx + ax) * 0.84;
        d.vy = (d.vy + ay) * 0.84;
        d.x += d.vx;
        d.y += d.vy;
      }
      burst = Math.max(0, burst - 2);
      paint();
      if (visible && !document.hidden) frame = requestAnimationFrame(step);
    };

    const kick = (): void => {
      if (!frame) frame = requestAnimationFrame(step);
    };

    const local = (event: PointerEvent): { x: number; y: number } => {
      const rect = this.host.nativeElement.getBoundingClientRect();
      return { x: event.clientX - rect.left, y: event.clientY - rect.top };
    };

    const resizeObserver = new ResizeObserver(() => {
      layout();
      if (reduce) paint();
    });
    resizeObserver.observe(this.host.nativeElement);
    layout();

    if (reduce) {
      paint();
    } else {
      const onMove = (e: PointerEvent): void => {
        pointer = local(e);
      };
      const onDown = (e: PointerEvent): void => {
        pointer = local(e);
        burst = 24;
      };
      const onLeave = (): void => {
        pointer = null;
      };
      parent.addEventListener('pointermove', onMove, { passive: true });
      parent.addEventListener('pointerdown', onDown, { passive: true });
      parent.addEventListener('pointerleave', onLeave, { passive: true });
      const io = new IntersectionObserver(([entry]) => {
        visible = entry.isIntersecting;
        if (visible) kick();
      });
      io.observe(this.host.nativeElement);
      const onVisibility = (): void => {
        if (!document.hidden) kick();
      };
      document.addEventListener('visibilitychange', onVisibility);
      started = performance.now();
      kick();

      this.destroyRef.onDestroy(() => {
        parent.removeEventListener('pointermove', onMove);
        parent.removeEventListener('pointerdown', onDown);
        parent.removeEventListener('pointerleave', onLeave);
        document.removeEventListener('visibilitychange', onVisibility);
        io.disconnect();
      });
    }

    this.destroyRef.onDestroy(() => {
      resizeObserver.disconnect();
      if (frame) cancelAnimationFrame(frame);
    });
  }
}
