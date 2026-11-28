import pathlib, json, urllib.request, hashlib, zipfile, tomllib
out=pathlib.Path("qualification")
pins={}
for line in pathlib.Path("qa-dependencies/requirements.txt").read_text().splitlines():
    if "==" not in line: continue
    head,*hashes=line.split()
    n,v=head.split("=="); pins[n]=(v,{h.split(":")[-1] for h in hashes})
(out/"all-wheels").mkdir(exist_ok=True)
lock=tomllib.loads((out/"rpds-Cargo.lock").read_text())["package"]
expected={p["name"]:p["version"] for p in lock if p["name"]!="rpds-py"}
evidence=[]
for n,(v,hashes) in pins.items():
    with urllib.request.urlopen(f"https://pypi.org/pypi/{n}/{v}/json",timeout=30) as resp: data=json.load(resp)
    selected=[x for x in data["urls"] if x["digests"]["sha256"] in hashes]
    assert len(selected)==len(hashes) and {x["digests"]["sha256"] for x in selected}==hashes
    for f in selected:
        assert f["filename"].endswith(".whl") and not f["yanked"]
        assert f["url"].startswith("https://files.pythonhosted.org/")
        with urllib.request.urlopen(f["url"],timeout=60) as resp: raw=resp.read(10_000_000)
        assert hashlib.sha256(raw).hexdigest()==f["digests"]["sha256"]
        path=out/"all-wheels"/f["filename"];path.write_bytes(raw)
        row={"filename":path.name,"sha256":hashlib.sha256(raw).hexdigest(),"size":len(raw)}
        with zipfile.ZipFile(path) as z:
            assert z.testzip() is None
            if n=="rpds-py":
                sboms=[k for k in z.namelist() if k.endswith(".cyclonedx.json") and ".dist-info/sboms/" in k]
                assert len(sboms)==1
                sbom=json.loads(z.read(sboms[0]))
                components={c["name"]:c["version"] for c in sbom["components"] if c.get("purl","").startswith("pkg:cargo/")}
                assert components and all(expected.get(k)==v for k,v in components.items())
                assert components.get("pyo3")=="0.29.3" and components.get("archery")=="1.2.3"
                row["embedded_sbom_components"]=components
                native=[k for k in z.namelist() if k.endswith((".so",".pyd",".dylib"))]
                assert native
                row["native_sha256"]={k:hashlib.sha256(z.read(k)).hexdigest() for k in native}
        evidence.append(row)
        print(path.name,row["sha256"],flush=True)
(out/"all-wheel-evidence.json").write_text(json.dumps(evidence,indent=2))
assert len(evidence)==10
