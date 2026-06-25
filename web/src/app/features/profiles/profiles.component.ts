import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { AuthService } from '../../core/services/auth.service';
import { TranslationService } from '../../core/i18n/translation.service';
import { TranslatePipe } from '../../core/i18n/translate.pipe';
import { catchError, of } from 'rxjs';

interface Profile {
  id: string;
  name: string;
  description?: string;
  rules_count?: number;
  organization_id?: string;
  organization_name?: string;
  is_template?: boolean;
  is_default?: boolean;
  created_at?: string;
}

interface ProfileRule {
  id: string;
  rule_template: string;
  severity: SeverityType;
  connector_instance_id?: string;
  params: Record<string, unknown>;
  display_order: number;
  is_active: boolean;
}

interface ProfileWithRules extends Profile {
  rules: ProfileRule[];
}

type SeverityType = 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

@Component({
  selector: 'app-profiles',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, TranslatePipe],
  template: `
    <div class="profiles-page">
      <div class="page-header">
        <div class="page-header-left">
          <h1 class="page-title">{{ 'profiles.title' | t }}</h1>
        </div>
        <button *ngIf="canManage" class="btn-primary" (click)="openCreate()">{{ 'profiles.create_button' | t }}</button>
      </div>

      <div *ngIf="loading()" class="skeleton-list">
        <div class="skeleton skeleton-row" *ngFor="let i of [1,2,3,4]"></div>
      </div>

      <div *ngIf="error() && !loading()" class="error-banner">{{ error() }}</div>

      <div *ngIf="!loading() && !error()">
        <!-- Org profiles -->
        <div class="section-label">{{ 'profiles.org_profiles' | t }}</div>
        <div class="data-table-wrap">
          <table class="data-table" *ngIf="orgProfiles().length > 0; else profilesEmpty">
            <thead>
              <tr>
                <th scope="col">{{ 'profiles.table_name' | t }}</th>
                <th scope="col">{{ 'common.description' | t }}</th>
                <th scope="col">{{ 'profiles.table_rules' | t }}</th>
                <th scope="col" *ngIf="canManage"></th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let p of orgProfiles()">
                <td class="cell-primary">{{ p.name }}</td>
                <td class="cell-muted">{{ p.description ?? '—' }}</td>
                <td>{{ p.rules_count ?? '—' }}</td>
                <td *ngIf="canManage && !p.is_default" class="cell-actions">
                  <button class="btn-ghost" (click)="openEdit(p)">{{ 'common.edit' | t }}</button>
                  <button
                    class="btn-ghost btn-danger-ghost"
                    [disabled]="deletingId() === p.id"
                    [title]="deletingId() === p.id ? ('common.disabled_tooltip.operation_in_progress' | t) : ''"
                    (click)="deleteProfile(p)"
                  >
                    {{ deletingId() === p.id ? ('profiles.deleting' | t) : ('common.delete' | t) }}
                  </button>
                </td>
                <td *ngIf="canManage && p.is_default" class="cell-muted">
                  {{ 'profiles.default_profile' | t }}
                </td>
              </tr>
            </tbody>
          </table>
          <ng-template #profilesEmpty>
            <div class="empty-state">{{ 'profiles.no_profiles' | t }}</div>
          </ng-template>
        </div>
      </div>
    </div>

    <!-- MODAL: Create/Edit Template -->
    <div class="modal-overlay" *ngIf="showModal()" (click)="showModal.set(false)">
      <div class="modal-panel modal-panel-wide" (click)="$event.stopPropagation()">
        <div class="modal-header">
          <h3 class="modal-title">{{ editingProfile() ? ('profiles.edit_title' | t) : ('profiles.create_title' | t) }}</h3>
          <button class="modal-close" (click)="showModal.set(false)">&times;</button>
        </div>
        <form [formGroup]="profileForm" (ngSubmit)="submitProfile()">
          <div class="form-row">
            <div class="form-group">
              <label for="prof-name">{{ 'profiles.name_label' | t }}<span class="required-star" aria-hidden="true">*</span></label>
              <input id="prof-name" type="text" formControlName="name" aria-required="true" [placeholder]="'profiles.template_placeholder' | t" />
            </div>
            <div class="form-group">
              <label for="prof-desc">{{ 'common.description' | t }}</label>
              <input id="prof-desc" type="text" formControlName="description" [placeholder]="'profiles.desc_placeholder' | t" />
            </div>
          </div>

          <div *ngIf="editingProfile() && !editingProfile()!.is_default" class="rules-section">
            <div class="rules-section-header">
              <h4>{{ 'profiles.rules_label' | t }}</h4>
              <button type="button" class="btn-ghost btn-sm" (click)="openAddRule()">
                + {{ 'profiles.add_rule' | t }}
              </button>
            </div>

            <div *ngIf="showRuleForm()" class="rule-form">
              <div class="form-row">
                <div class="form-group">
                  <label for="rule-template">{{ 'profiles.rule_template' | t }}<span class="required-star" aria-hidden="true">*</span></label>
                  <select id="rule-template" [formControl]="ruleFormControl('rule_template')" aria-required="true">
                    <option value="">-- {{ 'profiles.select_rule' | t }} --</option>
                    <option *ngFor="let tmpl of ruleTemplates()" [value]="tmpl">{{ formatRuleName(tmpl) }}</option>
                  </select>
                </div>
                <div class="form-group">
                  <label for="rule-severity">{{ 'profiles.severity_label' | t }}<span class="required-star" aria-hidden="true">*</span></label>
                  <select id="rule-severity" [formControl]="ruleFormControl('severity')" aria-required="true">
                    <option value="INFO">INFO</option>
                    <option value="LOW">LOW</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="HIGH">HIGH</option>
                    <option value="CRITICAL">CRITICAL</option>
                  </select>
                </div>
              </div>
              <div class="rule-form-actions">
                <button type="button" class="btn-secondary btn-sm" (click)="cancelRuleForm()">{{ 'common.cancel' | t }}</button>
                <button type="button" class="btn-primary btn-sm" [disabled]="savingRule()" [title]="savingRule() ? ('common.disabled_tooltip.operation_in_progress' | t) : ''" (click)="submitRule()">
                  {{ savingRule() ? ('profiles.saving' | t) : (editingRule() ? ('profiles.update_rule' | t) : ('profiles.add_rule' | t)) }}
                </button>
              </div>
            </div>

            <div class="rules-list" *ngIf="profileRules().length > 0">
              <div class="rule-item" *ngFor="let rule of profileRules()">
                <div class="rule-info">
                  <span class="rule-template">{{ formatRuleName(rule.rule_template) }}</span>
                  <span class="severity-badge" [ngClass]="'severity-' + rule.severity.toLowerCase()">{{ rule.severity }}</span>
                </div>
                <div class="rule-actions" *ngIf="!editingProfile()!.is_default">
                  <button type="button" class="btn-ghost btn-xs" (click)="openEditRule(rule)">{{ 'common.edit' | t }}</button>
                  <button type="button" class="btn-ghost btn-danger-ghost btn-xs" (click)="deleteRule(rule)">{{ 'common.delete' | t }}</button>
                </div>
              </div>
            </div>
            <div *ngIf="profileRules().length === 0 && !showRuleForm()" class="empty-rules">
              {{ 'profiles.no_rules' | t }}
            </div>
          </div>

          <div *ngIf="modalError()" class="error-banner error-banner-sm">{{ modalError() }}</div>
          <div class="modal-footer">
            <button type="button" class="btn-secondary" (click)="showModal.set(false)">{{ 'common.cancel' | t }}</button>
            <button type="submit" class="btn-primary" [disabled]="saving()" [title]="saving() ? ('common.disabled_tooltip.operation_in_progress' | t) : ''">
              {{ saving() ? ('profiles.saving' | t) : (editingProfile() ? ('profiles.save_changes' | t) : ('profiles.create_button' | t)) }}
            </button>
          </div>
        </form>
      </div>
    </div>
  `,
  styles: [`
    :host { display: block; }

    .profiles-page { padding: 0; }

    .page-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: var(--spacing-lg);
    }

    .page-header-left {
      display: flex;
      align-items: baseline;
      gap: var(--spacing-md);
    }

    .page-title {
      font-family: var(--font-display);
      font-size: 2.25rem;
      font-weight: 400;
      line-height: 1.1;
      letter-spacing: -0.02em;
      margin: 0;
      color: var(--ink);
    }

    .global-badge {
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

    .section-label {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--ink);
      margin-bottom: var(--spacing-sm);
    }

    .section-label-muted {
      color: var(--muted);
      margin-top: var(--spacing-md);
    }

    .data-table-wrap {
      background: var(--surface-raised);
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-lg);
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
    .data-table tr:hover td { background: var(--paper-secondary); }

    .cell-primary { font-weight: 500; }
    .cell-muted { color: var(--muted); }

    .cell-actions {
      display: flex;
      gap: var(--spacing-sm);
      justify-content: flex-end;
      align-items: center;
    }

    .btn-ghost {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--muted);
      background: none;
      border: 0.0625rem solid transparent;
      border-radius: var(--rounded-md);
      padding: 0.25rem 0.625rem;
      cursor: pointer;
      transition: color 0.12s ease, background-color 0.12s ease, border-color 0.12s ease;
    }

    .btn-ghost:hover:not(:disabled) { color: var(--ink); background: var(--paper-secondary); border-color: var(--border); }
    .btn-ghost:disabled { opacity: 0.45; cursor: not-allowed; }

    .btn-danger-ghost { color: var(--verdict-invalid); }
    .btn-danger-ghost:hover:not(:disabled) { background: var(--verdict-invalid-bg); border-color: var(--verdict-invalid-border); }

    .btn-primary {
      display: inline-flex;
      align-items: center;
      background: var(--ink);
      color: var(--paper);
      border: 0.0625rem solid var(--ink);
      border-radius: var(--rounded-md);
      padding: 0.5625rem 1.125rem;
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      cursor: pointer;
      transition: background-color 0.15s ease;
    }

    .btn-primary:hover:not(:disabled) { background: var(--ink-secondary); }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

    .btn-secondary {
      display: inline-flex;
      align-items: center;
      background: transparent;
      color: var(--ink);
      border: 0.0625rem solid var(--border-strong);
      border-radius: var(--rounded-md);
      padding: 0.5625rem 1.125rem;
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      cursor: pointer;
      transition: background-color 0.15s ease;
    }

    .btn-secondary:hover { background: var(--paper-secondary); }

    .error-banner {
      background: var(--verdict-invalid-bg);
      color: var(--verdict-invalid);
      border: 0.0625rem solid var(--verdict-invalid-border);
      border-radius: var(--rounded-md);
      padding: var(--spacing-sm) var(--spacing-md);
      font-size: 0.8125rem;
      margin-bottom: var(--spacing-md);
    }

    .error-banner-sm { margin-bottom: 0; margin-top: var(--spacing-sm); }

    .skeleton-list { display: flex; flex-direction: column; gap: var(--spacing-sm); }

    .skeleton {
      border-radius: var(--rounded-md);
      background: linear-gradient(90deg, var(--paper-secondary) 25%, #e5e2db 50%, var(--paper-secondary) 75%);
      background-size: 200% 100%;
      animation: shimmer 1.6s linear infinite;
    }

    .skeleton-row { height: 2.75rem; }

    @keyframes shimmer {
      0% { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }

    .empty-state {
      padding: var(--spacing-xl) var(--spacing-lg);
      text-align: center;
      font-size: 0.8125rem;
      color: var(--muted);
    }

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
      width: 30rem;
      max-width: calc(100vw - 3rem);
    }

    .modal-panel-wide {
      width: 45rem;
      max-width: calc(100vw - 3rem);
    }

    .form-row {
      display: flex;
      gap: var(--spacing-md);
    }

    .form-row .form-group {
      flex: 1;
    }

    .rules-section {
      margin-top: var(--spacing-lg);
      padding-top: var(--spacing-md);
      border-top: 0.0625rem solid var(--border);
    }

    .rules-section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: var(--spacing-md);
    }

    .rules-section-header h4 {
      margin: 0;
      font-size: 0.875rem;
      font-weight: 600;
    }

    .rule-form {
      background: var(--paper-secondary);
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-md);
      padding: var(--spacing-md);
      margin-bottom: var(--spacing-md);
    }

    .rule-form-actions {
      display: flex;
      justify-content: flex-end;
      gap: var(--spacing-sm);
      margin-top: var(--spacing-md);
    }

    .rules-list {
      display: flex;
      flex-direction: column;
      gap: var(--spacing-xs);
    }

    .rule-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: var(--spacing-sm) var(--spacing-md);
      background: var(--paper);
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-md);
    }

    .rule-info {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);
    }

    .rule-template {
      font-family: var(--font-mono);
      font-size: 0.8125rem;
    }

    .severity-badge {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      padding: 0.125rem 0.375rem;
      border-radius: var(--rounded-sm);
      text-transform: uppercase;
    }

    .severity-info { background: #e8f4fd; color: #0077b6; }
    .severity-low { background: #e8f5e9; color: #2e7d32; }
    .severity-medium { background: #fff8e1; color: #f57f17; }
    .severity-high { background: #ffebee; color: #c62828; }
    .severity-critical { background: #4a0e0e; color: #ff6659; }

    .rule-actions {
      display: flex;
      gap: var(--spacing-xs);
    }

    .empty-rules {
      text-align: center;
      color: var(--muted);
      font-size: 0.8125rem;
      padding: var(--spacing-md);
    }

    .btn-xs {
      font-size: 0.625rem;
      padding: 0.125rem 0.375rem;
    }

    .btn-sm {
      font-size: 0.6875rem;
      padding: 0.25rem 0.5rem;
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

    .form-group {
      margin-bottom: var(--spacing-md);
    }

    .form-group label {
      display: block;
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--ink);
      margin-bottom: var(--spacing-xs);
    }

    .required-star {
      color: var(--verdict-invalid);
      margin-left: 0.25rem;
      font-size: 0.75rem;
    }

    .form-group input {
      width: 100%;
      background: var(--paper);
      color: var(--ink);
      border: 0.0625rem solid var(--border-strong);
      border-radius: var(--rounded-md);
      padding: 0.5625rem 0.75rem;
      font-family: var(--font-sans);
      font-size: 0.9375rem;
      outline: none;
      transition: border-color 0.15s ease, background-color 0.15s ease, box-shadow 0.15s ease;
    }

    .form-group input:focus {
      border-color: var(--ink);
      background: var(--surface-raised);
      box-shadow: 0 0 0 0.1875rem rgba(232, 213, 163, 0.4);
    }

    @media (max-width: 48rem) {
      .page-header { flex-wrap: wrap; gap: var(--spacing-sm); }

      .page-header .btn-primary { width: 100%; }

      .page-title { font-size: 1.75rem; }

      .data-table-wrap { overflow-x: auto; }

      .modal-panel,
      .modal-panel-wide {
        width: calc(100vw - 1.5rem);
        max-width: none;
        padding: var(--spacing-md);
        max-height: calc(100vh - 3rem);
        overflow-y: auto;
      }

      .modal-header { margin-bottom: var(--spacing-md); }
      .modal-title { font-size: 0.9375rem; }

      .form-row {
        flex-direction: column;
        gap: var(--spacing-sm);
      }

      .form-group input {
        padding: 0.625rem 0.75rem;
        min-height: 2.75rem;
        font-size: 0.875rem;
      }

      .form-group label { font-size: 0.625rem; }

      .rules-section-header {
        flex-direction: column;
        align-items: flex-start;
        gap: var(--spacing-sm);
      }

      .rule-item {
        flex-direction: column;
        align-items: flex-start;
        gap: var(--spacing-xs);
        padding: var(--spacing-sm);
      }

      .rule-actions { align-self: flex-end; }

      .rule-form-actions {
        flex-direction: column-reverse;
        gap: var(--spacing-xs);
      }

      .rule-form-actions .btn-primary,
      .rule-form-actions .btn-secondary {
        width: 100%;
        justify-content: center;
        min-height: 2.75rem;
      }

      .modal-footer {
        flex-direction: column-reverse;
        gap: var(--spacing-xs);
        margin-top: var(--spacing-md);
        padding-top: var(--spacing-sm);
      }

      .modal-footer .btn-primary,
      .modal-footer .btn-secondary {
        width: 100%;
        justify-content: center;
        padding: 0.625rem 1rem;
        min-height: 2.75rem;
      }

      .form-group select {
        padding: 0.625rem 0.75rem;
        min-height: 2.75rem;
        font-size: 0.875rem;
      }
    }
  `],
})
export class ProfilesComponent implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly authService = inject(AuthService);
  private readonly fb = inject(FormBuilder);
  private readonly ts = inject(TranslationService);

  private orgId: string | null = null;
  readonly canManage = this.authService.getUserRole() === 'MANAGER';
  readonly isAdmin = false;

  allProfiles = signal<Profile[]>([]);
  templates = signal<Profile[]>([]);
  orgProfiles = signal<Profile[]>([]);
  loading = signal(true);
  error = signal<string | null>(null);

  showModal = signal(false);
  editingProfile = signal<Profile | null>(null);
  saving = signal(false);
  modalError = signal<string | null>(null);
  deletingId = signal<string | null>(null);

  profileRules = signal<ProfileRule[]>([]);
  editingRule = signal<ProfileRule | null>(null);
  showRuleForm = signal(false);
  savingRule = signal(false);
  ruleTemplates = signal<string[]>([
    'has_high_severity_vulnerabilities',
    'has_critical_vulnerabilities',
    'has_open_high_priority_issues',
    'has_code_smells',
    'has_security_hotspots',
    'has_uncovered_code',
    'has_duplicated_code',
    'has_blocking_issues',
    'meets_minimum_test_coverage',
    'meets_maximum_complexity',
  ]);

  profileForm = this.fb.group({
    name: ['', [Validators.required]],
    description: [''],
  });

  ruleForm = this.fb.group({
    rule_template: ['', [Validators.required]],
    severity: ['HIGH' as SeverityType, [Validators.required]],
  });

  ngOnInit(): void {
    const user = this.authService.getUser();
    this.orgId = user?.organization_id ?? null;
    if (!this.orgId) {
      this.error.set(this.ts.translateInstant('profiles.loading_error'));
      this.loading.set(false);
      return;
    }
    this.http.get<Profile[]>(`/api/v1/organizations/${this.orgId}/profiles`)
      .pipe(catchError(() => { this.error.set(this.ts.translateInstant('profiles.loading_error')); return of([]); }))
      .subscribe(data => {
        this.allProfiles.set(data);
        this.templates.set([]);
        this.orgProfiles.set(data);
        this.loading.set(false);
      });
  }

  openCreate(): void {
    this.editingProfile.set(null);
    this.profileRules.set([]);
    this.profileForm.reset({ name: '', description: '' });
    this.modalError.set(null);
    this.showModal.set(true);
  }

  openEdit(p: Profile): void {
    this.editingProfile.set(p);
    this.profileRules.set([]);
    this.profileForm.patchValue({ name: p.name, description: p.description ?? '' });
    this.modalError.set(null);
    this.showModal.set(true);
    this.loadProfileRules(p.id);
  }

  private loadProfileRules(profileId: string): void {
    this.http.get<ProfileWithRules>(`/api/v1/profiles/${profileId}`)
      .pipe(catchError(() => of(null)))
      .subscribe(data => {
        if (data?.rules) {
          this.profileRules.set(data.rules);
        }
      });
  }

  openAddRule(): void {
    this.editingRule.set(null);
    this.ruleForm.reset({ rule_template: '', severity: 'HIGH' as SeverityType });
    this.showRuleForm.set(true);
  }

  openEditRule(rule: ProfileRule): void {
    this.editingRule.set(rule);
    this.ruleForm.patchValue({
      rule_template: rule.rule_template,
      severity: rule.severity,
    });
    this.showRuleForm.set(true);
  }

  cancelRuleForm(): void {
    this.editingRule.set(null);
    this.ruleForm.reset({ rule_template: '', severity: 'HIGH' as SeverityType });
    this.showRuleForm.set(false);
  }

  ruleFormControl(name: string): any {
    return this.ruleForm.get(name);
  }

  formatRuleName(template: string): string {
    const translated = this.ts.translateInstant('rules.' + template);
    if (translated && !translated.startsWith('rules.')) {
      return translated;
    }
    return template
      .replaceAll('_', ' ')
      .replace(/has_/i, '')
      .replace(/meets_/i, '')
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ');
  }

  submitRule(): void {
    if (this.ruleForm.invalid || !this.editingProfile()) return;
    this.savingRule.set(true);
    const profileId = this.editingProfile()!.id;
    const editing = this.editingRule();

    if (editing) {
      this.http.patch<{ id: string; is_active: boolean }>(`/api/v1/rules/${editing.id}`, {
        severity: this.ruleForm.value.severity,
      }).pipe(
        catchError((err: HttpErrorResponse) => {
          this.modalError.set(err.error?.detail ?? this.ts.translateInstant('profiles.rule_saving_error'));
          this.savingRule.set(false);
          return of(null);
        })
      ).subscribe(data => {
        if (data) {
          this.profileRules.update(rules => rules.map(r =>
            r.id === data.id ? { ...r, severity: this.ruleForm.value.severity as SeverityType } : r
          ));
          this.cancelRuleForm();
        }
        this.savingRule.set(false);
      });
    } else {
      this.http.post<{ id: string; rule_template: string }>(`/api/v1/profiles/${profileId}/rules`, {
        rule_template: this.ruleForm.value.rule_template,
        severity: this.ruleForm.value.severity,
      }).pipe(
        catchError((err: HttpErrorResponse) => {
          this.modalError.set(err.error?.detail ?? this.ts.translateInstant('profiles.rule_saving_error'));
          this.savingRule.set(false);
          return of(null);
        })
      ).subscribe(data => {
        if (data) {
          const newRule: ProfileRule = {
            id: data.id,
            rule_template: data.rule_template,
            severity: this.ruleForm.value.severity as SeverityType,
            params: {},
            display_order: 0,
            is_active: true,
          };
          this.profileRules.update(rules => [...rules, newRule]);
          this.cancelRuleForm();
        }
        this.savingRule.set(false);
      });
    }
  }

  deleteRule(rule: ProfileRule): void {
    this.http.delete(`/api/v1/rules/${rule.id}`)
      .pipe(catchError(() => of(null)))
      .subscribe(() => {
        this.profileRules.update(rules => rules.filter(r => r.id !== rule.id));
      });
  }

  submitProfile(): void {
    if (this.profileForm.invalid) { this.profileForm.markAllAsTouched(); return; }
    this.saving.set(true);
    this.modalError.set(null);
    const editing = this.editingProfile();
    const body = { ...this.profileForm.value, is_default: false };
    const req = editing
      ? this.http.patch<Profile>(`/api/v1/profiles/${editing.id}`, body)
      : this.http.post<Profile>(`/api/v1/organizations/${this.orgId}/profiles`, body);
    req.pipe(catchError((err: HttpErrorResponse) => {
      this.modalError.set(err.error?.detail ?? this.ts.translateInstant('profiles.saving_error'));
      this.saving.set(false);
      return of(null);
    })).subscribe(p => {
      if (p) {
        const formDesc = this.profileForm.value.description ?? '';
        const rulesCount = this.profileRules().length;
        if (editing) {
          this.orgProfiles.update(list => list.map(x =>
            x.id === p.id
              ? { ...x, name: p.name, description: formDesc, is_default: p.is_default, rules_count: rulesCount }
              : x
          ));
        } else {
          this.orgProfiles.update(list => [...list, {
            id: p.id,
            name: p.name,
            description: formDesc,
            rules_count: 0,
            is_default: p.is_default,
            is_template: false,
          }]);
        }
        this.showModal.set(false);
      }
      this.saving.set(false);
    });
  }

  deleteProfile(p: Profile): void {
    this.deletingId.set(p.id);
    this.http.delete(`/api/v1/profiles/${p.id}`)
      .pipe(catchError(() => { this.deletingId.set(null); return of(null); }))
      .subscribe(() => {
        this.orgProfiles.update(list => list.filter(x => x.id !== p.id));
        this.deletingId.set(null);
      });
  }
}
