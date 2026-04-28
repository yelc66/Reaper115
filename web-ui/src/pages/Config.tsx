import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Save, Trash2 } from "lucide-react";

import { systemApi } from "../api/queries";
import { Button, Card, ErrorState, Input, LoadingState, PageHeader, Select } from "../components/ui";
import { cn, errorMessage } from "../lib/utils";

const SEHUA_SECTION_NAMES = [
  "国产原创",
  "亚洲无码原创",
  "亚洲有码原创",
  "高清中文字幕",
  "素人有码系列",
  "4K原版",
  "VR视频区",
  "欧美无码",
];

type SehuaSection = { name: string; save_path: string };

type FormState = {
  log_level: string;
  web_enable: boolean;
  web_port: string;
  bot_token: string;
  allowed_user: string;
  app_id: string;
  access_token: string;
  refresh_token: string;
  clean_switch: boolean;
  clean_less_than: string;
  // 涩花
  sehua_enable: boolean;
  sehua_sync_time: string;
  sehua_base_url: string;
  sehua_notify_me: boolean;
  sehua_sort_by_year_month: boolean;
  sehua_sections: SehuaSection[];
  // Javbee
  javbee_enable: boolean;
  javbee_sync_time: string;
  javbee_base_url: string;
  javbee_notify_me: boolean;
};

function toForm(cfg: Record<string, unknown>): FormState {
  const sehua = (cfg.sehua_spider ?? {}) as Record<string, unknown>;
  const javbee = (cfg.javbee_spider ?? {}) as Record<string, unknown>;
  const cp = (cfg.clean_policy ?? {}) as Record<string, unknown>;
  const web = (cfg.web ?? {}) as Record<string, unknown>;
  return {
    log_level: (cfg.log_level as string) || "info",
    web_enable: web.enable !== false,
    web_port: String(web.port ?? 8000),
    bot_token: (cfg.bot_token as string) || "",
    allowed_user: String(cfg.allowed_user ?? ""),
    app_id: (cfg["115_app_id"] as string) || "",
    access_token: (cfg.access_token as string) || "",
    refresh_token: (cfg.refresh_token as string) || "",
    clean_switch: (cp.switch as string) !== "off",
    clean_less_than: (cp.less_than as string) || "400M",
    sehua_enable: (sehua.enable as boolean) || false,
    sehua_sync_time: (sehua.sync_time as string) || "03:00",
    sehua_base_url: (sehua.base_url as string) || "www.sehuatang.net",
    sehua_notify_me: sehua.notify_me !== false,
    sehua_sort_by_year_month: (sehua.sort_by_year_month as boolean) || false,
    sehua_sections: (sehua.sections as SehuaSection[]) || [],
    javbee_enable: (javbee.enable as boolean) || false,
    javbee_sync_time: (javbee.sync_time as string) || "04:00",
    javbee_base_url: (javbee.base_url as string) || "www.javbee.me",
    javbee_notify_me: javbee.notify_me !== false,
  };
}

function fromForm(f: FormState, original: Record<string, unknown>): Record<string, unknown> {
  return {
    ...original,
    log_level: f.log_level,
    web: { ...(original.web as object || {}), enable: f.web_enable, port: Number(f.web_port) },
    bot_token: f.bot_token,
    allowed_user: f.allowed_user,
    "115_app_id": f.app_id,
    access_token: f.access_token,
    refresh_token: f.refresh_token,
    clean_policy: { switch: f.clean_switch ? "on" : "off", less_than: f.clean_less_than },
    sehua_spider: {
      ...(original.sehua_spider as object || {}),
      enable: f.sehua_enable,
      sync_time: f.sehua_sync_time,
      base_url: f.sehua_base_url,
      notify_me: f.sehua_notify_me,
      sort_by_year_month: f.sehua_sort_by_year_month,
      sections: f.sehua_sections,
    },
    javbee_spider: {
      ...(original.javbee_spider as object || {}),
      enable: f.javbee_enable,
      sync_time: f.javbee_sync_time,
      base_url: f.javbee_base_url,
      notify_me: f.javbee_notify_me,
    },
  };
}

