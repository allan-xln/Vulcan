import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Vulcan",
  description: "Multi-tenant operational intelligence with explainable analytics.",
  icons: {
    icon: "/vulcan-symbol.svg",
    shortcut: "/vulcan-symbol.svg",
    apple: "/vulcan-symbol.svg"
  }
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
