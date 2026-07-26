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
  is_system?: boolean;
  created_at?: string;
  schedule?: string | null;
  schedule_last_run_at?: string | null;
}

const SCHEDULE_PRESETS: { key: string; cron: string }[] = [
  { key: 'hourly', cron: '0 * * * *' },
  { key: 'daily', cron: '0 6 * * *' },
  { key: 'weekly', cron: '0 6 * * 1' },
];

interface ProfileRule {
  id: string;
  rule_template: string;
  severity: SeverityType;
  connector_instance_id?: string;
  params: Record<string, unknown>;
  display_order: number;
  is_active: boolean;
  connector_types: string[];
}

interface ProfileWithRules extends Profile {
  rules: ProfileRule[];
}

type SeverityType = 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

const RULE_CONNECTOR_TYPES_FRONTEND: Record<string, string[]> = {
  'RV-01': [],
  'RV-02': ['GESTOR_TAREAS', 'REPO_CODIGO'],
  'RV-03': ['GESTOR_TAREAS'],
  'RV-04': ['GESTOR_TAREAS'],
  'RV-05': ['SISTEMA_DOCUMENTAL'],
  'RV-06': ['SISTEMA_DOCUMENTAL'],
  'RV-07': ['GESTOR_TAREAS', 'GESTION_CAMBIOS', 'HERRAMIENTA_PLANIFICACION'],
  'RV-08': ['GESTOR_TAREAS', 'HERRAMIENTA_PLANIFICACION'],
  'RV-09': ['REPO_CODIGO'],
  'RV-10': ['SISTEMA_DOCUMENTAL'],
};

const RULE_DEFAULT_ARTIFACT_TYPES_FRONTEND: Record<string, string> = {
  'RV-03': 'TAREA',
  'RV-04': 'TAREA',
  'RV-05': 'DOCUMENTO',
  'RV-06': 'DOCUMENTO',
  'RV-09': 'CODIGO',
  'RV-10': 'DOCUMENTO',
  'RV-08': 'TAREA',
  'custom_field_check': 'TAREA',
};

const CUSTOM_FIELD_CHECK_OPERATORS = ['non_empty', 'equals', 'not_equals', 'contains', 'gt', 'gte', 'lt', 'lte'] as const;

const ARTIFACT_TYPES = ['TAREA', 'CODIGO', 'DOCUMENTO', 'PLAN', 'CAMBIO'];

/** "80" -> 80 (number), but "007"/"1e10"/"v2" stay strings: a round-trip check
 * (String(Number(x)) === x) tells apart a plain integer/decimal from an
 * identifier that merely looks numeric. Mirrors what the API stores in
 * `VerificationRule.params.value`, which the Rust engine reads back as a
 * typed JSON value (see engine/src/rules/custom_field_check.rs).
 */
function coerceCustomFieldValue(raw: string): string | number {
  const trimmed = raw.trim();
  const asNumber = Number(trimmed);
  const looksNumeric = trimmed.length > 0 && !Number.isNaN(asNumber) && String(asNumber) === trimmed;
  return looksNumeric ? asNumber : raw;
}

/** Client-side mirror of `custom_field_check::field_matches` in the Rust engine,
 * for the live preview only — never used to decide a real verdict. Keeping the
 * two in sync is why every branch here is commented with its Rust counterpart.
 */
function isNonEmptyValue(value: unknown): boolean {
  if (value === undefined || value === null) return false;
  if (typeof value === 'string') return value.trim().length > 0;
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === 'object') return Object.keys(value as object).length > 0;
  return true;
}

function customFieldMatches(actual: unknown, operator: string, expected: string | number | undefined): boolean {
  if (operator === 'non_empty') return isNonEmptyValue(actual);
  if (actual === undefined || actual === null) return false;
  switch (operator) {
    case 'equals':
      return actual === expected;
    case 'not_equals':
      return actual !== expected;
    case 'contains':
      return typeof actual === 'string' && typeof expected === 'string' && actual.includes(expected);
    case 'gt':
    case 'gte':
    case 'lt':
    case 'lte': {
      const a = typeof actual === 'number' ? actual : Number.NaN;
      const e = typeof expected === 'number' ? expected : Number.NaN;
      if (Number.isNaN(a) || Number.isNaN(e)) return false;
      const comparisons: Record<string, boolean> = {
        gt: a > e,
        gte: a >= e,
        lt: a < e,
        lte: a <= e,
      };
      return comparisons[operator];
    }
    default:
      return false;
  }
}

function ruleSupportsArtifactType(template: string): boolean {
  return template in RULE_DEFAULT_ARTIFACT_TYPES_FRONTEND;
}

function defaultArtifactType(template: string): string {
  return RULE_DEFAULT_ARTIFACT_TYPES_FRONTEND[template] ?? 'TAREA';
}

