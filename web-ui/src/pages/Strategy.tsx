import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Pencil, Plus, Trash2, XCircle } from "lucide-react";

import { strategyApi } from "../api/queries";
import type { StrategyRule, StrategyRuleInput } from "../api/types";
import { Badge, Button, Card, EmptyState, ErrorState, Input, LoadingState, PageHeader } from "../components/ui";
import { errorMessage } from "../lib/utils";

const emptyRule: StrategyRuleInput = {
  section_name: "",
  strategy_name: "",
  pattern: "",
  specify_save_path: "",
};

export function Strategy() {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState<StrategyRule | null>(null);
  const [form, setForm] = useState<StrategyRuleInput>(emptyRule);
  const [testTitle, setTestTitle] = useState("");
  const rules = useQuery({ queryKey: ["strategy", "rules"], queryFn: strategyApi.list });
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["strategy", "rules"] });
  const create = useMutation({ mutationFn: strategyApi.create, onSuccess: () => { setForm(emptyRule); refresh(); } });
  const update = useMutation({ mutationFn: ({ id, rule }: { id: number; rule: StrategyRuleInput }) => strategyApi.update(id, rule), onSuccess: () => { setEditing(null); setForm(emptyRule); refresh(); } });
  const remove = useMutation({ mutationFn: strategyApi.delete, onSuccess: refresh });
  const test = useMutation({ mutationFn: strategyApi.test });

  useEffect(() => {
    if (editing) setForm({ section_name: editing.section_name, strategy_name: editing.strategy_name, pattern: editing.pattern, specify_save_path: editing.specify_save_path || "" });
  }, [editing]);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (editing) update.mutate({ id: editing.id, rule: form });
    else create.mutate(form);
  }

  return (
    <>
      <PageHeader title="策略管理" description="维护标题正则规则，并用样例标题即时验证匹配结果" />
      <div className="grid gap-4 xl:grid-cols-[1fr_420px]">
        <Card>
          {rules.isPending ? <LoadingState /> : null}
          {rules.isError ? <ErrorState message={errorMessage(rules.error)} /> : null}
          {rules.data?.items.length === 0 ? <EmptyState>暂无策略规则</EmptyState> : null}
          {rules.data?.items.length ? (
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
                  {rules.data.items.map((rule) => (
                    <tr key={rule.id}>
                      <td className="py-3 pr-4 font-medium">{rule.strategy_name}</td>
                      <td className="py-3 pr-4">{rule.section_name}</td>
                      <td className="max-w-sm py-3 pr-4 font-mono text-xs">{rule.pattern}</td>
                      <td className="py-3 pr-4 text-muted-foreground">{rule.specify_save_path || "-"}</td>
                      <td className="py-3 pr-4">
                        <div className="flex justify-end gap-2">
                          <Button size="icon" variant="secondary" onClick={() => setEditing(rule)} aria-label="编辑"><Pencil className="h-4 w-4" /></Button>
                          <Button size="icon" variant="ghost" loading={remove.isPending} onClick={() => remove.mutate(rule.id)} aria-label="删除"><Trash2 className="h-4 w-4" /></Button>
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
            <h2 className="mb-4 text-base font-semibold">{editing ? "编辑规则" : "新增规则"}</h2>
            <form className="space-y-3" onSubmit={submit}>
              <Input required placeholder="版块名称" value={form.section_name} onChange={(event) => setForm({ ...form, section_name: event.target.value })} />
              <Input required placeholder="策略名称" value={form.strategy_name} onChange={(event) => setForm({ ...form, strategy_name: event.target.value })} />
              <Input required placeholder="正则表达式" value={form.pattern} onChange={(event) => setForm({ ...form, pattern: event.target.value })} />
              <Input placeholder="指定保存路径" value={form.specify_save_path || ""} onChange={(event) => setForm({ ...form, specify_save_path: event.target.value })} />
              <div className="flex gap-2">
                <Button loading={create.isPending || update.isPending} type="submit"><Plus className="h-4 w-4" />保存</Button>
                {editing ? <Button type="button" variant="secondary" onClick={() => { setEditing(null); setForm(emptyRule); }}>取消</Button> : null}
              </div>
            </form>
          </Card>
          <Card>
            <h2 className="mb-4 text-base font-semibold">正则测试</h2>
            <div className="space-y-3">
              <Input placeholder="样例标题" value={testTitle} onChange={(event) => setTestTitle(event.target.value)} />
              <Button variant="secondary" disabled={!form.pattern || !testTitle} loading={test.isPending} onClick={() => test.mutate({ pattern: form.pattern, title: testTitle })}>测试当前正则</Button>
              {test.data ? (
                <Badge tone={test.data.matched ? "success" : "danger"}>
                  {test.data.matched ? <CheckCircle2 className="mr-1 h-3.5 w-3.5" /> : <XCircle className="mr-1 h-3.5 w-3.5" />}
                  {test.data.matched ? "匹配" : "不匹配"}
                </Badge>
              ) : null}
              {test.isError ? <ErrorState message={errorMessage(test.error)} /> : null}
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}
