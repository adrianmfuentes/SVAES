import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { TranslatePipe } from '../../core/i18n/translate.pipe';
import { LangToggleComponent } from '../../core/components/lang-toggle/lang-toggle.component';
import { SiteFooterComponent } from '../../core/components/site-footer/site-footer.component';
import { SeoService } from '../../core/services/seo.service';
import { TocNavigation } from '../legal/toc-navigation';

const PAGE_DETAILS = {
  accessibility: {
    title: 'Declaración de accesibilidad',
    description: 'Declaración de accesibilidad de SVAES: objetivo WCAG 2.2, medidas aplicadas, limitaciones conocidas y cómo avisar de un problema.',
    path: '/accesibilidad',
    sections: ['goal', 'done', 'tests', 'limits', 'report'].map((key) => ({
      id: 'a11y-' + key,
      label: 'info.a11y.' + key + '_title',
    })),
  },
  sitemap: {
    title: 'Mapa del sitio',
    description: 'Mapa del sitio de SVAES: todas las páginas públicas y de la aplicación.',
    path: '/mapa-del-sitio',
    sections: ['public', 'legal', 'app'].map((key) => ({
      id: 'map-' + key,
      label: 'info.map.' + key,
    })),
  },
  cookies: {
    title: 'Política de cookies',
    description: 'Información sobre cookies y almacenamiento local en SVAES.',
    path: '/legal/cookies',
    sections: ['storage', 'manage', 'privacy'].map((key) => ({
      id: 'cookies-' + key,
      label: 'info.cookies.' + key + '_title',
    })),
  },
} as const;

export type InfoPage = keyof typeof PAGE_DETAILS;

interface MapChild {
  readonly key: string;
  readonly fragment: string;
}

interface MapEntry {
  readonly key: string;
  readonly desc: string;
  readonly link?: string;
  readonly current?: boolean;
  readonly children?: readonly MapChild[];
}

@Component({
  selector: 'app-info-page',
  standalone: true,
  imports: [RouterModule, TranslatePipe, LangToggleComponent, SiteFooterComponent],
  templateUrl: './info-page.component.html',
  styleUrl: './info-page.component.scss',
})
export class InfoPageComponent extends TocNavigation implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly seo = inject(SeoService);

  readonly page: InfoPage = (this.route.snapshot.data['page'] as InfoPage) ?? 'accessibility';

  readonly details = PAGE_DETAILS[this.page];

  readonly doneItems = [1, 2, 3, 4, 5, 6, 7, 8];
  readonly limitItems = [1, 2, 3];

  readonly publicPages: readonly MapEntry[] = [
    {
      key: 'info.map.home',
      desc: 'info.map.home_desc',
      link: '/',
      children: [
        { key: 'info.map.home_what', fragment: 'que-hace' },
        { key: 'info.map.home_connectors', fragment: 'conectores' },
        { key: 'info.map.home_research', fragment: 'investigacion' },
      ],
    },
    { key: 'info.map.login', desc: 'info.map.login_desc', link: '/auth/login' },
    { key: 'info.map.request', desc: 'info.map.request_desc', link: '/request-access' },
  ];

  readonly legalPages: readonly MapEntry[] = [
    { key: 'info.map.privacy', desc: 'info.map.privacy_desc', link: '/legal/privacidad' },
    { key: 'info.map.cookies', desc: 'info.map.cookies_desc', link: '/legal/cookies' },
    { key: 'info.map.notice', desc: 'info.map.notice_desc', link: '/legal/aviso-legal' },
    { key: 'info.map.accessibility', desc: 'info.map.accessibility_desc', link: '/accesibilidad' },
    { key: 'info.map.sitemap', desc: 'info.map.sitemap_desc', link: '/mapa-del-sitio', current: true },
  ];

  readonly appPages: readonly MapEntry[] = [
    { key: 'info.map.app_dashboard', desc: 'info.map.app_dashboard_desc' },
    { key: 'info.map.app_releases', desc: 'info.map.app_releases_desc' },
    { key: 'info.map.app_projects', desc: 'info.map.app_projects_desc' },
    { key: 'info.map.app_connectors', desc: 'info.map.app_connectors_desc' },
    { key: 'info.map.app_profiles', desc: 'info.map.app_profiles_desc' },
    { key: 'info.map.app_channels', desc: 'info.map.app_channels_desc' },
    { key: 'info.map.app_logs', desc: 'info.map.app_logs_desc' },
    { key: 'info.map.app_system', desc: 'info.map.app_system_desc' },
    { key: 'info.map.app_org', desc: 'info.map.app_org_desc' },
    { key: 'info.map.app_admin', desc: 'info.map.app_admin_desc' },
    { key: 'info.map.app_profile', desc: 'info.map.app_profile_desc' },
  ];

  ngOnInit(): void {
    this.seo.setPage(this.details);
  }
}
