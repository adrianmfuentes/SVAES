import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { mockIntersectionObserver } from '../../../../test-support/browser-effects';
import { InfoPageComponent } from './info-page.component';

describe('InfoPageComponent table of contents', () => {
  const originalUrl = location.pathname + location.search + location.hash;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideRouter([
        { path: 'accesibilidad', component: InfoPageComponent, data: { page: 'accessibility' } },
        { path: 'mapa-del-sitio', component: InfoPageComponent, data: { page: 'sitemap' } },
        { path: 'legal/cookies', component: InfoPageComponent, data: { page: 'cookies' } },
      ])],
    });
  });

  afterEach(() => {
    TestBed.resetTestingModule();
    history.replaceState(null, '', originalUrl);
    vi.unstubAllGlobals();
  });

  it.each([
    ['/accesibilidad', ['a11y-goal', 'a11y-done', 'a11y-tests', 'a11y-limits', 'a11y-report']],
    ['/mapa-del-sitio', ['map-public', 'map-legal', 'map-app']],
    ['/legal/cookies', ['cookies-storage', 'cookies-manage', 'cookies-privacy']],
  ])('wires the section index for %s and focuses the destination', async (url, ids) => {
    const observer = mockIntersectionObserver();
    vi.stubGlobal('matchMedia', () => ({ matches: true }));
    const harness = await RouterTestingHarness.create();
    const page = await harness.navigateByUrl(url, InfoPageComponent);
    history.replaceState(null, '', url);
    const root = harness.routeNativeElement!;
    const links = [...root.querySelectorAll<HTMLAnchorElement>('.legal-toc-link')];
    expect(links.map((link) => link.getAttribute('href'))).toEqual(ids.map((id) => url + '#' + id));
    expect(observer.observe).toHaveBeenCalledTimes(ids.length);

    const section = root.querySelector<HTMLElement>('#' + ids[1])!;
    section.scrollIntoView = vi.fn();
    const first = root.querySelector<HTMLElement>('#' + ids[0])!;
    observer.intersect([{ target: first, isIntersecting: true }, { target: section, isIntersecting: false }]);
    harness.detectChanges();
    expect(links[0].getAttribute('aria-current')).toBe('location');
    links[1].click();
    harness.detectChanges();
    expect(section.scrollIntoView).toHaveBeenCalledWith({ behavior: 'auto', block: 'start' });
    expect(document.activeElement).toBe(section);
    expect(location.pathname + location.hash).toBe(url + '#' + ids[1]);
    expect(links[1].getAttribute('aria-current')).toBe('location');
    page.goTo('missing', new Event('click'));
    expect(page.active()).toBe(ids[1]);
    TestBed.resetTestingModule();
    expect(observer.disconnect).toHaveBeenCalledOnce();
  });
});
