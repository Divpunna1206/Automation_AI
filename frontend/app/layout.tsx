import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "Agentic Job Hunt Pipeline",
  description: "Human-in-the-loop job application assistant"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
