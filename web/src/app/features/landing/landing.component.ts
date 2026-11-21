import { Component, DestroyRef, ElementRef, HostListener, OnInit, afterNextRender, inject, signal, viewChild, viewChildren } from '@angular/core';
import { NgTemplateOutlet } from '@angular/common';
import { RouterModule } from '@angular/router';
import { TranslatePipe } from '../../core/i18n/translate.pipe';
import { LangToggleComponent } from '../../core/components/lang-toggle/lang-toggle.component';
import { SiteFooterComponent } from '../../core/components/site-footer/site-footer.component';
import { FlutedGlassComponent } from '../../core/components/fluted-glass/fluted-glass.component';
import { SeoService } from '../../core/services/seo.service';

/** Sections reachable from the navbar, footer and in-page links. */
export type SectionId = 'que-hace' | 'investigacion';

@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [RouterModule, NgTemplateOutlet, TranslatePipe, LangToggleComponent, SiteFooterComponent, FlutedGlassComponent],
  templateUrl: './landing.component.html',
  styleUrl: './landing.component.scss',
})
export class LandingComponent implements OnInit {
  private readonly seo = inject(SeoService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly scrollProgress = viewChild<ElementRef<HTMLElement>>('scrollProgress');
  private readonly demoSteps = viewChildren<ElementRef<HTMLElement>>('demoStep');
  private readonly demoRoot = viewChild<ElementRef<HTMLElement>>('demoRoot');
  private readonly plates = viewChildren<ElementRef<HTMLElement>>('plate');

  readonly menuOpen = signal(false);
  /** True once the glass backdrop is painted; sections then let it show through. */
  readonly interactiveGlass = signal(false);
  readonly glass = signal(false);
  /** True when the sections stack as sheets (wide screens, motion allowed). */
  readonly stack = signal(false);
  /** True when the demo plays as a scroll-driven 3D scene (any screen size, motion allowed). */
  readonly cinema = signal(false);

  readonly sections: readonly { readonly id: SectionId; readonly labelKey: string }[] = [
    { id: 'que-hace', labelKey: 'landing.nav_product' },
    { id: 'investigacion', labelKey: 'landing.nav_research' },
  ];

  /** The four things SVAES does with a release, in order. */
  readonly stations = ['link', 'read', 'eval', 'decide'] as const;
  readonly demoStepIndex = signal(0);
  readonly announcedDemoStep = signal<(typeof this.stations)[number] | null>(null);

  readonly researchSteps = ['requirement', 'evidence', 'compare', 'result'] as const;

  constructor() {
    // Browser only: sheets stack on wide screens when motion is allowed.
    afterNextRender(() => {
      if (typeof window.matchMedia === 'function') {
        const media = window.matchMedia('(min-width: 64rem) and (hover: hover) and (pointer: fine) and (prefers-reduced-motion: no-preference)');
        const sync = (): void => {
          this.interactiveGlass.set(media.matches);
          if (!media.matches) this.glass.set(false);
        };
        sync();
        media.addEventListener('change', sync);
        this.destroyRef.onDestroy(() => media.removeEventListener('change', sync));
      }
      if (typeof window.matchMedia === 'function') {
        const cine = window.matchMedia('(min-height: 30rem) and (prefers-reduced-motion: no-preference)');
        const syncCinema = (): void => this.cinema.set(cine.matches);
        syncCinema();
        cine.addEventListener('change', syncCinema);
        this.destroyRef.onDestroy(() => cine.removeEventListener('change', syncCinema));
      }
      this.initSheets();
      this.initScrollProgress();
    });
  }

  /**
   * Two sheets, one passing behind the other. The hero sticks under the header while the next one
   * slides over it; `--cover` (0..1) says how much of it the next sheet has already covered, and
   * the CSS uses it to push the sheet back, dim it and fade its content. Sections taller than the
   * viewport stick by their bottom edge instead, so none of their content is lost.
   */
  private initSheets(): void {
    if (typeof window.matchMedia !== 'function') return;
    const media = window.matchMedia(
      '(min-width: 64rem) and (min-height: 35rem) and (prefers-reduced-motion: no-preference)',
    );
    let frame = 0;

    const update = (): void => {
      frame = 0;
      const hero = document.querySelector<HTMLElement>('.hero');
      const rest = document.querySelector<HTMLElement>('.rest');
      const header = document.querySelector<HTMLElement>('.site-header');
      if (!hero || !rest) return;
      const height = window.innerHeight;
      const headerHeight = header?.getBoundingClientRect().height ?? 72;
      const nextTop = rest.getBoundingClientRect().top;
      const top = Math.min(headerHeight, height - hero.offsetHeight);
      const progress = (height - nextTop) / Math.max(1, height - headerHeight);
      const t = Math.min(1, Math.max(0, (progress - 0.15) / 0.85));
      hero.style.top = `${top}px`;
      const overlap = Math.max(0, hero.getBoundingClientRect().bottom - nextTop);
      hero.style.clipPath = `inset(0 0 ${overlap}px)`;
      hero.style.setProperty('--cover', (t * t * (3 - 2 * t)).toFixed(3));
    };
    const reset = (): void => {
      cancelAnimationFrame(frame);
      frame = 0;
      const hero = document.querySelector<HTMLElement>('.hero');
      if (!hero) return;
      hero.style.removeProperty('top');
      hero.style.removeProperty('clip-path');
      hero.style.removeProperty('--cover');
      window.dispatchEvent(new Event('sheet-cover'));
    };
    const schedule = (): void => {
      if (!frame) frame = requestAnimationFrame(update);
    };
    const apply = (): void => {
      this.stack.set(media.matches);
      if (media.matches) {
        window.addEventListener('scroll', schedule, { passive: true, capture: true });
        window.addEventListener('resize', schedule, { passive: true });
        update();
      } else {
        window.removeEventListener('scroll', schedule, true);
        window.removeEventListener('resize', schedule);
        reset();
      }
    };
    // Keyboard users: a sheet that is covered would hide the focus ring (WCAG 2.4.11), so the first
    // Tab turns the stacking off for the rest of the visit and the page reads as plain sections.
    let keyboard = false;
    const onKey = (e: KeyboardEvent): void => {
      if (e.key !== 'Tab' || keyboard) return;
      keyboard = true;
      media.removeEventListener('change', apply);
      window.removeEventListener('scroll', schedule, true);
      window.removeEventListener('resize', schedule);
      this.stack.set(false);
      reset();
    };
    window.addEventListener('keydown', onKey);
    media.addEventListener('change', apply);
    apply();
    this.destroyRef.onDestroy(() => {
      window.removeEventListener('keydown', onKey);
      media.removeEventListener('change', apply);
      window.removeEventListener('scroll', schedule, true);
      window.removeEventListener('resize', schedule);
      if (frame) cancelAnimationFrame(frame);
    });
  }

  selectDemoStep(index: number): void {
    this.demoStepIndex.set(index);
    this.announcedDemoStep.set(this.stations[index]);
    const demo = this.demoRoot()?.nativeElement;
    const pin = demo?.querySelector<HTMLElement>('.demo__pin');
    if (!this.cinema() || !demo || !pin) return;
    const range = demo.offsetHeight - pin.offsetHeight;
    if (range <= 0) return;
    const headerBottom = document.querySelector<HTMLElement>('.site-header')?.getBoundingClientRect().bottom ?? 0;
    const top = demo.getBoundingClientRect().top + window.scrollY - headerBottom;
    this.demoLock = index;
    window.scrollTo({ top: top + (index / (this.stations.length - 1)) * range, behavior: this.scrollBehavior() });
  }

  /** Index being scrolled to after a click; scroll-driven selection is paused until it arrives. */
  private demoLock: number | null = null;

  /**
   * The demo is a tall track with a sticky pin. `--s` on `.demo` is the scroll progress through that
   * track mapped to 0..3; `--a` on each plate is how close the camera is to it (1 = in focus).
   * Returns the progress (0..3) or null when there is nothing to drive.
   */
  private driveStage(headerBottom: number): number | null {
    const demo = this.demoRoot()?.nativeElement;
    const pin = demo?.querySelector<HTMLElement>('.demo__pin');
    if (!demo || !pin) return null;
    const range = demo.offsetHeight - pin.offsetHeight;
    if (range <= 0) return null;
    const last = this.demoSteps().length - 1;
    const p = Math.min(1, Math.max(0, (headerBottom - demo.getBoundingClientRect().top) / range));
    const target = p * last;
    this.stageTarget = target;
    this.stageDemo = demo;
    if (!this.stageFrame) this.stageFrame = requestAnimationFrame(this.stageTick);
    this.bindStagePointer(pin);
    return target;
  }

  private stageTarget = 0;
  private stageCurrent = 0;
  private stageFrame = 0;
  private stageDemo: HTMLElement | null = null;

  /** The camera chases the scroll position, so it glides instead of stepping with the wheel. */
  private readonly stageTick = (): void => {
    this.stageFrame = 0;
    const demo = this.stageDemo;
    if (!demo) return;
    this.stageCurrent += (this.stageTarget - this.stageCurrent) * 0.12;
    const settled = Math.abs(this.stageTarget - this.stageCurrent) < 0.002;
    const s = settled ? this.stageTarget : this.stageCurrent;
    this.stageCurrent = s;
    demo.style.setProperty('--s', s.toFixed(3));
    this.plates().forEach(({ nativeElement }, i) => {
      nativeElement.style.setProperty('--a', Math.max(0, 1 - Math.abs(s - i)).toFixed(3));
      nativeElement.style.setProperty('--p', Math.min(1, Math.max(0, s - i)).toFixed(3));
    });
    if (!settled) this.stageFrame = requestAnimationFrame(this.stageTick);
  };

  private stagePointerBound = false;

  /** Pointer tilt, eased in a rAF loop that stops once it has settled. */
  private bindStagePointer(stage: HTMLElement): void {
    if (this.stagePointerBound) return;
    this.stagePointerBound = true;
    const target = { x: 0, y: 0 };
    const now = { x: 0, y: 0 };
    let frame = 0;
    const tick = (): void => {
      now.x += (target.x - now.x) * 0.1;
      now.y += (target.y - now.y) * 0.1;
      stage.style.setProperty('--rx', now.x.toFixed(3));
      stage.style.setProperty('--ry', now.y.toFixed(3));
      frame = Math.abs(target.x - now.x) + Math.abs(target.y - now.y) > 0.002 ? requestAnimationFrame(tick) : 0;
    };
    const kick = (): void => {
      if (!frame) frame = requestAnimationFrame(tick);
    };
    const move = (e: PointerEvent): void => {
      const r = stage.getBoundingClientRect();
      target.x = ((e.clientX - r.left) / Math.max(1, r.width)) * 2 - 1;
      target.y = ((e.clientY - r.top) / Math.max(1, r.height)) * 2 - 1;
      kick();
    };
    const leave = (): void => {
      target.x = 0;
      target.y = 0;
      kick();
    };
    stage.addEventListener('pointermove', move);
    stage.addEventListener('pointerleave', leave);
    this.destroyRef.onDestroy(() => {
      stage.removeEventListener('pointermove', move);
      stage.removeEventListener('pointerleave', leave);
      cancelAnimationFrame(frame);
    });
  }

  private initScrollProgress(): void {
    const indicator = this.scrollProgress()?.nativeElement;
    const root = document.scrollingElement;
    if (!indicator || !root) return;

    const header = indicator.closest('.site-header');
    let lastScrollStep = -1;
    let lastScrollTop = root.scrollTop;
    let frame: number | undefined;
    const update = (): void => {
      frame = undefined;
      const distance = root.scrollHeight - root.clientHeight;
      const fraction = distance > 0 ? Math.min(1, Math.max(0, root.scrollTop / distance)) : 0;
      indicator.style.transform = `scaleX(${fraction})`;

      if (this.cinema()) {
        const headerBottom = header?.getBoundingClientRect().bottom ?? 0;
        const s = this.driveStage(headerBottom);
        const index = s === null ? -1 : Math.round(s);
        if (this.demoLock !== null && s !== null && Math.abs(s - this.demoLock) < 0.08) this.demoLock = null;

        if (root.scrollTop !== lastScrollTop && this.demoLock === null) {
          // A click stays selected until scrolling crosses into another step.
          if (index >= 0 && index !== lastScrollStep) this.demoStepIndex.set(index);
          lastScrollStep = index;
        }
      }
      lastScrollTop = root.scrollTop;
    };
    const schedule = (): void => {
      frame ??= requestAnimationFrame(update);
    };

    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', schedule);
    const landing = indicator.closest('.landing');
    const observer = landing && typeof ResizeObserver !== 'undefined' ? new ResizeObserver(schedule) : null;
    if (observer && landing) observer.observe(landing);
    update();

    this.destroyRef.onDestroy(() => {
      window.removeEventListener('scroll', schedule);
      window.removeEventListener('resize', schedule);
      observer?.disconnect();
      cancelAnimationFrame(this.stageFrame);
      if (frame !== undefined) cancelAnimationFrame(frame);
    });
  }

  ngOnInit(): void {
    this.seo.setPage({
      title: 'SVAES | Verificación Automática de Entregas',
      fullTitle: true,
      description:
        'Antes de publicar una versión, SVAES comprueba que sus tareas, código y documentos existen, están completos y encajan entre sí, y guarda el motivo de cada decisión.',
      path: '/',
    });

    this.seo.setJsonLd({
      '@context': 'https://schema.org',
      '@type': 'SoftwareApplication',
      name: 'SVAES',
      alternateName: 'Sistema de Verificación Automática de Entregas',
      applicationCategory: 'BusinessApplication',
      operatingSystem: 'Web',
      url: 'https://svaes.adrianmf.dev/',
      description:
        'Sistema de verificación automática de entregas: conecte sus herramientas de desarrollo, defina reglas de verificación y obtenga trazabilidad completa de cada release.',
    });
  }

  /** The logo on the home page scrolls to the top instead of reloading. */
  goTop(event: Event): void {
    event.preventDefault();
    this.menuOpen.set(false);
    window.scrollTo({ top: 0, behavior: this.scrollBehavior() });
    document.getElementById('main-content')?.focus({ preventScroll: true });
    history.replaceState(null, '', '/');
  }

  toggleMenu(): void {
    this.menuOpen.update((open) => !open);
  }

  @HostListener('document:keydown.escape')
  closeMenu(): void {
    this.menuOpen.set(false);
  }

  /**
   * Scrolls to a section and moves keyboard focus to its heading, so screen-reader
   * and keyboard users land where the visual jump takes them (WCAG 2.4.3).
   */
  goTo(id: string, event: Event): void {
    event.preventDefault();
    this.menuOpen.set(false);

    const target = document.getElementById(id);
    if (!target) return;

    target.scrollIntoView({ behavior: this.scrollBehavior(), block: 'start' });
    target.focus({ preventScroll: true });
    history.replaceState(null, '', `#${id}`);
  }

  private scrollBehavior(): ScrollBehavior {
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
    return reduce ? 'auto' : 'smooth';
  }
}
