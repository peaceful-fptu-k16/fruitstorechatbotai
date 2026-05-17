import type { Metadata } from "next";
import { Be_Vietnam_Pro, Playfair_Display } from "next/font/google";

import "./globals.css";

/* Be Vietnam Pro – thiết kế riêng cho tiếng Việt */
const bodyFont = Be_Vietnam_Pro({
  subsets: ["vietnamese", "latin"],
  variable: "--font-body",
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

/* Playfair Display – tiêu đề sang trọng */
const titleFont = Playfair_Display({
  subsets: ["latin"],
  variable: "--font-title",
  weight: ["500", "600", "700"],
  style: ["normal", "italic"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Trái Cây Tươi – Chatbot Tư Vấn Thông Minh",
  description:
    "Chatbot AI tư vấn trái cây tươi theo khẩu vị, tồn kho thời gian thực và ngân sách của bạn.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="vi">
      <body className={`${titleFont.variable} ${bodyFont.variable}`}>
        {/* Animated background blobs – trang trí nền */}
        <div
          aria-hidden="true"
          className="bg-blob"
          style={
            {
              width: "640px",
              height: "640px",
              top: "-220px",
              left: "-160px",
              background:
                "radial-gradient(circle, rgba(245,166,35,0.20) 0%, transparent 70%)",
              "--dur": "15s",
              "--delay": "0s",
            } as React.CSSProperties
          }
        />
        <div
          aria-hidden="true"
          className="bg-blob"
          style={
            {
              width: "520px",
              height: "520px",
              top: "30%",
              right: "-180px",
              background:
                "radial-gradient(circle, rgba(240,99,34,0.16) 0%, transparent 70%)",
              "--dur": "19s",
              "--delay": "4s",
            } as React.CSSProperties
          }
        />
        <div
          aria-hidden="true"
          className="bg-blob"
          style={
            {
              width: "420px",
              height: "420px",
              bottom: "-80px",
              left: "38%",
              background:
                "radial-gradient(circle, rgba(45,149,85,0.14) 0%, transparent 70%)",
              "--dur": "17s",
              "--delay": "8s",
            } as React.CSSProperties
          }
        />

        <div className="relative z-10">{children}</div>
      </body>
    </html>
  );
}

