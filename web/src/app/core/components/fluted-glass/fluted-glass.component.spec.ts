import { fluteAt } from './fluted-glass.component';

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
