import { type ReactNode, FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Pencil, Plus, Save, Trash2, XCircle } from "lucide-react";

import { strategyApi, systemApi } from "../api/queries";
import type { StrategyRule, StrategyRuleInput } from "../api/types";
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

type SehuaSection = { name: string; savePath: string };

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
    sehuaSections: ((s.sections as Array<{ name: string; save_path: string }> | undefined) || []).map(
      (sec) => ({ name: sec.name, savePath: sec.save_path }),
    ),
  };
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
        .map((sec) => ({ name: sec.name.trim(), save_path: normalizePath(sec.savePath) }))
        .filter((sec) => sec.name && sec.save_path),
    },
  };
}

const EMPTY_RULE: StrategyRuleInput = {
  site: "sehuatang",
  sectionName: "",
  name: "",
  pattern: "",
  savePath: "",
  kind: "include",
  active: true,
};

function normalizePath(v?: string | null) {
  const t = (v || "").trim();
  if (!t) return "";
  return t.startsWith("/") ? t : `/${t}`;
}

function normalizeRuleInput(r: StrategyRuleInput): StrategyRuleInput {
  return {
    site: r.site.trim(),
    sectionName: r.sectionName.trim(),
    name: r.name.trim(),
    pattern: r.pattern.trim(),
    savePath: normalizePath(r.savePath),
    kind: r.kind ?? "include",
    active: r.active ?? true,
  };
}

function uniqueValues(vals: string[]) {
  return Array.from(new Set(vals.map((v) => v.trim()).filter(Boolean)));
}

function getConfiguredSehuaSections(config?: Record<string, unknown>) {
  const s = (config?.sehuatang_spider ?? {}) as Record<string, unknown>;
  return ((s.sections as Array<{ name?: string }> | undefined) || []).map((sec) => sec.name || "");
}

