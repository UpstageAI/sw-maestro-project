import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Brainrot Patent",
  description: "Turn absurd ideas into patent-style demo documents.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}

