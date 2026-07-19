/**
 * CLI-It extension for Pi (@mariozechner/pi-coding-agent).
 *
 * Registers the /cli-it command family. Each command reads the markdown SOP
 * shipped beside this extension (install.sh copies the plugin assets here),
 * remaps repo-absolute paths to the user's working directory, and injects the
 * result as a user message. The commands are prompts — the agent does the work.
 */

import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

// Minimal structural type for the Pi ExtensionAPI surface we use.
interface ExtensionAPI {
  registerCommand(
    name: string,
    options: {
      description: string;
      handler: (args: string[]) => void | Promise<void>;
    }
  ): void;
  sendUserMessage(message: string): void;
  notify(message: string, level?: "info" | "warning" | "error"): void;
}

const EXT_DIR = dirname(fileURLToPath(import.meta.url));

const COMMANDS: Record<string, { asset: string; description: string; needsArg: boolean }> = {
  "cli-it": {
    asset: "commands/cli-it.md",
    description: "Build a CLI-It agent harness for a local path or GitHub URL",
    needsArg: true,
  },
  "cli-it:refine": {
    asset: "commands/refine.md",
    description: "Gap analysis + coverage refinement for an existing harness",
    needsArg: false,
  },
  "cli-it:test": {
    asset: "commands/test.md",
    description: "Run harness tests and update TEST.md",
    needsArg: false,
  },
  "cli-it:validate": {
    asset: "commands/validate.md",
    description: "Validate a harness against the HARNESS.md checklist",
    needsArg: false,
  },
  "cli-it:list": {
    asset: "commands/list.md",
    description: "List harnesses in the project and installed CLI-It tools",
    needsArg: false,
  },
};

function readAsset(relative: string): string | null {
  const path = join(EXT_DIR, relative);
  return existsSync(path) ? readFileSync(path, "utf-8") : null;
}

/**
 * Remap paths written for the monorepo layout onto this installation:
 *  - hardcoded upstream checkout roots → the user's cwd
 *  - cli-it-plugin/repl_skin.py → the copy installed beside the extension
 *  - guides/templates/scripts references → extension-relative absolute paths
 */
function remapPaths(content: string): string {
  return content
    .replace(/\/root\/cli-it\//g, `${process.cwd()}/`)
    .replace(/cli-it-plugin\/repl_skin\.py/g, join(EXT_DIR, "scripts", "repl_skin.py"))
    .replace(/cli-it-plugin\/skill_generator\.py/g, join(EXT_DIR, "skill_generator.py"))
    .replace(/cli-it-plugin\/preview_bundle\.py/g, join(EXT_DIR, "preview_bundle.py"))
    .replace(/(?<![\w/])guides\//g, `${join(EXT_DIR, "guides")}/`)
    .replace(/(?<![\w/])templates\//g, `${join(EXT_DIR, "templates")}/`);
}

function isValidTarget(arg: string): boolean {
  if (/^https:\/\/github\.com\//.test(arg)) return true;
  if (arg.startsWith("/") || arg.startsWith("./") || arg.startsWith("~") || arg.startsWith("..")) {
    return true;
  }
  // bare names are rejected by design — the methodology needs real source
  return existsSync(arg);
}

export default function activate(pi: ExtensionAPI): void {
  for (const [name, spec] of Object.entries(COMMANDS)) {
    pi.registerCommand(name, {
      description: spec.description,
      handler: (args: string[]) => {
        const target = (args ?? []).join(" ").trim();
        if (spec.needsArg && !target) {
          pi.notify(`usage: /${name} <local-path-or-github-url>`, "warning");
          return;
        }
        if (spec.needsArg && !isValidTarget(target)) {
          pi.notify(
            `'${target}' is not a local path or GitHub URL — bare software names are not accepted`,
            "error"
          );
          return;
        }

        const harness = readAsset("HARNESS.md");
        const command = readAsset(spec.asset);
        if (!harness || !command) {
          pi.notify(
            "cli-it extension assets missing — re-run install.sh from the CLI-It repo",
            "error"
          );
          return;
        }

        const parts = [
          "# CLI-It methodology (HARNESS.md)",
          remapPaths(harness),
          `# Command: /${name}`,
          remapPaths(command),
        ];
        if (target) parts.push(`# Target\n\n${target}`);
        pi.sendUserMessage(parts.join("\n\n---\n\n"));
      },
    });
  }
}
