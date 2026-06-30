# Claude session notes for kevinrothwx-site

Read this at the start of every session before doing any code work.

**Also read `SESSION_NOTES.md`** alongside this file. CLAUDE.md is workflow rules (OneDrive recovery, GitHub Desktop discipline, mandatory sweep). SESSION_NOTES.md is project state — what's built, brand decisions, sport-by-sport status, outstanding work.

## The OneDrive truncation problem (CRITICAL)

This repo lives in `C:\Users\kjrfs\OneDrive\Documents\GitHub\kevinrothwx-site`, which is OneDrive-synced. The Linux sandbox mounts it via cloud sync, which creates a three-way file state:

- Cloud copy: usually correct
- Linux disk view (bash sees this): can be silently truncated mid-file
- Windows disk view (GitHub Desktop sees this): syncs from cloud, can lag

When the Edit or Write tool runs on a long file, OneDrive's sync conflict resolution sometimes drops the tail of the file. The Read tool reads from cloud (sees the complete file), but bash reads from disk (sees the truncated file). Git commits use the disk version, so Kevin can push truncated files without realizing it. Render then deploys broken code and pages return 500.

On 2026-06-10 this caused a cascade: 10 Python files and 7 templates were all silently truncated, PGA and NASCAR served 500 errors, the diagnosis and recovery took multiple hours.

## MANDATORY workflow after any batch of code edits

Before telling Kevin to push, ALWAYS run this verification sweep:

```bash
cd "$REPO_ROOT" && python3 <<'EOF'
import ast, os
broken_py = []
for root, dirs, files in os.walk('.'):
    if '.git' in root or '__pycache__' in root: continue
    for fn in files:
        if fn.endswith('.py'):
            try:
                ast.parse(open(os.path.join(root, fn)).read())
            except SyntaxError as e:
                broken_py.append((os.path.join(root, fn), e.lineno, e.msg))
print(f"Python: {len(broken_py)} broken")
for p, l, m in broken_py: print(f"  {p}:{l}: {m}")

from jinja2 import Environment, FileSystemLoader, TemplateSyntaxError
env = Environment(loader=FileSystemLoader('templates'))
broken_j = []
for root, dirs, files in os.walk('templates'):
    for fn in files:
        if fn.endswith('.html'):
            full = os.path.join(root, fn)
            try:
                env.parse(open(full).read())
            except TemplateSyntaxError as e:
                broken_j.append((os.path.relpath(full, 'templates'), e.lineno, e.message))
print(f"Templates: {len(broken_j)} broken")
for p, l, m in broken_j: print(f"  {p}:{l}: {m}")
EOF
```

If anything is broken, fix it BEFORE asking Kevin to push.

## Recovery procedure when truncation is found

For each broken file:

1. Read the full content via the Read tool. The Read tool reads from OneDrive cloud which usually has the complete version.
2. Write the full content back to disk via bash heredoc:

```bash
cat > path/to/file.py <<'PYEOF'
... complete file content here ...
PYEOF
```

The heredoc bypasses the Edit-tool path that races with OneDrive sync and writes directly to the Linux disk. Wait 3-5 seconds (`sleep 5`) after writing, then verify with `python3 -c "import ast; ast.parse(open('path').read())"`.

Do NOT trust the file is fine just because Read shows correct content. Bash and git see the disk version, which is what gets pushed.

## When using Edit tool on long files

If editing files longer than ~100 lines or files where you're touching content near the end:

1. Make the edit.
2. Wait 2-3 seconds.
3. Run the syntax sweep above for whichever file type you touched.
4. If broken, fix via heredoc per recovery procedure.

For short files / single-line edits / files where the touched lines are well above the end, the Edit tool is usually fine. The truncation tends to hit the tail of the file.

## Pushing through GitHub Desktop

Kevin commits and pushes from his Windows machine via GitHub Desktop. Linux-side git operations on this OneDrive path are unreliable (the index file itself can get corrupted by sync races). Do not attempt `git add`/`git commit`/`git push` from bash on this repo.

When telling Kevin to push:
- List the files he should check in GitHub Desktop.
- Tell him to glance at one or two diffs to confirm they look complete (especially the last few lines).
- If GitHub Desktop shows zero changes when he expected some, OneDrive hasn't synced yet — wait, do not push.

## Render deploy notes

- Service name: `kevinrothwx-site`
- Plan: Starter ($7/mo)
- Persistent disk mounted at `/var/data` (1 GB), used by `persistence.py` for writeups + MLB freeze
- Warmer threads run every 25 min for each sport (mlb, worldcup, golf, nascar, cws)
- Admin password is set via `ADMIN_PASSWORD` env var; admin URLs are `/admin/{mlb,worldcup,golf,nascar,cws}`

## Things to NOT touch

- Anything at `app.kevinrothwx.com` (that's the separate OVERcast service)
- The MLB forecast freeze logic when a game is already in progress (treat frozen snapshots as immutable)
