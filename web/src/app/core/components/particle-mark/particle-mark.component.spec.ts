import { TestBed } from '@angular/core/testing';
import { canvasContext, frameQueue, mockIntersectionObserver, mockResizeObserver } from '../../../../../test-support/browser-effects';
import { ParticleMarkComponent, pickPoints } from './particle-mark.component';

describe('pickPoints', () => {
  const size = 8;
  const mask = new Uint8Array(size * size);
  for (let y = 2; y < 6; y++) for (let x = 2; x < 6; x++) mask[y * size + x] = 255;

  it('only picks points where the mask is solid', () => {
    const pts = pickPoints(mask, size, 1, () => 0.5);
    expect(pts).toHaveLength(16);
    for (const p of pts) {
      expect(p.x).toBeGreaterThanOrEqual(2 / size);
      expect(p.x).toBeLessThan(6 / size);
      expect(p.y).toBeGreaterThanOrEqual(2 / size);
      expect(p.y).toBeLessThan(6 / size);
    }
  });

  it('thins the stipple with the density', () => {
    expect(pickPoints(mask, size, 0, () => 0.5)).toHaveLength(0);
  });
});

describe('ParticleMarkComponent', () => {
  function setup(reduce: boolean, width: number) {
    const frames = frameQueue();
    const observer = mockResizeObserver();
    const intersection = mockIntersectionObserver();
    vi.stubGlobal('matchMedia', () => ({ matches: reduce }));
    vi.spyOn(document, 'hidden', 'get').mockReturnValue(false);
    vi.spyOn(Math, 'random').mockReturnValue(0.1);
    let load!: () => void;
    vi.stubGlobal('Image', class {
      set onload(callback: () => void) { load = callback; }
    });
    const mask = new Uint8ClampedArray(320 * 320 * 4);
    mask[3] = 255;
    mask[7] = 255;
    const ctx = { ...canvasContext(), getImageData: vi.fn(() => ({ data: mask })) };
    const contexts = vi.spyOn(HTMLCanvasElement.prototype, 'getContext')
      .mockReturnValue(ctx as unknown as CanvasRenderingContext2D);
    const fixture = TestBed.createComponent(ParticleMarkComponent);
    const host = fixture.nativeElement as HTMLElement;
    const bounds = vi.spyOn(host, 'getBoundingClientRect').mockReturnValue(new DOMRect(0, 0, width, 400));
    fixture.componentRef.setInput('src', '/images/mark.svg');
    fixture.detectChanges();
    return { fixture, host, ctx, contexts, frames, observer, intersection, bounds, load };
  }

  afterEach(() => {
    TestBed.resetTestingModule();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('samples the mark, responds to input and suspends frames when offscreen', () => {
    const { fixture, host, ctx, frames, observer, intersection, bounds, load } = setup(false, 1024);
    load();
    const parent = host.parentElement!;
    expect(ctx.drawImage).toHaveBeenCalledOnce();
    expect(frames.size).toBe(1);
    frames.paint(performance.now());
    const scattered = ctx.fillRect.mock.calls.map((args) => args.slice());
    expect(scattered).toHaveLength(3);
    parent.dispatchEvent(new MouseEvent('pointermove', { clientX: 390, clientY: 55 }));
    parent.dispatchEvent(new MouseEvent('pointerdown', { clientX: 395, clientY: 60 }));
    frames.paint(performance.now() + 1200);
    expect(ctx.fillRect.mock.calls.slice(-3)).not.toEqual(scattered);
    parent.dispatchEvent(new Event('pointerleave'));

    intersection.intersect([{ target: host, isIntersecting: false }]);
    frames.paint(performance.now() + 1300);
    expect(frames.size).toBe(0);
    intersection.intersect([{ target: host, isIntersecting: true }]);
    expect(frames.size).toBe(1);
    document.dispatchEvent(new Event('visibilitychange'));
    expect(frames.size).toBe(1);
    bounds.mockReturnValue(new DOMRect(0, 0, 420, 400));
    observer.resize();
    expect(host.querySelector('canvas')?.width).toBe(420);
    fixture.destroy();
    expect(frames.size).toBe(0);
    expect(observer.disconnect).toHaveBeenCalledOnce();
    expect(intersection.disconnect).toHaveBeenCalledOnce();
  });

  it('draws a static mark with reduced motion and repaints after resizing', () => {
    const { fixture, ctx, frames, observer, intersection, load } = setup(true, 400);
    load();
    expect(ctx.fillRect).toHaveBeenCalledTimes(3);
    expect(frames.size).toBe(0);
    expect(intersection.observe).not.toHaveBeenCalled();
    observer.resize();
    expect(ctx.fillRect).toHaveBeenCalledTimes(6);
    fixture.destroy();
  });

  it.each([0, 1])('leaves the canvas blank when context %s is unavailable', (contextIndex) => {
    const { fixture, ctx, contexts, frames, observer, load } = setup(false, 400);
    if (contextIndex) contexts.mockReturnValueOnce(ctx as unknown as CanvasRenderingContext2D);
    contexts.mockReturnValueOnce(null);
    load();
    expect(observer.observe).not.toHaveBeenCalled();
    expect(ctx.fillRect).not.toHaveBeenCalled();
    expect(frames.size).toBe(0);
    fixture.destroy();
  });
});
