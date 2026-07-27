import { Component, ElementRef, effect, inject, OnInit, OnDestroy, signal, computed, viewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, ActivatedRoute } from '@angular/router';
import { TranslationService } from '../../../core/i18n/translation.service';
import { TranslatePipe } from '../../../core/i18n/translate.pipe';
import { ToastService } from '../../../core/services/toast.service';
import { ConfirmDialogComponent } from '../../../core/components/confirm-dialog/confirm-dialog.component';
import { catchError, debounceTime, distinctUntilChanged, EMPTY, forkJoin, of, Subject, Subscription, switchMap } from 'rxjs';
import {
  Artifact,
  BrowseItem,
  ProfileRule,
  ReleaseDetail,
  ReleaseService,
  VerificationProgress,
  VerificationResult,
} from '../services/release.service';
import { ConnectorService } from '../../connectors/services/connector.service';

interface ConnectorApiItem {
  id: string;
  name: string;
  connector_type: string;
  connector_implementation: string;
  status: string;
  created_at: string;
  last_tested_at?: string;
}

const CONNECTOR_TYPE_TO_ARTIFACT: Record<string, string[]> = {
  'GESTOR_TAREAS': ['TAREA', 'CAMBIO'],
  'REPO_CODIGO': ['CODIGO'],
  'SISTEMA_DOCUMENTAL': ['DOCUMENTO'],
  'HERRAMIENTA_PLANIFICACION': ['PLAN'],
  'GESTION_CAMBIOS': ['CAMBIO', 'TAREA'],
};

@Component({
  selector: 'app-release-detail',
  standalone: true,
  imports: [CommonModule, RouterModule, TranslatePipe, ConfirmDialogComponent],
  templateUrl: './release-detail.component.html',
  styleUrls: ['./release-detail.component.scss'],
})
export class ReleaseDetailComponent implements OnInit, OnDestroy {
  private readonly releaseService = inject(ReleaseService);
  private readonly connectorService = inject(ConnectorService);
  private readonly route = inject(ActivatedRoute);
  readonly ts = inject(TranslationService);
  private readonly toast = inject(ToastService);

  release = signal<ReleaseDetail | null>(null);
  artifacts = signal<Artifact[]>([]);
  artifactToDelete = signal<string | null>(null);
  latestResult = signal<VerificationResult | null>(null);
  verificationHistory = signal<VerificationResult[]>([]);
  loading = signal(true);
  error = signal<string | null>(null);
  verifying = signal(false);
  expandedRule = signal<number | null>(null);
  showVerifyNotice = signal(false);
  taskId = signal<string | null>(null);
  verificationProgress = signal<VerificationProgress | null>(null);

  showImportModal = signal(false);
  orgConnectors = signal<ConnectorApiItem[]>([]);
  connectorsLoading = signal(false);
  importConnector = signal<ConnectorApiItem | null>(null);
  importArtifactType = signal<string>('TAREA');
  importExternalRef = signal('');
  importDescription = signal('');
  importing = signal(false);
  importError = signal<string | null>(null);
  showArtifactTypeHelp = signal(false);

  missingConnectorTypes = signal<string[]>([]);

  private readonly importDialogEl = viewChild<ElementRef<HTMLDialogElement>>('importDialogEl');
  private readonly helpDialogEl = viewChild<ElementRef<HTMLDialogElement>>('helpDialogEl');
  private readonly verifyDialogEl = viewChild<ElementRef<HTMLDialogElement>>('verifyDialogEl');

  constructor() {
    effect(() => {
      const el = this.importDialogEl();
      if (el && !el.nativeElement.open && typeof el.nativeElement.showModal === 'function') el.nativeElement.showModal();
    });
    effect(() => {
      const el = this.helpDialogEl();
      if (el && !el.nativeElement.open && typeof el.nativeElement.showModal === 'function') el.nativeElement.showModal();
    });
    effect(() => {
      const el = this.verifyDialogEl();
      if (el && !el.nativeElement.open && typeof el.nativeElement.showModal === 'function') el.nativeElement.showModal();
    });
  }

