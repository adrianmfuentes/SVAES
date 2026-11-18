/**
 * Hero animation: release artifacts travel along ten lanes and enter the
 * verification record. Each lane lines up with a row of the record and each
 * arrival is timed to the moment that row's result appears (the CSS
 * animation-delay on the rows: INTRO_START + index * INTRO_STEP seconds).
 * After the intro a quieter ambient flow keeps running.
 *
 * Decorative only: it is hidden from assistive tech, never runs under
 * prefers-reduced-motion, pauses when off-screen or in a background tab, and
 * stays off on narrow screens where the record sits below the title.
 */

const INTRO_START = 0.5; // seconds, keep in sync with `.acta tbody tr` delay
const INTRO_STEP = 0.2; // seconds, keep in sync with `.acta tbody tr` delay
const TRAVEL = 1.15; // seconds an intro particle travels before arriving
const MIN_WIDTH = 1024;
const LANE = 190; // px: length of each lane, in the gap left of the record

const INK = '13, 15, 18';
const SAND = '184, 160, 106';
const AMBER = '140, 98, 0';

interface Lane {
  y: number;
}

interface Particle {
  lane: number;
  arrive: number; // time (s) at which it reaches the record edge
  speed: number; // px/s
  warn: boolean;
  intro: boolean;
}

export class HeroFlow {
  private readonly ctx: CanvasRenderingContext2D | null;
  private readonly media = window.matchMedia('(prefers-reduced-motion: reduce)');
  private readonly resizeObserver: ResizeObserver;
  private readonly visibility: IntersectionObserver;

  private lanes: Lane[] = [];
  private particles: Particle[] = [];
  private gateX = 0;
  private width = 0;
  private height = 0;
  private dpr = 1;

  private raf = 0;
  private start = 0;
  private visible = true;
  private nextAmbient = 3.4;

  constructor(
    private readonly canvas: HTMLCanvasElement,
    private readonly record: HTMLElement,
  ) {
    this.ctx = canvas.getContext('2d');
    this.resizeObserver = new ResizeObserver(() => this.layout());
    this.resizeObserver.observe(canvas);
    this.resizeObserver.observe(record);
    this.visibility = new IntersectionObserver(([entry]) => {
      this.visible = entry.isIntersecting;
      this.sync();
    });
    this.visibility.observe(canvas);
    document.addEventListener('visibilitychange', this.sync);
    this.media.addEventListener('change', this.sync);
    this.layout();
  }

  destroy(): void {
    cancelAnimationFrame(this.raf);
    this.resizeObserver.disconnect();
    this.visibility.disconnect();
    document.removeEventListener('visibilitychange', this.sync);
    this.media.removeEventListener('change', this.sync);
  }

  private get enabled(): boolean {
    return !!this.ctx && !this.media.matches && this.width >= MIN_WIDTH;
  }

  private readonly sync = (): void => {
    cancelAnimationFrame(this.raf);
    this.raf = 0;
    if (!this.enabled) {
      this.ctx?.clearRect(0, 0, this.canvas.width, this.canvas.height);
      return;
    }
    if (this.visible && !document.hidden) {
      this.start = performance.now() - this.elapsedBeforePause();
      this.raf = requestAnimationFrame(this.frame);
    }
  };

  private pausedAt = 0;
  private elapsedBeforePause(): number {
    return this.pausedAt;
  }

  private layout(): void {
    const box = this.canvas.getBoundingClientRect();
    if (box.width === 0 || box.height === 0) return; // not laid out (yet): keep the last good state
    this.width = box.width;
    this.height = box.height;
    this.dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = Math.round(box.width * this.dpr);
    const h = Math.round(box.height * this.dpr);
    if (this.canvas.width !== w) this.canvas.width = w;
    if (this.canvas.height !== h) this.canvas.height = h;

    const rows = Array.from(this.record.querySelectorAll<HTMLElement>('tbody tr'));
    this.lanes = rows.map((row) => {
      const r = row.getBoundingClientRect();
      return { y: r.top - box.top + r.height / 2 };
    });
    this.gateX = this.record.getBoundingClientRect().left - box.left;

    if (!this.particles.length) this.seedIntro();
    this.sync();
  }

