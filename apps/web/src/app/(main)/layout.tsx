import { Suspense } from "react";

import { FilterSidebar } from "@/components/filter-sidebar";

export default function DashboardLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <div className="app-dashboard">
      <Suspense fallback={<aside className="filter-sidebar filter-sidebar--loading" />}>
        <FilterSidebar />
      </Suspense>
      <main className="app-main">{children}</main>
    </div>
  );
}
