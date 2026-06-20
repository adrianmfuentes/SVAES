import { Component, inject, OnInit, OnDestroy, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, ActivatedRoute } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { TranslationService } from '../../../core/i18n/translation.service';
import { TranslatePipe } from '../../../core/i18n/translate.pipe';
import { ToastService } from '../../../core/services/toast.service';
import { ConfirmDialogComponent } from '../../../core/components/confirm-dialog/confirm-dialog.component';
import { catchError, debounceTime, distinctUntilChanged, EMPTY, forkJoin, of, Subject, Subscription, switchMap } from 'rxjs';

interface ReleaseDetail {
  id: string;
  name: string;
  version: string;
  description: string;
  status: string;
  project_id: string;
  profile_id: string;
  created_by: string;
  created_at: string;
  updated_at: string;
  organization_id?: string;
  project_name?: string;
  organization_name?: string;
  pending_task_id?: string | null;
}

interface VerificationProgress {
  current: number;
  total: number;
  stage: string;
  pct: number;
}

interface Artifact {
  id: string;
  release_id: string;
  connector_instance_id: string;
  connector_implementation: string;
  artifact_type: string;
  external_ref: string;
  description?: string;
  metadata?: Record<string, unknown>;
  created_at?: string;
}

interface RuleResult {
  rule_id: string;
  rule_name?: string;
  connector?: string;
  status?: string;
  result?: string;
  message?: string;
  evidence?: string;
  severity?: string;
}

interface ConnectorApiItem {
  id: string;
  name: string;
  connector_type: string;
  connector_implementation: string;
  status: string;
  created_at: string;
  last_tested_at?: string;
}

interface BrowseItem {
  ref: string;
  title: string;
  subtitle: string;
}

const CONNECTOR_TYPE_TO_ARTIFACT: Record<string, string> = {
  'GESTOR_TAREAS': 'TAREA',
  'REPO_CODIGO': 'CODIGO',
  'SISTEMA_DOCUMENTAL': 'DOCUMENTO',
  'GESTION_CAMBIOS': 'TAREA',
};

interface VerificationResult {
  id: string;
  release_id: string;
  verdict: string;
  rule_results: RuleResult[];
  summary: Record<string, number> | string;
  profile_snapshot?: Record<string, unknown>;
  duration_ms: number;
  executed_at: string;
}