  browseItems = signal<BrowseItem[]>([]);
  browseLoading = signal(false);
  browseError = signal<string | null>(null);
  browseSearch = signal('');
  browseManual = signal(false);

  filteredBrowseItems = computed(() => {
    const q = this.browseSearch().toLowerCase().trim();
    if (!q) return this.browseItems();
    return this.browseItems().filter(
      i => i.title.toLowerCase().includes(q) || i.ref.toLowerCase().includes(q)
    );
  });

  availableArtifactTypes = computed(() => {
    const conn = this.importConnector();
    if (!conn) return ['TAREA', 'CODIGO', 'DOCUMENTO', 'PLAN', 'CAMBIO'];
    return CONNECTOR_TYPE_TO_ARTIFACT[conn.connector_type] ?? ['TAREA'];
  });

  expandedEvidence = computed(() => {
    const idx = this.expandedRule();
    if (idx === null) return null;
    const results = this.latestResult()?.rule_results;
    if (!results || idx >= results.length) return null;
    const rule = results[idx];
    const raw = rule.evidence || rule.message || null;
    return raw ? this.ts.translateInstant(raw, rule.evidence_params ?? undefined) : null;
  });

  fetchErrors = computed(() => {
    const results = this.latestResult()?.rule_results;
    if (!results) return [];
    return results.filter(r => r.rule_id === 'artifact_fetch_error');
  });

  stageLabel = computed(() => {
    const p = this.verificationProgress();
    if (!p) return this.ts.translateInstant('release_detail.verify_stage_loading');
    const key = `release_detail.verify_stage_${p.stage}`;
    return this.ts.translateInstant(key) || p.stage;
  });

  private releaseId = '';
  private orgId = '';
  private profileRules: ProfileRule[] = [];

  private loadProfileRules(profileId: string): void {
    this.releaseService.getProfileRules(profileId)
      .pipe(catchError(() => of(null)))
      .subscribe(data => {
        if (data?.rules) {
          this.profileRules = data.rules;
          this.computeMissingConnectorTypes();
        }
      });
  }

  private computeMissingConnectorTypes(): void {
    const availableTypes = new Set(this.orgConnectors().map(c => c.connector_type));
    const missing = new Set<string>();
    for (const rule of this.profileRules) {
      this.collectMissingTypesForRule(rule, availableTypes, missing);
    }
    this.missingConnectorTypes.set([...missing]);
  }

  private collectMissingTypesForRule(rule: { connector_types: string[]; connector_types_mode: string }, availableTypes: Set<string>, missing: Set<string>): void {
    if (rule.connector_types_mode === 'ANY') {
      if (!rule.connector_types.some(ct => availableTypes.has(ct))) {
        for (const ct of rule.connector_types) missing.add(ct);
      }
    } else {
      for (const ct of rule.connector_types) {
        if (!availableTypes.has(ct)) missing.add(ct);
      }
    }
  }
  private readonly browseSearchSubject = new Subject<string>();
  private browseSearchSub?: Subscription;
  private activeBrowseConn: ConnectorApiItem | null = null;
  private seenEnVerificacion = false;
  private pollingInterval?: ReturnType<typeof setInterval>;

