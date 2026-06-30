import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Vulcan",
  description: "Multi-tenant operational intelligence with explainable analytics.",
  applicationName: "Vulcan",
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Vulcan"
  },
  icons: {
    icon: "/vulcan-symbol.svg",
    shortcut: "/vulcan-symbol.svg",
    apple: "/vulcan-symbol.svg"
  }
};

export const viewport: Viewport = {
  themeColor: "#050507"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
