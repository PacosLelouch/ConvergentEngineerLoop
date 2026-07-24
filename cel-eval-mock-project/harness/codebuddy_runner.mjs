/** Run CodeBuddy Agent SDK with the same mutation checkpoint collector as Codex. */

import { execFileSync } from "node:child_process";
import { appendFileSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, isAbsolute, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { query } from "@tencent-ai/agent-sdk";


function parseArgs(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index];
    const value = argv[index + 1];
    if (!key?.startsWith("--") || value === undefined) {
      throw new Error("usage: node codebuddy_runner.mjs --config FILE (--prompt TEXT | --prompt-file FILE)");
    }
    result[key.slice(2)] = value;
  }
  return result;
}


const args = parseArgs(process.argv.slice(2));
if (!args.config || (!args.prompt && !args["prompt-file"])) {
  throw new Error("--config and one of --prompt/--prompt-file are required");
}
const configPath = resolve(args.config);
const config = JSON.parse(readFileSync(configPath, "utf8"));
config.workspace = resolve(config.workspace);
config.output = resolve(config.output);
const workerHome = resolve(config.worker_home ?? resolve(config.workspace, ".eval-user-home"));
mkdirSync(workerHome, { recursive: true });
process.env.HOME = workerHome;
if (process.platform === "win32") process.env.USERPROFILE = workerHome;
const prompt = args.prompt ?? readFileSync(resolve(args["prompt-file"]), "utf8");
const harnessRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const python = config.python_executable ?? (process.platform === "win32" ? "python" : "python3");
const pythonEnv = {
  ...process.env,
  PYTHONPATH: process.env.PYTHONPATH
    ? `${harnessRoot}${process.platform === "win32" ? ";" : ":"}${process.env.PYTHONPATH}`
    : harnessRoot,
};


function callCollector(command, extraArgs = [], input = "") {
  return execFileSync(
    python,
    ["-m", "harness.cli", command, "--config", configPath, ...extraArgs],
    { cwd: harnessRoot, env: pythonEnv, input, encoding: "utf8", maxBuffer: 20 * 1024 * 1024 },
  );
}


function appendJsonl(filename, value) {
  appendFileSync(resolve(config.output, filename), `${JSON.stringify(value)}\n`, "utf8");
}


callCollector("verify");
callCollector("capture", ["--cause", "baseline"]);
const started = Date.now();
let resultMessage = null;
let thrownError = null;

const postToolUse = async (input, toolUseID) => {
  const toolInput = input?.tool_input ?? input?.input ?? {};
  const safeEvent = {
    hook_event_name: "PostToolUse",
    tool_name: input?.tool_name ?? input?.toolName,
    tool_use_id: toolUseID,
    tool_input: Object.fromEntries(Object.keys(toolInput).map((key) => [key, null])),
  };
  appendJsonl("events.jsonl", {
    event: "tool_completed",
    tool_name: safeEvent.tool_name,
    tool_use_id: toolUseID,
  });
  callCollector("capture", ["--cause", "post_tool_use"], JSON.stringify(safeEvent));
  return {};
};

const options = {
  cwd: config.workspace,
  maxTurns: config.max_turns ?? 50,
  settingSources: config.setting_sources ?? ["project"],
  permissionMode: config.permission_mode ?? "acceptEdits",
  persistSession: false,
  hooks: {
    PostToolUse: [{ matcher: "*", hooks: [postToolUse], timeout: config.hook_timeout_ms ?? 300000 }],
  },
};
if (config.model) options.model = config.model;
if (config.path_to_codebuddy) options.pathToCodebuddyCode = config.path_to_codebuddy;
if (options.permissionMode === "bypassPermissions") options.allowDangerouslySkipPermissions = true;

try {
  const stream = query({ prompt, options });
  for await (const message of stream) {
    appendJsonl("platform-events.jsonl", message);
    if (message.type === "assistant") {
      for (const block of message.message?.content ?? []) {
        if (block.type === "tool_use") {
          appendJsonl("events.jsonl", {
            event: "tool_use",
            tool_name: block.name,
            tool_use_id: block.id,
            input_keys: Object.keys(block.input ?? {}).sort(),
          });
        }
      }
    } else if (message.type === "result") {
      resultMessage = message;
    }
  }
} catch (error) {
  thrownError = error;
} finally {
  callCollector("capture", ["--cause", "final"]);
  callCollector("verify");
}

const runData = {
  platform: "codebuddy",
  exit_code: thrownError || resultMessage?.is_error ? 1 : 0,
  duration_ms: resultMessage?.duration_ms ?? (Date.now() - started),
  duration_api_ms: resultMessage?.duration_api_ms,
  num_turns: resultMessage?.num_turns ?? 0,
  total_cost_usd: resultMessage?.total_cost_usd,
  usage: resultMessage?.usage ?? {},
  result_subtype: resultMessage?.subtype,
  error: thrownError ? String(thrownError) : undefined,
};
writeFileSync(resolve(config.output, "run.json"), JSON.stringify(runData, null, 2), "utf8");
callCollector("reduce");
if (thrownError) throw thrownError;
process.exitCode = runData.exit_code;
