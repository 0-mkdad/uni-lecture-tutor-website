import json, urllib.request, pathlib, datetime
URL="https://uni-lecture-tutor-mcp.uni-lecture-tutor-mcp.workers.dev/mcp"
headers={"Content-Type":"application/json","Accept":"application/json, text/event-stream"}
results=[]
def rpc(method,params=None,id=None):
    msg={"jsonrpc":"2.0","method":method}
    if params is not None:msg["params"]=params
    if id is not None:msg["id"]=id
    with urllib.request.urlopen(urllib.request.Request(URL,data=json.dumps(msg).encode(),headers=headers),timeout=30) as resp:
        session=resp.headers.get("Mcp-Session-Id")
        if session:headers["Mcp-Session-Id"]=session
        status=resp.status;ctype=resp.headers.get("Content-Type","")
        if id is None:return None
        if "text/event-stream" in ctype:
            for raw in resp:
                line=raw.decode().strip()
                if line.startswith("data:"):
                    obj=json.loads(line[5:].strip())
                    if obj.get("id")==id:break
            else:raise RuntimeError("No matching SSE response")
        else:obj=json.load(resp)
    assert obj.get("id")==id and "error" not in obj,(method,obj)
    return obj["result"]
init=rpc("initialize",{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"ULT-synthetic-release-check","version":"1.0"}},1)
headers["MCP-Protocol-Version"]=init["protocolVersion"]
rpc("notifications/initialized")
tools=rpc("tools/list",{},2)["tools"]
assert [t["name"] for t in tools]==["validate_lecture_coverage"]
tool=tools[0]
assert set(tool["inputSchema"]["properties"])=={"total_pages","covered_pages"}
cases=[(30,[]),(30,list(range(1,13))),(5,[1,3,5]),(5,[3,1,3,2]),(3,[3,1,2]),(32,[1]),(1,[1]),(10000,[1,10000])]
for i,(n,ps) in enumerate(cases,3):
    request={"total_pages":n,"covered_pages":ps};c=set(ps);wanted={"total_pages":n,"covered_pages":len(c),"remaining_pages":n-len(c),"progress_percent":((20000*len(c)+n)//(2*n))/100,"next_page":next((k for k in range(1,n+1) if k not in c),None)}
    response=rpc("tools/call",{"name":tool["name"],"arguments":request},i)
    assert not response.get("isError"),response
    actual=response.get("structuredContent")
    if actual is None:
        text=[x["text"] for x in response["content"] if x.get("type")=="text"]
        assert len(text)==1
        actual=json.loads(text[0])
    assert actual==wanted,(actual,wanted)
    results.append({"case":i-2,"request":request,"result":actual,"status":"PASS"})
    print("PASS",i-2,flush=True)
pathlib.Path("mcp-smoke.json").write_text(json.dumps({"utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"serverInfo":init["serverInfo"],"tool_schema":tool["inputSchema"],"results":results,"scope":"synthetic numeric arithmetic only; not ChatGPT host acceptance"},indent=2))
