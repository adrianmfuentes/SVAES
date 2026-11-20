import { ringsAt } from './ripple-field.component';

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
