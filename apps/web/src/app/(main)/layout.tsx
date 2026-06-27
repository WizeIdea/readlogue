import { Header } from "@/components/header";

export default function DashboardLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <div className="app-shell">
      <Header />
      <main className="app-main">{children}</main>
    </div>
  );
}