@Component({
  selector: 'app-release-detail',
  standalone: true,
  imports: [CommonModule, RouterModule, TranslatePipe, ConfirmDialogComponent],
  template: `
    <div class="detail-page">
      <div class="page-header">
        <div class="page-header-left">
          <a routerLink="/app/releases" class="back-link">{{ 'release_detail.back_releases' | t }}</a>
          <h1 class="page-title">{{ release()?.name || ('common.loading' | t) }}</h1>
        </div>
        <div class="page-header-actions">
          <button class="btn-secondary" (click)="exportPdf()">
            {{ 'release_detail.export_pdf' | t }}
          </button>
        </div>
      </div>

      @if (loading()) {
        <div class="skeleton-block">
          <div class="skeleton skeleton-banner"></div>
          <div class="skeleton skeleton-card"></div>
          <div class="skeleton skeleton-row" *ngFor="let i of [1,2,3,4,5]"></div>
        </div>
      }

      @if (error() && !loading()) {
        <div class="error-banner">{{ error() }}</div>
      }

      @if (!loading() && !error() && release()) {
        <!-- Verdict banner -->
        @if (latestVerdict) {
          <div class="verdict-banner" [ngClass]="verdictBannerClass()">
            <span class="verdict-icon">{{ verdictIcon() }}</span>
            <span class="verdict-badge" [ngClass]="verdictBadgeClass()">{{ verdictLabel() }}</span>
            <code class="verdict-release-id">{{ release()!.id | slice:0:8 }}</code>
            <span class="verdict-separator">|</span>
            <span class="verdict-timestamp">{{ latestResult()?.executed_at | date:'dd MMM yyyy, HH:mm:ss' }}</span>
          </div>
        }

        <!-- Release info card -->
        <div class="card info-card">
          <h2 class="card-title">{{ release()!.name }}</h2>
          <div class="info-grid">
            <div class="info-field">
              <span class="info-label">{{ 'release_detail.field_version' | t }}</span>
              <span class="info-value">{{ release()!.version }}</span>
            </div>
            <div class="info-field">
              <span class="info-label">{{ 'release_detail.field_status' | t }}</span>
              <span class="verdict-badge-sm" [ngClass]="statusBadgeClass()">{{ release()!.status }}</span>
            </div>
            <div class="info-field">
              <span class="info-label">{{ 'release_detail.project' | t }}</span>
              <span class="info-value">{{ release()!.project_name || release()!.project_id | slice:0:8 }}</span>
            </div>
            <div class="info-field">
              <span class="info-label">{{ 'release_detail.field_org' | t }}</span>
              <span class="info-value text-muted">{{ release()!.organization_name || '—' }}</span>
            </div>
            <div class="info-field">
              <span class="info-label">{{ 'release_detail.field_created' | t }}</span>
              <span class="info-value text-muted">{{ release()!.created_at | date:'dd MMM yyyy, HH:mm' }}</span>
            </div>
            <div class="info-field">
              <span class="info-label">{{ 'release_detail.field_updated' | t }}</span>
              <span class="info-value text-muted">{{ release()!.updated_at | date:'dd MMM yyyy, HH:mm' }}</span>
            </div>
          </div>
          @if (release()!.description) {
            <div class="info-description">
              <span class="info-label">{{ 'common.description' | t }}</span>
              <p class="info-description-text">{{ release()!.description }}</p>
            </div>
          }
        </div>

        <!-- Verification progress card -->
        @if (release()?.status === 'EN_VERIFICACION') {
          <div class="verification-progress-card" role="status" aria-live="polite">
            <div class="vp-header">
              <span class="vp-dot" aria-hidden="true"></span>
              <span class="vp-title">{{ 'release_detail.verify_progress_title' | t }}</span>
              <span class="vp-pct" aria-hidden="true">{{ verificationProgress()?.pct ?? 0 }}%</span>
            </div>
            <div
              class="vp-bar-track"
              role="progressbar"
              [attr.aria-valuenow]="verificationProgress()?.pct ?? 0"
              aria-valuemin="0"
              aria-valuemax="100">
              <div class="vp-bar-fill" [style.width.%]="verificationProgress()?.pct ?? 0"></div>
            </div>
            <span class="vp-stage">{{ stageLabel() }}</span>
          </div>
        }

        <!-- Verification rule results table -->
        @if (latestResult(); as result) {
          <div class="card rules-section">
            <h2 class="card-title">{{ 'release_detail.verification_title' | t }}</h2>
            <div class="data-table-wrap">
              <table class="data-table rules-table">
                <thead>
                  <tr>
                    <th scope="col" class="col-id">{{ 'release_detail.rule_id' | t }}</th>
                    <th scope="col" class="col-name">{{ 'release_detail.rule_name' | t }}</th>
                    <th scope="col" class="col-connector">{{ 'release_detail.rule_connector' | t }}</th>
                    <th scope="col" class="col-result">{{ 'release_detail.rule_result' | t }}</th>
                    <th scope="col" class="col-evidence">{{ 'release_detail.rule_evidence' | t }}</th>
                  </tr>
                </thead>
                <tbody>
                  @for (rule of result.rule_results; track rule.rule_id; let i = $index) {
                    <tr
                      [class.expanded]="expandedRule() === i"
                      (click)="toggleEvidence(i)">
                      <td><code class="mono-sm">{{ rule.rule_id | slice:0:8 }}</code></td>
                      <td class="cell-primary">{{ rule.rule_name || ('common.dash' | t) }}</td>
                      <td class="cell-muted">{{ rule.connector || ('common.dash' | t) }}</td>
                      <td>
                        <span class="verdict-badge" [ngClass]="ruleResultClass(rule.status ?? rule.result ?? '')">
                          {{ translateRuleResult(rule.status ?? rule.result ?? '') }}
                        </span>
                      </td>
                      <td class="cell-evidence" (click)="$event.stopPropagation()">
                        @let evidenceText = rule.evidence ?? rule.message;
                        @if (evidenceText) {
                          <span>{{ evidenceText | slice:0:100 }}{{ evidenceText.length > 100 ? '…' : '' }}</span>
                          @if (evidenceText.length > 100) {
                            <button class="btn-expand" (click)="toggleEvidence(i)">{{ 'release_detail.see_more_btn' | t }}</button>
                          }
                        } @else {
                          <span class="cell-muted">{{ 'common.dash' | t }}</span>
                        }
                      </td>
                    </tr>
                    @let expandedEvidence = rule.evidence ?? rule.message;
                    @if (expandedRule() === i && expandedEvidence) {
                      <tr class="evidence-row">
                        <td colspan="5">
                          <pre class="evidence-block">{{ expandedEvidence }}</pre>
                        </td>
                      </tr>
                    }
                  }
                </tbody>
              </table>
            </div>
            @if (result.summary) {
              <div class="summary-bar">
                <span class="summary-label">{{ 'release_detail.summary_label' | t }}</span>
                @if (isSummaryString(result.summary)) {
                  <span class="summary-text cell-muted">{{ result.summary }}</span>
                } @else {
                  @for (item of summaryItems(result.summary); track item[0]) {
                    <span class="summary-chip" [ngClass]="ruleResultClass(item[0])">
                      {{ item[1] }} {{ translateRuleResult(item[0]) }}
                    </span>
                  }
                }
                <span class="summary-duration text-muted">{{ result.duration_ms }}ms</span>
              </div>
            }
          </div>
        }

        <!-- Artifacts section -->
        <div class="card artifacts-section">
          <div class="section-header">
            <h2 class="card-title">{{ 'release_detail.artifacts_title' | t : { n: artifacts().length } }}</h2>
            <div class="section-actions">
              @if (artifacts().length > 0) {
                @if (release()?.status === 'EN_VERIFICACION') {
                  <button class="btn-danger" (click)="cancelVerification()">
                    {{ 'release_detail.cancel_verification' | t }}
                  </button>
                } @else {
                  <button
                    class="btn-accent"
                    [disabled]="verifying()"
                    (click)="launchVerification()">
                    @if (verifying()) { {{ 'release_detail.verifying_label' | t }} } @else { {{ 'release_detail.verify_label' | t }} }
                  </button>
                }
              }
              <button class="btn-secondary" (click)="openImportModal()">{{ 'release.import_artifacts' | t }}</button>
            </div>
          </div>
          @if (artifacts().length > 0) {
            <div class="data-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th scope="col">{{ 'release_detail.col_type' | t }}</th>
                    <th scope="col">{{ 'release_detail.rule_connector' | t }}</th>
                    <th scope="col">{{ 'release_detail.col_ext_ref' | t }}</th>
                    <th scope="col">{{ 'common.description' | t }}</th>
                    <th scope="col" class="col-actions"></th>
                  </tr>
                </thead>
                <tbody>
                  @for (a of artifacts(); track a.id) {
                    <tr>
                      <td>
                        <span class="artifact-type-badge">{{ ts.translateInstant('artifact_type.' + a.artifact_type) }}</span>
                      </td>
                      <td class="cell-muted">{{ ts.translateInstant('connector_type.' + a.connector_implementation) || a.connector_implementation }}</td>
                      <td><code class="mono-sm">{{ a.external_ref }}</code></td>
                      <td class="cell-muted">{{ a.description || ('common.dash' | t) }}</td>
                      <td class="cell-actions">
                        <button class="btn-icon btn-danger" (click)="deleteArtifact(a.id)" [title]="'common.delete' | t">
                          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                            <path d="M2 4h10M5 4V3a1 1 0 011-1h2a1 1 0 011 1v1M11 4v8a1 1 0 01-1 1H4a1 1 0 01-1-1V4" stroke="currentColor" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round"/>
                          </svg>
                        </button>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          } @else {
            <div class="empty-state">
              <p class="empty-state-text">{{ 'release.no_artifacts' | t }}</p>
              <button class="btn-accent" (click)="openImportModal()">{{ 'release.import_first_artifact' | t }}</button>
            </div>
          }
        </div>

        <!-- Import Artifacts Modal -->
        @if (showImportModal()) {
          <div class="modal-overlay" (click)="closeImportModal()" role="dialog" aria-modal="true" aria-labelledby="import-modal-title">
            <div class="modal-panel" (click)="$event.stopPropagation()">
              <div class="modal-header">
                <h3 class="modal-title" id="import-modal-title">{{ 'release.import_artifacts' | t }}</h3>
                <button class="modal-close" (click)="closeImportModal()" [attr.aria-label]="'common.close' | t">&times;</button>
              </div>

              <!-- Connector selector -->
              <div class="form-group">
                <label class="form-label" for="import-connector">{{ 'release.artifact_connector' | t }}</label>
                @if (connectorsLoading()) {
                  <p class="form-hint">{{ 'release.loading_connectors' | t }}</p>
                } @else if (orgConnectors().length === 0) {
                  <p class="form-hint form-hint--warn">{{ 'release.no_connectors' | t }}</p>
                } @else {
                  <select id="import-connector" class="form-select" (change)="onConnectorSelect($any($event.target).value)">
                    <option value="">{{ 'release.select_connector' | t }}</option>
                    @for (conn of orgConnectors(); track conn.id) {
                      <option [value]="conn.id">{{ conn.name }} · {{ conn.connector_type }}</option>
                    }
                  </select>
                }
                @if (importConnector(); as conn) {
                  <div class="connector-meta">
                    <span class="connector-meta-type">{{ conn.connector_type }}</span>
                    <span class="connector-meta-status">{{ 'release.connector_status_active' | t }}</span>
                  </div>
                }
              </div>

              <!-- Artifact type — auto-set from connector type, still editable -->
              <div class="form-group">
                <label class="form-label" for="import-type">{{ 'release.artifact_type' | t }}</label>
                <select id="import-type" class="form-select" [value]="importArtifactType()" (change)="importArtifactType.set($any($event.target).value)">
                  <option value="TAREA">{{ 'artifact_type.TAREA' | t }}</option>
                  <option value="CODIGO">{{ 'artifact_type.CODIGO' | t }}</option>
                  <option value="DOCUMENTO">{{ 'artifact_type.DOCUMENTO' | t }}</option>
                </select>
              </div>

              <!-- Smart reference picker: browse items from connector or manual fallback -->
              @if (importConnector()) {
                <div class="form-group">
                  <label class="form-label">{{ 'release.external_ref' | t }}</label>

                  @if (browseLoading()) {
                    <p class="form-hint">{{ 'release.browse_loading' | t }}</p>
                  } @else if (browseError() && !browseManual()) {
                    <p class="form-hint form-hint--warn">{{ 'release.browse_error' | t }}</p>
                    <button type="button" class="btn-link" (click)="browseManual.set(true)">
                      {{ 'release.browse_manual_label' | t }}
                    </button>
                  } @else if (!browseManual() && browseItems().length > 0) {
                    <!-- Selected item display -->
                    @if (importExternalRef()) {
                      <div class="browse-selected">
                        <div class="browse-selected-info">
                          <span class="browse-selected-title">{{ importDescription() || importExternalRef() }}</span>
                          <code class="browse-selected-ref">{{ importExternalRef() }}</code>
                        </div>
                        <button type="button" class="btn-icon btn-danger" (click)="clearBrowseSelection()" aria-label="Clear selection">✕</button>
                      </div>
                    } @else {
                      <!-- Search + list -->
                      <input type="text" class="form-input browse-search"
                        [placeholder]="'release.browse_search_placeholder' | t"
                        [value]="browseSearch()"
                        (input)="onBrowseSearchInput($any($event.target).value)"
                        autocomplete="off" />
                      <div class="browse-list" role="listbox" aria-label="Available items">
                        @for (item of filteredBrowseItems(); track item.ref) {
                          <button type="button" class="browse-item" role="option"
                            (click)="selectBrowseItem(item)">
                            <span class="browse-item-title">{{ item.title }}</span>
                            <span class="browse-item-meta">
                              <code class="browse-item-ref">{{ item.ref }}</code>
                              @if (item.subtitle) {
                                <span class="browse-item-sub">{{ item.subtitle }}</span>
                              }
                            </span>
                          </button>
                        }
                        @if (filteredBrowseItems().length === 0) {
                          <p class="browse-empty">{{ 'release.browse_empty' | t }}</p>
                        }
                      </div>
                      <button type="button" class="btn-link" (click)="browseManual.set(true)">
                        {{ 'release.browse_manual_label' | t }}
                      </button>
                    }
                  } @else if (!browseManual() && browseItems().length === 0 && !browseLoading()) {
                    <p class="form-hint">{{ 'release.browse_empty' | t }}</p>
                    <button type="button" class="btn-link" (click)="browseManual.set(true)">
                      {{ 'release.browse_manual_label' | t }}
                    </button>
                  }

                  @if (browseManual()) {
                    <input id="import-ref" type="text" class="form-input"
                      [placeholder]="'release.external_ref_placeholder' | t"
                      [value]="importExternalRef()"
                      (input)="importExternalRef.set($any($event.target).value)" />
                  }
                </div>
              }

              <!-- Description — pre-filled from selected item, still editable -->
              <div class="form-group">
                <label class="form-label" for="import-desc">{{ 'release.description_optional' | t }}</label>
                <input id="import-desc" type="text" class="form-input"
                  [placeholder]="'release.description_placeholder' | t"
                  [value]="importDescription()"
                  (input)="importDescription.set($any($event.target).value)" />
              </div>

              @if (importError()) {
                <div class="error-banner error-banner-sm" role="alert">{{ importError() }}</div>
              }
              <div class="modal-footer">
                <button type="button" class="btn-secondary" (click)="closeImportModal()">{{ 'common.cancel' | t }}</button>
                <button type="button" class="btn-accent"
                  [disabled]="importing() || !importConnector() || !importExternalRef()"
                  (click)="importArtifacts()">
                  {{ importing() ? ('release.importing' | t) : ('release.import' | t) }}
                </button>
              </div>
            </div>
          </div>
        }

        <!-- Verification history -->
        @if (verificationHistory().length > 1) {
          <div class="card history-section">
            <h2 class="card-title">{{ 'release_detail.history' | t }}</h2>
            <div class="data-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th scope="col">{{ 'release_detail.history_verdict' | t }}</th>
                    <th scope="col">{{ 'release_detail.col_duration' | t }}</th>
                    <th scope="col">{{ 'release_detail.col_executed' | t }}</th>
                    <th scope="col"></th>
                  </tr>
                </thead>
                <tbody>
                  @for (h of verificationHistory(); track h.id) {
                    <tr>
                      <td>
                        <span class="verdict-badge" [ngClass]="verdictBadgeMap(h.verdict)">
                          {{ translateVerdict(h.verdict) }}
                        </span>
                      </td>
                      <td class="cell-muted">{{ h.duration_ms }}ms</td>
                      <td class="cell-muted">{{ h.executed_at | date:'dd MMM yyyy, HH:mm' }}</td>
                      <td class="cell-action">
                        <button class="btn-ghost" (click)="loadResultDetail(h.id)">{{ 'release_detail.see_btn' | t }}</button>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </div>
        }

        @if (!latestResult() && artifacts().length === 0) {
          <div class="card empty-card">
            <p class="empty-text">{{ 'release_detail.empty_desc' | t }}</p>
            <p class="empty-hint">{{ 'release_detail.add_artifact_first' | t }}</p>
            <button class="btn-accent" disabled>
              {{ 'release_detail.start_verification_btn' | t }}
            </button>
          </div>
        }
      }

      <!-- Verification launch notice overlay -->
      @if (showVerifyNotice()) {
        <div class="verify-overlay" role="dialog" aria-modal="true" aria-labelledby="verify-notice-title">
          <div class="verify-notice-panel">
            <div class="verify-scanner">
              <div class="scanner-ring scanner-ring-1"></div>
              <div class="scanner-ring scanner-ring-2"></div>
              <div class="scanner-ring scanner-ring-3"></div>
              <div class="scanner-core">
                <svg width="26" height="26" viewBox="0 0 28 28" fill="none" aria-hidden="true">
                  <rect x="5" y="3" width="13" height="17" rx="2" stroke="currentColor" stroke-width="1.5"/>
                  <path d="M9 9h5M9 13h5M9 17h3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                  <circle cx="20" cy="20" r="5" fill="var(--ink)" stroke="currentColor" stroke-width="1.5"/>
                  <path d="M17.5 20l1.5 1.5 3-3" stroke="currentColor" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </div>
            </div>
            <div class="verify-notice-body">
              <h2 class="verify-notice-title" id="verify-notice-title">{{ 'release_detail.verify_launched_title' | t }}</h2>
              <p class="verify-notice-desc">{{ 'release_detail.verify_launched_desc' | t }}</p>
              <div class="verify-channels">
                <span class="verify-channel">
                  <svg width="12" height="12" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                    <circle cx="7" cy="7" r="5.5" stroke="currentColor" stroke-width="1.25"/>
                    <path d="M7 1.5C7 1.5 5 4 5 7s2 5.5 2 5.5M7 1.5C7 1.5 9 4 9 7s-2 5.5-2 5.5M1.5 7h11" stroke="currentColor" stroke-width="1.25"/>
                  </svg>
                  {{ 'release_detail.verify_channel_web' | t }}
                </span>
                <span class="verify-channel">
                  <svg width="12" height="12" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                    <rect x="1.5" y="3" width="11" height="8" rx="1.5" stroke="currentColor" stroke-width="1.25"/>
                    <path d="M1.5 4.5l5.5 4 5.5-4" stroke="currentColor" stroke-width="1.25" stroke-linecap="round"/>
                  </svg>
                  {{ 'release_detail.verify_channel_email' | t }}
                </span>
              </div>

              @if (verificationProgress(); as p) {
                <div class="vp-overlay-progress" role="progressbar" [attr.aria-valuenow]="p.pct" aria-valuemin="0" aria-valuemax="100">
                  <div class="vp-overlay-bar-track">
                    <div class="vp-overlay-bar-fill" [style.width.%]="p.pct"></div>
                  </div>
                  <span class="vp-overlay-stage">{{ stageLabel() }}</span>
                </div>
              }
            </div>
            <button class="verify-notice-dismiss" (click)="dismissVerifyNotice()">
              {{ 'release_detail.verify_launched_dismiss' | t }}
            </button>
          </div>
        </div>
      }
    </div>

    @if (artifactToDelete()) {
      <app-confirm-dialog
        [title]="ts.translateInstant('release.confirm_delete_artifact_title')"
        [message]="ts.translateInstant('release.confirm_delete_artifact_message')"
        [confirmText]="ts.translateInstant('common.delete')"
        [cancelText]="ts.translateInstant('common.cancel')"
        (confirmed)="confirmDeleteArtifact()"
        (cancelled)="artifactToDelete.set(null)">
      </app-confirm-dialog>
    }
  `,
  styles: [`
    :host { display: block; }

    .detail-page { padding: 0; }

    .page-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      margin-bottom: var(--spacing-lg);
      flex-wrap: wrap;
      gap: var(--spacing-md);
    }

    .page-header-left {
      display: flex;
      flex-direction: column;
      gap: var(--spacing-xs);
    }

    .back-link {
      font-family: var(--font-sans);
      font-size: 0.8125rem;
      color: var(--muted);
      text-decoration: none;
      transition: color 0.12s ease;
    }

    .back-link:hover { color: var(--ink); }

    .page-title {
      font-family: var(--font-display);
      font-size: 2.25rem;
      font-weight: 400;
      line-height: 1.1;
      letter-spacing: -0.02em;
      margin: 0;
      color: var(--ink);
    }

    .page-header-actions {
      display: flex;
      gap: var(--spacing-sm);
    }

    /* Verdict banner */
    .verdict-banner {
      height: 3.5rem;
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0 1.5rem;
      border-radius: var(--rounded-md);
      margin-bottom: var(--spacing-lg);
      border: 0.0625rem solid;
    }

    .verdict-banner-valid {
      background: var(--verdict-valid-bg);
      border-color: var(--verdict-valid-border);
      border-left: 0.25rem solid var(--verdict-valid);
    }

    .verdict-banner-warning {
      background: var(--verdict-warning-bg);
      border-color: var(--verdict-warning-border);
      border-left: 0.25rem solid var(--verdict-warning);
    }

    .verdict-banner-invalid {
      background: var(--verdict-invalid-bg);
      border-color: var(--verdict-invalid-border);
      border-left: 0.25rem solid var(--verdict-invalid);
    }

    .verdict-banner-unevaluated {
      background: var(--verdict-unevaluated-bg);
      border-color: var(--verdict-unevaluated-border);
      border-left: 0.25rem solid var(--verdict-unevaluated);
    }

    .verdict-icon {
      font-size: 1rem;
      width: 1rem;
      text-align: center;
      flex-shrink: 0;
    }

    .verdict-valid-icon { color: var(--verdict-valid); }
    .verdict-warning-icon { color: var(--verdict-warning); }
    .verdict-invalid-icon { color: var(--verdict-invalid); }
    .verdict-unevaluated-icon { color: var(--verdict-unevaluated); }

    .verdict-banner .verdict-badge {
      display: inline-flex;
      align-items: center;
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      border-radius: var(--rounded-sm);
      padding: 0.125rem 0.5rem;
      border: 0.0625rem solid;
    }

    .verdict-badge-valid { color: var(--verdict-valid); background: var(--verdict-valid-bg); border-color: var(--verdict-valid-border); }
    .verdict-badge-warning { color: var(--verdict-warning); background: var(--verdict-warning-bg); border-color: var(--verdict-warning-border); }
    .verdict-badge-invalid { color: var(--verdict-invalid); background: var(--verdict-invalid-bg); border-color: var(--verdict-invalid-border); }
    .verdict-badge-unevaluated { color: var(--verdict-unevaluated); background: var(--verdict-unevaluated-bg); border-color: var(--verdict-unevaluated-border); }

    .verdict-release-id {
      font-family: var(--font-mono);
      font-size: 0.8125rem;
      color: var(--ink);
    }

    .verdict-separator {
      color: var(--border-strong);
    }

    .verdict-timestamp {
      font-size: 0.8125rem;
      color: var(--muted);
    }

    /* Card */
    .card {
      background: var(--surface-raised);
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-lg);
      padding: var(--spacing-lg);
      margin-bottom: var(--spacing-lg);
    }

    .card-title {
      font-family: var(--font-display);
      font-size: 1.5rem;
      font-weight: 400;
      line-height: 1.2;
      letter-spacing: -0.01em;
      margin: 0 0 var(--spacing-md);
      color: var(--ink);
    }

    /* Info grid */
    .info-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: var(--spacing-md);
    }

    .info-field {
      display: flex;
      flex-direction: column;
      gap: 0.125rem;
    }

    .info-label {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
    }

    .info-value {
      font-size: 0.9375rem;
      color: var(--ink);
    }

    .info-description {
      margin-top: var(--spacing-md);
      padding-top: var(--spacing-md);
      border-top: 0.0625rem solid var(--border);
    }

    .info-description-text {
      font-size: 0.9375rem;
      line-height: 1.65;
      color: var(--ink);
      margin: var(--spacing-xs) 0 0;
    }

    .verdict-badge-sm {
      display: inline-flex;
      align-items: center;
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      border-radius: var(--rounded-sm);
      padding: 0.125rem 0.5rem;
      border: 0.0625rem solid;
      align-self: flex-start;
    }

    .status-borrador { color: var(--verdict-unevaluated); background: var(--verdict-unevaluated-bg); border-color: var(--verdict-unevaluated-border); }
    .status-pendiente { color: var(--verdict-unevaluated); background: var(--verdict-unevaluated-bg); border-color: var(--verdict-unevaluated-border); }
    .status-en_verificacion { color: var(--verdict-warning); background: var(--verdict-warning-bg); border-color: var(--verdict-warning-border); }
    .status-valida { color: var(--verdict-valid); background: var(--verdict-valid-bg); border-color: var(--verdict-valid-border); }
    .status-con_advertencias { color: var(--verdict-warning); background: var(--verdict-warning-bg); border-color: var(--verdict-warning-border); }
    .status-no_valida { color: var(--verdict-invalid); background: var(--verdict-invalid-bg); border-color: var(--verdict-invalid-border); }
    .status-archivada { color: var(--verdict-unevaluated); background: var(--verdict-unevaluated-bg); border-color: var(--verdict-unevaluated-border); }

    /* Verification rule table */
    .data-table-wrap {
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-md);
      overflow: hidden;
    }

    .data-table {
      width: 100%;
      border-collapse: collapse;
    }

    .data-table th {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
      padding: var(--spacing-sm) var(--spacing-md);
      text-align: left;
      border-bottom: 0.0625rem solid var(--border);
      background: var(--paper-secondary);
    }

    .data-table td {
      font-size: 0.8125rem;
      color: var(--ink);
      padding: var(--spacing-sm) var(--spacing-md);
      border-bottom: 0.0625rem solid var(--border);
      vertical-align: middle;
      height: 2.75rem;
    }

    .data-table tr:last-child td { border-bottom: none; }

    .data-table tbody tr:hover td { background: var(--paper-secondary); }
    .data-table tbody tr { cursor: default; }

    .col-id { width: 5rem; }
    .col-connector { width: 8.75rem; }
    .col-result { width: 7.5rem; }

    .cell-primary { font-weight: 500; }
    .cell-muted { color: var(--muted); }
    .cell-evidence { max-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .cell-action { text-align: right; }

    .mono-sm {
      font-family: var(--font-mono);
      font-size: 0.6875rem;
      color: var(--muted);
    }

    .verdict-badge {
      display: inline-flex;
      align-items: center;
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      border-radius: var(--rounded-sm);
      padding: 0.125rem 0.5rem;
      border: 0.0625rem solid;
    }

    .result-valid { color: var(--verdict-valid); background: var(--verdict-valid-bg); border-color: var(--verdict-valid-border); }
    .result-warning { color: var(--verdict-warning); background: var(--verdict-warning-bg); border-color: var(--verdict-warning-border); }
    .result-invalid { color: var(--verdict-invalid); background: var(--verdict-invalid-bg); border-color: var(--verdict-invalid-border); }
    .result-unevaluated { color: var(--verdict-unevaluated); background: var(--verdict-unevaluated-bg); border-color: var(--verdict-unevaluated-border); }

    .btn-expand {
      font-size: 0.6875rem;
      color: var(--accent-dark);
      background: none;
      border: none;
      cursor: pointer;
      padding: 0;
      margin-left: var(--spacing-sm);
    }

    .btn-expand:hover { color: var(--ink); }

    .evidence-row td {
      padding: 0 var(--spacing-md) var(--spacing-md);
      border-bottom: 0.0625rem solid var(--border);
      height: auto;
    }

    .evidence-block {
      font-family: var(--font-mono);
      font-size: 0.8125rem;
      line-height: 1.6;
      color: var(--ink);
      background: var(--paper);
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-md);
      padding: var(--spacing-md);
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      max-height: 25rem;
      overflow-y: auto;
    }

    /* Summary bar */
    .summary-bar {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);
      margin-top: var(--spacing-md);
      padding: var(--spacing-md);
      background: var(--paper);
      border-radius: var(--rounded-md);
      border: 0.0625rem solid var(--border);
      flex-wrap: wrap;
    }

    .summary-label {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
      margin-right: var(--spacing-sm);
    }

    .summary-chip {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      padding: 0.125rem 0.5rem;
      border-radius: var(--rounded-sm);
      border: 0.0625rem solid;
    }

    .summary-duration { margin-left: auto; font-size: 0.8125rem; }

    .artifact-type-badge {
      display: inline-flex;
      align-items: center;
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--muted);
      background: var(--paper-secondary);
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-sm);
      padding: 0.125rem 0.5rem;
    }

    .btn-ghost {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--muted);
      background: none;
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-md);
      padding: 0.3125rem 0.75rem;
      cursor: pointer;
      transition: color 0.12s ease, background-color 0.12s ease;
    }

    .btn-ghost:hover { color: var(--ink); background: var(--paper-secondary); }

    .error-banner {
      background: var(--verdict-invalid-bg);
      color: var(--verdict-invalid);
      border: 0.0625rem solid var(--verdict-invalid-border);
      border-radius: var(--rounded-md);
      padding: var(--spacing-sm) var(--spacing-md);
      font-size: 0.8125rem;
      margin-bottom: var(--spacing-md);
    }

    /* Skeleton */
    .skeleton-block { display: flex; flex-direction: column; gap: var(--spacing-md); }

    .skeleton {
      border-radius: var(--rounded-md);
      background: linear-gradient(90deg, var(--paper-secondary) 25%, #e5e2db 50%, var(--paper-secondary) 75%);
      background-size: 200% 100%;
      animation: shimmer 1.6s linear infinite;
    }

    .skeleton-banner { height: 3.5rem; }
    .skeleton-card { height: 12.5rem; }
    .skeleton-row { height: 2.75rem; }

    @keyframes shimmer {
      0% { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }

    .empty-card {
      text-align: center;
      padding: var(--spacing-xxl) var(--spacing-lg);
    }

    .empty-text {
      font-size: 0.9375rem;
      color: var(--muted);
      margin: 0 0 var(--spacing-sm);
    }

    .empty-hint {
      font-size: 0.8125rem;
      color: var(--muted);
      margin: 0 0 var(--spacing-md);
    }

    @media (max-width: 48rem) {
      .page-header {
        flex-direction: column;
        align-items: flex-start;
        gap: var(--spacing-sm);
      }

      .page-header-actions { flex-wrap: wrap; }

      .page-title { font-size: 1.75rem; }

      .verdict-banner {
        height: auto;
        flex-wrap: wrap;
        padding: var(--spacing-md);
      }

      .info-grid { grid-template-columns: repeat(2, 1fr); }

      .data-table-wrap { overflow-x: auto; }
    }

    @media (max-width: 30rem) {
      .info-grid { grid-template-columns: 1fr; }
    }

    /* Section header */
    .section-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: var(--spacing-md);
    }

    .section-header .card-title { margin: 0; }

    /* Empty state */
    .empty-state {
      text-align: center;
      padding: var(--spacing-xl) var(--spacing-lg);
    }

    .empty-state-text {
      font-size: 0.9375rem;
      color: var(--muted);
      margin: 0 0 var(--spacing-md);
    }

    /* Modal */
    .modal-overlay {
      position: fixed;
      inset: 0;
      background: var(--overlay);
      z-index: 100;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .modal-panel {
      background: var(--surface-raised);
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-lg);
      padding: var(--spacing-lg);
      width: 28rem;
      max-width: calc(100vw - 3rem);
    }

    .modal-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: var(--spacing-lg);
    }

    .modal-title {
      font-family: var(--font-sans);
      font-size: 1rem;
      font-weight: 600;
      margin: 0;
    }

    .modal-close {
      font-size: 1.25rem;
      color: var(--muted);
      background: none;
      border: none;
      cursor: pointer;
      padding: 0 0.25rem;
      line-height: 1;
    }

    .modal-close:hover { color: var(--ink); }

    .modal-footer {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: var(--spacing-sm);
      margin-top: var(--spacing-lg);
      padding-top: var(--spacing-md);
      border-top: 0.0625rem solid var(--border);
    }

    /* Form elements */
    .form-group {
      margin-bottom: var(--spacing-md);
    }

    .form-label {
      display: block;
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--ink);
      margin-bottom: var(--spacing-xs);
    }

    .form-select,
    .form-input {
      width: 100%;
      font-family: var(--font-sans);
      font-size: 0.9375rem;
      color: var(--ink);
      background: var(--paper);
      border: 0.0625rem solid var(--border-strong);
      border-radius: var(--rounded-md);
      padding: 0.5625rem 0.75rem;
      box-sizing: border-box;
    }

    .form-select:focus,
    .form-input:focus {
      outline: none;
      border-color: var(--ink);
      background: var(--surface-raised);
      box-shadow: 0 0 0 3px rgba(232, 213, 163, 0.4);
    }

    .error-banner-sm {
      font-size: 0.8125rem;
      padding: var(--spacing-sm) var(--spacing-md);
      margin-top: var(--spacing-sm);
    }

    .form-hint {
      font-size: 0.8125rem;
      color: var(--muted);
      margin: 0.25rem 0 0;
    }

    .form-hint--warn {
      color: var(--verdict-invalid);
      background: var(--verdict-invalid-bg);
      border: 0.0625rem solid var(--verdict-invalid-border);
      border-radius: var(--rounded-md);
      padding: var(--spacing-sm) var(--spacing-md);
    }

    .connector-meta {
      display: flex;
      gap: var(--spacing-sm);
      align-items: center;
      margin-top: var(--spacing-xs);
    }

    .connector-meta-type {
      font-family: var(--font-mono);
      font-size: 0.6875rem;
      font-weight: 600;
      color: var(--muted);
      background: var(--paper-secondary);
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-sm);
      padding: 0.125rem 0.5rem;
      letter-spacing: 0.04em;
    }

    .connector-meta-status {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--verdict-valid);
      background: var(--verdict-valid-bg);
      border: 0.0625rem solid var(--verdict-valid-border);
      border-radius: var(--rounded-sm);
      padding: 0.125rem 0.5rem;
    }

    .btn-link {
      background: none;
      border: none;
      padding: 0;
      font-family: var(--font-sans);
      font-size: 0.8125rem;
      color: var(--muted);
      cursor: pointer;
      text-decoration: underline;
      margin-top: var(--spacing-xs);
    }

    .btn-link:hover { color: var(--ink); }

    .browse-search {
      margin-bottom: var(--spacing-xs);
    }

    .browse-list {
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-md);
      max-height: 12rem;
      overflow-y: auto;
      background: var(--paper);
    }

    .browse-item {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 0.125rem;
      width: 100%;
      padding: 0.5rem 0.75rem;
      background: none;
      border: none;
      border-bottom: 0.0625rem solid var(--border);
      cursor: pointer;
      text-align: left;
      transition: background-color 0.1s ease;
    }

    .browse-item:last-child { border-bottom: none; }

    .browse-item:hover { background: var(--paper-secondary); }

    .browse-item-title {
      font-family: var(--font-sans);
      font-size: 0.875rem;
      color: var(--ink);
      font-weight: 500;
    }

    .browse-item-meta {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);
    }

    .browse-item-ref {
      font-family: var(--font-mono);
      font-size: 0.6875rem;
      color: var(--muted);
    }

    .browse-item-sub {
      font-size: 0.6875rem;
      color: var(--muted);
      font-family: var(--font-sans);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    .browse-empty {
      font-size: 0.8125rem;
      color: var(--muted);
      padding: var(--spacing-sm) var(--spacing-md);
      margin: 0;
    }

    .browse-selected {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: var(--spacing-sm);
      border: 0.0625rem solid var(--verdict-valid-border);
      background: var(--verdict-valid-bg);
      border-radius: var(--rounded-md);
      padding: 0.5rem 0.75rem;
    }

    .browse-selected-info {
      display: flex;
      flex-direction: column;
      gap: 0.125rem;
      min-width: 0;
    }

    .browse-selected-title {
      font-family: var(--font-sans);
      font-size: 0.875rem;
      color: var(--ink);
      font-weight: 500;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .browse-selected-ref {
      font-family: var(--font-mono);
      font-size: 0.6875rem;
      color: var(--verdict-valid);
    }

    .section-actions {
      display: flex;
      gap: var(--spacing-sm);
      align-items: center;
    }

    .col-actions {
      width: 3rem;
      text-align: right;
    }

    .cell-actions {
      text-align: right;
    }

    .btn-icon {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 1.75rem;
      height: 1.75rem;
      border-radius: var(--rounded-md);
      border: 0.0625rem solid var(--border);
      background: none;
      color: var(--muted);
      cursor: pointer;
      padding: 0;
      transition: color 0.12s ease, border-color 0.12s ease, background-color 0.12s ease;
    }

    .btn-icon:hover {
      color: var(--ink);
      border-color: var(--border-strong);
      background: var(--paper-secondary);
    }

    .btn-danger:hover {
      color: var(--verdict-invalid);
      border-color: var(--verdict-invalid-border);
      background: var(--verdict-invalid-bg);
    }

    /* ===== VERIFY LAUNCH NOTICE OVERLAY ===== */
    .verify-overlay {
      position: fixed;
      inset: 0;
      background: rgba(13, 15, 18, 0.68);
      backdrop-filter: blur(4px);
      -webkit-backdrop-filter: blur(4px);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      padding: 1rem;
      animation: verifyOverlayIn 0.2s ease forwards;
    }

    @keyframes verifyOverlayIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    .verify-notice-panel {
      background: var(--surface-raised);
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-lg);
      max-width: 22rem;
      width: 100%;
      overflow: hidden;
      animation: verifyPanelIn 0.3s cubic-bezier(0.22, 1, 0.36, 1) forwards;
    }

    @keyframes verifyPanelIn {
      from { opacity: 0; transform: translateY(1.25rem) scale(0.96); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }

    .verify-scanner {
      position: relative;
      background: var(--ink);
      height: 9rem;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .scanner-ring {
      position: absolute;
      border-radius: 50%;
      border: 1.5px solid rgba(232, 213, 163, 0.55);
      width: 3.5rem;
      height: 3.5rem;
      animation: verifyRingPulse 2.1s ease-out infinite;
    }

    .scanner-ring-1 { animation-delay: 0s; }
    .scanner-ring-2 { animation-delay: 0.55s; }
    .scanner-ring-3 { animation-delay: 1.1s; }

    @keyframes verifyRingPulse {
      0% { transform: scale(1); opacity: 0.9; }
      75% { opacity: 0.12; }
      100% { transform: scale(3.5); opacity: 0; }
    }

    .scanner-core {
      position: relative;
      z-index: 1;
      width: 3rem;
      height: 3rem;
      background: rgba(232, 213, 163, 0.08);
      border: 1.5px solid rgba(232, 213, 163, 0.5);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      color: rgba(232, 213, 163, 0.9);
    }

    .verify-notice-body {
      padding: 1.375rem 1.5rem 0.875rem;
    }

    .verify-notice-title {
      font-family: var(--font-display);
      font-size: 1.375rem;
      font-weight: 400;
      color: var(--ink);
      margin: 0 0 0.5rem;
      line-height: 1.2;
      letter-spacing: -0.01em;
    }

    .verify-notice-desc {
      font-family: var(--font-sans);
      font-size: 0.9rem;
      color: var(--muted);
      line-height: 1.65;
      margin: 0 0 1rem;
    }

    .verify-channels {
      display: flex;
      gap: 0.4375rem;
      flex-wrap: wrap;
    }

    .verify-channel {
      display: inline-flex;
      align-items: center;
      gap: 0.3125rem;
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--ink);
      background: var(--paper-secondary, var(--paper));
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-sm);
      padding: 0.25rem 0.625rem;
    }

    .verify-notice-dismiss {
      display: block;
      width: calc(100% - 3rem);
      margin: 0.875rem 1.5rem 1.375rem;
      padding: 0.5625rem 1rem;
      font-family: var(--font-sans);
      font-size: 0.8125rem;
      font-weight: 600;
      letter-spacing: 0.04em;
      text-align: center;
      color: var(--ink);
      background: var(--paper, #F6F4F0);
      border: 0.0625rem solid var(--border-strong);
      border-radius: var(--rounded-md);
      cursor: pointer;
      transition: background-color 0.12s ease, border-color 0.12s ease;
    }

    .verify-notice-dismiss:hover {
      background: var(--paper-secondary, #ede9e3);
      border-color: var(--ink);
    }

    /* ── Overlay mini progress bar ── */
    .vp-overlay-progress {
      margin: 0.25rem 1.5rem 0.75rem;
      display: flex;
      flex-direction: column;
      gap: 0.375rem;
    }

    .vp-overlay-bar-track {
      height: 0.1875rem;
      background: var(--border);
      border-radius: 9999px;
      overflow: hidden;
    }

    .vp-overlay-bar-fill {
      height: 100%;
      background: linear-gradient(to right, var(--accent-dark), rgba(232, 213, 163, 0.6));
      border-radius: 9999px;
      transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .vp-overlay-stage {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      color: var(--muted);
    }

    /* ── In-page progress card ── */
    .verification-progress-card {
      background: var(--surface-raised);
      border: 0.0625rem solid var(--border);
      border-left: 0.25rem solid var(--accent-dark);
      border-radius: var(--rounded-lg);
      padding: var(--spacing-md) var(--spacing-lg);
      margin-bottom: var(--spacing-lg);
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .vp-header {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .vp-dot {
      width: 0.5rem;
      height: 0.5rem;
      border-radius: 50%;
      background: var(--accent-dark);
      flex-shrink: 0;
      animation: vpDotPulse 1.8s ease-in-out infinite;
    }

    @keyframes vpDotPulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50%       { opacity: 0.4; transform: scale(0.75); }
    }

    .vp-title {
      font-family: var(--font-sans);
      font-size: 0.8125rem;
      font-weight: 600;
      color: var(--ink);
      flex: 1;
    }

    .vp-pct {
      font-family: var(--font-mono);
      font-size: 0.8125rem;
      color: var(--accent-dark);
      font-weight: 600;
      flex-shrink: 0;
    }

    .vp-bar-track {
      height: 0.25rem;
      background: var(--border);
      border-radius: 9999px;
      overflow: hidden;
    }

    .vp-bar-fill {
      height: 100%;
      background: linear-gradient(to right, var(--accent-dark), rgba(232, 213, 163, 0.55));
      border-radius: 9999px;
      transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
      min-width: 0.25rem;
    }

    .vp-stage {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--muted);
    }
  `],
})
export class ReleaseDetailComponent implements OnInit, OnDestroy {
  private readonly http = inject(HttpClient);
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

