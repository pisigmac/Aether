const vscode = require("vscode");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawn } = require("child_process");

const repoFile = path.join(os.homedir(), ".aether", "live-repo");
const pidFile = path.join(os.homedir(), ".aether", "livebar.pid");

function workspaceRepo() {
  const folder = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0];
  return folder ? folder.uri.fsPath : "";
}

function publishRepo() {
  const repo = workspaceRepo();
  if (!repo) return;
  fs.mkdirSync(path.dirname(repoFile), { recursive: true });
  fs.writeFileSync(repoFile, repo);
}

function pidAlive(pid) {
  if (!pid) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch (err) {
    return err && err.code === "EPERM";
  }
}

function aetherBin() {
  if (process.env.AETHER_BIN) return process.env.AETHER_BIN;
  const folders = vscode.workspace.workspaceFolders || [];
  for (const folder of folders) {
    const candidate = path.join(folder.uri.fsPath, "engine", ".venv", "bin", "aether");
    if (fs.existsSync(candidate)) return candidate;
  }
  return "aether";
}

function showBar() {
  publishRepo();
  let existing = 0;
  try {
    existing = Number(fs.readFileSync(pidFile, "utf8").trim());
  } catch {
    existing = 0;
  }
  if (pidAlive(existing)) return;
  const child = spawn(aetherBin(), ["livebar"], {
    detached: true,
    stdio: "ignore",
  });
  child.unref();
}

function activate(context) {
  publishRepo();
  showBar();
  context.subscriptions.push(
    vscode.workspace.onDidChangeWorkspaceFolders(() => publishRepo()),
    vscode.window.onDidChangeWindowState((state) => {
      if (state.focused) publishRepo();
    }),
    vscode.commands.registerCommand("aether.livebar.show", showBar),
  );
}

function deactivate() {}

module.exports = { activate, deactivate };
