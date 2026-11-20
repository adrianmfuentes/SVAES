import { TestBed } from '@angular/core/testing';
import { canvasContext, frameQueue, mockResizeObserver } from '../../../../../test-support/browser-effects';
import { FlutedGlassComponent, GlassScene, fluteAt } from './fluted-glass.component';

describe('fluteAt', () => {
  it('shows a squeezed, shifted slice far from the pointer', () => {
    const f = fluteAt(100, 20, 0, 2.6, 0.9);
    expect(f.sw).toBeCloseTo(20 * 2.6);
    expect(f.sx + f.sw / 2).toBeGreaterThan(110); // centred right of the flute centre
  });

  it('shows exactly what is behind the flute when fully clear', () => {
    const f = fluteAt(100, 20, 1, 2.6, 0.9);
    expect(f.sx).toBeCloseTo(100);
    expect(f.sw).toBeCloseTo(20);
  });

  it('clamps clarity outside 0..1', () => {
    expect(fluteAt(0, 10, 5, 2, 1).sw).toBeCloseTo(10);
    expect(fluteAt(0, 10, -3, 2, 1).sw).toBeCloseTo(20);
  });
});

describe('FlutedGlassComponent', () => {
  const scenes: GlassScene[] = [
    { selector: '#glass-missing', ground: '#fff' },
    {
      selector: '#glass-test',
      ground: '#f5f8fb',
      squeeze: 1.6,
      pull: 0.4,
      rest: 0.2,
      scrollClear: true,
      art: '4',
      blobs: [
        { x: 0.25, y: 0.5, r: 0.1, color: '#abc' },
        { x: 0.5, y: 0.5, r: 0.1, color: '#def', alpha: 0.6 },
      ],
      words: [
        { text: 'Valid', mark: 'check', color: '#080' },
        { text: 'Invalid', mark: 'cross', color: '#800' },
        { text: 'Warning', mark: 'warn', color: '#880' },
        { text: 'Pending', mark: 'dash', color: '#888' },
      ],
    },
    { selector: '#glass-offscreen', ground: '#000', art: 'hidden' },
  ];

  afterEach(() => {
    TestBed.resetTestingModule();
    document.querySelectorAll('[data-glass-test]').forEach((element) => element.remove());
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('paints visible scenes, responds to the pointer and repaints on scroll and resize', async () => {
    vi.stubGlobal('innerWidth', 1080);
    vi.stubGlobal('innerHeight', 420);
    vi.stubGlobal('devicePixelRatio', 3);
    vi.stubGlobal('matchMedia', () => ({ matches: false }));
    const frames = frameQueue();
    const observer = mockResizeObserver();
    const output = canvasContext();
    const world = canvasContext();
    const shade = canvasContext();
    const contexts = vi.spyOn(HTMLCanvasElement.prototype, 'getContext');
    for (const context of [output, world, shade]) {
      contexts.mockReturnValueOnce(context as unknown as CanvasRenderingContext2D);
    }
    for (const [id, top] of [['glass-test', -40], ['glass-offscreen', 600]] as const) {
      const section = document.createElement('section');
      section.id = id;
      section.dataset['glassTest'] = '';
      section.style.setProperty('--cover', '0.5');
      vi.spyOn(section, 'getBoundingClientRect').mockReturnValue(new DOMRect(0, top, 1080, 300));
      document.body.append(section);
    }

    const fixture = TestBed.createComponent(FlutedGlassComponent);
    const ready = vi.fn();
    fixture.componentInstance.ready.subscribe(ready);
    fixture.componentRef.setInput('scenes', scenes);
    fixture.detectChanges();
    await Promise.resolve();
    expect(fixture.nativeElement.querySelector('canvas').width).toBe(2160);
    expect(world.fillText.mock.calls.map(([label]) => label)).toEqual(['4', 'Valid', 'Invalid', 'Warning', 'Pending']);
    expect(world.arc).toHaveBeenCalledTimes(2);
    expect(output.drawImage).toHaveBeenCalled();
    expect(shade.createLinearGradient).toHaveBeenCalledOnce();
    expect(ready).toHaveBeenCalledOnce();

    document.dispatchEvent(new MouseEvent('pointermove', { clientX: 120, clientY: 60 }));
    document.dispatchEvent(new MouseEvent('pointerdown', { clientX: 130, clientY: 65 }));
    expect(frames.size).toBe(1);
    frames.paint();
    expect(output.createRadialGradient).toHaveBeenCalledWith(130, 65, 0, 130, 65, expect.any(Number));
    document.documentElement.dispatchEvent(new Event('pointerleave'));
    for (let i = 0; i < 45 && frames.size; i++) frames.paint();
    expect(frames.size).toBe(0);
    window.dispatchEvent(new Event('scroll'));
    window.dispatchEvent(new Event('sheet-cover'));
    expect(frames.size).toBe(1);
    frames.paint();

    vi.stubGlobal('innerWidth', 410);
    world.fillText.mockClear();
    observer.resize();
    expect(world.fillText.mock.calls.map(([label]) => label)).toEqual(['4']);
    fixture.componentRef.setInput('scenes', []);
    fixture.detectChanges();
    expect(output.clearRect).toHaveBeenLastCalledWith(0, 0, 410, 420);
    expect(ready).toHaveBeenCalledOnce();
    window.dispatchEvent(new Event('scroll'));
    fixture.destroy();
    expect(frames.size).toBe(0);
    expect(observer.disconnect).toHaveBeenCalledOnce();
  });

  it('ignores pointer input with reduced motion and leaves backgrounds intact without a canvas', async () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true }));
    const frames = frameQueue();
    mockResizeObserver();
    const ctx = canvasContext();
    const contexts = vi.spyOn(HTMLCanvasElement.prototype, 'getContext')
      .mockReturnValue(ctx as unknown as CanvasRenderingContext2D);
    const fixture = TestBed.createComponent(FlutedGlassComponent);
    fixture.componentRef.setInput('scenes', []);
    fixture.detectChanges();
    await Promise.resolve();
    expect(ctx.drawImage).toHaveBeenCalled();
    document.dispatchEvent(new MouseEvent('pointermove'));
    expect(frames.size).toBe(0);
    fixture.destroy();

    for (const missing of [0, 1, 2]) {
      contexts.mockReset();
      contexts.mockReturnValue(ctx as unknown as CanvasRenderingContext2D);
      for (let i = 0; i < missing; i++) contexts.mockReturnValueOnce(ctx as unknown as CanvasRenderingContext2D);
      contexts.mockReturnValueOnce(null);
      const fallback = TestBed.createComponent(FlutedGlassComponent);
      const ready = vi.fn();
      fallback.componentInstance.ready.subscribe(ready);
      fallback.componentRef.setInput('scenes', []);
      fallback.detectChanges();
      await Promise.resolve();
      expect(ready).toHaveBeenCalledTimes(missing === 2 ? 1 : 0);
      fallback.destroy();
    }
  });
});
