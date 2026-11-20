import { Component, DestroyRef, ElementRef, HostListener, OnInit, afterNextRender, inject, signal, viewChild } from '@angular/core';
import { RouterModule } from '@angular/router';
import { TranslatePipe } from '../../core/i18n/translate.pipe';
import { LangToggleComponent } from '../../core/components/lang-toggle/lang-toggle.component';
import { SiteFooterComponent } from '../../core/components/site-footer/site-footer.component';
import { FlutedGlassComponent } from '../../core/components/fluted-glass/fluted-glass.component';
import { SeoService } from '../../core/services/seo.service';

interface ConnectorGroup {
  readonly labelKey: string;
  readonly items: readonly string[];
}

/** Sections reachable from the navbar, footer and in-page links. */
export type SectionId = 'que-hace' | 'conectores' | 'investigacion';

@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [RouterModule, TranslatePipe, LangToggleComponent, SiteFooterComponent, FlutedGlassComponent],
  templateUrl: './landing.component.html',
  styleUrl: './landing.component.scss',
})
export class LandingComponent implements OnInit {
  private readonly seo = inject(SeoService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly scrollProgress = viewChild<ElementRef<HTMLElement>>('scrollProgress');

  readonly menuOpen = signal(false);
  /** True once the glass backdrop is painted; sections then let it show through. */
  readonly glass = signal(false);
  /** True when the sections stack as sheets (wide screens, motion allowed). */
  readonly stack = signal(false);

  readonly sections: readonly { readonly id: SectionId; readonly labelKey: string }[] = [
    { id: 'que-hace', labelKey: 'landing.nav_product' },
    { id: 'conectores', labelKey: 'landing.nav_connectors' },
    { id: 'investigacion', labelKey: 'landing.nav_research' },
  ];

  /** The four things SVAES does with a release, in order. */
  readonly stations = ['link', 'read', 'eval', 'decide'] as const;

  readonly researchSteps = ['requirement', 'evidence', 'compare', 'result'] as const;

  readonly connectorGroups: readonly ConnectorGroup[] = [
    { labelKey: 'landing.conn_cat_tasks', items: ['Jira', 'Linear', 'Trello', 'Asana'] },
    { labelKey: 'landing.conn_cat_source', items: ['GitHub', 'GitLab', 'Bitbucket', 'Gitea'] },
    { labelKey: 'landing.conn_cat_docs', items: ['Confluence', 'Notion', 'Wiki.js', 'BookStack'] },
    {
      labelKey: 'landing.conn_cat_change',
      items: ['Jira Service Management', 'GLPI', 'Zammad', 'Redmine'],
    },
    { labelKey: 'landing.conn_cat_planning', items: ['ClickUp', 'Taiga', 'Plane', 'Miro'] },
  ];

  constructor() {
    // Browser only: sheets stack on wide screens when motion is allowed.
    afterNextRender(() => {
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
    const sheets = ['.hero'];
    const nextOf = ['.rest'];
    let frame = 0;
    // Eased copy of each sheet's cover: the page follows the scroll with a little inertia, so the
    // sheets glide instead of tracking every wheel notch.
    const shown = sheets.map(() => 0);
    const smooth = (t: number): number => t * t * (3 - 2 * t);

    const update = (): void => {
      frame = 0;
      const vh = window.innerHeight;
      const header = document.querySelector('.site-header')?.getBoundingClientRect().height ?? 72;
      let settling = false;
      sheets.forEach((sel, i) => {
        const el = document.querySelector<HTMLElement>(sel);
        if (!el) return;
        el.style.top = `${Math.min(header, vh - el.offsetHeight)}px`;
        const nextTop = document.querySelector(nextOf[i])?.getBoundingClientRect().top ?? vh;
        // The next sheet has to climb a sixth of the way before the one below starts to recede;
        // then an S-curve takes it from 0 to 1.
        const raw = (vh - nextTop) / (vh - header);
        const target = smooth(Math.min(1, Math.max(0, (raw - 0.15) / 0.85)));
        shown[i] += (target - shown[i]) * 0.14;
        if (Math.abs(target - shown[i]) > 0.002) settling = true;
        else shown[i] = target;
        el.style.setProperty('--cover', shown[i].toFixed(3));
      });
      // The glass behind paints the dimming from --cover, so tell it to repaint.
      window.dispatchEvent(new Event('sheet-cover'));
      if (settling) frame = requestAnimationFrame(update);
    };
    const schedule = (): void => {
      if (!frame) frame = requestAnimationFrame(update);
    };
    const apply = (): void => {
      this.stack.set(media.matches);
      if (media.matches) {
        window.addEventListener('scroll', schedule, { passive: true });
        window.addEventListener('resize', schedule, { passive: true });
        update();
      } else {
        window.removeEventListener('scroll', schedule);
        window.removeEventListener('resize', schedule);
        for (const sel of sheets) {
          const el = document.querySelector<HTMLElement>(sel);
          el?.style.removeProperty('top');
          el?.style.removeProperty('--cover');
        }
      }
    };
    // Keyboard users: a sheet that is covered would hide the focus ring (WCAG 2.4.11), so the first
    // Tab turns the stacking off for the rest of the visit and the page reads as plain sections.
    let keyboard = false;
    const onKey = (e: KeyboardEvent): void => {
      if (e.key !== 'Tab' || keyboard) return;
      keyboard = true;
      media.removeEventListener('change', apply);
      window.removeEventListener('scroll', schedule);
      window.removeEventListener('resize', schedule);
      this.stack.set(false);
      for (const sel of sheets) {
        const el = document.querySelector<HTMLElement>(sel);
        el?.style.removeProperty('top');
        el?.style.removeProperty('--cover');
      }
    };
    window.addEventListener('keydown', onKey);
    media.addEventListener('change', apply);
    apply();
    this.destroyRef.onDestroy(() => {
      window.removeEventListener('keydown', onKey);
      media.removeEventListener('change', apply);
      window.removeEventListener('scroll', schedule);
      window.removeEventListener('resize', schedule);
      if (frame) cancelAnimationFrame(frame);
    });
  }

  private initScrollProgress(): void {
    const indicator = this.scrollProgress()?.nativeElement;
    const root = document.scrollingElement;
    if (!indicator || !root) return;

    let frame: number | undefined;
    const update = (): void => {
      frame = undefined;
      const distance = root.scrollHeight - root.clientHeight;
      const fraction = distance > 0 ? Math.min(1, Math.max(0, root.scrollTop / distance)) : 0;
      indicator.style.transform = `scaleX(${fraction})`;
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
      if (frame !== undefined) cancelAnimationFrame(frame);
    });
  }

  ngOnInit(): void {
    this.seo.setPage({
      title: 'SVAES: Verificación Automática de Entregas',
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
