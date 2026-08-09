import { config } from "dotenv";
import { dirname, resolve } from "path";
import { fileURLToPath } from "url";

// This side-effect module must be the first dependency evaluated by index.ts.
// Runtime configuration imports can then validate values loaded from the
// project-local .env instead of freezing defaults before dotenv runs.
const moduleDirectory = dirname(fileURLToPath(import.meta.url));
const envPath = resolve(moduleDirectory, "../.env");

try {
  config({ path: envPath, quiet: true });
} catch {
  // .env is optional.
}
