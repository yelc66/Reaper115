import { type ReactNode, FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Pencil, Plus, Save, Trash2, XCircle } from "lucide-react";

import { strategyApi, systemApi } from "../api/queries";
import type { StrategyRule, StrategyRuleInput } from "../api/types";
import { Badge, Button, Card, EmptyState, ErrorState, Input, LoadingState, PageHeader, Select, Textarea } from "../components/ui";
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

type SehuaSection = {
  name: string;
  savePath: string;
};

type CrawlerFormState = {
  sehuaEnabled: boolean;
  sehuaSyncTime: string;
  sehuaBaseUrl: string;
  sehuaCookieString: string;
  sehuaNotifyMe: boolean;
  sehuaSortByYearMonth: boolean;
  sehuaSections: SehuaSection[];
};

function toCrawlerFormState(config: Record<string, unknown>): CrawlerFormState {
  const sehuaConfig = (config.sehuatang_spider ?? {}) as Record<string, unknown>;

  return {
    sehuaEnabled: (sehuaConfig.enable as boolean) || false,
    sehuaSyncTime: (sehuaConfig.sync_time as string) || "03:00",
    sehuaBaseUrl: (sehuaConfig.base_url as string) || "www.sehuatang.net",
    sehuaCookieString: (sehuaConfig.cookie_string as string) || "",
    sehuaNotifyMe: sehuaConfig.notify_me !== false,
    sehuaSortByYearMonth: (sehuaConfig.sort_by_year_month as boolean) || false,
    sehuaSections: ((sehuaConfig.sections as Array<{ name: string; save_path: string }> | undefined) || []).map(
      (section) => ({
        name: section.name,
        savePath: section.save_path,
      }),
    ),
  };
}

function toCrawlerApiConfig(
  formState: CrawlerFormState,
  original: Record<string, unknown>,
): Record<string, unknown> {
  return {
    ...original,
    sehuatang_spider: {
      ...((original.sehuatang_spider as object) || {}),
      enable: formState.sehuaEnabled,
      sync_time: formState.sehuaSyncTime,
      base_url: formState.sehuaBaseUrl,
      cookie_string: formState.sehuaCookieString.trim(),
      notify_me: formState.sehuaNotifyMe,
      sort_by_year_month: formState.sehuaSortByYearMonth,
      sections: formState.sehuaSections
        .map((section) => ({
          name: section.name.trim(),
          save_path: normalizeSavePath(section.savePath),
        }))
        .filter((section) => section.name && section.save_path),
    },
  };
}

const EMPTY_RULE: StrategyRuleInput = {
  sectionName: "",
  strategyName: "",
  pattern: "",
  specifySavePath: "",
};

function uniqueValues(values: string[]) {
  return Array.from(new Set(values.map((value) => value.trim()).filter(Boolean)));
}

function normalizeSavePath(value?: string | null) {
  const trimmed = (value || "").trim();
  if (!trimmed) return "";
  return trimmed.startsWith("/") ? trimmed : `/${trimmed}`;
}

function normalizeRuleInput(rule: StrategyRuleInput): StrategyRuleInput {
  return {
    sectionName: rule.sectionName.trim(),
    strategyName: rule.strategyName.trim(),
    pattern: rule.pattern.trim(),
    specifySavePath: normalizeSavePath(rule.specifySavePath),
  };
}

function getConfiguredSehuaSections(config?: Record<string, unknown>) {
  const sehuaConfig = (config?.sehuatang_spider ?? {}) as Record<string, unknown>;
  const sections = (sehuaConfig.sections as Array<{ name?: string }> | undefined) || [];
  return sections.map((section) => section.name || "");
}