  ngOnInit(): void {
    this.route.paramMap
      .pipe(
        switchMap((params) => {
          const id = params.get('id');
          if (!id) {
            this.loading.set(false);
            this.error.set(this.ts.translateInstant('release_detail.no_id_error'));
            return of(null);
          }
          this.releaseId = id;
          return forkJoin({
            release: this.releaseService.getRelease(id).pipe(
              catchError(() => { this.error.set(this.ts.translateInstant('release_detail.loading_error')); return of(null); }),
            ),
            artifacts: this.releaseService.listArtifacts(id).pipe(
              catchError(() => of([] as Artifact[])),
            ),
            results: this.releaseService.getResults(id).pipe(
              catchError(() => of([] as VerificationResult[])),
            ),
          });
        }),
      )
      .subscribe((data) => {
        if (!data) return;
        this.release.set(data.release);
        this.artifacts.set(data.artifacts || []);
        const results = data.results || [];
        this.verificationHistory.set(results);
        if (results.length > 0) {
          this.latestResult.set(results[0]);
        }
        const orgId = data.release?.organization_id;
        if (orgId) {
          this.orgId = orgId;
          this.connectorsLoading.set(true);
          this.connectorService.list(orgId)
            .pipe(catchError(() => of([] as ConnectorApiItem[])))
            .subscribe(connectors => {
              this.orgConnectors.set(connectors);
              this.connectorsLoading.set(false);
              this.computeMissingConnectorTypes();
            });
        }
        const profileId = data.release?.profile_id;
        if (profileId && orgId) {
          this.loadProfileRules(profileId);
        }
        if (data.release?.status === 'EN_VERIFICACION' && data.release.pending_task_id && !this.pollingInterval) {
          this.taskId.set(data.release.pending_task_id);
          this.seenEnVerificacion = true;
          this.refreshAndPoll();
        }
        this.loading.set(false);
      });
  }

  launchVerification(): void {
    if (!this.releaseId || this.verifying()) return;
    if (this.artifacts().length === 0) return;
    this.verifying.set(true);
    if ('Notification' in globalThis && Notification.permission === 'default') {
      Notification.requestPermission();
    }
    this.releaseService
      .verify(this.releaseId)
      .pipe(
        catchError(() => {
          this.error.set(this.ts.translateInstant('release_detail.verification_error'));
          this.verifying.set(false);
          return of(null);
        }),
      )
      .subscribe((result) => {
        if (result) {
          this.taskId.set(result.task_id);
          this.verificationProgress.set({ current: 0, total: 1, stage: 'loading', pct: 0 });
          this.seenEnVerificacion = true;
          this.showVerifyNotice.set(true);
          this.refreshAndPoll();
        } else {
          this.verificationProgress.set(null);
          this.verifying.set(false);
        }
      });
  }

  dismissVerifyNotice(): void {
    this.showVerifyNotice.set(false);
  }

  cancelVerification(): void {
    if (!this.releaseId) return;
    this.releaseService
      .cancel(this.releaseId)
      .pipe(
        catchError(() => {
          this.toast.error(this.ts.translateInstant('release_detail.cancel_verification_error'));
          return of(null);
        }),
      )
      .subscribe((result) => {
        if (result?.cancelled) {
          this.seenEnVerificacion = false;
          this.stopPolling();
          this.verifying.set(false);
          this.showVerifyNotice.set(false);
          this.reloadData();
          this.toast.info(this.ts.translateInstant('release_detail.cancel_verification_success'), 4000);
        }
      });
  }

  private refreshAndPoll(): void {
    this.stopPolling();
    this.pollOnce();
    this.pollingInterval = setInterval(() => this.pollOnce(), 3000);
  }

  private pollOnce(): void {
    const tid = this.taskId();
    const taskObs = tid
      ? this.releaseService.getTaskStatus(tid).pipe(catchError(() => of(null)))
      : of(null);

    forkJoin({
      release: this.releaseService.getRelease(this.releaseId).pipe(catchError(() => of(null))),
      task: taskObs,
    }).subscribe(({ release, task }) => {
      if (task?.progress) this.verificationProgress.set(task.progress);
      if (!release) return;
      this.release.set(release);
      if (release.status === 'EN_VERIFICACION') {
        this.seenEnVerificacion = true;
        return;
      }
      if (!this.seenEnVerificacion) return;
      this.seenEnVerificacion = false;
      this.stopPolling();
      this.verifying.set(false);
      this.showVerifyNotice.set(false);
      this.reloadData();
      const TERMINAL = ['VALIDA', 'NO_VALIDA', 'CON_ADVERTENCIAS'];
      if (TERMINAL.includes(release.status)) {
        this.toast.info(this.ts.translateInstant('release_detail.verify_complete_toast'), 6000);
        this.showBrowserNotification(release);
      } else {
        this.toast.error(this.ts.translateInstant('release_detail.verify_failed_toast'), 6000);
      }
    });
  }