  stageLabel = computed(() => {
    const p = this.verificationProgress();
    if (!p) return this.ts.translateInstant('release_detail.verify_stage_loading');
    const key = `release_detail.verify_stage_${p.stage}`;
    return this.ts.translateInstant(key) || p.stage;
  });

  private releaseId = '';
  private orgId = '';
  private readonly browseSearchSubject = new Subject<string>();
  private browseSearchSub?: Subscription;
  private activeBrowseConn: ConnectorApiItem | null = null;
  private seenEnVerificacion = false;
  private pollingInterval?: ReturnType<typeof setInterval>;
  private progressInterval?: ReturnType<typeof setInterval>;

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
            release: this.http.get<ReleaseDetail>(`/api/v1/releases/${id}`).pipe(
              catchError(() => { this.error.set(this.ts.translateInstant('release_detail.loading_error')); return of(null); }),
            ),
            artifacts: this.http.get<Artifact[]>(`/api/v1/releases/${id}/artifacts`).pipe(
              catchError(() => of([] as Artifact[])),
            ),
            results: this.http.get<VerificationResult[]>(`/api/v1/releases/${id}/results`).pipe(
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
          this.http.get<ConnectorApiItem[]>(`/api/v1/organizations/${orgId}/connectors`)
            .pipe(catchError(() => of([] as ConnectorApiItem[])))
            .subscribe(connectors => {
              this.orgConnectors.set(connectors);
              this.connectorsLoading.set(false);
            });
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
    this.verifying.set(true);
    if ('Notification' in globalThis && Notification.permission === 'default') {
      Notification.requestPermission();
    }
    this.http
      .post<{ task_id: string; status: string }>(`/api/v1/releases/${this.releaseId}/verify`, {})
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
    this.http
      .post<{ cancelled: boolean }>(`/api/v1/releases/${this.releaseId}/cancel`, {})
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
    this.poll();
    this.pollProgress();
    this.pollingInterval = setInterval(() => this.poll(), 3000);
    this.progressInterval = setInterval(() => this.pollProgress(), 2000);
  }

