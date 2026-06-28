import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "ReadLogue",
  description: "Research corpus curation",
  manifest: "/site.webmanifest",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
