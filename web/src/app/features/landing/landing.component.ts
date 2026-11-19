import {
  Component,
  DestroyRef,
  ElementRef,
  HostListener,
  OnInit,
  afterNextRender,
  inject,
  signal,
  viewChild,
} from '@angular/core';
import { RouterModule } from '@angular/router';
import { TranslatePipe } from '../../core/i18n/translate.pipe';
import { LangToggleComponent } from '../../core/components/lang-toggle/lang-toggle.component';
import { SiteFooterComponent } from '../../core/components/site-footer/site-footer.component';
import { SeoService } from '../../core/services/seo.service';
import { initLandingMotion, type LandingMotion } from './landing-motion';

type RuleStatus = 'valid' | 'warning';
type Severity = 'blocking' | 'non_blocking';

interface ActaRow {
  readonly id: string;
  readonly severity: Severity;
  readonly status: RuleStatus;
}

interface ConnectorGroup {
  readonly labelKey: string;
  readonly items: readonly string[];
}

/** Sections reachable from the navbar, footer and in-page links. */
export type SectionId = 'que-hace' | 'reglas' | 'conectores' | 'investigacion';

@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [RouterModule, TranslatePipe, LangToggleComponent, SiteFooterComponent],
  templateUrl: './landing.component.html',
  styleUrl: './landing.component.scss',
})
export class LandingComponent implements OnInit {
  private readonly seo = inject(SeoService);

  private readonly destroyRef = inject(DestroyRef);
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  private motion: LandingMotion | null = null;
  private readonly siteNav = viewChild<ElementRef<HTMLElement>>('siteNav');
  private hovering = false;

  readonly menuOpen = signal(false);
  readonly activeSection = signal<string | null>(null);

  readonly flowSteps = [1, 2, 3, 4] as const;

  readonly sections: readonly { readonly id: SectionId; readonly labelKey: string }[] = [
    { id: 'que-hace', labelKey: 'landing.nav_product' },
    { id: 'reglas', labelKey: 'landing.nav_rules' },
    { id: 'conectores', labelKey: 'landing.nav_connectors' },
    { id: 'investigacion', labelKey: 'landing.nav_research' },
  ];

  /** Five of the ten built-in rules (RV-01..RV-10), as a sample record. Severity follows the engine's defaults. */
  readonly rules: readonly ActaRow[] = [
    { id: 'RV01', severity: 'blocking', status: 'valid' },
    { id: 'RV02', severity: 'blocking', status: 'valid' },
    { id: 'RV04', severity: 'blocking', status: 'valid' },
    { id: 'RV06', severity: 'non_blocking', status: 'warning' },
    { id: 'RV10', severity: 'blocking', status: 'valid' },
  ];

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
    // Browser only: the hero animation never runs during prerender/SSR.
    afterNextRender(() => {
      const supported =
        typeof window.matchMedia === 'function' &&
        typeof ResizeObserver !== 'undefined' &&
        typeof IntersectionObserver !== 'undefined';
      const release = (): void => document.documentElement.classList.add('motion-done');
      if (!supported) {
        release();
        return;
      }
      const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      if (!reduce) {
        let destroyed = false;
        this.destroyRef.onDestroy(() => {
          destroyed = true;
          this.motion?.destroy();
        });
        initLandingMotion(this.host.nativeElement)
          .then((m) => (destroyed ? m.destroy() : (this.motion = m)))
          .catch(release);
        // Safety net: never leave the intro hidden if the animation chunk is slow or fails.
        window.setTimeout(release, 4000);
      }
      this.watchSections();
      window.addEventListener('resize', this.settlePill);
      this.destroyRef.onDestroy(() => window.removeEventListener('resize', this.settlePill));
    });
  }


  ngOnInit(): void {
    this.seo.setPage({
      title: 'SVAES — Verificación Automática de Entregas',
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

  /** Scroll-spy: the navbar pill follows the section that is being read. */
  private watchSections(): void {
    const targets = this.sections
      .map((s) => document.getElementById(s.id)?.closest('section'))
      .filter((el): el is HTMLElement => !!el);
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          const id = entry.target.querySelector('h2')?.id ?? null;
          if (entry.isIntersecting) this.activeSection.set(id);
          else if (this.activeSection() === id) this.activeSection.set(null);
        }
        requestAnimationFrame(this.settlePill);
      },
      { rootMargin: '-35% 0px -60% 0px' },
    );
    targets.forEach((el) => observer.observe(el));
    this.destroyRef.onDestroy(() => observer.disconnect());
  }

  /** Slides the navbar pill under the hovered or focused link. */
  movePill(event: Event): void {
    const link = (event.currentTarget as HTMLElement | null) ?? null;
    this.hovering = true;
    this.placePill(link);
  }

  leavePill(): void {
    this.hovering = false;
    this.settlePill();
  }

  /** Returns the pill to the active section's link, or hides it at the top of the page. */
  private readonly settlePill = (): void => {
    if (this.hovering) return;
    const nav = this.siteNav()?.nativeElement;
    this.placePill(nav?.querySelector<HTMLElement>('a[aria-current="true"]') ?? null);
  };

  private placePill(link: HTMLElement | null): void {
    const nav = this.siteNav()?.nativeElement;
    if (!nav) return;
    if (!link) {
      nav.style.setProperty('--pill-o', '0');
      return;
    }
    const box = nav.getBoundingClientRect();
    const rect = link.getBoundingClientRect();
    nav.style.setProperty('--pill-x', `${rect.left - box.left}px`);
    nav.style.setProperty('--pill-w', `${rect.width}px`);
    nav.style.setProperty('--pill-o', '1');
  }

  /** The logo on the home page scrolls to the top smoothly instead of jumping. */
  goTop(event: Event): void {
    event.preventDefault();
    this.menuOpen.set(false);
    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
    if (this.motion && !reduceMotion) this.motion.scrollTop();
    else window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
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

    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
    if (this.motion && !reduceMotion) this.motion.scrollTo(target);
    else target.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
    target.focus({ preventScroll: true });
    history.replaceState(null, '', `#${id}`);
  }

}
