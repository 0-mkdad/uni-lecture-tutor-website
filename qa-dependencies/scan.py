import json, urllib.request, datetime, pathlib, hashlib, tomllib, sys
from importlib.metadata import version
root=pathlib.Path("qa-dependencies")
out=pathlib.Path("qualification")
out.mkdir(exist_ok=True)
pins={line.split("==")[0]:line.split("==")[1].split()[0] for line in (root/"requirements.txt").read_text().splitlines() if "==" in line}
raw=urllib.request.urlopen("https://raw.githubusercontent.com/crate-py/rpds/fc7a1853152f23ee056c07fc97bb2a63557553ed/Cargo.lock",timeout=30).read()
assert hashlib.sha1(f"blob {len(raw)}\0".encode()+raw).hexdigest()=="825bf3fafa0320f018f64ba4a054223fe8fd994c"
(out/"rpds-Cargo.lock").write_bytes(raw)
crates=tomllib.loads(raw.decode())["package"]
queries=[{"package":{"ecosystem":"PyPI","name":n},"version":v} for n,v in pins.items()]+[{"package":{"ecosystem":"crates.io","name":p["name"]},"version":p["version"]} for p in crates if p["name"]!="rpds-py"]
results=[]
for q in queries:
    req=urllib.request.Request("https://api.osv.dev/v1/query",data=json.dumps(q).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=30) as resp:
        answer=json.load(resp)
    if not isinstance(answer,dict) or set(answer)-{"vulns"} or ("vulns" in answer and not isinstance(answer["vulns"],list)): raise RuntimeError(f"Unexpected OSV response: {answer}")
    results.append({"query":q,"response":answer})
    print(q, [v["id"] for v in answer.get("vulns",[])],flush=True)
(out/"osv.json").write_text(json.dumps({"utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"results":results},indent=2))
assert {n:version(n) for n in pins}==pins
if any(r["response"].get("vulns") for r in results): sys.exit(1)
