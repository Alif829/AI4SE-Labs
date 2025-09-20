import subprocess
import sys
from git import Repo, Git
from pathlib import Path
import shutil

# Map language -> (git url, dir name, tag)
_GRAMMARs = {
    "java": ("https://github.com/tree-sitter/tree-sitter-java.git", "tree-sitter-java", "v0.20.0"),
    "python": ("https://github.com/tree-sitter/tree-sitter-python.git", "tree-sitter-python", "v0.20.0"),
}

WORKDIR = Path(__file__).resolve().parent.parent
GRAMMAR_ROOT = WORKDIR / "third_party"
BUILD_DIR = WORKDIR / "build"
BUILD_DIR.mkdir(exist_ok=True)


def run_cmd(cmd, cwd=None):
    print("RUN:", " ".join(cmd), "cwd=", cwd)
    subprocess.check_call(cmd, cwd=cwd)


def download_grammars(languages):
    try:
        grammars = _GRAMMARs if languages == "all" else {k: _GRAMMARs[k] for k in languages}
    except KeyError as e:
        raise ValueError(f"Invalid or unsupported language: {e}. Supported languages: {list(_GRAMMARs.keys())}")

    langs = []
    GRAMMAR_ROOT.mkdir(exist_ok=True)

    for lang, (url, dir_name, tag) in grammars.items():
        repo_dir = GRAMMAR_ROOT / dir_name
        if not repo_dir.exists():
            print(f"Cloning {lang} grammar from {url} -> {repo_dir}")
            Repo.clone_from(url, repo_dir)
        else:
            print(f"Grammar dir already exists: {repo_dir}")
            repo = Repo(repo_dir)
            # fetch tags
            try:
                repo.remotes.origin.fetch(tags=True)
            except Exception:
                pass
        repo = Repo(repo_dir)
        g = Git(str(repo_dir))
        print(f"Checking out {tag} for {lang}")
        g.checkout(tag)
        langs.append(repo_dir)

    # For each downloaded grammar, try to build with the provided Makefile
    built_libs = []
    for repo_dir in langs:
        print(f"Building grammar in {repo_dir}")
        # many grammars provide a Makefile that builds a shared library
        try:
            run_cmd(["make"], cwd=str(repo_dir))
        except subprocess.CalledProcessError as e:
            print(f"make failed in {repo_dir}: {e}. Trying fallback: run 'npm install' then 'npm run build' if present.")
            # try fallback: if package.json exists, try npm build steps (best-effort)
            pkg = repo_dir / "package.json"
            if pkg.exists():
                try:
                    run_cmd(["npm", "install"], cwd=str(repo_dir))
                    run_cmd(["npm", "run", "build"], cwd=str(repo_dir))
                except Exception:
                    print("npm build fallback failed; skipping build for", repo_dir)
        # search for produced shared lib
        candidates = list(repo_dir.glob("**/libtree-sitter-*.dylib")) + list(repo_dir.glob("**/libtree-sitter-*.so")) + list(repo_dir.glob("**/tree_sitter_*.so"))
        if candidates:
            lib = candidates[0]
            print("Found built library:", lib)
            # copy/rename to build/my-languages.so (single-file for simplicity)
            dest = BUILD_DIR / "my-languages.so"
            shutil.copyfile(lib, dest)
            built_libs.append(dest)
        else:
            print("No built library found for", repo_dir)

    if not built_libs:
        raise RuntimeError("No grammar shared libraries were built. Inspect build output.")

    print("Built grammar libraries:")
    for b in built_libs:
        print(" -", b)
    return built_libs


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: download_grammars.py <lang>|all")
        sys.exit(1)
    arg = sys.argv[1:]
    if arg == ["all"]:
        langs = "all"
    else:
        langs = arg
    download_grammars(langs)
