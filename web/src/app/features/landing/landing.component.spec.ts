import { TestBed, ComponentFixture } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { frameQueue, mockResizeObserver } from '../../../../test-support/browser-effects';
import { LandingComponent } from './landing.component';

describe('LandingComponent', () => {
  let fixture: ComponentFixture<LandingComponent>;
  let component: LandingComponent;
  let host: HTMLElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LandingComponent],
      providers: [provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(LandingComponent);
    component = fixture.componentInstance;
    host = fixture.nativeElement as HTMLElement;
    fixture.detectChanges();
  });

  it('should create the component', () => {
    expect(component).toBeTruthy();
  });

  it('renders one h1 and a heading for every section target', () => {
    expect(host.querySelectorAll('h1')).toHaveLength(1);
    for (const section of component.sections) {
      expect(host.querySelector(`#${section.id}`)).not.toBeNull();
    }
  });

  it('toggles the mobile menu and exposes its state', () => {
    const toggle = host.querySelector<HTMLButtonElement>('.menu-toggle')!;
    expect(toggle.getAttribute('aria-expanded')).toBe('false');

    toggle.click();
    fixture.detectChanges();
    expect(toggle.getAttribute('aria-expanded')).toBe('true');

    component.closeMenu();
    fixture.detectChanges();
    expect(toggle.getAttribute('aria-expanded')).toBe('false');
  });

  it('moves focus to the target heading when navigating to a section', () => {
    const scrollSpy = vi.fn();
    const target = host.querySelector<HTMLElement>('#investigacion')!;
    target.scrollIntoView = scrollSpy;
    const event = new Event('click', { cancelable: true });

    component.goTo('investigacion', event);

    expect(event.defaultPrevented).toBe(true);
    expect(scrollSpy).toHaveBeenCalled();
    expect(document.activeElement).toBe(target);
  });

  it('lists the four steps', () => {
    expect(host.querySelectorAll('.steps .step')).toHaveLength(4);
  });

  it('shows the selected step and announces its evidence after activation', () => {
    const steps = [...host.querySelectorAll<HTMLButtonElement>('.step__button')];
    expect(steps.map((step) => step.getAttribute('aria-pressed'))).toEqual(['true', 'false', 'false', 'false']);

    steps[3].click();
    fixture.detectChanges();

    expect(steps.map((step) => step.getAttribute('aria-pressed'))).toEqual(['false', 'false', 'false', 'true']);
    const verdict = host.querySelector('.step__record .demo-record__value')?.textContent?.trim();
    expect(verdict).toBeTruthy();
    expect(host.querySelector('.demo__preview .demo-record__value')?.textContent?.trim()).toBe(verdict);
    expect(host.querySelector('.demo [role="status"]')?.textContent).toContain(verdict);
  });
});

describe('Landing scroll behavior', () => {
  const originalScrollingElement = Object.getOwnPropertyDescriptor(document, 'scrollingElement');

  afterEach(() => {
    TestBed.resetTestingModule();
    if (originalScrollingElement) {
      Object.defineProperty(document, 'scrollingElement', originalScrollingElement);
    } else {
      Reflect.deleteProperty(document, 'scrollingElement');
    }
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  async function setup(matches: boolean) {
    const media = Object.assign(new EventTarget(), { matches });
    vi.stubGlobal('matchMedia', () => media);
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null);
    const observer = mockResizeObserver();
    const frames = frameQueue();
    const root = { scrollTop: 0, scrollHeight: 1800, clientHeight: 800 };
    Object.defineProperty(document, 'scrollingElement', { configurable: true, value: root });
    await TestBed.configureTestingModule({
      imports: [LandingComponent],
      providers: [provideRouter([])],
    }).compileComponents();
    const fixture = TestBed.createComponent(LandingComponent);
    const host = fixture.nativeElement as HTMLElement;
    const header = host.querySelector('.site-header')!;
    const rest = host.querySelector('.rest')!;
    vi.spyOn(header, 'getBoundingClientRect').mockReturnValue(new DOMRect(0, 0, 1024, 72));
    const bounds = vi.spyOn(rest, 'getBoundingClientRect').mockReturnValue(new DOMRect(0, 900, 1024, 750));
    fixture.detectChanges();
    await Promise.resolve();
    return { fixture, host, root, frames, observer, media, bounds };
  }

  it('tracks scroll and layout changes, clamps overscroll, and cancels pending frames', async () => {
    const { fixture, host, root, frames, observer } = await setup(false);
    const progress = host.querySelector<HTMLElement>('.site-header__progress-fill')!;
    expect(progress.style.transform).toBe('scaleX(0)');
    root.scrollTop = 500;
    window.dispatchEvent(new Event('scroll'));
    window.dispatchEvent(new Event('scroll'));
    expect(frames.size).toBe(1);
    frames.paint();
    expect(progress.style.transform).toBe('scaleX(0.5)');

    root.scrollTop = 1200;
    window.dispatchEvent(new Event('resize'));
    frames.paint();
    expect(progress.style.transform).toBe('scaleX(1)');
    root.scrollTop = -1200;
    window.dispatchEvent(new Event('scroll'));
    frames.paint();
    expect(progress.style.transform).toBe('scaleX(0)');
    root.scrollHeight = root.clientHeight;
    observer.resize();
    frames.paint();
    expect(progress.style.transform).toBe('scaleX(0)');
    window.dispatchEvent(new Event('scroll'));
    fixture.destroy();
    expect(frames.size).toBe(0);
    expect(observer.disconnect).toHaveBeenCalledOnce();
    window.dispatchEvent(new Event('scroll'));
    expect(frames.size).toBe(0);
  });

  it('follows the covering sheet on scroll and restores ordinary layout for keyboard use', async () => {
    const { fixture, host, frames, media, bounds } = await setup(true);
    const hero = host.querySelector<HTMLElement>('.hero')!;
    expect(fixture.componentInstance.stack()).toBe(true);
    expect(hero.style.top).toBe('72px');

    bounds.mockReturnValue(new DOMRect(0, 72, 1024, 750));
    window.dispatchEvent(new Event('scroll'));
    frames.paint();
    expect(hero.style.getPropertyValue('--cover')).toBe('1.000');
    expect(frames.size).toBe(0);
    bounds.mockReturnValue(new DOMRect(0, 900, 1024, 750));
    window.dispatchEvent(new Event('scroll'));
    frames.paint();
    expect(hero.style.getPropertyValue('--cover')).toBe('0.000');
    expect(frames.size).toBe(0);

    media.matches = false;
    media.dispatchEvent(new Event('change'));
    expect(hero.style.top).toBe('');
    media.matches = true;
    media.dispatchEvent(new Event('change'));
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Shift' }));
    expect(fixture.componentInstance.stack()).toBe(true);
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab' }));
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab' }));
    expect(fixture.componentInstance.stack()).toBe(false);
    expect(hero.style.getPropertyValue('--cover')).toBe('');
    media.dispatchEvent(new Event('change'));
    expect(fixture.componentInstance.stack()).toBe(false);

    const scroll = vi.spyOn(window, 'scrollTo').mockImplementation(() => undefined);
    fixture.componentInstance.goTop(new Event('click', { cancelable: true }));
    expect(scroll).toHaveBeenCalledWith({ top: 0, behavior: 'auto' });
    expect(document.activeElement).toBe(host.querySelector('main'));
    expect(location.pathname).toBe('/');
    fixture.destroy();
  });
});