function CrawlerConfigPanel() {
  const queryClient = useQueryClient();
  const [formState, setFormState] = useState<CrawlerFormState | null>(null);
  const [original, setOriginal] = useState<Record<string, unknown>>({});
  const [justSaved, setJustSaved] = useState(false);

  const configQuery = useQuery({ queryKey: ["system", "config"], queryFn: systemApi.config });
  const saveMutation = useMutation({
    mutationFn: (config: Record<string, unknown>) => systemApi.updateConfig(config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["system"] });
      setJustSaved(true);
      setTimeout(() => setJustSaved(false), 2500);
    },
  });

  useEffect(() => {
    if (configQuery.data?.config) {
      setOriginal(configQuery.data.config);
      setFormState(toCrawlerFormState(configQuery.data.config));
    }
  }, [configQuery.data]);

  function patchForm<K extends keyof CrawlerFormState>(key: K, value: CrawlerFormState[K]) {
    setFormState((previous) => (previous ? { ...previous, [key]: value } : previous));
  }

  function saveCrawlerConfig() {
    if (!formState) return;
    saveMutation.mutate(toCrawlerApiConfig(formState, original));
  }

  if (configQuery.isPending) return <LoadingState />;
  if (configQuery.isError) return <ErrorState message={errorMessage(configQuery.error)} />;
  if (!formState) return null;

  return (
    <Section title="爬虫配置" onSave={saveCrawlerConfig} saving={saveMutation.isPending} justSaved={justSaved}>
      <SpiderBlock label="涩花（sehuatang.net）">
        <Row label="开启爬虫">
          <Switch
            checked={formState.sehuaEnabled}
            onCheckedChange={(checked) => patchForm("sehuaEnabled", checked)}
          />
        </Row>
        <Row label="触发时间" hint="24h 格式，每日定时爬取前一天数据">
          <Input
            value={formState.sehuaSyncTime}
            onChange={(event) => patchForm("sehuaSyncTime", event.target.value)}
            className="max-w-28"
            placeholder="03:00"
          />
        </Row>
        <Row label="站点地址" hint="可填临时镜像地址加速">
          <Input
            value={formState.sehuaBaseUrl}
            onChange={(event) => patchForm("sehuaBaseUrl", event.target.value)}
            placeholder="www.sehuatang.net"
          />
        </Row>
        <Row label="站点 Cookie" hint="浏览器请求头里的 Cookie，格式 a=b; c=d，留空则不注入">
          <Textarea
            value={formState.sehuaCookieString}
            onChange={(event) => patchForm("sehuaCookieString", event.target.value)}
            className="min-h-20"
            placeholder="cookie_a=value; cookie_b=value"
          />
        </Row>
        <Row label="通知我">
          <Switch
            checked={formState.sehuaNotifyMe}
            onCheckedChange={(checked) => patchForm("sehuaNotifyMe", checked)}
          />
        </Row>
        <Row label="按年月整理">
          <Switch
            checked={formState.sehuaSortByYearMonth}
            onCheckedChange={(checked) => patchForm("sehuaSortByYearMonth", checked)}
          />
        </Row>
        <Row label="爬取版块" hint="选择版块及对应 115 保存路径，至少填一个">
          <div className="space-y-2">
            {formState.sehuaSections.map((section, sectionIndex) => (
              <div key={sectionIndex} className="flex items-center gap-2">
                <Select
                  value={section.name}
                  onChange={(event) =>
                    patchForm(
                      "sehuaSections",
                      formState.sehuaSections.map((currentSection, currentIndex) =>
                        currentIndex === sectionIndex
                          ? { ...currentSection, name: event.target.value }
                          : currentSection,
                      ),
                    )
                  }
                  className="w-40 shrink-0"
                >
                  {SEHUA_SECTION_OPTIONS.map((option) => (
                    <option key={option}>{option}</option>
                  ))}
                </Select>
                <Input
                  value={section.savePath}
                  onChange={(event) =>
                    patchForm(
                      "sehuaSections",
                      formState.sehuaSections.map((currentSection, currentIndex) =>
                        currentIndex === sectionIndex
                          ? { ...currentSection, savePath: event.target.value }
                          : currentSection,
                      ),
                    )
                  }
                  placeholder="/AV/涩花/..."
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() =>
                    patchForm(
                      "sehuaSections",
                      formState.sehuaSections.filter((_, currentIndex) => currentIndex !== sectionIndex),
                    )
                  }
                >
                  <Trash2 className="h-4 w-4 text-rose-500" />
                </Button>
              </div>
            ))}
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() =>
                patchForm("sehuaSections", [
                  ...formState.sehuaSections,
                  { name: "国产原创", savePath: "/AV/涩花/国产原创" },
                ])
              }
            >
              <Plus className="h-4 w-4" />
              添加版块
            </Button>
          </div>
        </Row>
      </SpiderBlock>
      {saveMutation.isError ? <ErrorState message={errorMessage(saveMutation.error)} /> : null}
    </Section>
  );
}

