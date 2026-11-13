import "./globals.css";

export const metadata = {
  title: "ReportGenix | CSA Engineering",
  description: "Engineering reports automated.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