  private reloadData(): void {
    this.error.set(null);
    forkJoin({
      release: this.releaseService.getRelease(this.releaseId).pipe(
        catchError(() => { this.error.set(this.ts.translateInstant('release_detail.loading_error')); return of(null); }),
      ),
      artifacts: this.releaseService.listArtifacts(this.releaseId).pipe(
        catchError(() => of([] as Artifact[])),
      ),
      results: this.releaseService.getResults(this.releaseId).pipe(
        catchError(() => of([] as VerificationResult[])),
      ),
    }).subscribe(data => {
      if (data.release) this.release.set(data.release);
      this.artifacts.set(data.artifacts || []);
      const results = data.results || [];
      this.verificationHistory.set(results);
      if (results.length > 0) {
        this.latestResult.set(results[0]);
      }
    });
  }

  private stopPolling(): void {
    if (this.pollingInterval !== undefined) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = undefined;
    }
    this.verificationProgress.set(null);
  }

  private showBrowserNotification(release: ReleaseDetail): void {
    if ('Notification' in globalThis && Notification.permission === 'granted') {
      new Notification(this.ts.translateInstant('release_detail.verify_notif_title'), {
        body: this.ts.translateInstant('release_detail.verify_notif_body', { name: release.name }),
      });
    }
  }

  openImportModal(): void {
    this.importConnector.set(null);
    this.importArtifactType.set('TAREA');
    this.importExternalRef.set('');
    this.importDescription.set('');
    this.importError.set(null);
    this.browseItems.set([]);
    this.browseError.set(null);
    this.browseSearch.set('');
    this.browseManual.set(false);
    this.showImportModal.set(true);
  }

  closeImportModal(): void {
    this.showImportModal.set(false);
  }

  ngOnDestroy(): void {
    this.browseSearchSub?.unsubscribe();
    this.stopPolling();
  }

  onConnectorSelect(connectorId: string): void {
    const conn = this.orgConnectors().find(c => c.id === connectorId);
    this.importConnector.set(conn || null);
    this.importExternalRef.set('');
    this.importDescription.set('');
    this.browseItems.set([]);
    this.browseError.set(null);
    this.browseSearch.set('');
    this.browseManual.set(false);

    if (!conn) return;

    this.activeBrowseConn = conn;
    const artifactTypes = CONNECTOR_TYPE_TO_ARTIFACT[conn.connector_type] ?? ['TAREA'];
    this.importArtifactType.set(artifactTypes[0]);

    // Cargar sin filtro de texto: cada conector expone un listado por defecto
    // (issues abiertas, páginas recientes, tareas de la lista configurada...).
    // Precargar con el nombre de la entrega restringía la búsqueda a coincidencias
    // literales de texto, que casi nunca existen fuera de Confluence.
    this.fetchBrowseItems(conn, '');

    this.browseSearchSub?.unsubscribe();
    this.browseSearchSub = this.browseSearchSubject.pipe(
      debounceTime(400),
      distinctUntilChanged(),
    ).subscribe(q => {
      if (this.activeBrowseConn) this.fetchBrowseItems(this.activeBrowseConn, q);
    });
  }

  onBrowseSearchInput(value: string): void {
    this.browseSearch.set(value);
    this.browseSearchSubject.next(value);
  }

  private fetchBrowseItems(conn: ConnectorApiItem, q: string): void {
    this.browseLoading.set(true);
    this.browseError.set(null);
    this.releaseService.browseConnector(this.orgId, conn.id, q)
      .pipe(catchError(() => {
      this.browseError.set(this.ts.translateInstant('release.browse_error'));
      this.browseLoading.set(false);
      return of([] as BrowseItem[]);
    })).subscribe(items => {
      this.browseItems.set(items);
      this.browseLoading.set(false);
    });
  }

  selectBrowseItem(item: BrowseItem): void {
    this.importExternalRef.set(item.ref);
    this.importDescription.set(item.title);
  }

  clearBrowseSelection(): void {
    this.importExternalRef.set('');
    this.importDescription.set('');
  }

  importArtifacts(): void {
    const connector = this.importConnector();
    if (!connector || !this.importExternalRef()) {
      this.importError.set(this.ts.translateInstant('release.select_connector_error'));
      return;
    }
    this.importing.set(true);
    this.importError.set(null);

    const body = {
      artifacts: [{
        connector_instance_id: connector.id,
        connector_implementation: connector.connector_implementation,
        artifact_type: this.importArtifactType(),
        external_ref: this.importExternalRef(),
        description: this.importDescription(),
      }],
    };

    this.releaseService.importArtifacts(this.releaseId, body)
      .pipe(
        catchError((err) => {
          this.importError.set(err.error?.detail || this.ts.translateInstant('release.import_error'));
          this.importing.set(false);
          return of(null);
        }),
      )
      .subscribe((result: any) => {
        this.importing.set(false);
        if (result) {
          this.closeImportModal();
          this.releaseService.listArtifacts(this.releaseId)
            .pipe(catchError(() => of([] as Artifact[])))
            .subscribe(artifacts => this.artifacts.set(artifacts));
        }
      });
  }

  deleteArtifact(artifactId: string): void {
    this.artifactToDelete.set(artifactId);
  }

  confirmDeleteArtifact(): void {
    const artifactId = this.artifactToDelete();
    if (!artifactId) return;
    this.artifactToDelete.set(null);
    
    this.releaseService.deleteArtifact(this.releaseId, artifactId)
      .pipe(
        catchError(() => {
          this.toast.error(this.ts.translateInstant('release.artifact_delete_error'));
          return EMPTY;
        }),
      )
      .subscribe(() => {
        this.artifacts.update(list => list.filter(a => a.id !== artifactId));
        this.toast.success(this.ts.translateInstant('release.artifact_delete_success'));
      });
  }

  loadResultDetail(resultId: string): void {
    this.releaseService
      .getResultDetail(this.releaseId, resultId)
      .pipe(catchError(() => of(null)))
      .subscribe((result) => {
        if (result) {
          this.latestResult.set(result);
        }
      });
  }

  exportPdf(): void {
    const result = this.latestResult();
    if (!result) return;
    this.releaseService.exportResultPdf(
      this.releaseId, result.id, this.ts.currentLang ?? 'es'
    ).pipe(
      catchError(() => {
        this.toast.error(this.ts.translateInstant('release_detail.export_error'));
        return EMPTY;
      })
    ).subscribe(blob => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const lang = this.ts.currentLang ?? 'es';
      const slugify = (s: string) => {
        const normalized = s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
        const dashed = normalized.replace(/[^a-z0-9]+/g, '-');
        let start = 0;
        while (start < dashed.length && dashed[start] === '-') start++;
        let end = dashed.length;
        while (end > start && dashed[end - 1] === '-') end--;
        return dashed.slice(start, end);
      };
      const orgName  = slugify(this.release()?.organization_name ?? 'org');
      const dateStr  = result.executed_at
        ? new Date(result.executed_at).toISOString().slice(0, 10)
        : new Date().toISOString().slice(0, 10);
      const word     = lang === 'en' ? 'verification' : 'verificacion';
      a.download = `${orgName}-${dateStr}-${word}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    });
  }

  toggleEvidence(index: number): void {
    this.expandedRule.update((current) => (current === index ? null : index));
  }

  get latestVerdict(): string | null {
    return this.latestResult()?.verdict || null;
  }

  verdictBannerClass(): Record<string, boolean> {
    const v = this.latestVerdict;
    return {
      'verdict-banner-valid': v === 'VALID',
      'verdict-banner-warning': v === 'WITH_WARNINGS' || v === 'VALID_WITH_WARNINGS',
      'verdict-banner-invalid': v === 'INVALID',
      'verdict-banner-unevaluated': !v || v === 'NOT_EVALUATED',
    };
  }

  verdictBadgeClass(): Record<string, boolean> {
    const v = this.latestVerdict;
    return {
      'verdict-badge-valid': v === 'VALID',
      'verdict-badge-warning': v === 'WITH_WARNINGS' || v === 'VALID_WITH_WARNINGS',
      'verdict-badge-invalid': v === 'INVALID',
      'verdict-badge-unevaluated': !v || v === 'NOT_EVALUATED',
    };
  }

  verdictIcon(): string {
    const v = this.latestVerdict;
    if (v === 'VALID') return '\u2713';
    if (v === 'WITH_WARNINGS' || v === 'VALID_WITH_WARNINGS') return '\u26A0';
    if (v === 'INVALID') return '\u2715';
    return '\u2014';
  }

  verdictLabel(): string {
    return this.ts.translateInstant('verdict.' + (this.latestVerdict || 'NOT_EVALUATED'));
  }

  statusBadgeClass(): Record<string, boolean> {
    const s = (this.release()?.status || '').toLowerCase();
    return {
      'status-borrador': s === 'borrador',
      'status-pendiente': s === 'pendiente',
      'status-en_verificacion': s === 'en_verificacion',
      'status-valida': s === 'valida',
      'status-con_advertencias': s === 'con_advertencias',
      'status-no_valida': s === 'no_valida',
      'status-archivada': s === 'archivada',
    };
  }

  ruleResultClass(result: string): Record<string, boolean> {
    const r = result?.toUpperCase() || '';
    return {
      'result-valid': r === 'VALID' || r === 'PASSED' || r === 'SUCCESS' || r === 'OK',
      'result-warning': r === 'WITH_WARNINGS' || r === 'WARNING' || r === 'VALID_WITH_WARNINGS',
      'result-invalid': r === 'INVALID' || r === 'FAILED' || r === 'ERROR',
      'result-unevaluated': !r || r === 'NOT_EVALUATED' || r === 'SKIPPED' || r === 'NO_EVALUADA',
    };
  }

  verdictBadgeMap(verdict: string): Record<string, boolean> {
    return this.ruleResultClass(verdict);
  }

  verdictLabelMap(verdict: string): string {
    return this.ts.translateInstant('verdict.' + (verdict?.toUpperCase() || 'NOT_EVALUATED'));
  }

  

  translateVerdict(verdict: string): string {
    return this.ts.translateInstant('verdict.' + verdict);
  }

  translateRuleResult(result: string): string {
    return this.ts.translateInstant('rule_result.' + result);
  }

  translateRuleName(rule: { rule_id?: string; rule_name?: string }): string {
    const key = 'rules.' + (rule.rule_id ?? '');
    const translated = this.ts.translateInstant(key);
    if (!translated || translated === key) return rule.rule_name ?? rule.rule_id ?? '';
    return translated;
  }

  translateEvidence(raw: string | null | undefined, params?: Record<string, string | number>): string {
    if (!raw) return '';
    const translated = this.ts.translateInstant(raw, params);
    return translated;
  }

  isSummaryString(summary: Record<string, number> | string): summary is string {
    return typeof summary === 'string';
  }

  summaryTotal(summary: Record<string, number> | string): number {
    if (typeof summary !== 'object' || summary === null) return 0;
    const total = summary['TOTAL'];
    return typeof total === 'number' ? total : 0;
  }

  summaryStatusItems(summary: Record<string, number> | string): Array<[string, number]> {
    if (typeof summary !== 'object' || summary === null) return [];
    return Object.entries(summary)
      .filter(([key]) => key !== 'TOTAL')
      .sort((a, b) => b[1] - a[1]) as Array<[string, number]>;
  }

  summaryItems(summary: Record<string, number> | string): Array<[string, number]> {
    if (typeof summary !== 'object' || summary === null) return [];
    return Object.entries(summary).sort((a, b) => b[1] - a[1]) as Array<[string, number]>;
  }
}
