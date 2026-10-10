import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NeerDrishti — Watershed Intelligence & Verification",
  description:
    "Cross-check field photos against Sentinel-2 satellite data to verify water conservation work — check dams, farm ponds, afforestation — at any coordinate on earth.",
  keywords: [
    "NeerDrishti",
    "watershed intelligence",
    "satellite verification",
    "NDVI",
    "NDWI",
    "water conservation",
    "check dam",
    "field photo audit",
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full antialiased" suppressHydrationWarning>
      <head />
      <body
        className="min-h-full flex flex-col bg-strata text-basalt selection:bg-reservoir/20 selection:text-reservoir"
        suppressHydrationWarning
      >
        {children}
      </body>
    </html>
  );
}
