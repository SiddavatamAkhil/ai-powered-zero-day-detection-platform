/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  experimental: {
    workerThreads: false,
    cpus: 1,
  },
};

module.exports = nextConfig;
