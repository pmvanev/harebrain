from terminal_bench.registry.client import RegistryClient

c = RegistryClient()
for name, ver in [("terminal-bench-core", "head"), ("terminal-bench-core", "0.1.1")]:
    try:
        d = c.get_dataset(name, ver)
        print(name, ver, "->",
              "url=", getattr(d, "github_url", None),
              "branch=", getattr(d, "branch", None),
              "path=", getattr(d, "dataset_path", None),
              "commit=", getattr(d, "commit_hash", None))
    except Exception as e:
        print(name, ver, "ERR", type(e).__name__, e)
