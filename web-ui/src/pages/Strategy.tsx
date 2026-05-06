import { type ReactNode, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Pencil, Plus, Save, Trash2, XCircle } from "lucide-react";

import { strategyApi, systemApi } from "../api/queries";
import type { SectionRule } from "../api/types";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  Input,
  LoadingState,
  PageHeader,
  Select,
  Switch,
  Textarea,
} from "../components/ui";
import { cn, errorMessage } from "../lib/utils";

// ── Constants ──────────────────────────────────────────────────────────────

const SEHUA_SECTION_OPTIONS = [
  "国产原创",
  "亚洲无码原创",
  "亚洲有码原创",
  "高清中文字幕",
  "素人有码系列",
  "4K原版",
  "VR视频区",
  "欧美无码",
];

const EMPTY_RULE: SectionRule = {
  name: "",
  pattern: "",
  savePath: "",
  kind: "include",
  active: true,
};

// ── Types ──────────────────────────────────────────────────────────────────

type SehuaSection = { name: string; savePath: string; rules: SectionRule[] };

type CrawlerFormState = {
  sehuaEnabled: boolean;
  sehuaSyncTime: string;
  sehuaBaseUrl: string;
  sehuaCookieString: string;
  sehuaNotifyMe: boolean;
  sehuaNotifyWithImage: boolean;
  sehuaSortByYearMonth: boolean;
  sehuaRenameByTitle: boolean;
  sehuaSections: SehuaSection[];
};

type EditingState = { sectionIdx: number; ruleIdx: number | null } | null;

// ── Config converters ──────────────────────────────────────────────────────

function toCrawlerFormState(config: Record<string, unknown>): CrawlerFormState {
  const s = (config.sehuatang_spider ?? {}) as Record<string, unknown>;
  return {
    sehuaEnabled: (s.enable as boolean) || false,
    sehuaSyncTime: (s.sync_time as string) || "03:00",
    sehuaBaseUrl: (s.base_url as string) || "www.sehuatang.net",
    sehuaCookieString: (s.cookie_string as string) || "",
    sehuaNotifyMe: s.notify_me !== false,
    sehuaNotifyWithImage: s.notify_with_image !== false,
    sehuaSortByYearMonth: (s.sort_by_year_month as boolean) || false,
    sehuaRenameByTitle: (s.rename_by_title as boolean) || false,
    sehuaSections: (
      (s.sections as Array<{ name: string; save_path: string; rules?: unknown[] }> | undefined) || []
    ).map((sec) => ({
      name: sec.name,
      savePath: sec.save_path,
      rules: ((sec.rules || []) as Array<Record<string, unknown>>).map((r) => ({
        name: String(r.name || ""),
        pattern: String(r.pattern || ""),
        savePath: String(r.save_path || ""),
        kind: r.kind === "exclude" ? ("exclude" as const) : ("include" as const),
        active: r.active !== false,
      })),
    })),
  };
}

function normalizePath(v?: string | null) {
  const t = (v || "").trim();
  if (!t) return "";
  return t.startsWith("/") ? t : `/${t}`;
}

function toCrawlerApiConfig(form: CrawlerFormState, original: Record<string, unknown>): Record<string, unknown> {
  return {
    ...original,
    sehuatang_spider: {
      ...((original.sehuatang_spider as object) || {}),
      enable: form.sehuaEnabled,
      sync_time: form.sehuaSyncTime,
      base_url: form.sehuaBaseUrl,
      cookie_string: form.sehuaCookieString.trim(),
      notify_me: form.sehuaNotifyMe,
      notify_with_image: form.sehuaNotifyWithImage,
      sort_by_year_month: form.sehuaSortByYearMonth,
      rename_by_title: form.sehuaRenameByTitle,
      sections: form.sehuaSections
        .map((sec) => ({
          name: sec.name.trim(),
          save_path: normalizePath(sec.savePath),
          rules: sec.rules
            .map((r) => ({
              name: r.name.trim(),
              pattern: r.pattern.trim(),
              save_path: normalizePath(r.savePath),
              kind: r.kind,
              active: r.active,
            }))
            .filter((r) => r.name && r.pattern),
        }))
        .filter((sec) => sec.name && sec.save_path),
    },
  };
}

