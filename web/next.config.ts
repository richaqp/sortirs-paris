import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "**.paris.fr" },
      { protocol: "https", hostname: "**.ticketmaster.com" },
      { protocol: "https", hostname: "**.ticketweb.com" },
      { protocol: "https", hostname: "**.livenation.com" },
      { protocol: "https", hostname: "opendata.paris.fr" },
      { protocol: "https", hostname: "**.scdn.co" },
      { protocol: "https", hostname: "**.ticketmaster.net" },
    ],
  },
};

export default nextConfig;
