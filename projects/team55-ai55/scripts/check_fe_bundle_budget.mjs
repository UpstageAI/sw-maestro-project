import { readdir, readFile } from "node:fs/promises";
import { gzipSync } from "node:zlib";

const BUNDLE_GZIP_BUDGET_BYTES = 300 * 1024;
const ASSETS_DIR = new URL("../FE/dist/assets/", import.meta.url);

const files = await readdir(ASSETS_DIR);
const bundleFiles = files.filter((file) => /\.(js|css)$/.test(file));

if (bundleFiles.length === 0) {
  throw new Error("No FE bundle assets found. Run npm run build:fe first.");
}

let totalGzipBytes = 0;
const details = [];

for (const file of bundleFiles) {
  const content = await readFile(new URL(file, ASSETS_DIR));
  const gzipBytes = gzipSync(content).byteLength;
  totalGzipBytes += gzipBytes;
  details.push(`${file}=${(gzipBytes / 1024).toFixed(2)}KB`);
}

if (totalGzipBytes > BUNDLE_GZIP_BUDGET_BYTES) {
  throw new Error(
    `FE bundle gzip budget exceeded: ${(totalGzipBytes / 1024).toFixed(2)}KB > 300.00KB (${details.join(", ")})`,
  );
}

console.log(`FE bundle gzip ${(totalGzipBytes / 1024).toFixed(2)}KB / 300.00KB (${details.join(", ")})`);
