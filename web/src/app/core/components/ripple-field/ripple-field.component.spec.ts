import { TestBed } from '@angular/core/testing';
import { canvasContext, frameQueue, mockIntersectionObserver, mockResizeObserver } from '../../../../../test-support/browser-effects';
import { RippleFieldComponent, ringsAt } from './ripple-field.component';

describe('ringsAt', () => {
  it('has no rings before the drop or after it has settled', () => {
    expect(ringsAt(-1, 1)).toEqual([]);
    expect(ringsAt(10_000, 1)).toEqual([]);
  });

  it('spreads outward and fades as the drop ages', () => {
    const early = ringsAt(800, 1);
    const late = ringsAt(2400, 1);
    expect(early.length).toBeGreaterThan(0);
    expect(late[0].radius).toBeGreaterThan(early[0].radius);
    expect(late[0].alpha).toBeLessThan(early[0].alpha);
  });

  it('travels less far when hit softly', () => {
    expect(ringsAt(1000, 0.3)[0].radius).toBeLessThan(ringsAt(1000, 1)[0].radius);
  });
});

describe('RippleFieldComponent', () => {
  function setup(reduce: boolean) {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'performance'] });
    vi.spyOn(Math, 'random').mockReturnValue(0);
    vi.spyOn(document, 'hidden', 'get').mockReturnValue(false);
    vi.stubGlobal('matchMedia', () => ({ matches: reduce }));
    const frames = frameQueue();
    const observer = mockResizeObserver();
    const intersection = mockIntersectionObserver();
    const ctx = canvasContext();
    const contexts = vi.spyOn(HTMLCanvasElement.prototype, 'getContext')
      .mockReturnValue(ctx as unknown as CanvasRenderingContext2D);
    const fixture = TestBed.createComponent(RippleFieldComponent);
    const host = fixture.nativeElement as HTMLElement;
    vi.spyOn(host, 'getBoundingClientRect').mockReturnValue(new DOMRect(10, 20, 400, 300));
    return { fixture, host, ctx, contexts, frames, observer, intersection };
  }

  afterEach(() => {
    TestBed.resetTestingModule();
    vi.useRealTimers();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('draws pointer and ambient ripples, then cancels work on destruction', () => {
    const { fixture, host, ctx, frames, observer, intersection } = setup(false);
    fixture.detectChanges();
    const parent = host.parentElement!;
    const move = (x: number) => parent.dispatchEvent(new MouseEvent('pointermove', { clientX: x, clientY: 70 }));
    move(35);
    move(40);
    parent.dispatchEvent(new Event('pointerleave'));
    move(43);
    for (let i = 0; i < 25; i++) {
      parent.dispatchEvent(new MouseEvent('pointerdown', { clientX: 175 + i, clientY: 75 }));
    }
    frames.paint(performance.now() + 200);
    expect(ctx.stroke).toHaveBeenCalled();
    expect(ctx.arc).toHaveBeenCalledWith(189, 55, expect.any(Number), 0, Math.PI * 2);
    expect(ctx.arc.mock.calls.every(([x]) => x !== 30)).toBe(true);
    vi.advanceTimersByTime(3400);
    frames.paint(performance.now() + 200);
    expect(ctx.arc).toHaveBeenCalledWith(expect.closeTo(220), 45, expect.any(Number), 0, Math.PI * 2);
    intersection.intersect([{ target: host, isIntersecting: false }]);
    vi.advanceTimersByTime(3200);
    frames.paint(performance.now());
    expect(frames.size).toBe(0);
    move(220);
    fixture.destroy();
    expect(frames.size).toBe(0);
    expect(observer.disconnect).toHaveBeenCalledOnce();
    expect(intersection.disconnect).toHaveBeenCalledOnce();
    expect(vi.getTimerCount()).toBe(0);
  });

  it('paints the static reduced-motion surface and ignores pointer events', () => {
    const { fixture, host, ctx, frames, observer } = setup(true);
    fixture.componentRef.setInput('tone', 'snow');
    fixture.detectChanges();
    const count = ctx.stroke.mock.calls.length;
    expect(count).toBeGreaterThan(0);
    host.parentElement?.dispatchEvent(new MouseEvent('pointerdown'));
    expect(frames.size).toBe(0);
    observer.resize();
    expect(ctx.stroke).toHaveBeenCalledTimes(count * 2);
    fixture.destroy();
  });

  it('does not install observers without a rendering context', () => {
    const { fixture, contexts, observer } = setup(false);
    contexts.mockReturnValue(null);
    fixture.detectChanges();
    expect(observer.observe).not.toHaveBeenCalled();
    fixture.destroy();
  });
});