// ── Main component ─────────────────────────────────────────────────────────

export function Strategy() {
  const queryClient = useQueryClient();
  const [crawlerForm, setCrawlerForm] = useState<CrawlerFormState | null>(null);
  const [original, setOriginal] = useState<Record<string, unknown>>({});
  const [justSaved, setJustSaved] = useState(false);
  const [editing, setEditing] = useState<EditingState>(null);
  const [ruleForm, setRuleForm] = useState<SectionRule>(EMPTY_RULE);
  const [testPattern, setTestPattern] = useState("");
  const [testTitle, setTestTitle] = useState("");

  const configQuery = useQuery({ queryKey: ["system", "config"], queryFn: systemApi.config });

  useEffect(() => {
    if (configQuery.data?.config) {
      setOriginal(configQuery.data.config);
      setCrawlerForm(toCrawlerFormState(configQuery.data.config));
    }
  }, [configQuery.data]);

  // client-side regex test (instant)
  const regexTestResult = useMemo(() => {
    if (!testPattern || !testTitle) return null;
    try {
      return new RegExp(testPattern, "i").test(testTitle);
    } catch {
      return "invalid";
    }
  }, [testPattern, testTitle]);

  // server-side validation test (for regex error messages)
  const testMutation = useMutation({
    mutationFn: () => strategyApi.test(testPattern, testTitle),
  });

  function patchCrawler<K extends keyof CrawlerFormState>(key: K, value: CrawlerFormState[K]) {
    setCrawlerForm((prev) => (prev ? { ...prev, [key]: value } : prev));
  }

  function patchSection(idx: number, patch: Partial<SehuaSection>) {
    setCrawlerForm((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        sehuaSections: prev.sehuaSections.map((sec, i) => (i === idx ? { ...sec, ...patch } : sec)),
      };
    });
  }

  function addSection() {
    if (!crawlerForm) return;
    const used = new Set(crawlerForm.sehuaSections.map((s) => s.name));
    const defaultName = SEHUA_SECTION_OPTIONS.find((o) => !used.has(o)) ?? SEHUA_SECTION_OPTIONS[0];
    patchCrawler("sehuaSections", [
      ...crawlerForm.sehuaSections,
      { name: defaultName, savePath: `/AV/涩花/${defaultName}`, rules: [] },
    ]);
  }

  function removeSection(idx: number) {
    if (!crawlerForm) return;
    if (editing?.sectionIdx === idx) setEditing(null);
    patchCrawler(
      "sehuaSections",
      crawlerForm.sehuaSections.filter((_, i) => i !== idx),
    );
  }

  function openNewRule(sectionIdx: number) {
    setEditing({ sectionIdx, ruleIdx: null });
    setRuleForm({ ...EMPTY_RULE });
  }

  function openEditRule(sectionIdx: number, ruleIdx: number) {
    const rule = crawlerForm!.sehuaSections[sectionIdx].rules[ruleIdx];
    setEditing({ sectionIdx, ruleIdx });
    setRuleForm({ ...rule });
  }

  function closeEditor() {
    setEditing(null);
    setRuleForm(EMPTY_RULE);
  }

  function submitRule() {
    if (!editing || !crawlerForm) return;
    const { sectionIdx, ruleIdx } = editing;
    const normalized: SectionRule = {
      name: ruleForm.name.trim(),
      pattern: ruleForm.pattern.trim(),
      savePath: normalizePath(ruleForm.savePath),
      kind: ruleForm.kind,
      active: ruleForm.active,
    };
    if (!normalized.name || !normalized.pattern) return;
    const section = crawlerForm.sehuaSections[sectionIdx];
    const newRules =
      ruleIdx === null
        ? [...section.rules, normalized]
        : section.rules.map((r, i) => (i === ruleIdx ? normalized : r));
    patchSection(sectionIdx, { rules: newRules });
    closeEditor();
  }

  function removeRule(sectionIdx: number, ruleIdx: number) {
    if (!crawlerForm) return;
    if (editing?.sectionIdx === sectionIdx && editing?.ruleIdx === ruleIdx) closeEditor();
    const section = crawlerForm.sehuaSections[sectionIdx];
    patchSection(sectionIdx, { rules: section.rules.filter((_, i) => i !== ruleIdx) });
  }

  function toggleRule(sectionIdx: number, ruleIdx: number, active: boolean) {
    if (!crawlerForm) return;
    const section = crawlerForm.sehuaSections[sectionIdx];
    patchSection(sectionIdx, {
      rules: section.rules.map((r, i) => (i === ruleIdx ? { ...r, active } : r)),
    });
  }

  const saveMutation = useMutation({
    mutationFn: (config: Record<string, unknown>) => systemApi.updateConfig(config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["system"] });
      setJustSaved(true);
      setTimeout(() => setJustSaved(false), 2500);
    },
  });

  if (configQuery.isPending) return <LoadingState />;
  if (configQuery.isError) return <ErrorState message={errorMessage(configQuery.error)} />;

  return (
    <>
      <PageHeader
        title="抓取策略"
        description="配置爬虫参数、板块和过滤规则，全部保存到 config.yaml。"
        actions={
          <Button
            size="sm"
            loading={saveMutation.isPending}
            onClick={() => crawlerForm && saveMutation.mutate(toCrawlerApiConfig(crawlerForm, original))}
          >
            <Save className="h-3.5 w-3.5" />
            <span>{justSaved ? "已保存" : "保存更改"}</span>
          </Button>
        }
      />

      {saveMutation.isError ? (
        <div className="mb-4">
          <ErrorState message={errorMessage(saveMutation.error)} />
        </div>
      ) : null}

      {crawlerForm ? (
        <>
          {/* ── 基础设置 ── */}
          <Card className="mb-4">
            <h2 className="mb-4 text-base font-semibold">基础设置</h2>
            <div className="flex flex-col gap-3">
              <ConfigRow label="启用爬虫">
                <Switch
                  checked={crawlerForm.sehuaEnabled}
                  onCheckedChange={(v) => patchCrawler("sehuaEnabled", v)}
                />
              </ConfigRow>
              <ConfigRow label="每日同步时间" hint="24 小时制，默认抓取前一天的帖子">
                <Input
                  value={crawlerForm.sehuaSyncTime}
                  onChange={(e) => patchCrawler("sehuaSyncTime", e.target.value)}
                  className="max-w-28"
                  placeholder="03:00"
                />
              </ConfigRow>
              <ConfigRow label="基础域名" hint="可填写镜像域名">
                <Input
                  value={crawlerForm.sehuaBaseUrl}
                  onChange={(e) => patchCrawler("sehuaBaseUrl", e.target.value)}
                  placeholder="www.sehuatang.net"
                />
              </ConfigRow>
              <ConfigRow label="Cookie 字符串" hint="浏览器 Cookie 请求头，格式如 a=b; c=d">
                <Textarea
                  value={crawlerForm.sehuaCookieString}
                  onChange={(e) => patchCrawler("sehuaCookieString", e.target.value)}
                  placeholder="cookie_a=value; cookie_b=value"
                />
              </ConfigRow>
              <ConfigRow label="发送通知">
                <Switch
                  checked={crawlerForm.sehuaNotifyMe}
                  onCheckedChange={(v) => patchCrawler("sehuaNotifyMe", v)}
                />
              </ConfigRow>
              <ConfigRow label="通知带封面图" hint="关闭后跳过图片下载">
                <Switch
                  checked={crawlerForm.sehuaNotifyWithImage}
                  onCheckedChange={(v) => patchCrawler("sehuaNotifyWithImage", v)}
                />
              </ConfigRow>
              <ConfigRow label="按年月归档">
                <Switch
                  checked={crawlerForm.sehuaSortByYearMonth}
                  onCheckedChange={(v) => patchCrawler("sehuaSortByYearMonth", v)}
                />
              </ConfigRow>
              <ConfigRow label="按标题重命名" hint="清理后将 115 文件夹重命名为涩花标题">
                <Switch
                  checked={crawlerForm.sehuaRenameByTitle}
                  onCheckedChange={(v) => patchCrawler("sehuaRenameByTitle", v)}
                />
              </ConfigRow>
            </div>
          </Card>

          {/* ── 板块列表 ── */}
          <div className="mb-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-base font-semibold">板块与规则</h2>
              <Button type="button" variant="secondary" size="sm" onClick={addSection}>
                <Plus className="h-3.5 w-3.5" />
                <span>添加板块</span>
              </Button>
            </div>

            {crawlerForm.sehuaSections.length === 0 ? (
              <Card>
                <EmptyState>还没有配置板块，点击"添加板块"开始配置。</EmptyState>
              </Card>
            ) : (
              <div className="flex flex-col gap-3">
                {crawlerForm.sehuaSections.map((sec, sIdx) => (
                  <SectionCard
                    key={sIdx}
                    sec={sec}
                    sIdx={sIdx}
                    editing={editing}
                    ruleForm={ruleForm}
                    setRuleForm={setRuleForm}
                    onSectionNameChange={(name) => {
                      const auto = `/AV/涩花/${sec.name}`;
                      const savePath = sec.savePath === auto ? `/AV/涩花/${name}` : sec.savePath;
                      patchSection(sIdx, { name, savePath });
                    }}
                    onSectionPathChange={(savePath) => patchSection(sIdx, { savePath })}
                    onRemoveSection={() => removeSection(sIdx)}
                    onOpenNewRule={() => openNewRule(sIdx)}
                    onOpenEditRule={(rIdx) => openEditRule(sIdx, rIdx)}
                    onRemoveRule={(rIdx) => removeRule(sIdx, rIdx)}
                    onToggleRule={(rIdx, active) => toggleRule(sIdx, rIdx, active)}
                    onSubmitRule={submitRule}
                    onCloseEditor={closeEditor}
                  />
                ))}
              </div>
            )}
          </div>
        </>
      ) : null}

      {/* ── 正则测试 ── */}
      <Card>
        <h2 className="mb-4 text-base font-semibold">正则测试</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-muted-foreground">匹配规则</label>
            <Input
              placeholder="(SSIS|SONE|MIDV)-\\d{3,4}"
              value={testPattern}
              onChange={(e) => setTestPattern(e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-muted-foreground">测试文本</label>
            <Input
              placeholder="[新作品][SSIS-985] 蓝色彼岸 完全主観"
              value={testTitle}
              onChange={(e) => setTestTitle(e.target.value)}
            />
          </div>
        </div>
        <div className="mt-3 flex items-center gap-3">
          {regexTestResult === "invalid" ? (
            <Badge tone="danger">
              <XCircle className="h-3 w-3" /> 正则无效
            </Badge>
          ) : regexTestResult === true ? (
            <Badge tone="success">
              <CheckCircle2 className="h-3 w-3" /> 匹配
            </Badge>
          ) : regexTestResult === false ? (
            <Badge tone="danger">
              <XCircle className="h-3 w-3" /> 不匹配
            </Badge>
          ) : (
            <span className="text-xs text-muted-foreground">输入规则和文本后即时显示结果</span>
          )}
          {testMutation.isError ? (
            <span className="text-xs text-rose-500">{errorMessage(testMutation.error)}</span>
          ) : null}
        </div>
      </Card>
    </>
  );
}

// ── SectionCard ────────────────────────────────────────────────────────────

type SectionCardProps = {
  sec: SehuaSection;
  sIdx: number;
  editing: EditingState;
  ruleForm: SectionRule;
  setRuleForm: (r: SectionRule) => void;
  onSectionNameChange: (name: string) => void;
  onSectionPathChange: (path: string) => void;
  onRemoveSection: () => void;
  onOpenNewRule: () => void;
  onOpenEditRule: (rIdx: number) => void;
  onRemoveRule: (rIdx: number) => void;
  onToggleRule: (rIdx: number, active: boolean) => void;
  onSubmitRule: () => void;
  onCloseEditor: () => void;
};

function SectionCard({
  sec,
  sIdx,
  editing,
  ruleForm,
  setRuleForm,
  onSectionNameChange,
  onSectionPathChange,
  onRemoveSection,
  onOpenNewRule,
  onOpenEditRule,
  onRemoveRule,
  onToggleRule,
  onSubmitRule,
  onCloseEditor,
}: SectionCardProps) {
  const isEditing = editing?.sectionIdx === sIdx;
  const isEditingNewRule = isEditing && editing?.ruleIdx === null;

  return (
    <Card>
      {/* Section header */}
      <div className="mb-3 flex items-start gap-2">
        <div className="flex min-w-0 flex-1 flex-col gap-1.5 sm:flex-row sm:items-center">
          <Select
            value={sec.name}
            onChange={(e) => onSectionNameChange(e.target.value)}
            className="w-full sm:w-40 shrink-0"
          >
            {SEHUA_SECTION_OPTIONS.map((opt) => (
              <option key={opt}>{opt}</option>
            ))}
          </Select>
          <Input
            value={sec.savePath}
            onChange={(e) => onSectionPathChange(e.target.value)}
            placeholder="/AV/涩花/..."
            className="min-w-0 flex-1"
          />
        </div>
        <Button type="button" variant="ghost" size="icon" onClick={onRemoveSection}>
          <Trash2 className="h-3.5 w-3.5 text-rose-500" />
        </Button>
      </div>

      {/* Divider + rules label */}
      <div className="mb-2 flex items-center gap-2">
        <span className="text-xs font-medium text-muted-foreground">过滤规则</span>
        <span className="flex-1 border-t border-border/60" />
        {sec.rules.length === 0 ? (
          <span className="text-xs text-muted-foreground">无规则 — 全部下载</span>
        ) : (
          <span className="text-xs text-muted-foreground">{sec.rules.length} 条</span>
        )}
      </div>

      {/* Rules table */}
      {sec.rules.length > 0 && (
        <div className="mb-2 overflow-x-auto">
          <table className="w-full text-sm">
            <tbody>
              {sec.rules.map((rule, rIdx) => {
                const isEditingThis = isEditing && editing?.ruleIdx === rIdx;
                if (isEditingThis) {
                  return (
                    <tr key={rIdx} className="border-t border-border/60">
                      <td colSpan={5} className="py-2">
                        <RuleEditor
                          ruleForm={ruleForm}
                          setRuleForm={setRuleForm}
                          isNew={false}
                          onSubmit={onSubmitRule}
                          onCancel={onCloseEditor}
                        />
                      </td>
                    </tr>
                  );
                }
                return (
                  <tr key={rIdx} className="border-t border-border/60">
                    <td className="py-2 pr-3">
                      <Badge tone={rule.kind === "include" ? "success" : "danger"}>
                        {rule.kind === "include" ? "包含" : "排除"}
                      </Badge>
                    </td>
                    <td className="py-2 pr-3 min-w-0">
                      <div className="font-mono text-[13px] text-cell">{rule.pattern}</div>
                      <div className="mt-0.5 text-xs text-muted-foreground text-cell">{rule.name}</div>
                    </td>
                    <td className="py-2 pr-3 text-xs text-muted-foreground">
                      {rule.savePath ? <span className="font-mono">{rule.savePath}</span> : <span>—</span>}
                    </td>
                    <td className="py-2 pr-3">
                      <Switch
                        checked={rule.active}
                        onCheckedChange={(v) => onToggleRule(rIdx, v)}
                      />
                    </td>
                    <td className="py-2">
                      <div className="flex justify-end gap-1">
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={() => onOpenEditRule(rIdx)}
                          aria-label="编辑"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={() => onRemoveRule(rIdx)}
                          aria-label="删除"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* New rule inline editor */}
      {isEditingNewRule && (
        <div className={cn("mb-2 rounded-md border border-primary/20 bg-primary/5 p-3", sec.rules.length > 0 && "mt-2")}>
          <RuleEditor
            ruleForm={ruleForm}
            setRuleForm={setRuleForm}
            isNew={true}
            onSubmit={onSubmitRule}
            onCancel={onCloseEditor}
          />
        </div>
      )}

      {/* Add rule button */}
      {!isEditingNewRule && (
        <Button type="button" variant="ghost" size="sm" className="mt-1 text-muted-foreground" onClick={onOpenNewRule}>
          <Plus className="h-3.5 w-3.5" />
          <span>添加规则</span>
        </Button>
      )}
    </Card>
  );
}

// ── RuleEditor ─────────────────────────────────────────────────────────────

function RuleEditor({
  ruleForm,
  setRuleForm,
  isNew,
  onSubmit,
  onCancel,
}: {
  ruleForm: SectionRule;
  setRuleForm: (r: SectionRule) => void;
  isNew: boolean;
  onSubmit: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
      <div>
        <label className="mb-1 block text-xs font-medium text-muted-foreground">规则名称</label>
        <Input
          required
          placeholder="无码字幕"
          value={ruleForm.name}
          onChange={(e) => setRuleForm({ ...ruleForm, name: e.target.value })}
        />
      </div>
      <div className="lg:col-span-2">
        <label className="mb-1 block text-xs font-medium text-muted-foreground">匹配规则（正则）</label>
        <Input
          required
          placeholder="无码字幕"
          value={ruleForm.pattern}
          onChange={(e) => setRuleForm({ ...ruleForm, pattern: e.target.value })}
        />
      </div>
      <div>
        <label className="mb-1 block text-xs font-medium text-muted-foreground">类型</label>
        <Select
          value={ruleForm.kind}
          onChange={(e) => setRuleForm({ ...ruleForm, kind: e.target.value as "include" | "exclude" })}
        >
          <option value="include">包含</option>
          <option value="exclude">排除</option>
        </Select>
      </div>
      <div className="sm:col-span-2 lg:col-span-3">
        <label className="mb-1 block text-xs font-medium text-muted-foreground">
          存储路径（可选，留空则使用板块路径）
        </label>
        <Input
          placeholder="/AV/涩花/无码字幕"
          value={ruleForm.savePath || ""}
          onChange={(e) => setRuleForm({ ...ruleForm, savePath: e.target.value })}
        />
      </div>
      <div className="flex items-end gap-2 sm:col-span-2 lg:col-span-4">
        <Button
          type="button"
          size="sm"
          disabled={!ruleForm.name.trim() || !ruleForm.pattern.trim()}
          onClick={onSubmit}
        >
          <Save className="h-3.5 w-3.5" />
          <span>{isNew ? "添加" : "更新"}</span>
        </Button>
        <Button type="button" variant="secondary" size="sm" onClick={onCancel}>
          取消
        </Button>
        <div className="flex items-center gap-2 text-sm">
          <Switch
            checked={ruleForm.active}
            onCheckedChange={(v) => setRuleForm({ ...ruleForm, active: v })}
          />
          <span className="text-muted-foreground">启用</span>
        </div>
      </div>
    </div>
  );
}

// ── ConfigRow ──────────────────────────────────────────────────────────────

function ConfigRow({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <div className="config-row">
      <div className="config-row-label">
        <p className="text-sm font-medium">{label}</p>
        {hint ? <p className="mt-1 break-words text-xs leading-snug text-muted-foreground">{hint}</p> : null}
      </div>
      <div className="config-row-control">{children}</div>
    </div>
  );
}
