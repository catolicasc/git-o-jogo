import type { Metadata } from "next";
import { Cinzel, Lato } from "next/font/google";
import "./globals.css";

const cinzel = Cinzel({ subsets: ["latin"], variable: "--font-cinzel" });
const lato = Lato({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-lato",
});

export const metadata: Metadata = {
  title: "As Crônicas de Aetheria",
  description: "A collaborative storytelling game to teach Git.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${cinzel.variable} ${lato.variable} antialiased bg-[#f4e4bc] text-[#2c1810] overflow-hidden`}
        style={{
            backgroundImage: "url('/parchment-texture.jpg')", // Placeholder for texture
            backgroundBlendMode: "multiply",
        }}
      >
        <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(circle_at_center,transparent_0%,#00000030_100%)]" />
        {children}
      </body>
    </html>
  );
}
