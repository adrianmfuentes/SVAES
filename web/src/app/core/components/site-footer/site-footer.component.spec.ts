import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { SiteFooterComponent } from './site-footer.component';

describe('SiteFooterComponent', () => {
  const originalUrl = location.pathname + location.search + location.hash;

  async function setup() {
    await TestBed.configureTestingModule({
      imports: [SiteFooterComponent],
      providers: [provideRouter([])],
    }).compileComponents();
    const fixture = TestBed.createComponent(SiteFooterComponent);
    fixture.detectChanges();
    return fixture;
  }

  afterEach(() => {
    document.getElementById('footer-test-main')?.remove();
    document.body.style.overflow = '';
    history.replaceState(null, '', originalUrl);
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('focuses and scrolls the landing section, leaving navigation to the router on other pages', async () => {
    const footer = (await setup()).componentInstance;
    const main = document.createElement('main');
    main.id = 'footer-test-main';
    main.tabIndex = -1;
    const target = document.createElement('h2');
    target.id = 'conectores';
    target.tabIndex = -1;
    target.scrollIntoView = vi.fn();
    main.append(target);
    document.body.prepend(main);
    vi.stubGlobal('matchMedia', () => ({ matches: false }));
    history.replaceState(null, '', '/');
    const event = new MouseEvent('click', { cancelable: true });
    footer.goToSection(target.id, event);
    expect(event.defaultPrevented).toBe(true);
    expect(target.scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'start' });
    expect(document.activeElement).toBe(target);
    expect(location.hash).toBe('#conectores');

    const fallback = new MouseEvent('click', { cancelable: true });
    footer.goToSection('missing', fallback);
    history.replaceState(null, '', '/legal/cookies');
    footer.goToSection(target.id, fallback);
    expect(fallback.defaultPrevented).toBe(false);
    expect(target.scrollIntoView).toHaveBeenCalledOnce();

    const scroll = vi.spyOn(window, 'scrollTo').mockImplementation(() => undefined);
    vi.stubGlobal('matchMedia', () => ({ matches: true }));
    footer.scrollToTop(fallback);
    expect(fallback.defaultPrevented).toBe(true);
    expect(scroll).toHaveBeenCalledWith({ top: 0, behavior: 'auto' });
    expect(document.activeElement).toBe(main);
    main.remove();
    vi.stubGlobal('matchMedia', undefined);
    footer.scrollToTop(fallback);
    expect(scroll).toHaveBeenLastCalledWith({ top: 0, behavior: 'auto' });
  });

  it('locks and restores page scrolling when feedback opens and closes', async () => {
    const footer = (await setup()).componentInstance;
    footer.openFeedback();
    expect(footer.showFeedback()).toBe(true);
    expect(document.body.style.overflow).toBe('hidden');
    footer.closeFeedback();
    expect(footer.showFeedback()).toBe(false);
    expect(document.body.style.overflow).toBe('');
  });

  it('opens the glossary once and closes on backdrop and keyboard dismissal', async () => {
    const fixture = await setup();
    const footer = fixture.componentInstance;
    const dialog: HTMLDialogElement = fixture.nativeElement.querySelector('dialog');
    const show = vi.fn(() => { dialog.open = true; });
    const close = vi.fn(() => { dialog.open = false; });
    dialog.showModal = show;
    dialog.close = close;
    footer.openGlossary();
    footer.openGlossary();
    expect(show).toHaveBeenCalledOnce();

    dialog.querySelector('.glossary-dialog__panel')?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    dialog.querySelector('.glossary-dialog__close')?.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, key: 'Enter' }));
    dialog.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, key: 'Tab' }));
    expect(dialog.open).toBe(true);
    dialog.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(dialog.open).toBe(false);

    for (const key of ['Enter', 'Escape']) {
      footer.openGlossary();
      dialog.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, key }));
      expect(dialog.open).toBe(false);
    }
    expect(close).toHaveBeenCalledTimes(3);
    Object.defineProperties(dialog, {
      showModal: { value: undefined },
      close: { value: undefined },
    });
    footer.openGlossary();
    footer.closeGlossary();
    expect(dialog.open).toBe(false);
  });
});
