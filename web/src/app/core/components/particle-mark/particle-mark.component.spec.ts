import { pickPoints } from './particle-mark.component';

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