export function StrategyRulesManager() {
  const queryClient = useQueryClient();
  const [editingRule, setEditingRule] = useState<StrategyRule | null>(null);
  const [formState, setFormState] = useState<StrategyRuleInput>(EMPTY_RULE);
  const [testTitle, setTestTitle] = useState("");
  const configQuery = useQuery({ queryKey: ["system", "config"], queryFn: systemApi.config });
  const rulesQuery = useQuery({ queryKey: ["strategy", "rules"], queryFn: strategyApi.list });
  const sectionOptions = useMemo(
    () =>
      uniqueValues([
        ...getConfiguredSehuaSections(configQuery.data?.config),
        ...(rulesQuery.data?.items.map((rule) => rule.sectionName) || []),
        ...SEHUA_SECTION_OPTIONS,
      ]),
    [configQuery.data?.config, rulesQuery.data?.items],
  );
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["strategy", "rules"] });
  const createMutation = useMutation({
    mutationFn: strategyApi.create,
    onSuccess: () => {
      setFormState(EMPTY_RULE);
      refresh();
    },
  });
  const updateMutation = useMutation({
    mutationFn: ({ id, rule }: { id: number; rule: StrategyRuleInput }) => strategyApi.update(id, rule),
    onSuccess: () => {
      setEditingRule(null);
      setFormState(EMPTY_RULE);
      refresh();
    },
  });
  const removeMutation = useMutation({ mutationFn: strategyApi.delete, onSuccess: refresh });
  const testMutation = useMutation({ mutationFn: strategyApi.test });

  useEffect(() => {
    if (editingRule) {
      setFormState({
        sectionName: editingRule.sectionName,
        strategyName: editingRule.strategyName,
        pattern: editingRule.pattern,
        specifySavePath: editingRule.specifySavePath || "",
      });
    }
  }, [editingRule]);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const normalizedRule = normalizeRuleInput(formState);
    if (!normalizedRule.sectionName || !normalizedRule.strategyName || !normalizedRule.pattern) return;
    if (editingRule) {
      updateMutation.mutate({ id: editingRule.id, rule: normalizedRule });
      return;
    }
    createMutation.mutate(normalizedRule);
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[1fr_420px]">
        <Card>
          {rulesQuery.isPending ? <LoadingState /> : null}
          {rulesQuery.isError ? <ErrorState message={errorMessage(rulesQuery.error)} /> : null}
          {rulesQuery.data?.items.length === 0 ? <EmptyState>暂无策略规则</EmptyState> : null}
          {rulesQuery.data?.items.length ? (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="border-b border-border text-left text-muted-foreground">
                  <tr>
                    <th className="py-2 pr-4 font-medium">策略</th>
                    <th className="py-2 pr-4 font-medium">版块</th>
                    <th className="py-2 pr-4 font-medium">正则</th>
                    <th className="py-2 pr-4 font-medium">保存路径</th>
                    <th className="py-2 pr-4 text-right font-medium">操作</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {rulesQuery.data.items.map((rule) => (
                    <tr key={rule.id}>
                      <td className="py-3 pr-4 font-medium">{rule.strategyName}</td>
                      <td className="py-3 pr-4">{rule.sectionName}</td>
                      <td className="max-w-sm py-3 pr-4 font-mono text-xs">{rule.pattern}</td>
                      <td className="py-3 pr-4 text-muted-foreground">{rule.specifySavePath || "-"}</td>
                      <td className="py-3 pr-4">
                        <div className="flex justify-end gap-2">
                          <Button size="icon" variant="secondary" onClick={() => setEditingRule(rule)} aria-label="编辑">
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            size="icon"
                            variant="ghost"
                            loading={removeMutation.isPending}
                            onClick={() => removeMutation.mutate(rule.id)}
                            aria-label="删除"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </Card>
        <div className="space-y-4">
          <Card>
            <h2 className="mb-4 text-base font-semibold">{editingRule ? "编辑规则" : "新增规则"}</h2>
            <form className="space-y-3" onSubmit={handleSubmit}>
              <Select
                required
                value={formState.sectionName}
                onChange={(event) => setFormState({ ...formState, sectionName: event.target.value })}
              >
                <option value="" disabled>
                  选择版块
                </option>
                {sectionOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </Select>
              <Input
                required
                placeholder="策略名称"
                value={formState.strategyName}
                onChange={(event) => setFormState({ ...formState, strategyName: event.target.value })}
              />
              <Input
                required
                placeholder="正则表达式"
                value={formState.pattern}
                onChange={(event) => setFormState({ ...formState, pattern: event.target.value })}
              />
              <Input
                placeholder="指定保存路径"
                value={formState.specifySavePath || ""}
                onChange={(event) => setFormState({ ...formState, specifySavePath: event.target.value })}
              />
              <div className="flex gap-2">
                <Button loading={createMutation.isPending || updateMutation.isPending} type="submit">
                  <Plus className="h-4 w-4" />
                  保存
                </Button>
                {editingRule ? (
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => {
                      setEditingRule(null);
                      setFormState(EMPTY_RULE);
                    }}
                  >
                    取消
                  </Button>
                ) : null}
              </div>
            </form>
          </Card>
          <Card>
            <h2 className="mb-4 text-base font-semibold">正则测试</h2>
            <div className="space-y-3">
              <Input placeholder="样例标题" value={testTitle} onChange={(event) => setTestTitle(event.target.value)} />
              <Button
                variant="secondary"
                disabled={!formState.pattern || !testTitle}
                loading={testMutation.isPending}
                onClick={() => testMutation.mutate({ pattern: formState.pattern, title: testTitle })}
              >
                测试当前正则
              </Button>
              {testMutation.data ? (
                <Badge tone={testMutation.data.matched ? "success" : "danger"}>
                  {testMutation.data.matched ? (
                    <CheckCircle2 className="mr-1 h-3.5 w-3.5" />
                  ) : (
                    <XCircle className="mr-1 h-3.5 w-3.5" />
                  )}
                  {testMutation.data.matched ? "匹配" : "不匹配"}
                </Badge>
              ) : null}
              {testMutation.isError ? <ErrorState message={errorMessage(testMutation.error)} /> : null}
            </div>
          </Card>
        </div>
      </div>
  );
}

export function Strategy() {
  return (
    <>
      <PageHeader title="爬虫配置" description="管理爬虫运行参数、爬取版块和标题匹配策略" />
      <div className="space-y-4">
        <CrawlerConfigPanel />
        <SectionTitle title="爬虫策略" description="维护标题正则规则，并用样例标题即时验证匹配结果" />
        <StrategyRulesManager />
      </div>
    </>
  );
}

function Section({
  title,
  children,
  onSave,
  saving,
  justSaved,
}: {
  title: string;
  children: ReactNode;
  onSave?: () => void;
  saving?: boolean;
  justSaved?: boolean;
}) {
  return (
    <Card>
      <div className="mb-5 flex items-start justify-between gap-4">
        <h2 className="text-base font-semibold">{title}</h2>
        {onSave ? (
          <Button size="sm" onClick={onSave} loading={saving}>
            <Save className="h-3.5 w-3.5" />
            {justSaved ? "已保存 ✓" : "保存"}
          </Button>
        ) : null}
      </div>
      <div className="divide-y divide-border">{children}</div>
    </Card>
  );
}

function SectionTitle({ title, description }: { title: string; description: string }) {
  return (
    <div className="pt-1">
      <h2 className="text-base font-semibold">{title}</h2>
      <p className="mt-1 text-xs text-muted-foreground">{description}</p>
    </div>
  );
}

function SpiderBlock({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="overflow-hidden rounded-md border border-border">
      <div className="border-b border-border bg-muted/50 px-4 py-3 text-sm font-medium">{label}</div>
      <div className="divide-y divide-border px-4">{children}</div>
    </div>
  );
}

function Row({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-3 py-5 sm:flex-row sm:items-start sm:gap-10">
      <div className="sm:w-40 sm:shrink-0">
        <p className="text-sm font-medium">{label}</p>
        {hint ? <p className="mt-1 text-xs leading-snug text-muted-foreground">{hint}</p> : null}
      </div>
      <div className="flex flex-1 items-center">{children}</div>
    </div>
  );
}

function Switch({
  checked,
  onCheckedChange,
}: {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onCheckedChange(!checked)}
      className={cn(
        "relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30",
        checked ? "bg-primary" : "bg-muted-foreground/30",
      )}
    >
      <span
        className={cn(
          "pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform",
          checked ? "translate-x-4" : "translate-x-0",
        )}
      />
    </button>
  );
}
