export function frameQueue() {
  let nextId = 0;
  const pending = new Map<number, FrameRequestCallback>();
  vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
    pending.set(++nextId, callback);
    return nextId;
  });
  vi.stubGlobal('cancelAnimationFrame', (id: number) => pending.delete(id));
  return {
    get size() { return pending.size; },
    paint(time = performance.now()) {
      const callbacks = [...pending.values()];
      pending.clear();
      callbacks.forEach((callback) => callback(time));
    },
  };
}

export function mockResizeObserver() {
  const resize = vi.fn<() => void>();
  const observe = vi.fn();
  const disconnect = vi.fn();
  vi.stubGlobal('ResizeObserver', class {
    constructor(callback: () => void) { resize.mockImplementation(callback); }
    observe = observe;
    disconnect = disconnect;
  });
  return { resize, observe, disconnect };
}

export function mockIntersectionObserver() {
  const intersect = vi.fn<(entries: Pick<IntersectionObserverEntry, 'isIntersecting' | 'target'>[]) => void>();
  const observe = vi.fn();
  const disconnect = vi.fn();
  vi.stubGlobal('IntersectionObserver', class {
    constructor(callback: Parameters<typeof intersect.mockImplementation>[0]) {
      intersect.mockImplementation(callback);
    }
    observe = observe;
    disconnect = disconnect;
  });
  return { intersect, observe, disconnect };
}

export function canvasContext() {
  const gradient = { addColorStop: vi.fn() };
  return {
    arc: vi.fn(),
    beginPath: vi.fn(),
    clearRect: vi.fn(),
    clip: vi.fn(),
    closePath: vi.fn(),
    createLinearGradient: vi.fn(() => gradient),
    createRadialGradient: vi.fn(() => gradient),
    drawImage: vi.fn(),
    fill: vi.fn(),
    fillRect: vi.fn(),
    fillText: vi.fn(),
    lineTo: vi.fn(),
    measureText: vi.fn((text: string) => ({ width: text.length * 10 })),
    moveTo: vi.fn(),
    rect: vi.fn(),
    restore: vi.fn(),
    save: vi.fn(),
    setTransform: vi.fn(),
    stroke: vi.fn(),
  };
}