@Component({
  selector: 'app-profiles',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, TranslatePipe],
  templateUrl: './profiles.component.html',
  styleUrls: ['./profiles.component.scss'],
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
    'custom_field_check',
  ]);
  customOperators = CUSTOM_FIELD_CHECK_OPERATORS;
  customPreviewSample = signal<string>('{\n  "epic_id": "EPIC-1",\n  "status": "APPROVED",\n  "coverage": 85\n}');

  schedulePresets = SCHEDULE_PRESETS;

  profileForm = this.fb.group({
    name: ['', [Validators.required]],
    description: [''],
    schedule: [''],
  });

  ruleForm = this.fb.group({
    rule_template: ['', [Validators.required]],
    severity: ['HIGH' as SeverityType, [Validators.required]],
    artifactType: [''],
    expectedValue: [''],
    approvedStates: [''],
    masterArtifactId: [''],
    masterField: [''],
    customField: [''],
    customOperator: ['non_empty'],
    customValue: [''],
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
    this.profileForm.reset({ name: '', description: '', schedule: '' });
    this.modalError.set(null);
    this.showModal.set(true);
  }

  openEdit(p: Profile): void {
    this.editingProfile.set(p);
    this.profileRules.set([]);
    this.profileForm.patchValue({ name: p.name, description: p.description ?? '', schedule: p.schedule ?? '' });
    this.modalError.set(null);
    this.showModal.set(true);
    this.loadProfileRules(p.id);
  }

  applySchedulePreset(value: string): void {
    if (!value) return;
    this.profileForm.patchValue({ schedule: value === '__clear__' ? '' : value });
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

  private readonly emptyRuleForm = {
    rule_template: '', severity: 'HIGH' as SeverityType, artifactType: '', expectedValue: '',
    approvedStates: '', masterArtifactId: '', masterField: '', customField: '', customOperator: 'non_empty', customValue: '',
  };

  openAddRule(): void {
    this.editingRule.set(null);
    this.ruleForm.reset(this.emptyRuleForm);
    this.showRuleForm.set(true);
  }

  openEditRule(rule: ProfileRule): void {
    this.editingRule.set(rule);
    const approvedStates = (rule.params as any)?.['approved_states'];
    this.ruleForm.patchValue({
      rule_template: rule.rule_template,
      severity: rule.severity,
      artifactType: (rule.params as any)?.['artifact_type'] ?? '',
      expectedValue: (rule.params as any)?.['expected_value'] ?? '',
      approvedStates: Array.isArray(approvedStates) ? approvedStates.join(',') : '',
      masterArtifactId: (rule.params as any)?.['master_artifact_id'] ?? '',
      masterField: (rule.params as any)?.['master_field'] ?? '',
      customField: (rule.params as any)?.['field'] ?? '',
      customOperator: (rule.params as any)?.['operator'] ?? 'non_empty',
      customValue: (rule.params as any)?.['value'] !== undefined ? String((rule.params as any)['value']) : '',
    });
    this.showRuleForm.set(true);
  }

  cancelRuleForm(): void {
    this.editingRule.set(null);
    this.ruleForm.reset(this.emptyRuleForm);
    this.showRuleForm.set(false);
  }

  ruleFormControl(name: string): any {
    return this.ruleForm.get(name);
  }

  ruleSupportsArtifactType = ruleSupportsArtifactType;
  artifactTypeOptions = () => ARTIFACT_TYPES;
  defaultArtifactType = defaultArtifactType;
  selectedRuleTemplate = () => this.ruleForm.get('rule_template')?.value ?? '';
  selectedCustomOperator = () => this.ruleForm.get('customOperator')?.value ?? 'non_empty';

  customPreviewResult(): { status: 'ok' | 'fail' | 'error' | 'no_data'; message: string } {
    const field = (this.ruleForm.get('customField')?.value ?? '').trim();
    const operator = this.selectedCustomOperator();
    const rawValue = this.ruleForm.get('customValue')?.value ?? '';

    if (!field) {
      return { status: 'no_data', message: this.ts.translateInstant('profiles.custom_preview_no_field') };
    }

    let sample: Record<string, unknown>;
    try {
      const parsed = JSON.parse(this.customPreviewSample());
      if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
        throw new Error('not an object');
      }
      sample = parsed as Record<string, unknown>;
    } catch {
      return { status: 'error', message: this.ts.translateInstant('profiles.custom_preview_invalid_json') };
    }

    const expected = operator === 'non_empty' || !rawValue ? undefined : coerceCustomFieldValue(rawValue);
    const passed = customFieldMatches(sample[field], operator, expected);
    return {
      status: passed ? 'ok' : 'fail',
      message: this.ts.translateInstant(passed ? 'profiles.custom_preview_pass' : 'profiles.custom_preview_fail'),
    };
  }

  artifactTypeLabel(at: string): string {
    return this.ts.translateInstant('artifact_type.' + at) || at;
  }

  ruleArtifactTypeLabel(rule: ProfileRule): string {
    const configured = (rule.params as any)?.['artifact_type'];
    if (configured) {
      return this.artifactTypeLabel(configured as string);
    }
    return '';
  }

  ruleConfiguredArtifactType(rule: ProfileRule): string | null {
    const configured = (rule.params as any)?.['artifact_type'];
    return (configured && typeof configured === 'string') ? configured : null;
  }

  formatRuleName(template: string): string {
    const translated = this.ts.translateInstant('rules.' + template);
    if (translated && !translated.startsWith('rules.')) {
      if (/^RV-\d+$/.test(template)) {
        const short = translated.length > 25 ? translated.split(' ').slice(0, 3).join(' ') : translated;
        return `${template} - ${short}`;
      }
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

  translateProfileField(value: string | undefined | null): string {
    if (!value) return '—';
    const translated = this.ts.translateInstant(value);
    return (translated && !translated.startsWith(value + '.')) ? translated : value;
  }

  isEditableProfile(): boolean {
    if (!this.editingProfile()) return true;
    return !this.editingProfile()!.is_default && !this.editingProfile()!.is_system;
  }

  modalTitle(): string {
    if (!this.editingProfile()) return this.ts.translateInstant('profiles.create_title');
    if (this.editingProfile()!.is_default || this.editingProfile()!.is_system) return this.ts.translateInstant('profiles.view_title');
    return this.ts.translateInstant('profiles.edit_title');
  }

  isReadonlyProfile(): boolean {
    if (!this.editingProfile()) return false;
    return !!(this.editingProfile()!.is_default || this.editingProfile()!.is_system);
  }

  isViewOnlyProfile(): boolean {
    if (!this.editingProfile()) return false;
    return !!(this.editingProfile()!.is_default || this.editingProfile()!.is_system);
  }

  private buildRuleParams(template: string): Record<string, unknown> {
    const params: Record<string, unknown> = {};

    const artifactType = this.ruleForm.value.artifactType;
    if (artifactType && ruleSupportsArtifactType(template)) {
      params['artifact_type'] = artifactType;
    }
    const expectedValue = this.ruleForm.value.expectedValue;
    if (template === 'RV-06' && expectedValue) {
      params['expected_value'] = expectedValue;
    }
    const approvedStates = this.ruleForm.value.approvedStates;
    if (template === 'RV-10' && approvedStates) {
      params['approved_states'] = approvedStates.split(',').map(s => s.trim()).filter(s => s.length > 0);
    }
    if (template === 'RV-08') {
      this.addRv08Params(params);
    }
    if (template === 'custom_field_check') {
      this.addCustomFieldParams(params);
    }

    return params;
  }

  private addRv08Params(params: Record<string, unknown>): void {
    const masterArtifactId = this.ruleForm.value.masterArtifactId;
    const masterField = this.ruleForm.value.masterField;
    if (masterArtifactId) {
      params['master_artifact_id'] = masterArtifactId.trim();
    }
    if (masterField) {
      params['master_field'] = masterField.trim();
    }
  }

  private addCustomFieldParams(params: Record<string, unknown>): void {
    const customField = this.ruleForm.value.customField;
    const customOperator = this.ruleForm.value.customOperator;
    const customValue = this.ruleForm.value.customValue;
    if (customField) {
      params['field'] = customField.trim();
    }
    params['operator'] = customOperator || 'non_empty';
    if (customOperator !== 'non_empty' && customValue) {
      params['value'] = coerceCustomFieldValue(customValue);
    }
  }

  submitRule(): void {
    if (this.ruleForm.invalid || !this.editingProfile()) return;
    this.savingRule.set(true);
    const profileId = this.editingProfile()!.id;
    const editing = this.editingRule();
    const template = this.ruleForm.value.rule_template ?? '';
    const severity = this.ruleForm.value.severity;
    const params = this.buildRuleParams(template);

    if (editing) {
      this.http.patch<{ id: string; is_active: boolean }>(`/api/v1/rules/${editing.id}`, {
        severity,
        params,
      }).pipe(
        catchError((err: HttpErrorResponse) => {
          this.modalError.set(err.error?.detail ?? this.ts.translateInstant('profiles.rule_saving_error'));
          this.savingRule.set(false);
          return of(null);
        })
      ).subscribe(data => {
        if (data) {
          this.profileRules.update(rules => rules.map(r =>
            r.id === data.id ? { ...r, severity: severity as SeverityType, params } : r
          ));
          this.cancelRuleForm();
        }
        this.savingRule.set(false);
      });
    } else {
      this.http.post<{ id: string; rule_template: string }>(`/api/v1/profiles/${profileId}/rules`, {
        rule_template: template,
        severity,
        params,
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
            severity: severity as SeverityType,
            params,
            display_order: 0,
            is_active: true,
            connector_types: RULE_CONNECTOR_TYPES_FRONTEND[data.rule_template] ?? [],
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
    const name = this.profileForm.value.name ?? '';
    const description = this.profileForm.value.description ?? '';
    const schedule = this.profileForm.value.schedule ?? '';
    const req = editing
      ? this.http.patch<Profile>(`/api/v1/profiles/${editing.id}`, { name, description, schedule })
      : this.http.post<Profile>(`/api/v1/organizations/${this.orgId}/profiles`, { name, description, is_default: false });
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
              ? { ...x, name: p.name, description: formDesc, is_default: p.is_default, rules_count: rulesCount, schedule: p.schedule }
              : x
          ));
          this.editingProfile.update(current => current ? { ...current, schedule: p.schedule } : current);
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