  private seedIntro(): void {
    this.particles = this.lanes.map((_, i) => ({
      lane: i,
      arrive: INTRO_START + i * INTRO_STEP,
      speed: 0, // derived from TRAVEL
      warn: i === 5 || i === 8, // RV-06 and RV-09 end as warnings in the sample record
      intro: true,
    }));
  }

  private readonly frame = (now: number): void => {
    const ctx = this.ctx;
    if (!ctx) return;
    const t = (now - this.start) / 1000;
    this.pausedAt = now - this.start;

    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    ctx.clearRect(0, 0, this.width, this.height);

    // Lanes: short rules in the gap, fading in from the left, dashes flowing to the record.
    const laneStart = Math.max(0, this.gateX - LANE);
    const rule = ctx.createLinearGradient(laneStart, 0, this.gateX, 0);
    rule.addColorStop(0, `rgba(${INK}, 0)`);
    rule.addColorStop(1, `rgba(${INK}, 0.3)`);
    ctx.lineWidth = 1;
    ctx.setLineDash([2, 9]);
    ctx.lineDashOffset = -t * 16;
    ctx.strokeStyle = rule;
    for (const lane of this.lanes) {
      ctx.beginPath();
      ctx.moveTo(laneStart, lane.y + 0.5);
      ctx.lineTo(this.gateX, lane.y + 0.5);
      ctx.stroke();
    }
    ctx.setLineDash([]);

    // Ambient particles once the intro has played.
    if (t > this.nextAmbient && this.lanes.length) {
      const lane = Math.floor(Math.random() * this.lanes.length);
      const speed = 160 + Math.random() * 120;
      this.particles.push({
        lane,
        arrive: t + LANE / speed,
        speed,
        warn: Math.random() < 0.15,
        intro: false,
      });
      this.nextAmbient = t + 0.45 + Math.random() * 0.7;
    }

    const introSpeed = LANE / TRAVEL;
    this.particles = this.particles.filter((p) => t < p.arrive + 0.5);

    for (const p of this.particles) {
      const lane = this.lanes[p.lane];
      if (!lane) continue;
      const speed = p.intro ? introSpeed : p.speed;
      const dt = p.arrive - t;
      const x = this.gateX - dt * speed;

      if (dt > 0 && x > this.gateX - LANE) {
        const fade = Math.min(1, (x - (this.gateX - LANE)) / 50);
        this.drawParticle(ctx, x, lane.y, (p.intro ? 1 : 0.55) * fade, p.warn && dt < 0.25);
      } else if (dt <= 0) {
        this.drawFlash(ctx, lane.y, -dt / 0.5, p.warn);
      }
    }

    this.raf = requestAnimationFrame(this.frame);
  };

  private drawParticle(ctx: CanvasRenderingContext2D, x: number, y: number, alpha: number, warn: boolean): void {
    const colour = warn ? AMBER : INK;
    const trail = ctx.createLinearGradient(x - 70, 0, x, 0);
    trail.addColorStop(0, `rgba(${colour}, 0)`);
    trail.addColorStop(1, `rgba(${colour}, ${0.4 * alpha})`);
    ctx.fillStyle = trail;
    ctx.fillRect(x - 70, y - 1, 70, 2);
    ctx.fillStyle = `rgba(${colour}, ${0.9 * alpha})`;
    ctx.fillRect(x - 3, y - 3, 6, 6);
  }

  private drawFlash(ctx: CanvasRenderingContext2D, y: number, progress: number, warn: boolean): void {
    const k = Math.min(Math.max(progress, 0), 1);
    const eased = 1 - Math.pow(1 - k, 3);
    const colour = warn ? AMBER : SAND;
    const h = 34 * (0.35 + eased * 0.65);
    const g = ctx.createLinearGradient(this.gateX - 90 * eased, 0, this.gateX, 0);
    g.addColorStop(0, `rgba(${colour}, 0)`);
    g.addColorStop(1, `rgba(${colour}, ${0.5 * (1 - k)})`);
    ctx.fillStyle = g;
    ctx.fillRect(this.gateX - 90 * eased, y - h / 2, 90 * eased, h);
  }
}