export function Config() {
  const qc = useQueryClient();
  const [form, setForm] = useState<FormState | null>(null);
  const [original, setOriginal] = useState<Record<string, unknown>>({});
  const [justSaved, setJustSaved] = useState(false);

  const q = useQuery({ queryKey: ["system", "config"], queryFn: systemApi.config });
  const saveMut = useMutation({
    mutationFn: (cfg: Record<string, unknown>) => systemApi.updateConfig(cfg),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["system"] });
      setJustSaved(true);
      setTimeout(() => setJustSaved(false), 2500);
    },
  });

  useEffect(() => {
    if (q.data?.config) {
      setOriginal(q.data.config);
      setForm(toForm(q.data.config));
    }
  }, [q.data]);

  function patch<K extends keyof FormState>(key: K, val: FormState[K]) {
    setForm(prev => (prev ? { ...prev, [key]: val } : prev));
  }

  function handleSave() {
    if (form) saveMut.mutate(fromForm(form, original));
  }

  if (q.isPending) return <LoadingState />;
  if (q.isError) return <ErrorState message={errorMessage(q.error)} />;
  if (!form) return null;

  return (
    <>
      <PageHeader
        title="配置管理"
        description="管理机器人运行配置，保存后立即生效（端口等需重启）"
        actions={
          <Button onClick={handleSave} loading={saveMut.isPending}>
            <Save className="h-4 w-4" />
            {justSaved ? "已保存 ✓" : "保存配置"}
          </Button>
        }
      />
      <div className="space-y-4">

        {/* 基础设置 */}
        <Section title="基础设置">
          <Row label="日志级别">
            <Select value={form.log_level} onChange={e => patch("log_level", e.target.value)} className="max-w-40">
              {["debug", "info", "warning", "error", "critical"].map(l => (
                <option key={l}>{l}</option>
              ))}
            </Select>
          </Row>
          <Row label="Web 界面端口" hint="重启后生效">
            <Input
              type="number"
              value={form.web_port}
              onChange={e => patch("web_port", e.target.value)}
              className="max-w-32"
            />
          </Row>
          <Row label="开启 Web 界面">
            <Toggle v={form.web_enable} set={v => patch("web_enable", v)} />
          </Row>
        </Section>

        {/* Telegram */}
        <Section title="Telegram Bot">
          <Row label="Bot Token" hint="必填，@BotFather 创建">
            <Input
              type="password"
              value={form.bot_token}
              onChange={e => patch("bot_token", e.target.value)}
              placeholder="your_bot_token"
            />
          </Row>
          <Row label="授权用户 ID" hint="@getidsbot 获取，数字类型">
            <Input
              value={form.allowed_user}
              onChange={e => patch("allowed_user", e.target.value)}
              placeholder="your_user_id"
              className="max-w-56"
            />
          </Row>
        </Section>

        {/* 115 */}
        <Section title="115 开放平台" hint="App ID 与 Token 二选一，填 App ID 时 Token 可留空">
          <Row label="App ID">
            <Input
              value={form.app_id}
              onChange={e => patch("app_id", e.target.value)}
              placeholder="your_115_app_id"
            />
          </Row>
          <Row label="Access Token">
            <Input
              type="password"
              value={form.access_token}
              onChange={e => patch("access_token", e.target.value)}
              placeholder="your_access_token"
            />
          </Row>
          <Row label="Refresh Token">
            <Input
              type="password"
              value={form.refresh_token}
              onChange={e => patch("refresh_token", e.target.value)}
              placeholder="your_refresh_token"
            />
          </Row>
        </Section>

        {/* 清理策略 */}
        <Section title="离线下载清理">
          <Row label="开启自动清理">
            <Toggle v={form.clean_switch} set={v => patch("clean_switch", v)} />
          </Row>
          <Row label="最小文件大小" hint="小于此值自动删除，如 400M / 1G">
            <Input
              value={form.clean_less_than}
              onChange={e => patch("clean_less_than", e.target.value)}
              className="max-w-32"
              placeholder="400M"
            />
          </Row>
        </Section>

        {/* 爬虫配置 */}
        <Section title="爬虫配置">

          {/* 涩花 */}
          <SpiderBlock label="涩花（sehuatang.net）">
            <Row label="开启爬虫">
              <Toggle v={form.sehua_enable} set={v => patch("sehua_enable", v)} />
            </Row>
            <Row label="触发时间" hint="24h 格式，每日定时爬取前一天数据">
              <Input
                value={form.sehua_sync_time}
                onChange={e => patch("sehua_sync_time", e.target.value)}
                className="max-w-28"
                placeholder="03:00"
              />
            </Row>
            <Row label="站点地址" hint="可填临时镜像地址加速">
              <Input
                value={form.sehua_base_url}
                onChange={e => patch("sehua_base_url", e.target.value)}
                placeholder="www.sehuatang.net"
              />
            </Row>
            <Row label="通知我">
              <Toggle v={form.sehua_notify_me} set={v => patch("sehua_notify_me", v)} />
            </Row>
            <Row label="按年月整理">
              <Toggle v={form.sehua_sort_by_year_month} set={v => patch("sehua_sort_by_year_month", v)} />
            </Row>
            <Row label="爬取版块" hint="选择版块及对应 115 保存路径，至少填一个">
              <div className="space-y-2">
                {form.sehua_sections.map((s, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <Select
                      value={s.name}
                      onChange={e =>
                        patch(
                          "sehua_sections",
                          form.sehua_sections.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)),
                        )
                      }
                      className="w-40 shrink-0"
                    >
                      {SEHUA_SECTION_NAMES.map(n => (
                        <option key={n}>{n}</option>
                      ))}
                    </Select>
                    <Input
                      value={s.save_path}
                      onChange={e =>
                        patch(
                          "sehua_sections",
                          form.sehua_sections.map((x, j) => (j === i ? { ...x, save_path: e.target.value } : x)),
                        )
                      }
                      placeholder="/AV/涩花/…"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() =>
                        patch(
                          "sehua_sections",
                          form.sehua_sections.filter((_, j) => j !== i),
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
                    patch("sehua_sections", [
                      ...form.sehua_sections,
                      { name: "国产原创", save_path: "/AV/涩花/国产原创" },
                    ])
                  }
                >
                  <Plus className="h-4 w-4" />
                  添加版块
                </Button>
              </div>
            </Row>
          </SpiderBlock>

          {/* Javbee */}
          <SpiderBlock label="Javbee（javbee.me）">
            <Row label="开启爬虫">
              <Toggle v={form.javbee_enable} set={v => patch("javbee_enable", v)} />
            </Row>
            <Row label="触发时间" hint="24h 格式">
              <Input
                value={form.javbee_sync_time}
                onChange={e => patch("javbee_sync_time", e.target.value)}
                className="max-w-28"
                placeholder="04:00"
              />
            </Row>
            <Row label="站点地址">
              <Input
                value={form.javbee_base_url}
                onChange={e => patch("javbee_base_url", e.target.value)}
                placeholder="www.javbee.me"
              />
            </Row>
            <Row label="通知我">
              <Toggle v={form.javbee_notify_me} set={v => patch("javbee_notify_me", v)} />
            </Row>
          </SpiderBlock>

        </Section>

        {saveMut.isError && <ErrorState message={errorMessage(saveMut.error)} />}

        <div className="flex justify-end pb-4">
          <Button onClick={handleSave} loading={saveMut.isPending}>
            <Save className="h-4 w-4" />
            {justSaved ? "已保存 ✓" : "保存配置"}
          </Button>
        </div>
      </div>
    </>
  );
}

