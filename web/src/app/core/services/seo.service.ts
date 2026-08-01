import { Injectable, inject } from '@angular/core';
import { DOCUMENT } from '@angular/common';
import { Meta, Title } from '@angular/platform-browser';

const SITE_NAME = 'SVAES';
const BASE_URL = 'https://svaes.amfserver.duckdns.org';
const JSONLD_ID = 'seo-jsonld';

export interface PageSeo {
  title: string;
  description: string;
  path: string;
}

@Injectable({ providedIn: 'root' })
export class SeoService {
  private readonly titleService = inject(Title);
  private readonly meta = inject(Meta);
  private readonly document = inject(DOCUMENT);

  setPage({ title, description, path }: PageSeo): void {
    const fullTitle = `${title} · ${SITE_NAME}`;
    const url = `${BASE_URL}${path}`;

    this.titleService.setTitle(fullTitle);

    this.meta.updateTag({ name: 'description', content: description });
    this.meta.updateTag({ name: 'robots', content: 'index, follow' });
    this.meta.updateTag({ property: 'og:title', content: fullTitle });
    this.meta.updateTag({ property: 'og:description', content: description });
    this.meta.updateTag({ property: 'og:url', content: url });
    this.meta.updateTag({ name: 'twitter:title', content: fullTitle });
    this.meta.updateTag({ name: 'twitter:description', content: description });

    this.updateCanonical(url);
  }

  /** Marks the current page as non-indexable (auth-token forms, error pages). */
  setNoIndex(title?: string): void {
    if (title) {
      this.titleService.setTitle(`${title} · ${SITE_NAME}`);
    }
    this.meta.updateTag({ name: 'robots', content: 'noindex, nofollow' });
  }

  /** Injects a JSON-LD structured data block, replacing any previous one. */
  setJsonLd(data: Record<string, unknown>): void {
    this.document.getElementById(JSONLD_ID)?.remove();
    const script = this.document.createElement('script');
    script.id = JSONLD_ID;
    script.type = 'application/ld+json';
    script.text = JSON.stringify(data);
    this.document.head.appendChild(script);
  }

  private updateCanonical(url: string): void {
    let link: HTMLLinkElement | null = this.document.querySelector('link[rel="canonical"]');
    if (!link) {
      link = this.document.createElement('link');
      link.setAttribute('rel', 'canonical');
      this.document.head.appendChild(link);
    }
    link.setAttribute('href', url);
  }
}
