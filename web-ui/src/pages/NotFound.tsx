import { Link } from "react-router-dom";

import { Card } from "../components/ui";

export function NotFound() {
  return (
    <Card className="mx-auto max-w-md text-center">
      <h1 className="text-xl font-semibold">页面不存在</h1>
      <p className="mt-2 text-sm text-muted-foreground">当前路由没有对应的页面。</p>
      <Link className="mt-4 inline-flex h-9 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground" to="/">
        返回 Dashboard
      </Link>
    </Card>
  );
}