// ─── layout helpers ────────────────────────────────────────────────────────

function Section({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <div className="mb-4">
        <h2 className="text-base font-semibold">{title}</h2>
        {hint && <p className="mt-0.5 text-xs text-muted-foreground">{hint}</p>}
      </div>
      <div className="divide-y divide-border">{children}</div>
    </Card>
  );
}

function SpiderBlock({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="py-4 first:pt-0 last:pb-0">
      <div className="overflow-hidden rounded-md border border-border">
        <div className="border-b border-border bg-muted/50 px-4 py-2.5 text-sm font-medium">{label}</div>
        <div className="divide-y divide-border px-4">{children}</div>
      </div>
    </div>
  );
}

function Row({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2 py-4 first:pt-0 last:pb-0 sm:flex-row sm:items-start sm:gap-8">
      <div className="sm:w-36 sm:shrink-0">
        <p className="text-sm font-medium">{label}</p>
        {hint && <p className="mt-0.5 text-xs text-muted-foreground leading-snug">{hint}</p>}
      </div>
      <div className="flex-1">{children}</div>
    </div>
  );
}

function Toggle({ v, set }: { v: boolean; set: (x: boolean) => void }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={v}
      onClick={() => set(!v)}
      className={cn(
        "relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30",
        v ? "bg-primary" : "bg-muted-foreground/30",
      )}
    >
      <span
        className={cn(
          "pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform",
          v ? "translate-x-4" : "translate-x-0",
        )}
      />
    </button>
  );
}