export function Strategy() {
  const queryClient = useQueryClient();
  const [crawlerForm, setCrawlerForm] = useState<CrawlerFormState | null>(null);
  const [original, setOriginal] = useState<Record<string, unknown>>({});
  const [justSaved, setJustSaved] = useState(false);
  const [editingRule, setEditingRule] = useState<StrategyRule | null>(null);
  const [ruleEditorOpen, setRuleEditorOpen] = useState(false);
  const [ruleForm, setRuleForm] = useState<StrategyRuleInput>(EMPTY_RULE);
  const [testPattern, setTestPattern] = useState("");
  const [testTitle, setTestTitle] = useState("");

  const configQuery = useQuery({ queryKey: ["system", "config"], queryFn: systemApi.config });
  const rulesQuery = useQuery({ queryKey: ["strategy", "rules"], queryFn: strategyApi.list });

  const sectionOptions = useMemo(
    () =>
      uniqueValues([
        ...getConfiguredSehuaSections(configQuery.data?.config),
        ...(rulesQuery.data?.items.map((r) => r.sectionName) || []),
        ...SEHUA_SECTION_OPTIONS,
      ]),
    [configQuery.data?.config, rulesQuery.data?.items],
  );

  useEffect(() => {
    if (configQuery.data?.config) {
      setOriginal(configQuery.data.config);
      setCrawlerForm(toCrawlerFormState(configQuery.data.config));
    }
  }, [configQuery.data]);

  useEffect(() => {
    if (editingRule) {
      setRuleEditorOpen(true);
      setRuleForm({
        site: editingRule.site,
        sectionName: editingRule.sectionName,
        name: editingRule.name,
        pattern: editingRule.pattern,
        savePath: editingRule.savePath || "",
        kind: editingRule.kind,
        active: editingRule.active,
      });
    }
  }, [editingRule]);

  function patchCrawler<K extends keyof CrawlerFormState>(key: K, value: CrawlerFormState[K]) {
    setCrawlerForm((prev) => (prev ? { ...prev, [key]: value } : prev));
  }

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["strategy", "rules"] });

  const saveCrawlerMutation = useMutation({
    mutationFn: (config: Record<string, unknown>) => systemApi.updateConfig(config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["system"] });
      setJustSaved(true);
      setTimeout(() => setJustSaved(false), 2500);
    },
  });
  const createMutation = useMutation({
    mutationFn: strategyApi.create,
    onSuccess: () => {
      setRuleForm(EMPTY_RULE);
      setRuleEditorOpen(false);
      refresh();
    },
  });
  const updateMutation = useMutation({
    mutationFn: ({ id, rule }: { id: number; rule: StrategyRuleInput }) => strategyApi.update(id, rule),
    onSuccess: () => {
      setEditingRule(null);
      setRuleForm(EMPTY_RULE);
      setRuleEditorOpen(false);
      refresh();
    },
  });
  const removeMutation = useMutation({ mutationFn: strategyApi.delete, onSuccess: refresh });
  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, active }: { id: number; active: boolean }) => strategyApi.toggleActive(id, active),
    onSuccess: refresh,
  });
  const testMutation = useMutation({ mutationFn: strategyApi.test });

  function handleRuleSubmit(event: FormEvent) {
    event.preventDefault();
    const normalized = normalizeRuleInput(ruleForm);
    if (!normalized.site || !normalized.sectionName || !normalized.name || !normalized.pattern) return;
    if (editingRule) {
      updateMutation.mutate({ id: editingRule.id, rule: normalized });
    } else {
      createMutation.mutate(normalized);
    }
  }

  function openNewRuleEditor() {
    setEditingRule(null);
    setRuleForm({
      ...EMPTY_RULE,
      sectionName: sectionOptions[0] || "",
    });
    setRuleEditorOpen(true);
  }

  function closeRuleEditor() {
    setEditingRule(null);
    setRuleForm(EMPTY_RULE);
    setRuleEditorOpen(false);
  }

  if (configQuery.isPending) return <LoadingState />;
  if (configQuery.isError) return <ErrorState message={errorMessage(configQuery.error)} />;

  return (
    <>
      <PageHeader
        title="抓取策略"
        description="调整爬虫开关、同步时间、板块和关键词规则，保存到 crawler.yaml。"
        actions={
          <Button
            size="sm"
            loading={saveCrawlerMutation.isPending}
            onClick={() => crawlerForm && saveCrawlerMutation.mutate(toCrawlerApiConfig(crawlerForm, original))}
          >
            <Save className="h-3.5 w-3.5" />
            <span>{justSaved ? "已保存" : "保存更改"}</span>
          </Button>
        }
      />

      {crawlerForm ? (
        <>
          {/* ── Cadence + Sections ── */}
          <div className="mb-4 grid gap-4 xl:grid-cols-2">
            {/* Cadence */}
            <Card>
              <h2 className="mb-4 text-base font-semibold">同步设置</h2>
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

            {/* Sections */}
            <Card>
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-base font-semibold">抓取板块</h2>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    const used = new Set(crawlerForm.sehuaSections.map((s) => s.name));
                    const defaultName = SEHUA_SECTION_OPTIONS.find((o) => !used.has(o)) ?? SEHUA_SECTION_OPTIONS[0];
                    patchCrawler("sehuaSections", [
                      ...crawlerForm.sehuaSections,
                      { name: defaultName, savePath: `/AV/涩花/${defaultName}` },
                    ]);
                  }}
                >
                  <Plus className="h-3.5 w-3.5" />
                  <span>添加</span>
                </Button>
              </div>
              {crawlerForm.sehuaSections.length === 0 ? (
                <EmptyState>还没有配置板块，点击“添加”开始配置。</EmptyState>
              ) : (
                <div className="flex flex-col gap-2">
                  {crawlerForm.sehuaSections.map((sec, idx) => (
                    <div key={idx} className="inset-row gap-2">
                      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
                        <Select
                          value={sec.name}
                          onChange={(e) => {
                            const newName = e.target.value;
                            patchCrawler(
                              "sehuaSections",
                              crawlerForm.sehuaSections.map((cur, i) => {
                                if (i !== idx) return cur;
                                const auto = `/AV/涩花/${cur.name}`;
                                const savePath = cur.savePath === auto ? `/AV/涩花/${newName}` : cur.savePath;
                                return { name: newName, savePath };
                              }),
                            );
                          }}
                          className="w-full"
                        >
                          {SEHUA_SECTION_OPTIONS.map((opt) => (
                            <option key={opt}>{opt}</option>
                          ))}
                        </Select>
                        <Input
                          value={sec.savePath}
                          onChange={(e) =>
                            patchCrawler(
                              "sehuaSections",
                              crawlerForm.sehuaSections.map((cur, i) =>
                                i === idx ? { ...cur, savePath: e.target.value } : cur,
                              ),
                            )
                          }
                          placeholder="/AV/涩花/..."
                        />
                      </div>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() =>
                          patchCrawler(
                            "sehuaSections",
                            crawlerForm.sehuaSections.filter((_, i) => i !== idx),
                          )
                        }
                      >
                        <Trash2 className="h-3.5 w-3.5 text-rose-500" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>
          {saveCrawlerMutation.isError ? (
            <div className="mb-4">
              <ErrorState message={errorMessage(saveCrawlerMutation.error)} />
            </div>
          ) : null}
        </>
      ) : null}

      {/* ── Keyword rules ── */}
      <Card className="mb-4">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold">关键词规则</h2>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={openNewRuleEditor}
          >
            <Plus className="h-3.5 w-3.5" />
            <span>新建规则</span>
          </Button>
        </div>

        {rulesQuery.isPending ? <LoadingState /> : null}
        {rulesQuery.isError ? <ErrorState message={errorMessage(rulesQuery.error)} /> : null}
        {rulesQuery.data?.items.length === 0 ? (
          <EmptyState>还没有规则，点击“新建规则”添加一条。</EmptyState>
        ) : null}

        {rulesQuery.data?.items.length ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th className="w-8 pb-2 pr-4 text-left text-[13px] font-medium text-muted-foreground">#</th>
                  <th className="w-24 pb-2 pr-4 text-left text-[13px] font-medium text-muted-foreground">类型</th>
                  <th className="pb-2 pr-4 text-left text-[13px] font-medium text-muted-foreground">匹配规则</th>
                  <th className="w-32 pb-2 pr-4 text-left text-[13px] font-medium text-muted-foreground">板块</th>
                  <th className="w-20 pb-2 pr-4 text-left text-[13px] font-medium text-muted-foreground">启用</th>
                  <th className="w-20 pb-2 text-right text-[13px] font-medium text-muted-foreground" />
                </tr>
              </thead>
              <tbody>
                {rulesQuery.data.items.map((rule, idx) => (
                  <tr
                    key={rule.id}
                    className={cn("border-t border-border/60", editingRule?.id === rule.id && "bg-primary/5")}
                  >
                    <td className="py-3 pr-4 font-mono text-xs text-muted-foreground">{idx + 1}</td>
                    <td className="py-3 pr-4">
                      <Badge tone={rule.kind === "include" ? "success" : "danger"}>
                        {rule.kind === "include" ? "包含" : "排除"}
                      </Badge>
                    </td>
                    <td className="max-w-xs py-3 pr-4">
                      <div className="text-cell font-mono text-[13px]">{rule.pattern}</div>
                      <div className="text-cell mt-0.5 text-xs text-muted-foreground">{rule.name}</div>
                    </td>
                    <td className="py-3 pr-4"><div className="max-w-32 truncate">{rule.sectionName}</div></td>
                    <td className="py-3 pr-4">
                      <Switch
                        checked={rule.active}
                        onCheckedChange={(v) => toggleActiveMutation.mutate({ id: rule.id, active: v })}
                      />
                    </td>
                    <td className="py-3">
                      <div className="flex justify-end gap-1.5">
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={() => {
                            setEditingRule(rule);
                            setTestPattern(rule.pattern);
                          }}
                          aria-label="编辑"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          loading={removeMutation.isPending}
                          onClick={() => removeMutation.mutate(rule.id)}
                          aria-label="删除"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}

        {/* Inline rule editor (shown when adding/editing) */}
        {ruleEditorOpen && (
          <div className="mt-4 rounded-lg border border-primary/20 bg-primary/5 p-4">
            <h3 className="mb-3 text-sm font-semibold">{editingRule ? "编辑规则" : "新建规则"}</h3>
            <form className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" onSubmit={handleRuleSubmit}>
              <RuleField label="板块">
                <Select
                  required
                  value={ruleForm.sectionName}
                  onChange={(e) => setRuleForm({ ...ruleForm, sectionName: e.target.value })}
                >
                  <option value="" disabled>请选择板块</option>
                  {sectionOptions.map((opt) => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </Select>
              </RuleField>
              <RuleField label="名称">
                <Input
                  required
                  placeholder="规则名称"
                  value={ruleForm.name}
                  onChange={(e) => setRuleForm({ ...ruleForm, name: e.target.value })}
                />
              </RuleField>
              <RuleField label="类型">
                <Select
                  value={ruleForm.kind}
                  onChange={(e) => setRuleForm({ ...ruleForm, kind: e.target.value as "include" | "exclude" })}
                >
                  <option value="include">包含</option>
                  <option value="exclude">排除</option>
                </Select>
              </RuleField>
              <RuleField label="匹配规则" className="sm:col-span-2">
                <Input
                  required
                  placeholder="正则表达式"
                  value={ruleForm.pattern}
                  onChange={(e) => setRuleForm({ ...ruleForm, pattern: e.target.value })}
                />
              </RuleField>
              <RuleField label="保存路径（可选）">
                <Input
                  placeholder="/AV/涩花/..."
                  value={ruleForm.savePath || ""}
                  onChange={(e) => setRuleForm({ ...ruleForm, savePath: e.target.value })}
                />
              </RuleField>
              <div className="flex items-end gap-2 sm:col-span-2 lg:col-span-3">
                <Button loading={createMutation.isPending || updateMutation.isPending} type="submit" size="sm">
                  <Save className="h-3.5 w-3.5" />
                  <span>{editingRule ? "更新" : "创建"}</span>
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={closeRuleEditor}
                >
                  <span>取消</span>
                </Button>
                <div className="flex items-center gap-2 text-sm">
                  <Switch
                    checked={ruleForm.active}
                    onCheckedChange={(v) => setRuleForm({ ...ruleForm, active: v })}
                  />
                  <span className="text-muted-foreground">启用</span>
                </div>
              </div>
              {(createMutation.isError || updateMutation.isError) ? (
                <div className="sm:col-span-2 lg:col-span-3">
                  <ErrorState message={errorMessage((createMutation.error || updateMutation.error)!)} />
                </div>
              ) : null}
            </form>
          </div>
        )}
      </Card>

      {/* ── Regex tester ── */}
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
          <Button
            size="sm"
            disabled={!testPattern || !testTitle}
            loading={testMutation.isPending}
            onClick={() => testMutation.mutate({ pattern: testPattern, title: testTitle })}
          >
            <span>测试</span>
          </Button>
          {testMutation.data ? (
            <Badge tone={testMutation.data.matched ? "success" : "danger"}>
              {testMutation.data.matched ? (
                <><CheckCircle2 className="h-3 w-3" /> 匹配</>
              ) : (
                <><XCircle className="h-3 w-3" /> 不匹配</>
              )}
            </Badge>
          ) : null}
        </div>
        {testMutation.isError ? (
          <div className="mt-3">
            <ErrorState message={errorMessage(testMutation.error)} />
          </div>
        ) : null}
      </Card>
    </>
  );
}

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

function RuleField({
  label,
  children,
  className,
}: {
  label: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={className}>
      <label className="mb-1.5 block text-xs font-medium text-muted-foreground">{label}</label>
      {children}
    </div>
  );
}
