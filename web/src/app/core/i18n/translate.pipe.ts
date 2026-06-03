import { Pipe, PipeTransform, OnDestroy, ChangeDetectorRef, inject } from '@angular/core';
import { Subscription } from 'rxjs';
import { TranslationService } from './translation.service';

@Pipe({
  name: 't',
  standalone: true,
  pure: false,
})
export class TranslatePipe implements PipeTransform, OnDestroy {
  private readonly ts = inject(TranslationService);
  private readonly cdr = inject(ChangeDetectorRef);
  private sub?: Subscription;
  private lastKey = '';
  private lastParams?: Record<string, string | number>;
  private value = '';

  transform(key: string, params?: Record<string, string | number>): string {
    if (key !== this.lastKey || !this.deepEqual(params, this.lastParams)) {
      this.lastKey = key;
      this.lastParams = params;
      if (this.sub) this.sub.unsubscribe();
      this.sub = this.ts.lang$.subscribe(() => {
        this.value = this.ts.translateInstant(key, params);
        this.cdr.markForCheck();
      });
      this.value = this.ts.translateInstant(key, params);
    }
    return this.value;
  }

  ngOnDestroy(): void {
    if (this.sub) this.sub.unsubscribe();
  }

  private deepEqual(a?: Record<string, string | number>, b?: Record<string, string | number>): boolean {
    if (a === b) return true;
    if (!a || !b) return !a && !b;
    const keysA = Object.keys(a);
    const keysB = Object.keys(b);
    if (keysA.length !== keysB.length) return false;
    return keysA.every((k) => a[k] === b[k]);
  }
}