  private pollProgress(): void {
    const tid = this.taskId();
    if (!tid) return;
    this.http.get<{ progress?: VerificationProgress }>(`/api/v1/tasks/${tid}`)
      .pipe(catchError(() => of(null)))
      .subscribe(data => {
        if (data?.progress) {
          this.verificationProgress.set(data.progress);
        }
      });
  }

  private poll(): void {
    this.http.get<ReleaseDetail>(`/api/v1/releases/${this.releaseId}`)
      .pipe(catchError(() => of(null)))
      .subscribe(release => {
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
    this.loading.set(true);
    this.error.set(null);
    forkJoin({
      release: this.http.get<ReleaseDetail>(`/api/v1/releases/${this.releaseId}`).pipe(
        catchError(() => { this.error.set(this.ts.translateInstant('release_detail.loading_error')); return of(null); }),
      ),
      artifacts: this.http.get<Artifact[]>(`/api/v1/releases/${this.releaseId}/artifacts`).pipe(
        catchError(() => of([] as Artifact[])),
      ),
      results: this.http.get<VerificationResult[]>(`/api/v1/releases/${this.releaseId}/results`).pipe(
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
      this.loading.set(false);
    });
  }

  private stopPolling(): void {
    if (this.pollingInterval !== undefined) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = undefined;
    }
    if (this.progressInterval !== undefined) {
      clearInterval(this.progressInterval);
      this.progressInterval = undefined;
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
    const autoType = CONNECTOR_TYPE_TO_ARTIFACT[conn.connector_type] ?? 'TAREA';
    this.importArtifactType.set(autoType);

    const releaseName = this.release()?.name ?? '';
    this.browseSearch.set(releaseName);
    this.fetchBrowseItems(conn, releaseName);

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
    this.http.get<BrowseItem[]>(
      `/api/v1/organizations/${this.orgId}/connectors/${conn.id}/browse`,
      { params: q ? { q } : {} }
    ).pipe(catchError(() => {
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

    this.http.post(`/api/v1/releases/${this.releaseId}/artifacts/import`, body)
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
          this.http.get<Artifact[]>(`/api/v1/releases/${this.releaseId}/artifacts`)
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
    
    this.http.delete(`/api/v1/releases/${this.releaseId}/artifacts/${artifactId}`)
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
    this.http
      .get<VerificationResult>(`/api/v1/releases/${this.releaseId}/results/${resultId}`)
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
    window.open(`/api/v1/releases/${this.releaseId}/results/${result.id}/export?format=pdf`, '_blank');
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
      'result-unevaluated': !r || r === 'NOT_EVALUATED' || r === 'SKIPPED',
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

  isSummaryString(summary: Record<string, number> | string): summary is string {
    return typeof summary === 'string';
  }

  summaryItems(summary: Record<string, number> | string): [string, number][] {
    if (typeof summary !== 'object' || summary === null) return [];
    return Object.entries(summary).sort((a, b) => b[1] - a[1]);
  }
}
