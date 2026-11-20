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

/** One disturbance of the water surface. */
interface Drop {
  readonly x: number;
  readonly y: number;
  readonly t0: number;
  /** 0..1: how hard it was hit. Sets how far and how long it travels. */
  readonly amp: number;
}

const RING_COUNT = 5;
const SPEED = 110; // px per second of the leading ring
const BASE_LIFE = 3600; // ms for amp = 1
/** Ring colour per ground: glacier blue on paper, snow on deep water. */
const RING_COLORS = { ink: '63, 120, 168', snow: '226, 238, 247' } as const;

/** Pure ring geometry for a drop at a given age (ms). Exported for tests. */
export function ringsAt(
  age: number,
  amp: number,
): { readonly radius: number; readonly alpha: number }[] {
  const life = BASE_LIFE * (0.55 + 0.45 * amp);
  if (age < 0 || age >= life) return [];
  const t = age / life;
  const front = SPEED * (age / 1000) * (0.8 + 0.4 * amp);
  const rings: { radius: number; alpha: number }[] = [];
  for (let k = 0; k < RING_COUNT; k++) {
    // Rings lag behind the front and spread apart with distance, as real wavetrains do.
    const radius = front - k * (10 + front * 0.06);
    if (radius <= 1) continue;
    const alpha = 0.7 * amp * (1 - t) * (1 - t) * (1 - k / (RING_COUNT + 1)) * 160 / (160 + radius);
    rings.push({ radius, alpha });
  }
  return rings;
}

/**
 * A still water surface that answers the pointer. Decorative: it listens on its positioned
 * parent, draws thin concentric rings (no glow, no fill) and stops drawing when nothing moves.
 * Under prefers-reduced-motion it paints one static frame and ignores the pointer.
 */
@Component({
  selector: 'app-ripple-field',
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
export class RippleFieldComponent {
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly destroyRef = inject(DestroyRef);
  /** Which ground the field sits on: `ink` rings on light paper, `snow` rings on the deep pool. */
  readonly tone = input<'ink' | 'snow'>('ink');
  private readonly canvas = viewChild.required<ElementRef<HTMLCanvasElement>>('canvas');

  constructor() {
    afterNextRender(() => this.start());
  }

  private start(): void {
    const canvas = this.canvas().nativeElement;
    const ctx = canvas.getContext('2d');
    const parent = this.host.nativeElement.parentElement;
    if (!ctx || !parent) return;

    const ringColor = RING_COLORS[this.tone()];
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let drops: Drop[] = [];
    let width = 0;
    let height = 0;
    let dpr = 1;
    let frame = 0;
    let ambientTimer = 0;
    let visible = true;
    let last: { x: number; y: number } | null = null;

    const resize = (): void => {
      const rect = this.host.nativeElement.getBoundingClientRect();
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = rect.width;
      height = rect.height;
      canvas.width = Math.max(1, Math.round(width * dpr));
      canvas.height = Math.max(1, Math.round(height * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.lineWidth = 1;
      if (reduce) paintStatic();
      else draw(performance.now());
    };

    const draw = (now: number): void => {
      frame = 0;
      ctx.clearRect(0, 0, width, height);
      drops = drops.filter((d) => ringsAt(now - d.t0, d.amp).length > 0 || now - d.t0 < 0);
      for (const d of drops) {
        for (const ring of ringsAt(now - d.t0, d.amp)) {
          ctx.strokeStyle = `rgba(${ringColor}, ${ring.alpha.toFixed(3)})`;
          ctx.beginPath();
          ctx.arc(d.x, d.y, ring.radius, 0, Math.PI * 2);
          ctx.stroke();
        }
      }
      if (drops.length > 0) frame = requestAnimationFrame(draw);
    };

    const drop = (x: number, y: number, amp: number): void => {
      drops.push({ x, y, t0: performance.now(), amp });
      if (drops.length > 24) drops.shift();
      if (!frame) frame = requestAnimationFrame(draw);
    };

    const paintStatic = (): void => {
      ctx.clearRect(0, 0, width, height);
      const spots: [number, number][] = [
        [0.78, 0.4],
        [0.62, 0.72],
        [0.9, 0.82],
      ];
      for (const [fx, fy] of spots) {
        for (const ring of ringsAt(1500, 0.7)) {
          ctx.strokeStyle = `rgba(${ringColor}, ${ring.alpha.toFixed(3)})`;
          ctx.beginPath();
          ctx.arc(fx * width, fy * height, ring.radius, 0, Math.PI * 2);
          ctx.stroke();
        }
      }
    };

    const local = (event: PointerEvent): { x: number; y: number } => {
      const rect = this.host.nativeElement.getBoundingClientRect();
      return { x: event.clientX - rect.left, y: event.clientY - rect.top };
    };

    const onMove = (event: PointerEvent): void => {
      const p = local(event);
      // A drop only when the pointer has travelled far enough: a stroke, not a buzz.
      if (last && Math.hypot(p.x - last.x, p.y - last.y) < 56) return;
      last = p;
      drop(p.x, p.y, 0.4);
    };

    const onDown = (event: PointerEvent): void => {
      const p = local(event);
      last = p;
      drop(p.x, p.y, 1);
    };

    const onLeave = (): void => {
      last = null;
    };

    // Now and then the surface stirs by itself, away from the text, so it never looks dead.
    const ambient = (): void => {
      ambientTimer = window.setTimeout(
        () => {
          if (visible && !document.hidden) {
            drop(width * (0.55 + Math.random() * 0.4), height * (0.15 + Math.random() * 0.7), 0.6);
          }
          ambient();
        },
        3200 + Math.random() * 2800,
      );
    };

    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(this.host.nativeElement);
    resize();

    if (!reduce) {
      parent.addEventListener('pointermove', onMove, { passive: true });
      parent.addEventListener('pointerdown', onDown, { passive: true });
      parent.addEventListener('pointerleave', onLeave, { passive: true });
      const io = new IntersectionObserver(([entry]) => {
        visible = entry.isIntersecting;
      });
      io.observe(this.host.nativeElement);
      ambient();
      // First impression: one drop, a beat after load.
      window.setTimeout(() => drop(width * 0.74, height * 0.45, 0.8), 500);

      this.destroyRef.onDestroy(() => {
        parent.removeEventListener('pointermove', onMove);
        parent.removeEventListener('pointerdown', onDown);
        parent.removeEventListener('pointerleave', onLeave);
        io.disconnect();
        window.clearTimeout(ambientTimer);
      });
    }

    this.destroyRef.onDestroy(() => {
      resizeObserver.disconnect();
      if (frame) cancelAnimationFrame(frame);
    });
  }
}
