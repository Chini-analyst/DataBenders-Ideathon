/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Allow react-force-graph-2d (uses canvas)
  transpilePackages: ["react-force-graph-2d", "force-graph"],
  webpack: (config) => {
    // Required for react-force-graph-2d
    config.externals = config.externals || [];
    return config;
  },
};

module.exports = nextConfig;
